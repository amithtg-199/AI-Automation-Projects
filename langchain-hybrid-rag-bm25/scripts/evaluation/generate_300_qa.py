"""
Generate 300-500 evaluation Q&A pairs from ingested parent chunks in Postgres.
Uses all document types (pdf, docx, md, jpeg, etc.) including Jira.
Randomly samples chunks to ensure broad coverage across the entire document set.

Modes:
  auto   - LLM generates Q&A pairs automatically from random chunks
  manual - Interactive: shows random chunks, you type questions & answers yourself

Usage:
    uv run python -m scripts.evaluation.generate_300_qa <project_name> [--num-questions 300] [--mode auto]
    uv run python -m scripts.evaluation.generate_300_qa <project_name> --mode manual
"""

import argparse
import csv
import json
import logging
import os
import random
import sys
import time
import textwrap

from scripts.config import config
from scripts.database import PostgresDB

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def fetch_parent_chunks(project_name: str, exclude_jira: bool = True) -> list[dict]:
    """Fetch all parent chunks from documents (excluding Jira by default)."""
    db = PostgresDB()
    project_id = db.get_or_create_project(project_name)
    conn = db.get_connection()
    cur = conn.cursor()
    
    if exclude_jira:
        cur.execute("""
            SELECT p.content, d.file_name
            FROM parent_chunks p
            JOIN documents d ON p.document_id = d.document_id
            WHERE p.project_id = %s
              AND d.document_type != 'JIRA'
            ORDER BY p.parent_id
        """, (project_id,))
    else:
        cur.execute("""
            SELECT p.content, d.file_name
            FROM parent_chunks p
            JOIN documents d ON p.document_id = d.document_id
            WHERE p.project_id = %s
            ORDER BY p.parent_id
        """, (project_id,))
    
    rows = cur.fetchall()
    cur.close()
    db.close()
    chunks = [{"content": r[0], "file_name": r[1]} for r in rows]
    logger.info(f"Fetched {len(chunks)} parent chunks from Postgres (excluding Jira: {exclude_jira}).")
    return chunks


class RateLimitError(Exception):
    """Raised when LLM API returns 429 rate limit error."""
    pass


def generate_qa_from_chunk(llm, chunk_content: str, num_pairs: int = 3) -> list[dict]:
    """Use LLM to generate Q&A pairs from a single chunk.
    
    Raises:
        RateLimitError: If API returns 429 rate limit error
    """
    prompt = f"""You are a technical documentation expert for an enterprise software engineering project.

Given the following document chunk, generate exactly {num_pairs} high-quality question-answer pairs.

Rules:
1. Questions must be specific, technical, and answerable ONLY from the provided chunk content.
2. Answers must be factual, detailed, and directly grounded in the chunk text.
3. Do NOT invent information that is not in the chunk.
4. Cover different aspects of the chunk — do NOT ask similar questions.
5. Questions should test understanding of system design, processes, integrations, configurations, or business rules.
6. DO NOT reference any Jira ticket IDs.

Output ONLY a valid JSON array of objects with "question" and "ground_truth" keys.
Example:
[
  {{"question": "What happens during step X?", "ground_truth": "During step X, the system performs Y and Z."}},
  {{"question": "Which modules are involved in process A?", "ground_truth": "Process A involves modules B, C, and D."}}
]

Document Chunk:
---
{chunk_content[:3000]}
---

Generate exactly {num_pairs} Q&A pairs as JSON:"""

    messages = [{"role": "user", "content": prompt}]
    
    try:
        response = llm.invoke(messages)
        text = response.content if hasattr(response, 'content') else str(response)
        
        # Check for rate limit error in response
        if hasattr(response, 'response_metadata'):
            status = response.response_metadata.get('http_status', 0)
            if status == 429:
                raise RateLimitError("API rate limit exceeded (429)")
        
        # Extract JSON from response
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        
        pairs = json.loads(text)
        if isinstance(pairs, list):
            valid = []
            for p in pairs:
                if isinstance(p, dict) and "question" in p and "ground_truth" in p:
                    q = p["question"].strip()
                    a = p["ground_truth"].strip()
                    if len(q) > 20 and len(a) > 20:
                        valid.append({"question": q, "ground_truth": a})
            return valid
    except json.JSONDecodeError as e:
        logger.warning(f"JSON parse error: {e}")
    except RateLimitError:
        raise  # Re-raise for retry logic to handle
    except Exception as e:
        # Check if error message contains 429
        error_str = str(e).lower()
        if "429" in error_str or "rate limit" in error_str:
            raise RateLimitError(f"Rate limit detected: {e}")
        logger.warning(f"LLM error: {e}")
    
    return []


