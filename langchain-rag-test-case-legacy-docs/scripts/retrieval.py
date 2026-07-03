import os
import csv
import glob
import io
import re
import time
from qdrant_client import QdrantClient
from langchain_core.prompts import PromptTemplate

from scripts.config import config
from scripts.database import PostgresDB
from scripts.logger import get_logger
from scripts.llm_factory import get_llm, get_embeddings
from scripts.rate_limiter import AdaptiveRateLimiter
from scripts.metrics import (
    GENERATION_DOCUMENTS_CREATED, 
    GENERATION_TOKENS_APPROX,
    LLM_PROMPT_TOKENS,
    LLM_COMPLETION_TOKENS,
    LLM_COST_USD
)
from langchain_community.callbacks import get_openai_callback

logger = get_logger(__name__)

class RetrievalPipeline:
    def __init__(self, project_name: str):
        self.project_name = project_name
        self.qdrant = QdrantClient(host=config.QDRANT_HOST, port=config.QDRANT_PORT)
        self.embeddings = get_embeddings()
        self.llm = get_llm()
        self.db = PostgresDB()
        
        self.root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.prompts_dir = os.path.join(self.root_dir, "prompts")
        self.output_dir = os.path.join(self.root_dir, "output_documents", self.project_name)

    def _get_latest_prompt_dir(self):
        if not os.path.exists(self.prompts_dir):
            os.makedirs(self.prompts_dir)
            return None
        
        versions = []
        for d in os.listdir(self.prompts_dir):
            if d.startswith("v") and d[1:].isdigit():
                versions.append(int(d[1:]))
                
        if not versions:
            return None
            
        max_v = max(versions)
        return os.path.join(self.prompts_dir, f"v{max_v}")
        
    def _get_next_output_dir(self):
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            
        versions = [0]
        for d in os.listdir(self.output_dir):
            if d.startswith("v") and d[1:].isdigit():
                versions.append(int(d[1:]))
                
        next_v = max(versions) + 1
        new_dir = os.path.join(self.output_dir, f"v{next_v}")
        os.makedirs(new_dir)
        return new_dir

    def retrieve_context(self, query: str, top_k: int = 15):
        """Retrieves raw context from Qdrant/Postgres without LLM generation."""
        query_vector = self.embeddings.embed_query(query)
        search_results = self.qdrant.query_points(
            collection_name=self.project_name,
            query=query_vector,
            limit=top_k * 2
        ).points
        
        parent_ids = set()
        context_blocks = []
        citations = []

        with self.db.conn.cursor() as cur:
            for hit in search_results:
                parent_id = hit.payload["parent_id"]
                if parent_id not in parent_ids:
                    parent_ids.add(parent_id)
                    cur.execute("""
                        SELECT pc.content, pc.section_name, d.file_name 
                        FROM parent_chunks pc
                        JOIN documents d ON pc.document_id = d.document_id
                        WHERE pc.parent_id = %s
                    """, (parent_id,))
                    row = cur.fetchone()
                    if row:
                        content, section_name, file_name = row
                        context_blocks.append(f"Source: {file_name} ({section_name})\n{content}")
                        citations.append({"file": file_name, "section": section_name, "content": content})
                    
                    if len(parent_ids) >= top_k:
                        break
        return "\n\n---\n\n".join(context_blocks), citations
        
    def _get_all_project_chunks(self):
        """Retrieves ALL context blocks for the project to ensure 100% test coverage."""
        context_blocks = []
        project_id = self.db.get_or_create_project(self.project_name)
        
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT pc.content, pc.section_name, d.file_name 
            FROM parent_chunks pc
            JOIN documents d ON pc.document_id = d.document_id
            WHERE pc.project_id = %s
            ORDER BY d.file_name, pc.parent_id
        """, (project_id,))
        rows = cur.fetchall()
        cur.close()
        
        for row in rows:
            content, section_name, file_name = row
            context_blocks.append(f"Source: {file_name} ({section_name})\n{content}")
            
        return context_blocks

    def retrieve_and_answer(self, query: str, top_k: int = 5):
        """Standard Q&A RAG."""
        logger.info(f"Retrieval query: '{query}' (top_k={top_k})")
        full_context, citations = self.retrieve_context(query, top_k)

        prompt = PromptTemplate.from_template(
            "You are a Senior QA Test Architect. Answer the following question based on the provided requirements context.\n\n"
            "Context:\n{context}\n\n"
            "Question: {query}\n\n"
            "Answer clearly and strictly based on the context. If the answer is not in the context, say so."
        )
        
        chain = prompt | self.llm
        
        with get_openai_callback() as cb:
            response = chain.invoke({"context": full_context, "query": query})
            
            LLM_PROMPT_TOKENS.labels(project_name=self.project_name, agent_name="qa_answering", model_name=config.LLM_PROVIDER).inc(cb.prompt_tokens)
            LLM_COMPLETION_TOKENS.labels(project_name=self.project_name, agent_name="qa_answering", model_name=config.LLM_PROVIDER).inc(cb.completion_tokens)
            LLM_COST_USD.labels(project_name=self.project_name, agent_name="qa_answering", model_name=config.LLM_PROVIDER).inc(cb.total_cost)

        logger.info(f"Generated answer with {len(citations)} citations. Tokens: {cb.total_tokens}, Cost: ${cb.total_cost:.5f}")

        return {
            "answer": response.content,
            "citations": citations
        }
        
    # ── Output cleaning helpers ──────────────────────────────────────────

    _CONTENT_BLOCK_RE = re.compile(
        r"=====START OF (.*?)=====\n?(.*?)\n?=====END OF \1=====", re.DOTALL
    )
    _MD_FENCE_RE = re.compile(r"```(?:csv|markdown|md|text)?\n?", re.IGNORECASE)

    def extract_content_block(self, text: str):
        """Extracts content between =====START OF filename===== and =====END OF filename====="""
        match = self._CONTENT_BLOCK_RE.search(text)
        if match:
            filename = match.group(1).strip()
            content = match.group(2).strip()
            return filename, content
        return None, text.strip()

    @staticmethod
    def _strip_markdown_fences(text: str) -> str:
        """Remove stray ```csv / ``` fences the LLM might wrap around output."""
        text = re.sub(r"```(?:csv|markdown|md|text)?\n?", "", text, flags=re.IGNORECASE)
        text = text.replace("```", "")
        return text.strip()

    @staticmethod
    def _deduplicate_csv_header(full_text: str) -> str:
        """
        When multiple batches are appended, the CSV header row gets repeated.
        Keep only the first occurrence, parsed in a CSV-aware manner to preserve multi-line fields.
        """
        try:
            reader = csv.reader(io.StringIO(full_text))
            rows = list(reader)
        except Exception:
            # Fallback to line splitting if it fails to parse
            lines = full_text.splitlines()
            if len(lines) < 2:
                return full_text
            header = lines[0].strip()
            seen_header = False
            deduped = []
            for line in lines:
                if line.strip() == header:
                    if not seen_header:
                        seen_header = True
                        deduped.append(line)
                else:
                    deduped.append(line)
            return "\n".join(deduped)

        if not rows:
            return full_text

        header = rows[0]
        seen_header = False
        deduped_rows = []
        for row in rows:
            # Check if row is a duplicate header
            if [x.strip() for x in row] == [x.strip() for x in header]:
                if not seen_header:
                    seen_header = True
                    deduped_rows.append(row)
            else:
                deduped_rows.append(row)

        out = io.StringIO()
        writer = csv.writer(out, quoting=csv.QUOTE_MINIMAL)
        writer.writerows(deduped_rows)
        return out.getvalue()

    def repair_csv_content(self, text: str, filename: str) -> str:
        """
        Parses CSV text, identifies rows with mismatched column count,
        and dynamically repairs them using anchor-based column alignment.
        """
        reader = csv.reader(io.StringIO(text))
        try:
            rows = list(reader)
        except Exception as e:
            logger.warning(f"Error parsing CSV reader in repair: {e}. Attempting basic quote repair.")
            clean_lines = []
            for line in text.splitlines():
                if line.count('"') % 2 != 0:
                    line += '"'
                clean_lines.append(line)
            try:
                reader = csv.reader(io.StringIO("\n".join(clean_lines)))
                rows = list(reader)
            except Exception:
                return text

        if not rows:
            return text

        headers = [h.strip() for h in rows[0]]
        expected_count = len(headers)
        
        repaired_rows = [rows[0]]
        has_repairs = False

        for idx, row in enumerate(rows[1:], start=2):
            if len(row) == expected_count:
                repaired_rows.append(row)
                continue
                
            has_repairs = True
            repaired_row = None
            row = [x.strip() for x in row]
            
            fn_lower = filename.lower()
            if "test_cases" in fn_lower:
                if len(row) > 15:
                    left = row[0:5]
                    right = row[-6:]
                    middle = row[5:-6]
                    
                    steps_idx = -1
                    for i, val in enumerate(middle):
                        val_clean = val.replace("\n", " ").strip()
                        if (val_clean.startswith("1.") or 
                            "2." in val_clean or 
                            val.count("\n") > 0 or
                            "step 1" in val_clean.lower() or
                            "verify" in val_clean.lower() and "click" in val_clean.lower()):
                            steps_idx = i
                            break
                    if steps_idx == -1:
                        steps_idx = max(range(len(middle)), key=lambda i: len(middle[i]))
                    
                    pre_cond = ", ".join(middle[0:steps_idx])
                    steps = middle[steps_idx]
                    remaining = middle[steps_idx+1:]
                    if len(remaining) >= 2:
                        exp_res = ", ".join(remaining[:-1])
                        act_res = remaining[-1]
                    elif len(remaining) == 1:
                        exp_res = remaining[0]
                        act_res = "N/A"
                    else:
                        exp_res = "N/A"
                        act_res = "N/A"
                    
                    repaired_row = left + [pre_cond, steps, exp_res, act_res] + right
                    
            elif "rtm" in fn_lower:
                if len(row) > 6:
                    req_id = row[0]
                    status = row[-2]
                    defect_id = row[-1]
                    
                    tcid_idx = -1
                    for i in range(2, len(row) - 2):
                        val = row[i].upper()
                        if val.startswith("TC_") or "TC" in val or "REQ" in val:
                            tcid_idx = i
                            break
                    if tcid_idx == -1:
                        tcid_idx = 2
                        
                    req_desc = ", ".join(row[1:tcid_idx])
                    tcid = row[tcid_idx]
                    tc_desc = ", ".join(row[tcid_idx+1:-2])
                    repaired_row = [req_id, req_desc, tcid, tc_desc, status, defect_id]
                    
            elif "automation_recommendations" in fn_lower:
                if len(row) > 6:
                    req_id = row[0]
                    right = row[-4:]
                    feature_desc = ", ".join(row[1:-4])
                    repaired_row = [req_id, feature_desc] + right
                    
            elif "risk_matrix" in fn_lower:
                if len(row) > 7:
                    risk_id = row[0]
                    risk_cat = row[1]
                    owner = row[-1]
                    
                    prob_idx = -1
                    for i in range(2, len(row) - 3):
                        val = row[i].lower()
                        if val in ["high", "medium", "low"]:
                            prob_idx = i
                            break
                    if prob_idx == -1:
                        prob_idx = 3
                    
                    risk_desc = ", ".join(row[2:prob_idx])
                    prob = row[prob_idx]
                    impact = row[prob_idx+1]
                    mitigation = ", ".join(row[prob_idx+2:-1])
                    repaired_row = [risk_id, risk_cat, risk_desc, prob, impact, mitigation, owner]
                    
            elif "test_data_matrix" in fn_lower:
                if len(row) > 7:
                    left = row[0:3]
                    req_id = row[-1]
                    middle = row[3:-1]
                    third = len(middle) // 3
                    valid = ", ".join(middle[0:third])
                    invalid = ", ".join(middle[third:2*third])
                    edge = ", ".join(middle[2*third:])
                    repaired_row = left + [valid, invalid, edge, req_id]
                    
            elif "estimation_report" in fn_lower:
                if len(row) > 6:
                    component = ", ".join(row[0:-5])
                    right = row[-5:]
                    repaired_row = [component] + right

            if repaired_row is None:
                if len(row) > expected_count:
                    repaired_row = row[:expected_count-1] + [", ".join(row[expected_count-1:])]
                else:
                    repaired_row = row + ["N/A"] * (expected_count - len(row))
                    
            repaired_rows.append(repaired_row)

        if not has_repairs:
            return text

        logger.info(f"Repaired CSV column count mismatches in {filename}")
        out = io.StringIO()
        writer = csv.writer(out, quoting=csv.QUOTE_MINIMAL)
        writer.writerows(repaired_rows)
        return out.getvalue()

    @staticmethod
    def _validate_csv_structure(text: str, expected_columns: int | None = None) -> tuple[bool, str]:
        """
        Quick validation: parse CSV, check column count consistency.
        Returns (is_valid, message).
        """
        try:
            reader = csv.reader(io.StringIO(text))
            rows = list(reader)
            if not rows:
                return False, "CSV is empty"
            header_cols = len(rows[0])
            bad_rows = []
            for idx, row in enumerate(rows[1:], start=2):
                if len(row) != header_cols:
                    bad_rows.append(idx)
            if expected_columns and header_cols != expected_columns:
                return False, f"Expected {expected_columns} columns, got {header_cols}"
            if bad_rows:
                return False, f"Rows with mismatched column count: {bad_rows[:10]}{'...' if len(bad_rows) > 10 else ''}"
            return True, f"Valid CSV: {len(rows)-1} data rows, {header_cols} columns"
        except csv.Error as e:
            return False, f"CSV parse error: {e}"

    def _post_process_file(self, file_path: str):
        """
        Post-process a generated file:
         - Strip any leftover markdown fences
         - For CSV files: deduplicate headers, repair alignments, validate structure
        """
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        content = self._strip_markdown_fences(content)
        is_csv = file_path.endswith(".csv")

        if is_csv:
            filename = os.path.basename(file_path)
            content = self._deduplicate_csv_header(content)
            content = self.repair_csv_content(content, filename)
            valid, msg = self._validate_csv_structure(content)
            if valid:
                logger.info(f"Post-process [{filename}]: {msg}")
            else:
                logger.warning(f"Post-process [{filename}]: CSV issue → {msg}")
        else:
            filename = os.path.basename(file_path)
            section_count = content.count("\n# ") + content.count("\n## ")
            logger.info(f"Post-process [{filename}]: {len(content)} chars, ~{section_count} sections")

        for attempt in range(3):
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content + "\n")
                break
            except PermissionError:
                if attempt < 2:
                    time.sleep(1)
                else:
                    fallback_path = file_path + ".repaired"
                    logger.error(f"Permission denied to write {file_path}. Writing to {fallback_path}")
                    try:
                        with open(fallback_path, "w", encoding="utf-8") as f:
                            f.write(content + "\n")
                    except Exception as e:
                        logger.error(f"Failed to write to fallback path {fallback_path}: {e}")

    def _get_compact_csv(self, file_path: str) -> str:
        """
        Reads a CSV file generated in Phase 1 and returns a compact CSV string
        keeping only the columns needed for downstream Phase 2 contexts.
        Does NOT modify the file on disk.
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            reader = csv.reader(io.StringIO(content))
            rows = list(reader)
            if not rows:
                return ""
            header = [h.strip() for h in rows[0]]
            # Essential columns to keep for Phase 2 contexts
            target_cols = [
                "Scenario", "TID", "Requirement ID", "Priority", 
                "Severity", "Automation Candidate", "Recommended Framework"
            ]
            indices = []
            new_header = []
            for col in target_cols:
                for idx, h in enumerate(header):
                    if h.lower() == col.lower():
                        indices.append(idx)
                        new_header.append(h)
                        break
            if not indices:
                # If target columns are not found, fallback to first 80k characters
                return content[:80000]

            out_io = io.StringIO()
            writer = csv.writer(out_io)
            writer.writerow(new_header)
            for row in rows[1:]:
                if len(row) > max(indices):
                    writer.writerow([row[idx] for idx in indices])
            return out_io.getvalue()
        except Exception as e:
            logger.error(f"Error compacting CSV for context: {e}")
            return ""

    def _get_compact_markdown(self, file_path: str) -> str:
        """
        Reads an appended markdown test plan file from Phase 1 and returns a
        deduplicated in-memory string keeping only the unique/relevant sections
        to avoid redundant boilerplate context in Phase 2.
        Does NOT modify the file on disk.
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Split into batches by level 1 headers (e.g., '# **Master Test Plan')
            batches = re.split(r'\n(?=# \*\*Master Test Plan|# Master Test Plan|# \*\*)', content)
            if len(batches) <= 1:
                # Fallback to general level 1 header split if not found
                batches = re.split(r'\n(?=# )', content)

            if len(batches) <= 1:
                return content[:80000]

            compacted_parts = []
            # Keep the entire first batch (this has the structure and template boilerplate)
            compacted_parts.append(batches[0].strip())

            # For subsequent batches, only keep Section 2 (Scope) and Section 7 (Assumptions/Open Questions)
            for batch in batches[1:]:
                lines = batch.splitlines()
                keep_lines = []
                is_keeping = False

                if lines and lines[0].strip().startswith("#"):
                    keep_lines.append(lines[0])

                for line in lines[1:]:
                    # Start keeping when we encounter Section 2 (Scope) or Section 7 (Assumptions & Open Questions)
                    if re.search(r'^##\s+\*?\*?\s*(2\.|7\.)', line):
                        is_keeping = True
                        keep_lines.append(line)
                    # Stop keeping when we hit any other main numbered section (e.g. 3., 8., etc.)
                    elif re.search(r'^##\s+\*?\*?\s*\d+\.', line):
                        is_keeping = False
                    elif is_keeping:
                        keep_lines.append(line)

                if len(keep_lines) > 1:
                    compacted_parts.append("\n".join(keep_lines).strip())

            return "\n\n---\n\n".join(compacted_parts)
        except Exception as e:
            logger.error(f"Error compacting Markdown for context: {e}")
            return content[:80000]

    def _get_expected_filename_from_prompt(self, prompt_file: str) -> str:
        base_name = os.path.basename(prompt_file)
        try:
            with open(prompt_file, "r", encoding="utf-8") as f:
                content = f.read()
            # Look for =====START OF filename=====
            match = re.search(r"=====START OF\s+(.*?)\s*=====", content)
            if match:
                return match.group(1).strip()
        except Exception as e:
            logger.error(f"Error parsing prompt file for filename: {e}")
        
        name_without_ext = os.path.splitext(base_name)[0]
        return f"{self.project_name}_{name_without_ext}.md"

    def _get_latest_output_dir(self) -> tuple[str | None, int]:
        if not os.path.exists(self.output_dir):
            return None, 0
            
        versions = []
        for d in os.listdir(self.output_dir):
            if d.startswith("v") and d[1:].isdigit():
                versions.append(int(d[1:]))
                
        if not versions:
            return None, 0
            
        max_v = max(versions)
        return os.path.join(self.output_dir, f"v{max_v}"), max_v

    # ── Core generation engine ──────────────────────────────────────────

    def _determine_output_filename(self, prompt_name: str, target_filename: str | None) -> str:
        """
        Decide the output file name.  Priority:
          1. filename extracted from the LLM's =====START OF filename===== block
          2. infer from the prompt's own =====START OF===== declaration
          3. fallback: {project}_{prompt_stem}.md
        """
        if target_filename:
            return target_filename
        name_without_ext = os.path.splitext(prompt_name)[0]
        return f"{self.project_name}_{name_without_ext}.md"

    def _invoke_llm(self, chain, input_vars: dict, label: str, phase: str):
        """
        Invoke chain through the adaptive rate limiter, record Prometheus metrics,
        and return the raw AIMessage.
        """
        with get_openai_callback() as cb:
            response = self._rate_limiter.invoke(chain, input_vars, label=label)

            LLM_PROMPT_TOKENS.labels(
                project_name=self.project_name, agent_name=f"{phase}_generation",
                model_name=config.LLM_PROVIDER
            ).inc(cb.prompt_tokens)
            LLM_COMPLETION_TOKENS.labels(
                project_name=self.project_name, agent_name=f"{phase}_generation",
                model_name=config.LLM_PROVIDER
            ).inc(cb.completion_tokens)
            LLM_COST_USD.labels(
                project_name=self.project_name, agent_name=f"{phase}_generation",
                model_name=config.LLM_PROVIDER
            ).inc(cb.total_cost)

        return response

    def _generate_batched_document(
        self, prompt_file: str, batches: list, out_dir: str,
        phase_label: str, extra_context: str = ""
    ) -> str | None:
        """
        Generate a single document from a prompt template across multiple batches.
        Returns the final output file path, or None on total failure.
        """
        base_name = os.path.basename(prompt_file)
        name_without_ext = os.path.splitext(base_name)[0]
        total_batches = len(batches)

        with open(prompt_file, "r", encoding="utf-8") as f:
            prompt_text = f.read()

        logger.info(f"{phase_label}: Generating '{base_name}' ({total_batches} batches)")
        doc_start = time.time()

        out_file_name = f"{self.project_name}_{name_without_ext}.md"
        out_file_path = os.path.join(out_dir, out_file_name)
        csv_header_written = False

        for i, batch in enumerate(batches):
            batch_num = i + 1
            progress_pct = int(batch_num / total_batches * 100)
            logger.info(f"  Batch {batch_num}/{total_batches} ({progress_pct}%) for {base_name}...")
            batch_start = time.time()

            context_str = "\n\n---\n\n".join(batch)
            if extra_context:
                context_str = extra_context + "\n\n---\n\n" + context_str

            if "{context}" in prompt_text:
                template = prompt_text
            else:
                template = prompt_text + "\n\n### Project Context (Batch {batch_number} of {total_batches}):\n{context}"

            prompt = PromptTemplate.from_template(template)
            chain = prompt | self.llm

            try:
                input_vars = {"context": context_str}
                if "{batch_number}" in template:
                    input_vars["batch_number"] = batch_num
                if "{total_batches}" in template:
                    input_vars["total_batches"] = total_batches

                label = f"{phase_label}/{base_name} batch {batch_num}/{total_batches}"
                response = self._invoke_llm(chain, input_vars, label=label, phase=phase_label)

                target_filename, clean_content = self.extract_content_block(response.content)
                clean_content = self._strip_markdown_fences(clean_content)

                if target_filename and batch_num == 1:
                    out_file_name = target_filename
                    out_file_path = os.path.join(out_dir, out_file_name)

                is_csv = out_file_path.endswith(".csv")
                if is_csv and batch_num > 1:
                    lines = clean_content.splitlines()
                    if lines and csv_header_written:
                        header_candidate = lines[0].strip()
                        if any(kw in header_candidate.lower() for kw in ["scenario", "requirement", "risk", "tid", "test case"]):
                            lines = lines[1:]
                    clean_content = "\n".join(lines)
                elif is_csv and batch_num == 1:
                    csv_header_written = True

                char_count = len(clean_content)
                row_count = clean_content.count("\n")
                batch_elapsed = time.time() - batch_start
                if is_csv:
                    logger.info(f"  → {char_count} chars, {row_count} rows in {batch_elapsed:.1f}s")
                else:
                    logger.info(f"  → {char_count} chars in {batch_elapsed:.1f}s")

                GENERATION_DOCUMENTS_CREATED.labels(project_name=self.project_name, document_type=base_name).inc()
                GENERATION_TOKENS_APPROX.labels(project_name=self.project_name, document_type=base_name).observe(char_count // 4)

                mode = "a" if batch_num > 1 else "w"
                with open(out_file_path, mode, encoding="utf-8") as out_f:
                    out_f.write(clean_content + "\n")

            except Exception as e:
                logger.error(f"  ✗ Failed batch {batch_num} for {base_name}: {e}")

        if os.path.exists(out_file_path):
            self._post_process_file(out_file_path)

        doc_elapsed = time.time() - doc_start
        logger.info(f"{phase_label} complete: {out_file_name} in {doc_elapsed:.1f}s")
        return out_file_path

    def generate_test_documents(self):
        """
        Two-phase chained generation:
          Phase 1: test_plan + test_cases → both from raw ingested data (parallel)
          Phase 2: 6 downstream docs     → from test_plan + test_cases output
        """
        generation_start = time.time()
        self._rate_limiter = AdaptiveRateLimiter()

        prompt_dir = self._get_latest_prompt_dir()
        if not prompt_dir:
            logger.error("No prompt version directories found in prompts/ (e.g. prompts/v1). Please create one.")
            return

        prompt_files = glob.glob(os.path.join(prompt_dir, "*.txt")) + glob.glob(os.path.join(prompt_dir, "*.md"))
        if not prompt_files:
            logger.error(f"No prompt files (.txt or .md) found in {prompt_dir}")
            return

        # Check if we can resume in the latest version directory
        latest_dir, latest_v = self._get_latest_output_dir()
        resume_mode = False
        out_dir = None

        if latest_dir:
            # Check if Phase 1 files exist
            p1_files_exist = True
            for name in ["test_cases.csv", "test_plan.md"]:
                possible_paths = [
                    os.path.join(latest_dir, name),
                    os.path.join(latest_dir, f"{self.project_name}_{name}"),
                ]
                if not any(os.path.exists(p) for p in possible_paths):
                    p1_files_exist = False
                    break

            if p1_files_exist:
                resume_mode = True
                out_dir = latest_dir
                logger.info(f"Detected existing Phase 1 files in latest directory {out_dir}. Enabling Resume Mode.")

        if not out_dir:
            # Create a new version directory
            versions = [0]
            if os.path.exists(self.output_dir):
                for d in os.listdir(self.output_dir):
                    if d.startswith("v") and d[1:].isdigit():
                        versions.append(int(d[1:]))
            next_v = max(versions) + 1
            out_dir = os.path.join(self.output_dir, f"v{next_v}")
            os.makedirs(out_dir, exist_ok=True)
            logger.info(f"Starting new generation run in {out_dir}")

        logger.info(f"Generating test documents in {out_dir} using prompts from {prompt_dir}")

        # Classify prompts by phase
        phase1_names = ["test_plan.md", "test_cases.md", "test_plan.txt", "test_cases.txt"]
        phase1_prompts = [p for p in prompt_files if os.path.basename(p) in phase1_names]
        phase2_prompts = [p for p in prompt_files if os.path.basename(p) not in phase1_names]

        generated_files = []
        phase1_outputs = []

        if resume_mode:
            logger.info("Resuming from existing Phase 1 files. Skipping Phase 1 generation.")
            # Find and collect existing Phase 1 files
            for name in ["test_cases.csv", "test_plan.md"]:
                for filename in [name, f"{self.project_name}_{name}"]:
                    p = os.path.join(out_dir, filename)
                    if os.path.exists(p):
                        phase1_outputs.append(p)
                        generated_files.append(p)
                        break
        else:
            all_blocks = self._get_all_project_chunks()
            if not all_blocks:
                logger.warning(f"No documents found for project {self.project_name}. Please ingest data first.")
                return

            batch_size = config.GENERATION_BATCH_SIZE
            batches = [all_blocks[i:i + batch_size] for i in range(0, len(all_blocks), batch_size)]
            total_batches = len(batches)
            logger.info(f"Total parent chunks: {len(all_blocks)}. Batch size: {batch_size}. Batches: {total_batches}.")

            # ── PHASE 1: Test Plan + Test Cases (interleaved, single pass through chunks) ──
            logger.info("=" * 60)
            logger.info("PHASE 1: Core Generation from Raw Ingested Data")
            logger.info("=" * 60)

            # Prepare per-prompt state for interleaved batch processing
            phase1_state = []
            for p_file in phase1_prompts:
                base_name = os.path.basename(p_file)
                name_without_ext = os.path.splitext(base_name)[0]
                with open(p_file, "r", encoding="utf-8") as f:
                    prompt_text = f.read()
                phase1_state.append({
                    "prompt_file": p_file,
                    "base_name": base_name,
                    "prompt_text": prompt_text,
                    "out_file_name": f"{self.project_name}_{name_without_ext}.md",
                    "out_file_path": os.path.join(out_dir, f"{self.project_name}_{name_without_ext}.md"),
                    "csv_header_written": False,
                    "doc_start": time.time(),
                })

            logger.info(f"Interleaved generation: {len(phase1_state)} prompts × {total_batches} batches = {len(phase1_state) * total_batches} LLM calls")

            for i, batch in enumerate(batches):
                batch_num = i + 1
                progress_pct = int(batch_num / total_batches * 100)
                context_str = "\n\n---\n\n".join(batch)

                for st in phase1_state:
                    logger.info(f"  Batch {batch_num}/{total_batches} ({progress_pct}%) for {st['base_name']}...")
                    batch_start = time.time()

                    if "{context}" in st["prompt_text"]:
                        template = st["prompt_text"]
                    else:
                        template = st["prompt_text"] + "\n\n### Project Context (Batch {batch_number} of {total_batches}):\n{context}"

                    prompt = PromptTemplate.from_template(template)
                    chain = prompt | self.llm

                    try:
                        input_vars = {"context": context_str}
                        if "{batch_number}" in template:
                            input_vars["batch_number"] = batch_num
                        if "{total_batches}" in template:
                            input_vars["total_batches"] = total_batches

                        label = f"phase1/{st['base_name']} batch {batch_num}/{total_batches}"
                        response = self._invoke_llm(chain, input_vars, label=label, phase="phase1")

                        target_filename, clean_content = self.extract_content_block(response.content)
                        clean_content = self._strip_markdown_fences(clean_content)

                        if target_filename and batch_num == 1:
                            st["out_file_name"] = target_filename
                            st["out_file_path"] = os.path.join(out_dir, target_filename)

                        is_csv = st["out_file_path"].endswith(".csv")
                        if is_csv and batch_num > 1:
                            lines = clean_content.splitlines()
                            if lines and st["csv_header_written"]:
                                header_candidate = lines[0].strip()
                                if any(kw in header_candidate.lower() for kw in ["scenario", "requirement", "risk", "tid", "test case"]):
                                    lines = lines[1:]
                            clean_content = "\n".join(lines)
                        elif is_csv and batch_num == 1:
                            st["csv_header_written"] = True

                        char_count = len(clean_content)
                        row_count = clean_content.count("\n")
                        batch_elapsed = time.time() - batch_start
                        if is_csv:
                            logger.info(f"  → {char_count} chars, {row_count} rows in {batch_elapsed:.1f}s")
                        else:
                            logger.info(f"  → {char_count} chars in {batch_elapsed:.1f}s")

                        GENERATION_DOCUMENTS_CREATED.labels(project_name=self.project_name, document_type=st["base_name"]).inc()
                        GENERATION_TOKENS_APPROX.labels(project_name=self.project_name, document_type=st["base_name"]).observe(char_count // 4)

                        mode = "a" if batch_num > 1 else "w"
                        with open(st["out_file_path"], mode, encoding="utf-8") as out_f:
                            out_f.write(clean_content + "\n")

                    except Exception as e:
                        logger.error(f"  ✗ Failed batch {batch_num} for {st['base_name']}: {e}")

            # Post-process and collect Phase 1 outputs
            for st in phase1_state:
                if os.path.exists(st["out_file_path"]):
                    self._post_process_file(st["out_file_path"])
                    doc_elapsed = time.time() - st["doc_start"]
                    logger.info(f"Phase 1 complete: {st['out_file_name']} in {doc_elapsed:.1f}s")
                    phase1_outputs.append(st["out_file_path"])
                    generated_files.append(st["out_file_path"])

        # ── PHASE 2: Chained Generation from Phase 1 Artifacts ──
        logger.info("=" * 60)
        logger.info("PHASE 2: Chained Generation from Phase 1 Artifacts")
        logger.info("=" * 60)

        chained_context = ""
        for p1_file in phase1_outputs:
            if os.path.exists(p1_file):
                if p1_file.endswith(".csv"):
                    compact_content = self._get_compact_csv(p1_file)
                    logger.info(f"Compacted CSV {os.path.basename(p1_file)} from {os.path.getsize(p1_file)} bytes to {len(compact_content)} chars for Phase 2 context")
                    chained_context += f"\n\n--- Source: {os.path.basename(p1_file)} (Compacted) ---\n" + compact_content
                elif p1_file.endswith(".md"):
                    compact_content = self._get_compact_markdown(p1_file)
                    logger.info(f"Compacted Markdown {os.path.basename(p1_file)} from {os.path.getsize(p1_file)} bytes to {len(compact_content)} chars for Phase 2 context")
                    chained_context += f"\n\n--- Source: {os.path.basename(p1_file)} (Compacted) ---\n" + compact_content
                else:
                    with open(p1_file, "r", encoding="utf-8") as f:
                        chained_context += f"\n\n--- Source: {os.path.basename(p1_file)} ---\n" + f.read()

        if not chained_context.strip():
            logger.warning("Phase 1 context is empty. Skipping Phase 2.")
            return

        for idx, p_file in enumerate(phase2_prompts, 1):
            base_name = os.path.basename(p_file)
            name_without_ext = os.path.splitext(base_name)[0]

            expected_out_name = self._get_expected_filename_from_prompt(p_file)
            out_file_path = os.path.join(out_dir, expected_out_name)

            if resume_mode and os.path.exists(out_file_path):
                logger.info(f"Phase 2 [{idx}/{len(phase2_prompts)}]: '{expected_out_name}' already exists. Skipping.")
                if out_file_path not in generated_files:
                    generated_files.append(out_file_path)
                continue

            with open(p_file, "r", encoding="utf-8") as f:
                prompt_text = f.read()

            logger.info(f"Phase 2 [{idx}/{len(phase2_prompts)}]: Generating '{base_name}'")
            doc_start = time.time()

            if "{context}" in prompt_text:
                template = prompt_text
            else:
                template = prompt_text + "\n\n### Generated Project Context:\n{context}"

            prompt = PromptTemplate.from_template(template)
            chain = prompt | self.llm

            try:
                label = f"phase2/{base_name}"
                response = self._invoke_llm(
                    chain,
                    {"context": chained_context, "batch_number": 1, "total_batches": 1},
                    label=label, phase="phase2"
                )

                target_filename, clean_content = self.extract_content_block(response.content)
                clean_content = self._strip_markdown_fences(clean_content)

                out_file_name = self._determine_output_filename(base_name, target_filename)
                out_file_path = os.path.join(out_dir, out_file_name)

                char_count = len(clean_content)
                is_csv = out_file_path.endswith(".csv")
                row_count = clean_content.count("\n") if is_csv else 0
                doc_elapsed = time.time() - doc_start
                if is_csv:
                    logger.info(f"  → {char_count} chars, {row_count} rows in {doc_elapsed:.1f}s")
                else:
                    logger.info(f"  → {char_count} chars in {doc_elapsed:.1f}s")

                GENERATION_DOCUMENTS_CREATED.labels(project_name=self.project_name, document_type=base_name).inc()
                GENERATION_TOKENS_APPROX.labels(project_name=self.project_name, document_type=base_name).observe(char_count // 4)

                with open(out_file_path, "w", encoding="utf-8") as out_f:
                    out_f.write(clean_content + "\n")

                self._post_process_file(out_file_path)

                logger.info(f"Phase 2 complete: {out_file_name} in {doc_elapsed:.1f}s")
                generated_files.append(out_file_path)
            except Exception as e:
                logger.error(f"  ✗ Failed Phase 2 artifact {base_name}: {e}")

        # ── Generation Summary ──
        total_elapsed = time.time() - generation_start
        logger.info("=" * 60)
        logger.info("GENERATION SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Project     : {self.project_name}")
        logger.info(f"Output dir  : {out_dir}")
        logger.info(f"Total time  : {total_elapsed:.1f}s")
        logger.info(f"Files created: {len(generated_files)}")
        for fpath in generated_files:
            size = os.path.getsize(fpath) if os.path.exists(fpath) else 0
            logger.info(f"  • {os.path.basename(fpath)} ({size:,} bytes)")
        logger.info("=" * 60)


if __name__ == "__main__":
    # Example usage
    pipeline = RetrievalPipeline("VDRC_phase2")
    pipeline.generate_test_documents()
