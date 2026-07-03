import os
import json
import pandas as pd
import time
from datasets import Dataset

from scripts.config import config
from scripts.database import PostgresDB
from scripts.retrieval import RetrievalPipeline
from scripts.logger import get_logger
from scripts.llm_factory import get_llm, get_embeddings
from scripts.metrics import EVALUATION_QUESTIONS_GENERATED, EVALUATION_FAITHFULNESS, EVALUATION_ANSWER_RELEVANCY, EVALUATION_CONTEXT_PRECISION, EVALUATION_CONTEXT_RECALL
from langchain_core.documents import Document


# ── Ragas imports (version-agnostic) ─────────────────────────────────────────
# All ragas imports are wrapped so the app starts even if ragas is absent.
evaluate = None
faithfulness = None
answer_relevancy = None
context_precision = None
context_recall = None
TestsetGenerator = None
EvaluationDataset = None
SingleTurnSample = None
LangchainLLMWrapper = None
LangchainEmbeddingsWrapper = None
RunConfig = None
RAGAS_V1 = False
simple = reasoning = multi_context = None

import logging
_init_log = logging.getLogger("ragas_init")

# Compatibility shim: Ragas checks langchain_community.chat_models for VertexAI on import.
# In langchain-community >= 0.2, vertexai is removed/deprecated, which crashes Ragas imports.
import sys, types
try:
    if "langchain_community.chat_models.vertexai" not in sys.modules:
        _dummy_vx = types.ModuleType("langchain_community.chat_models.vertexai")
        _dummy_vx.ChatVertexAI = type("ChatVertexAI", (), {})
        _dummy_vx.VertexAI = type("VertexAI", (), {})
        sys.modules["langchain_community.chat_models.vertexai"] = _dummy_vx
        import langchain_community.chat_models
        setattr(langchain_community.chat_models, "VertexAI", _dummy_vx.VertexAI)
        setattr(langchain_community.chat_models, "ChatVertexAI", _dummy_vx.ChatVertexAI)
except Exception:
    pass

try:
    from ragas import evaluate
except Exception as _e:
    _init_log.warning(f"Failed to import evaluate from ragas: {_e}")

try:
    from ragas.metrics import (
        faithfulness,
        answer_relevancy,
        context_precision,
        context_recall
    )
except Exception as _e1:
    _init_log.info(f"Direct metric import failed ({_e1}), trying class instantiation...")
    try:
        from ragas.metrics import Faithfulness, AnswerRelevancy, ContextPrecision, ContextRecall
        faithfulness = Faithfulness()
        answer_relevancy = AnswerRelevancy()
        context_precision = ContextPrecision()
        context_recall = ContextRecall()
    except Exception as _e2:
        _init_log.warning(f"Failed to instantiate Ragas metric classes: {_e2}")

# --- Version detection: v0.1 vs v0.2+ --------------------------------
try:
    # Ragas < 0.2.0
    from ragas.testset.generator import TestsetGenerator
    from ragas.testset.evolutions import simple, reasoning, multi_context
    RAGAS_V1 = True
except Exception:
    # Ragas >= 0.2.0
    try:
        from ragas.testset import TestsetGenerator
    except Exception:
        TestsetGenerator = None
    RAGAS_V1 = False

# --- v0.2 native dataset classes --------------------------------------
try:
    from ragas import EvaluationDataset, SingleTurnSample
except Exception:
    pass  # v0.1 — not available

# --- LangChain wrappers (path varies by version) ----------------------
try:
    from ragas.llms import LangchainLLMWrapper
except Exception:
    pass
try:
    from ragas.embeddings import LangchainEmbeddingsWrapper
except Exception:
    pass

# --- RunConfig (path varies by version) -------------------------------
for _rc_path in ("ragas.run_config", "ragas.executor"):
    try:
        _mod = __import__(_rc_path, fromlist=["RunConfig"])
        RunConfig = getattr(_mod, "RunConfig", None)
        if RunConfig:
            break
    except Exception:
        continue

# v0.2 renames dataset columns; keep a map so our CSV output stays consistent
_V2_COL_MAP = {
    "user_input": "question",
    "response": "answer",
    "retrieved_contexts": "contexts",
    "reference": "ground_truth",
}