def get_llm():
    """Initialize the LLM from project config."""
    provider = config.LLM_PROVIDER.lower()
    
    if provider == "mistral":
        from langchain_mistralai import ChatMistralAI
        llm = ChatMistralAI(
            model=config.LLM_MODEL_NAME,
            api_key=config.LLM_API_KEY,
            max_retries=config.LLM_MAX_RETRIES,
            timeout=config.LLM_REQUEST_TIMEOUT,
            temperature=0.3,
        )
        logger.info(f"Using Mistral LLM: {config.LLM_MODEL_NAME}")
    elif provider == "ollama":
        from langchain_ollama import ChatOllama
        llm = ChatOllama(
            model=config.LLM_MODEL_NAME,
            base_url=config.OLLAMA_BASE_URL,
            temperature=0.3,
        )
        logger.info(f"Using Ollama LLM: {config.LLM_MODEL_NAME}")
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")
    
    return llm


def load_existing_pairs(output_file: str) -> list[dict]:
    """Load existing Q&A pairs from CSV for resume support."""
    if not os.path.exists(output_file):
        return []
    pairs = []
    with open(output_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if "question" in row and "ground_truth" in row:
                pairs.append({"question": row["question"], "ground_truth": row["ground_truth"]})
    logger.info(f"Loaded {len(pairs)} existing Q&A pairs from {output_file}")
    return pairs


def save_pairs_to_csv(pairs: list[dict], output_file: str):
    """Write Q&A pairs to CSV (overwrites)."""
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["question", "ground_truth"])
        writer.writeheader()
        writer.writerows(pairs)


