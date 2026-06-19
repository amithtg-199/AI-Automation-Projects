import os
import json
import pandas as pd
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
EvaluationDataset = None
SingleTurnSample = None
LangchainLLMWrapper = None
LangchainEmbeddingsWrapper = None
RunConfig = None
RAGAS_V1 = False
simple = reasoning = multi_context = None

try:
    from ragas import evaluate
    from ragas.metrics import (
        faithfulness,
        answer_relevancy,
        context_precision,
        context_recall
    )

    # --- Version detection: v0.1 vs v0.2+ --------------------------------
    try:
        # Ragas < 0.2.0
        from ragas.testset.generator import TestsetGenerator
        from ragas.testset.evolutions import simple, reasoning, multi_context
        RAGAS_V1 = True
    except ImportError:
        # Ragas >= 0.2.0
        try:
            from ragas.testset import TestsetGenerator
        except ImportError:
            TestsetGenerator = None
        RAGAS_V1 = False

    # --- v0.2 native dataset classes --------------------------------------
    try:
        from ragas import EvaluationDataset, SingleTurnSample
    except ImportError:
        pass  # v0.1 — not available

    # --- LangChain wrappers (path varies by version) ----------------------
    try:
        from ragas.llms import LangchainLLMWrapper
    except ImportError:
        pass
    try:
        from ragas.embeddings import LangchainEmbeddingsWrapper
    except ImportError:
        pass

    # --- RunConfig (path varies by version) -------------------------------
    for _rc_path in ("ragas.run_config", "ragas.executor"):
        try:
            _mod = __import__(_rc_path, fromlist=["RunConfig"])
            RunConfig = getattr(_mod, "RunConfig", None)
            if RunConfig:
                break
        except ImportError:
            continue
except ImportError:
    evaluate = None  # ragas not installed

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
        self.llm = get_llm()
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

        try:
            eval_timeout = int(os.environ.get("EVAL_TIMEOUT", "600"))
            eval_max_retries = int(os.environ.get("EVAL_MAX_RETRIES", "20"))
            eval_max_wait = int(os.environ.get("EVAL_MAX_WAIT", "120"))
            run_config = RunConfig(
                max_workers=1,
                timeout=eval_timeout,
                max_retries=eval_max_retries,
                max_wait=eval_max_wait,
            ) if RunConfig else None
        except Exception:
            run_config = None

        # Build a list of evaluate() call strategies, from most-preferred to fallback.
        # v0.2 prefers metrics to carry their own LLM; we still pass llm/embeddings
        # as kwargs for v0.1 compat — v0.2 silently ignores unknown kwargs.
        call_strategies = [
            # 1. Wrapped LLM + embeddings (works on both v0.1 & v0.2)
            dict(dataset=dataset, metrics=metrics, llm=self.ragas_llm, embeddings=self.ragas_embeddings),
            # 2. Raw LangChain objects (v0.1 native)
            dict(dataset=dataset, metrics=metrics, llm=self.llm, embeddings=self.embeddings),
            # 3. No LLM/embeddings kwargs (v0.2 metrics use their own defaults)
            dict(dataset=dataset, metrics=metrics),
        ]

        for attempt, kw in enumerate(call_strategies, 1):
            try:
                if run_config:
                    kw["run_config"] = run_config
                result = evaluate(**kw)
                row = result.to_pandas().iloc[0].to_dict()
                return self._normalize_columns(row)
            except TypeError as te:
                logger.warning(f"Evaluate attempt {attempt} hit TypeError (RAGAS wrapper compat): {te}")
                continue
            except TimeoutError:
                logger.warning(f"Evaluate attempt {attempt} timed out. Consider raising EVAL_TIMEOUT (current: {os.environ.get('EVAL_TIMEOUT', '600')}s).")
                continue
            except Exception as e:
                logger.warning(f"Evaluate attempt {attempt} failed: {e}")
                continue

        logger.error("All evaluate strategies exhausted for this question.")
        return None

    def run_evaluation(self, testset_csv: str, output_csv: str = "ragas_evaluation_results.csv"):
        """
        Run the RAG pipeline against the questions in the testset, then use RAGAS to grade the results.
        Evaluates ONE question at a time with a configurable delay to avoid 429 rate limit errors.
        Set EVAL_DELAY_SECONDS env var to control the delay (default: 5 seconds).
        """
        import time

        if not os.path.exists(testset_csv):
            logger.error(f"Testset file {testset_csv} not found.")
            return None

        delay_seconds = int(os.environ.get("EVAL_DELAY_SECONDS", "5"))
        logger.info(f"Rate-limit delay between evaluations: {delay_seconds}s (set EVAL_DELAY_SECONDS to change)")

        df = pd.read_csv(testset_csv)

        questions = df["question"].tolist()
        ground_truths = df["ground_truth"].tolist() if "ground_truth" in df.columns else [""] * len(questions)

        answers = []
        contexts = []

        logger.info(f"Running retrieval pipeline for {len(questions)} questions...")
        for i, q in enumerate(questions):
            logger.info(f"  Retrieving [{i+1}/{len(questions)}]: {q[:80]}...")
            res = self.retrieval_pipeline.retrieve_and_answer(q, top_k=5)
            answers.append(res["answer"])

            # Ragas expects contexts as a list of strings
            ctxs = [c["content"] for c in res["citations"]]
            contexts.append(ctxs)

        metrics = [
            faithfulness,
            answer_relevancy,
            context_precision,
            context_recall
        ]

        # Evaluate one question at a time to avoid rate limits
        logger.info(f"Running RAGAS evaluation one-at-a-time for {len(questions)} questions...")
        all_results = []
        for i in range(len(questions)):
            logger.info(f"  Evaluating [{i+1}/{len(questions)}]: {questions[i][:80]}...")

            row_result = self._evaluate_single(
                question=questions[i],
                answer=answers[i],
                contexts_list=contexts[i],
                ground_truth=ground_truths[i],
                metrics=metrics,
            )

            if row_result:
                all_results.append(row_result)
                logger.info(f"  Result: F={row_result.get('faithfulness', 'N/A'):.2f}, "
                            f"AR={row_result.get('answer_relevancy', 'N/A'):.2f}, "
                            f"CP={row_result.get('context_precision', 'N/A'):.2f}, "
                            f"CR={row_result.get('context_recall', 'N/A'):.2f}")
            else:
                # Insert NaN row so we don't lose the question
                all_results.append({
                    "question": questions[i], "answer": answers[i],
                    "contexts": contexts[i], "ground_truth": ground_truths[i],
                    "faithfulness": None, "answer_relevancy": None,
                    "context_precision": None, "context_recall": None,
                })
                logger.warning(f"  Evaluation failed for question {i+1}. Recorded as NaN.")

            # Sleep between questions to avoid 429 rate limits
            if i < len(questions) - 1:
                logger.info(f"  Sleeping {delay_seconds}s before next evaluation...")
                time.sleep(delay_seconds)

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

        result_df.to_csv(output_csv, index=False)
        logger.info(f"RAGAS evaluation complete. Results saved to {output_csv}")
        return result_df

if __name__ == "__main__":
    # Example usage script
    evaluator = RagasEvaluator("VDRC_phase2")
    
    # 1. First, generate a dataset (uncomment to run)
    # evaluator.generate_synthetic_dataset(num_questions=5, output_file="testset.csv")
    
    # 2. Then evaluate your RAG pipeline
    # evaluator.run_evaluation(testset_csv="testset.csv", output_csv="ragas_results.csv")
