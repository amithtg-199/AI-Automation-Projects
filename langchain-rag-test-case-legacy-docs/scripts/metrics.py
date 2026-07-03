from prometheus_client import Counter, Histogram, Gauge

# --- Ingestion Metrics ---
INGESTION_DOCUMENTS_PROCESSED = Counter(
    "rag_ingestion_documents_processed_total",
    "Total number of documents processed during ingestion",
    ["project_name", "doc_type"]
)
INGESTION_BYTES_EXTRACTED = Counter(
    "rag_ingestion_bytes_extracted_total",
    "Total bytes extracted by Docling/Unstructured",
    ["project_name"]
)
INGESTION_PARENT_CHUNKS = Counter(
    "rag_ingestion_parent_chunks_total",
    "Total parent chunks stored in Postgres",
    ["project_name"]
)
INGESTION_CHILD_CHUNKS = Counter(
    "rag_ingestion_child_chunks_total",
    "Total child chunks stored in Qdrant",
    ["project_name"]
)

# --- Generation Metrics ---
GENERATION_DOCUMENTS_CREATED = Counter(
    "rag_generation_documents_created_total",
    "Total test documents generated (Test Plan, Test Cases, etc)",
    ["project_name", "document_type"]
)
GENERATION_TOKENS_APPROX = Histogram(
    "rag_generation_tokens_approx",
    "Approximate tokens generated based on character count",
    ["project_name", "document_type"],
    buckets=[1000, 5000, 10000, 50000, 100000, float("inf")]
)

# --- LLM Utilization Metrics ---
LLM_PROMPT_TOKENS = Counter(
    "rag_llm_prompt_tokens_total",
    "Total prompt tokens sent to the LLM",
    ["project_name", "agent_name", "model_name"]
)
LLM_COMPLETION_TOKENS = Counter(
    "rag_llm_completion_tokens_total",
    "Total completion tokens received from the LLM",
    ["project_name", "agent_name", "model_name"]
)
LLM_COST_USD = Counter(
    "rag_llm_cost_usd_total",
    "Total estimated LLM cost in USD",
    ["project_name", "agent_name", "model_name"]
)

# --- Evaluation Metrics ---
EVALUATION_QUESTIONS_GENERATED = Counter(
    "rag_evaluation_questions_generated_total",
    "Total synthetic questions generated for evaluation",
    ["project_name"]
)
EVALUATION_FAITHFULNESS = Gauge(
    "rag_evaluation_faithfulness_score",
    "Average Ragas Faithfulness score",
    ["project_name"]
)
EVALUATION_ANSWER_RELEVANCY = Gauge(
    "rag_evaluation_answer_relevancy_score",
    "Average Ragas Answer Relevancy score",
    ["project_name"]
)
EVALUATION_CONTEXT_PRECISION = Gauge(
    "rag_evaluation_context_precision_score",
    "Average Ragas Context Precision score",
    ["project_name"]
)
EVALUATION_CONTEXT_RECALL = Gauge(
    "rag_evaluation_context_recall_score",
    "Average Ragas Context Recall score",
    ["project_name"]
)