def run_auto_mode(args, chunks: list[dict], output_file: str):
    """Automatic LLM-based Q&A generation from random chunks."""
    target = args.num_questions
    pairs_per = args.pairs_per_chunk
    max_retries_429 = 5
    initial_delay = args.delay
    
    # Resume: load existing pairs
    all_pairs = []
    if args.resume:
        all_pairs = load_existing_pairs(output_file)
        if len(all_pairs) >= target:
            logger.info(f"Already have {len(all_pairs)} pairs (target={target}). Nothing to do.")
            return
        logger.info(f"Resuming from {len(all_pairs)} existing pairs.")
    
    # Randomly shuffle chunks for diverse coverage
    random.seed(42)
    random.shuffle(chunks)
    
    # Calculate how many chunks we need to process
    remaining = target - len(all_pairs)
    chunks_needed = (remaining // pairs_per) + 10  # buffer for failures
    chunks_to_process = chunks[:min(chunks_needed, len(chunks))]
    logger.info(f"Will process {len(chunks_to_process)} randomly sampled chunks "
                f"(target: {target} questions, {pairs_per} per chunk, remaining: {remaining})")
    
    # Initialize LLM
    llm = get_llm()
    
    for i, chunk in enumerate(chunks_to_process, 1):
        if len(all_pairs) >= target:
            logger.info(f"Reached target of {target} questions. Stopping.")
            break
        
        logger.info(f"[{i}/{len(chunks_to_process)}] Generating from: {chunk['file_name'][:60]}... "
                     f"(collected: {len(all_pairs)}/{target})")
        
        # Retry loop for rate-limit (429) errors with exponential backoff
        retries = 0
        pairs = []
        while retries <= max_retries_429:
            try:
                pairs = generate_qa_from_chunk(llm, chunk["content"], pairs_per)
                if pairs:
                    break
                # If no pairs but no rate limit error, just retry
                retries += 1
                if retries <= max_retries_429:
                    wait = initial_delay * (2 ** retries)
                    logger.warning(f"  No pairs generated, retry {retries}/{max_retries_429}, waiting {wait:.1f}s...")
                    time.sleep(wait)
            except RateLimitError as e:
                retries += 1
                if retries <= max_retries_429:
                    # Exponential backoff: 2s, 4s, 8s, 16s, 32s
                    wait = initial_delay * (2 ** retries)
                    logger.warning(f"  Rate limit hit (429), retry {retries}/{max_retries_429}, waiting {wait:.1f}s...")
                    time.sleep(wait)
                else:
                    logger.error(f"  Max retries ({max_retries_429}) exceeded for rate limit. Skipping chunk.")
                    break
        
        if pairs:
            all_pairs.extend(pairs)
            logger.info(f"  -> Got {len(pairs)} pairs (total: {len(all_pairs)})")
        else:
            logger.warning(f"  -> No pairs generated from chunk {i} after retries")
        
        # Periodic save every 50 chunks to avoid data loss
        if i % 50 == 0:
            _save_deduplicated(all_pairs, target, output_file, interim=True)
        
        # Rate-limit delay between successful requests
        time.sleep(initial_delay)
    
    # Final save
    _save_deduplicated(all_pairs, target, output_file, interim=False)
    logger.info(f"Chunks processed: {min(i, len(chunks_to_process))}/{len(chunks_to_process)}")


def run_manual_mode(args, chunks: list[dict], output_file: str):
    """Interactive manual mode: shows random chunks, user types questions & answers."""
    target = args.num_questions
    max_retries_429 = 5
    
    # Load existing pairs for resume
    all_pairs = load_existing_pairs(output_file)
    if all_pairs:
        logger.info(f"Resuming manual mode with {len(all_pairs)} existing pairs.")
    
    # Randomly shuffle chunks
    random.seed(None)  # True random for manual mode
    random.shuffle(chunks)
    
    chunk_idx = 0
    print("\n" + "=" * 70)
    print(" MANUAL Q&A GENERATION MODE")
    print(f" Target: {target} pairs | Current: {len(all_pairs)} pairs")
    print(f" Total available chunks: {len(chunks)}")
    print("=" * 70)
    print("\nCommands:")
    print("  [Enter]     - Submit question & answer for this chunk")
    print("  'skip'      - Skip to next random chunk")
    print("  'done'      - Save and exit")
    print("  'status'    - Show current progress")
    print("  'bulk N'    - Generate N pairs from current chunk using LLM")
    print("=" * 70 + "\n")
    
    llm = None  # Lazy-init only if user wants bulk generation
    
    while len(all_pairs) < target and chunk_idx < len(chunks):
        chunk = chunks[chunk_idx]
        
        # Display chunk preview
        print(f"\n{'─' * 70}")
        print(f"CHUNK #{chunk_idx + 1} | Source: {chunk['file_name']}")
        print(f"{'─' * 70}")
        # Show first 1500 chars wrapped
        preview = chunk["content"][:1500]
        for line in preview.split("\n"):
            print(f"  {line}")
        if len(chunk["content"]) > 1500:
            print(f"  ... [{len(chunk['content']) - 1500} more chars]")
        print(f"{'─' * 70}")
        print(f"Progress: {len(all_pairs)}/{target} pairs")
        print()
        
        while True:
            cmd = input("Enter command (or type question): ").strip()
            
            if cmd.lower() == "skip":
                chunk_idx += 1
                break
            elif cmd.lower() == "done":
                _save_deduplicated(all_pairs, target, output_file, interim=False)
                print(f"\nSaved {len(all_pairs)} pairs to {output_file}")
                return
            elif cmd.lower() == "status":
                print(f"  Pairs collected: {len(all_pairs)}/{target}")
                print(f"  Chunks viewed: {chunk_idx + 1}/{len(chunks)}")
                continue
            elif cmd.lower().startswith("bulk"):
                # LLM-assisted bulk generation for current chunk
                parts = cmd.split()
                n = int(parts[1]) if len(parts) > 1 else 3
                if llm is None:
                    print("  Initializing LLM...")
                    llm = get_llm()
                print(f"  Generating {n} pairs from this chunk via LLM...")
                
                # Retry loop for rate limit
                retries = 0
                pairs = []
                while retries <= max_retries_429:
                    try:
                        pairs = generate_qa_from_chunk(llm, chunk["content"], n)
                        if pairs:
                            break
                        retries += 1
                        if retries <= max_retries_429:
                            wait = 2.0 * (2 ** retries)
                            print(f"  Retry {retries}/{max_retries_429}, waiting {wait:.1f}s...")
                            time.sleep(wait)
                    except RateLimitError as e:
                        retries += 1
                        if retries <= max_retries_429:
                            wait = 2.0 * (2 ** retries)
                            print(f"  Rate limit hit, retry {retries}/{max_retries_429}, waiting {wait:.1f}s...")
                            time.sleep(wait)
                        else:
                            print("  Max retries exceeded. Skipping.")
                            break
                
                if pairs:
                    # Show generated pairs for review
                    for pi, p in enumerate(pairs, 1):
                        print(f"\n  [{pi}] Q: {p['question']}")
                        print(f"      A: {p['ground_truth'][:200]}")
                    accept = input("\n  Accept all? (y/n/pick e.g. '1,3'): ").strip().lower()
                    if accept == "y":
                        all_pairs.extend(pairs)
                        print(f"  Added {len(pairs)} pairs. Total: {len(all_pairs)}")
                    elif accept == "n":
                        print("  Discarded.")
                    else:
                        # Pick specific indices
                        try:
                            indices = [int(x.strip()) - 1 for x in accept.split(",")]
                            selected = [pairs[idx] for idx in indices if 0 <= idx < len(pairs)]
                            all_pairs.extend(selected)
                            print(f"  Added {len(selected)} pairs. Total: {len(all_pairs)}")
                        except (ValueError, IndexError):
                            print("  Invalid selection. Discarded.")
                else:
                    print("  LLM failed to generate pairs for this chunk.")
                continue
            elif len(cmd) > 10:
                # User typed a question
                question = cmd
                ground_truth = input("Ground truth answer: ").strip()
                if len(ground_truth) > 10:
                    all_pairs.append({"question": question, "ground_truth": ground_truth})
                    print(f"  Added! Total: {len(all_pairs)}/{target}")
                    # Ask if user wants to add more for same chunk
                    more = input("  Add another for this chunk? (y/n): ").strip().lower()
                    if more != "y":
                        chunk_idx += 1
                        break
                else:
                    print("  Answer too short (min 10 chars). Try again.")
            else:
                print("  Question too short (min 10 chars). Type a question, 'skip', 'done', or 'bulk N'.")
        
        # Auto-save every 20 pairs
        if len(all_pairs) % 20 == 0 and len(all_pairs) > 0:
            _save_deduplicated(all_pairs, target, output_file, interim=True)
    
    # Final save
    _save_deduplicated(all_pairs, target, output_file, interim=False)
    print(f"\nDone! Saved {len(all_pairs)} pairs to {output_file}")


def _save_deduplicated(all_pairs: list[dict], target: int, output_file: str, interim: bool = False):
    """Deduplicate and save pairs to CSV."""
    seen = set()
    unique_pairs = []
    for p in all_pairs:
        q_key = p["question"].lower().strip()
        if q_key not in seen:
            seen.add(q_key)
            unique_pairs.append(p)
    
    final_pairs = unique_pairs[:target]
    save_pairs_to_csv(final_pairs, output_file)
    
    if interim:
        logger.info(f"  [auto-save] {len(final_pairs)} unique pairs saved to {output_file}")
    else:
        logger.info(f"\nGenerated {len(final_pairs)} Q&A pairs -> {output_file}")
        logger.info(f"Source: All document types (including Jira)")


def main():
    parser = argparse.ArgumentParser(description="Generate evaluation Q&A from ingested .docx chunks")
    parser.add_argument("project_name", nargs="?", default=config.DEFAULT_PROJECT_NAME, help="Project name (defaults to DEFAULT_PROJECT_NAME from config)")
    parser.add_argument("--mode", choices=["auto", "manual"], default="auto",
                        help="'auto' = LLM generates all; 'manual' = interactive mode")
    parser.add_argument("--num-questions", type=int, default=300, help="Target number of Q&A pairs (300-500)")
    parser.add_argument("--pairs-per-chunk", type=int, default=3, help="Q&A pairs to generate per chunk (auto mode)")
    parser.add_argument("--delay", type=float, default=2.0, help="Seconds between LLM calls (auto mode)")
    parser.add_argument("--resume", action="store_true", help="Resume from existing CSV instead of overwriting")
    args = parser.parse_args()
    
    # Fetch parent chunks (all document types including Jira)
    chunks = fetch_parent_chunks(args.project_name, exclude_jira=False)
    if not chunks:
        logger.error("No parent chunks found in Postgres. Run ingestion first.")
        sys.exit(1)
    
    # Output path
    output_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "eval_datasets", args.project_name
    )
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "questions_ground_truth.csv")
    
    if args.mode == "manual":
        run_manual_mode(args, chunks, output_file)
    else:
        run_auto_mode(args, chunks, output_file)


if __name__ == "__main__":
    main()