logger = get_logger(__name__)

class RagasEvaluator:
    def __init__(self, project_name: str):
        self.project_name = project_name
        self.retrieval_pipeline = RetrievalPipeline(project_name)
        self.db = PostgresDB()
        
        # Configure LLM and Embedding Judge for RAGAS
        self.llm = get_llm(for_eval=True)
        self.embeddings = get_embeddings()
        
        try:
            self.ragas_llm = LangchainLLMWrapper(self.llm) if LangchainLLMWrapper else self.llm
            self.ragas_embeddings = LangchainEmbeddingsWrapper(self.embeddings) if LangchainEmbeddingsWrapper else self.embeddings
        except Exception:
            self.ragas_llm = self.llm
            self.ragas_embeddings = self.embeddings

    def generate_synthetic_dataset(self, num_questions: int = 20, output_file: str = "synthetic_testset.csv"):
        """
        Generate a synthetic test dataset (questions + ground truths) from the parent chunks in Postgres.
        """
        logger.info(f"Fetching chunks from Postgres for project {self.project_name}...")
        project_id = self.db.get_or_create_project(self.project_name)
        
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT p.content, d.document_type, d.file_name 
            FROM parent_chunks p
            JOIN documents d ON p.document_id = d.document_id
            WHERE p.project_id = %s
            LIMIT 200
        """, (project_id,))
        rows = cur.fetchall()
        cur.close()
        
        documents = []
        for row in rows:
            documents.append(Document(
                page_content=row[0],
                metadata={"doc_type": row[1], "file_name": row[2]}
            ))
            
        if not documents:
            logger.error("No documents found in Postgres. Cannot generate dataset.")
            return None
            
        logger.info(f"Loaded {len(documents)} parent chunks. Generating {num_questions} questions... This may take a while as the LLM generates the data.")
        
        if RAGAS_V1:
            # Ragas < 0.2.0 API
            generator = getattr(TestsetGenerator, "from_langchain", TestsetGenerator)(
                generator_llm=self.llm,
                critic_llm=self.llm,
                embeddings=self.embeddings
            )
            
            testset = generator.generate_with_langchain_docs(
                documents,
                test_size=num_questions,
                distributions={simple: 0.5, reasoning: 0.25, multi_context: 0.25}
            )
        else:
            # Ragas >= 0.2.0 API — try multiple constructor signatures
            generator = None
            for factory_kwargs in [
                dict(llm=self.ragas_llm, embedding_model=self.ragas_embeddings),
                dict(llm=self.llm, embedding_model=self.embeddings),
            ]:
                try:
                    factory = getattr(TestsetGenerator, "from_langchain", None)
                    generator = factory(**factory_kwargs) if factory else TestsetGenerator(**factory_kwargs)
                    break
                except Exception as e:
                    logger.debug(f"TestsetGenerator init attempt failed: {e}")
                    continue
            if generator is None:
                logger.error("Could not initialise TestsetGenerator with any known signature.")
                return None

            testset = generator.generate_with_langchain_docs(
                documents,
                testset_size=num_questions
            )
        
        df = testset.to_pandas()
        # Normalise v0.2 column names so the CSV always has 'question' + 'ground_truth'
        df.rename(columns=_V2_COL_MAP, inplace=True)
        df.to_csv(output_file, index=False)
        logger.info(f"Synthetic dataset saved to {output_file}")
        EVALUATION_QUESTIONS_GENERATED.labels(project_name=self.project_name).inc(num_questions)
        return df
        
    # ── helpers ──────────────────────────────────────────────────────────────
    def _get_run_config(self, max_workers: int = None):
        """Build Ragas RunConfig throttled to max_workers to prevent API rate limits (429)."""
        try:
            eval_timeout = int(os.environ.get("EVAL_TIMEOUT", "180"))
            eval_max_retries = int(os.environ.get("EVAL_MAX_RETRIES", "10"))
            eval_max_wait = int(os.environ.get("EVAL_MAX_WAIT", "60"))
            workers = max_workers if max_workers is not None else int(os.environ.get("EVAL_MAX_WORKERS", "2"))
            if RunConfig:
                return RunConfig(
                    max_workers=workers,
                    timeout=eval_timeout,
                    max_retries=eval_max_retries,
                    max_wait=eval_max_wait,
                )
        except Exception:
            pass
        return None

    @staticmethod
    def _normalize_columns(row_dict: dict) -> dict:
        """Map v0.2 column names back to v0.1 names for consistent CSV output."""
        return {_V2_COL_MAP.get(k, k): v for k, v in row_dict.items()}

    def _build_dataset(self, question, answer, contexts_list, ground_truth):
        """
        Build the evaluation dataset in whichever format the installed ragas accepts.
        Returns (dataset, format_tag) where format_tag is 'v2' or 'v1'.
        """
        # Try v0.2 EvaluationDataset first
        if EvaluationDataset and SingleTurnSample:
            try:
                sample = SingleTurnSample(
                    user_input=question,
                    response=answer,
                    retrieved_contexts=contexts_list,
                    reference=ground_truth,
                )
                return EvaluationDataset(samples=[sample]), "v2"
            except Exception as e:
                logger.debug(f"EvaluationDataset build failed, falling back to HF Dataset: {e}")

        # Fallback: HuggingFace Dataset (v0.1 style, still accepted in v0.2)
        data = {
            "question": [question],
            "answer": [answer],
            "contexts": [contexts_list],
            "ground_truth": [ground_truth],
        }
        return Dataset.from_dict(data), "v1"

    def _get_fresh_eval_models(self):
        llm = get_llm(for_eval=True)
        emb = get_embeddings()
        try:
            r_llm = LangchainLLMWrapper(llm) if LangchainLLMWrapper else llm
            r_emb = LangchainEmbeddingsWrapper(emb) if LangchainEmbeddingsWrapper else emb
        except Exception:
            r_llm = llm
            r_emb = emb
        return llm, emb, r_llm, r_emb

    def _evaluate_single(self, question, answer, contexts_list, ground_truth, metrics):
        """
        Evaluate a single question through RAGAS.
        Returns a dict of metric scores, or None on failure.

        RunConfig is tuned for slow / rate-limited LLM APIs:
          - timeout:     EVAL_TIMEOUT       env var (default 600s = 10 min per question)
          - max_retries: EVAL_MAX_RETRIES   env var (default 20)
          - max_wait:    EVAL_MAX_WAIT      env var (default 120s back-off ceiling)
          - max_workers: always 1 to serialise LLM calls and avoid 429s
        """
        dataset, fmt = self._build_dataset(question, answer, contexts_list, ground_truth)
        logger.debug(f"Evaluation dataset format: {fmt}")

        run_config = self._get_run_config(max_workers=1)
        tl_llm, tl_emb, tl_ragas_llm, tl_ragas_emb = self._get_fresh_eval_models()

        for m in metrics:
            if hasattr(m, "llm"):
                try: m.llm = tl_ragas_llm
                except Exception: pass
            if hasattr(m, "embeddings"):
                try: m.embeddings = tl_ragas_emb
                except Exception: pass

        # Build a list of evaluate() call strategies, from most-preferred to fallback.
        # v0.2 prefers metrics to carry their own LLM; we still pass llm/embeddings
        # as kwargs for v0.1 compat — v0.2 silently ignores unknown kwargs.
        call_strategies = [
            # 1. Wrapped LLM + embeddings (works on both v0.1 & v0.2)
            dict(dataset=dataset, metrics=metrics, llm=tl_ragas_llm, embeddings=tl_ragas_emb),
            # 2. Raw LangChain objects (v0.1 native)
            dict(dataset=dataset, metrics=metrics, llm=tl_llm, embeddings=tl_emb),
            # 3. No LLM/embeddings kwargs (v0.2 metrics use their own defaults)
            dict(dataset=dataset, metrics=metrics),
        ]

        for attempt, kw in enumerate(call_strategies, 1):
            for retry in range(3):
                try:
                    if run_config:
                        kw["run_config"] = run_config
                    result = evaluate(**kw)
                    row = result.to_pandas().iloc[0].to_dict()
                    has_nan = any(pd.isna(val) for key, val in row.items() if key in ["faithfulness", "answer_relevancy", "context_precision", "context_recall"])
                    if has_nan and retry < 2:
                        sleep_t = (retry + 1) * 4.0
                        logger.warning(f"Evaluate strategy {attempt} returned NaN (API rate limit/timeout). Pausing {sleep_t}s before retry ({retry+1}/2)...")
                        time.sleep(sleep_t)
                        continue
                    return self._normalize_columns(row)
                except TypeError as te:
                    logger.warning(f"Evaluate strategy {attempt} hit TypeError (RAGAS wrapper compat): {te}")
                    break
                except Exception as e:
                    err_str = str(e).lower()
                    if retry < 2 and ("timeout" in err_str or "429" in err_str or "rate limit" in err_str):
                        sleep_t = (retry + 1) * 5.0
                        logger.warning(f"Evaluate strategy {attempt} hit temporary error ({e}). Retrying in {sleep_t}s ({retry+1}/2)...")
                        time.sleep(sleep_t)
                    else:
                        logger.warning(f"Evaluate strategy {attempt} failed after {retry+1} attempt(s): {e}")
                        break

        logger.error("All evaluate strategies and retries exhausted for this question.")
        return None

    def close(self):
        try:
            self.retrieval_pipeline.close()
            self.db.close()
        except Exception:
            pass

    def run_evaluation(self, testset_csv: str, output_csv: str = "ragas_evaluation_results.csv"):
        """
        Run the RAG pipeline against the questions in the testset, then use RAGAS to grade the results.
        Evaluates in batches of config.EVAL_BATCH_SIZE (default 5). If a 429 rate limit occurs,
        falls back to 1 question at a time with config.EVAL_DELAY_SECONDS delay.
        """
        import time

        if not os.path.exists(testset_csv):
            logger.error(f"Testset file {testset_csv} not found.")
            return None

        batch_size = config.EVAL_BATCH_SIZE
        delay_seconds = config.EVAL_DELAY_SECONDS
        logger.info(f"Adaptive Evaluation: Batch size={batch_size}, Fallback delay={delay_seconds}s")

        df = pd.read_csv(testset_csv)

        questions = df["question"].tolist()
        ground_truths = df["ground_truth"].tolist() if "ground_truth" in df.columns else [""] * len(questions)

        cache_file = os.path.join(os.path.dirname(output_csv), f"retrieval_cache_{self.project_name}.json")
        fallback_cache = os.path.join("/app/logs" if os.path.exists("/app/logs") else "logs", f"retrieval_cache_{self.project_name}.json")
        if not os.path.exists(cache_file) and os.path.exists(fallback_cache):
            cache_file = fallback_cache

        cached_results = {}
        if os.path.exists(cache_file):
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    cached_results = json.load(f)
                logger.info(f"Loaded {len(cached_results)} cached retrieval results from {cache_file}")
            except Exception as e:
                logger.warning(f"Could not load retrieval cache: {e}")

        import threading
        import concurrent.futures

        _tl_retrieval = threading.local()
        cache_lock = threading.Lock()

        def _fetch_single_answer(idx, q):
            q_key = q.strip()
            with cache_lock:
                if q_key in cached_results:
                    logger.info(f"  Using cached answer [{idx+1}/{len(questions)}]: {q[:60]}...")
                    return idx, cached_results[q_key]

            if not hasattr(_tl_retrieval, "pipeline"):
                from scripts.retrieval.pipeline import RetrievalPipeline
                _tl_retrieval.pipeline = RetrievalPipeline(project_name=self.project_name)

            logger.info(f"  Retrieving [{idx+1}/{len(questions)}]: {q[:80]}...")
            retries = 0
            max_retries = 6
            res = None
            while retries <= max_retries:
                try:
                    res = _tl_retrieval.pipeline.retrieve_and_answer(q, top_k=5)
                    break
                except Exception as e:
                    err_str = str(e).lower()
                    if "429" in err_str or "rate limit" in err_str or "too many requests" in err_str:
                        retries += 1
                        if retries <= max_retries:
                            wait_time = max(float(delay_seconds), 4.0) * (2 ** retries)
                            logger.warning(f"  [429 Rate Limit] Retry {retries}/{max_retries} for query {idx+1}. Waiting {wait_time:.1f}s...")
                            time.sleep(wait_time)
                        else:
                            logger.error(f"  Exceeded max retries for query {idx+1}. Using fallback empty response.")
                            res = {"answer": "Error: Rate limit exceeded during retrieval.", "citations": []}
                            break
                    else:
                        logger.warning(f"  Retrieval error for query {idx+1}: {e}")
                        res = {"answer": f"Error: {e}", "citations": []}
                        break

            with cache_lock:
                cached_results[q_key] = res
                if len(cached_results) % 5 == 0 or len(cached_results) == len(questions):
                    try:
                        with open(cache_file, "w", encoding="utf-8") as f:
                            json.dump(cached_results, f, indent=2, ensure_ascii=False)
                    except Exception as e:
                        logger.warning(f"Failed to write interim retrieval cache: {e}")

            time.sleep(float(delay_seconds))
            return idx, res

        logger.info(f"Running multi-threaded Phase 1 retrieval for {len(questions)} questions (workers={config.EVAL_MAX_WORKERS}, delay={delay_seconds}s)...")
        results_map = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=config.EVAL_MAX_WORKERS) as executor:
            future_to_idx = {executor.submit(_fetch_single_answer, i, q): i for i, q in enumerate(questions)}
            for future in concurrent.futures.as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    res_idx, res = future.result()
                    results_map[res_idx] = res
                except Exception as exc:
                    logger.error(f"Query {idx+1} generated an exception: {exc}")
                    results_map[idx] = {"answer": f"Error: {exc}", "citations": []}

        answers = []
        contexts = []
        for i in range(len(questions)):
            res = results_map.get(i, {"answer": "", "citations": []})
            answers.append(res.get("answer", ""))
            ctxs = [c["content"] for c in res.get("citations", [])]
            contexts.append(ctxs)

        metrics = [m for m in [faithfulness, answer_relevancy, context_precision, context_recall] if m is not None]
        for m in metrics:
            if hasattr(m, "llm"):
                try: m.llm = self.ragas_llm
                except Exception: pass
            if hasattr(m, "embeddings"):
                try: m.embeddings = self.ragas_embeddings
                except Exception: pass

        if not metrics or evaluate is None:
            logger.error(f"Ragas evaluation library or metric objects failed to import properly (evaluate loaded: {evaluate is not None}, loaded metrics count: {len(metrics)}).")
            return

        from concurrent.futures import ThreadPoolExecutor, as_completed
        workers = int(os.environ.get("EVAL_MAX_WORKERS", "2"))
        logger.info(f"Running streaming RAGAS evaluation across {len(questions)} items ({workers} parallel worker threads)...")
        
        all_results = [None] * len(questions)
        
        def _eval_item_worker(q_idx):
            q_text = questions[q_idx]
            a_text = answers[q_idx]
            c_text = contexts[q_idx]
            g_text = ground_truths[q_idx]
            logger.info(f" -> Starting Eval [{q_idx+1}/{len(questions)}]: {q_text[:50]}...")
            row_res = self._evaluate_single(q_text, a_text, c_text, g_text, metrics)
            if row_res:
                f_score = row_res.get('faithfulness')
                r_score = row_res.get('answer_relevancy')
                p_score = row_res.get('context_precision')
                c_score = row_res.get('context_recall')
                f_str = f"{f_score:.2f}" if isinstance(f_score, (int, float)) else "N/A"
                r_str = f"{r_score:.2f}" if isinstance(r_score, (int, float)) else "N/A"
                p_str = f"{p_score:.2f}" if isinstance(p_score, (int, float)) else "N/A"
                c_str = f"{c_score:.2f}" if isinstance(c_score, (int, float)) else "N/A"
                logger.info(f" ✓ Finished Eval [{q_idx+1}/{len(questions)}] | Faith: {f_str} | Rel: {r_str} | Prec: {p_str} | Rec: {c_str}")
                try:
                    self.db.insert_evaluation_feedback(
                        project_name=self.project_name,
                        question=row_res.get("question", ""),
                        answer=row_res.get("answer", ""),
                        contexts=row_res.get("contexts", []),
                        ground_truth=row_res.get("ground_truth", ""),
                        faithfulness=float(row_res.get("faithfulness") or 0.0),
                        answer_relevancy=float(row_res.get("answer_relevancy") or 0.0),
                        context_precision=float(row_res.get("context_precision") or 0.0),
                        context_recall=float(row_res.get("context_recall") or 0.0)
                    )
                except Exception as db_e:
                    logger.warning(f"Failed inserting feedback for [{q_idx+1}]: {db_e}")
                return q_idx, row_res
            else:
                logger.warning(f" ✗ Failed Eval [{q_idx+1}/{len(questions)}]")
                return q_idx, {
                    "question": q_text, "answer": a_text,
                    "contexts": c_text, "ground_truth": g_text,
                    "faithfulness": None, "answer_relevancy": None,
                    "context_precision": None, "context_recall": None,
                }

        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_map = {executor.submit(_eval_item_worker, i): i for i in range(len(questions))}
            for future in as_completed(future_map):
                idx, res_row = future.result()
                all_results[idx] = res_row

        result_df = pd.DataFrame(all_results)

        # Log basic metrics summary
        metric_gauge_map = {
            "faithfulness": EVALUATION_FAITHFULNESS,
            "answer_relevancy": EVALUATION_ANSWER_RELEVANCY,
            "context_precision": EVALUATION_CONTEXT_PRECISION,
            "context_recall": EVALUATION_CONTEXT_RECALL,
        }
        logger.info(f"Evaluation metrics summary for {len(questions)} questions:")
        for metric, gauge in metric_gauge_map.items():
            if metric in result_df.columns:
                avg_score = result_df[metric].mean(skipna=True)
                if pd.notna(avg_score):
                    logger.info(f"  - {metric.capitalize()}: {avg_score:.2f}")
                    gauge.labels(project_name=self.project_name).set(avg_score)
                else:
                    logger.warning(f"  - {metric.capitalize()}: NaN (all evaluations failed or ground_truth missing). Skipping Prometheus export.")

        import csv
        ordered_cols = ["question", "contexts", "answer", "ground_truth", "faithfulness", "answer_relevancy", "context_precision", "context_recall"]
        for col in ordered_cols:
            if col not in result_df.columns:
                result_df[col] = None
        result_df = result_df[ordered_cols]

        def _clean_field(val):
            if isinstance(val, list):
                return "\n\n---\n\n".join([str(x).strip() for x in val])
            return val

        for col in ["question", "contexts", "answer", "ground_truth"]:
            if col in result_df.columns:
                result_df[col] = result_df[col].apply(_clean_field)

        result_df.to_csv(output_csv, index=False, quoting=csv.QUOTE_ALL, encoding="utf-8-sig")
        logger.info(f"RAGAS evaluation complete. Results saved to {output_csv}")
        logger.info("------------------------------------------------------------")
        logger.info("Eval Optimization Loop Engineering Status:")
        logger.info(f"[Eval Optimization Loop Engineering] RAGAS benchmark evaluation complete. Scores saved to {output_csv}.")
        logger.info(f"[Action Required] Review benchmark scores in {output_csv}.")
        logger.info(f"[Next Step] If evaluation scores indicate gaps or test artifacts require refinement, trigger webhook call /webhook/human-review (or action='review') for human review acceptance logs.")
        logger.info("============================================================")
        return result_df

if __name__ == "__main__":
    import sys
    import os
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if PROJECT_ROOT not in sys.path:
        sys.path.append(PROJECT_ROOT)
    from scripts.logger import setup_action_logger
    from scripts.config import config
    project_name = sys.argv[1] if len(sys.argv) > 1 else config.DEFAULT_PROJECT_NAME
    setup_action_logger("evals", clear_old=True)
    evaluator = RagasEvaluator(project_name)
    
    eval_folder_file = os.path.join(PROJECT_ROOT, "eval_datasets", project_name, "questions_ground_truth.csv")
    results_file = os.path.join(PROJECT_ROOT, "logs", f"ragas_results_{project_name}.csv")
    
    if os.path.exists(eval_folder_file):
        logger.info(f"Using dedicated RAGAS eval dataset: {eval_folder_file}")
        evaluator.run_evaluation(testset_csv=eval_folder_file, output_csv=results_file)
    else:
        logger.info("Generating synthetic dataset...")
        evaluator.generate_synthetic_dataset(num_questions=5, output_file="testset.csv")
        evaluator.run_evaluation(testset_csv="testset.csv", output_csv=results_file)
