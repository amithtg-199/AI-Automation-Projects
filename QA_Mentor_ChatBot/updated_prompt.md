**Role**: You are a Sr. Architect, with 25+ years of experience in the Software Industry, Specialized in building Enterprise-grade AI-based applications.

**Working Directory**: D:\ai_3x_qa\git_hub_files\18072026

**Objective**: I want you to create a high-end QA Mentor UI Application which will have 2 phases.

**Phase-1: Advanced Hybrid RAG pipeline (Backend & AI Engine)**
Backend Architecture:
- Framework: Use **FastAPI** to expose high-performance, asynchronous REST endpoints for document ingestion, retrieval, and project management.
- Modular Design: Implement a modular architecture with distinct API routers (e.g., `/ingest`, `/chat`, `/projects`).
- Task Orchestration: Use background tasks or Celery to handle long-running ingestion processes asynchronously without blocking the API.

Ingestion:
- VectorDB: Qdrant
- Embedding Model: Mistral
- Sparse Indexing: BM25
- Advanced Document Parsing: Use `Unstructured.io` or `LlamaParse` for complex documents (PDFs, DOCX) to preserve tables, images, and formatting. 
- Document Chunking: Use **Semantic Chunking** or AST-based chunking for code repositories, and structural chunking for documents (avoiding basic RecursiveCharacterTextSplitter where possible to maintain context).
- Metadata: Add rich metadata to the documents as per the domain (project_name, version, document_type, document_name, author, timestamp).
- Document formats to be processed: DOCX, PDF, TXT, URLs, CSV, XLSX, Figma exports.
- Support ingesting multiple documents concurrently.
- Deduplication & Updates: Use **Chunk-level hashing** (MD5/SHA256). Save the hash value in a Redis cache/database. During a new ingestion of the same document, check the chunk hashes to only ingest new or modified chunks, and update the document's version metadata (e.g., v1 to v2).
- Project_name will be input by the user during ingestion. In the UI, the user can select the project name from a dropdown.
- Incorporate an Adaptive chunking strategy (chunking + overlapping) based on the document type and data to avoid data loss.
- Resiliency: If document size is huge and we receive a 429 error during parallel ingestion, add a failsafe mechanism that retries failed documents with exponential backoff. Log the error and document details.
- Error Handling: If ingestion fails due to any other error, add a failsafe mechanism with retries and exponential backoff. Log the error comprehensively.
- While ingesting, use the metadata to create a unique key for each document.
- Include a **Redis caching layer** for metadata and document hashes to avoid redundant database queries.
- Add Rate Limiting to avoid 429 errors.
- **Knowledge Graph (GraphRAG)**: Integrate Neo4j to build a highly sophisticated Knowledge Base from the input documents. Extract entities (e.g., Modules, Test Cases, Jira Epics, APIs) and relationships to map out exactly how code commits, test cases, and PRDs interlink.

Retrieval: 
- Should support Agentic Routing (Query Router): Analyze the user's query and dynamically route it to the appropriate index or datastore (e.g., Code index vs. Jira index).
- Should support hybrid search (Dense Vector + BM25 Sparse).
- Re-ranking: Implement Reciprocal Rank Fusion (RRF) followed by a **Cross-Encoder Re-ranker** to maximize precision. Use open-source/free models like **BGE-Reranker** (BAAI/bge-reranker-large) as the primary re-ranker for the project, keeping paid options like Cohere only as a configurable fallback.
- Adaptive Top-K retrieval based on query complexity.
- Use Mistral-large for retrieval synthesis.
- Incorporate a Query Expansion/HyDE strategy to improve retrieval accuracy for vague queries.
- Ensure a smooth fallback mechanism for failed retrievals. If data sent to the LLM is too large, save the chunk data in cache and send it in smaller batches to the LLM.
- Observability: Integrate telemetry (e.g., Langfuse or Arize Phoenix) to monitor token usage, retrieval latency, and hallucination metrics.

Input data sources for Ingestion (These input/src folders are to be created in the backend where the user will create a project_name directory and save the files under it):
- Selenium framework repo: https://github.com/PramodDutta/ATB13xSeleniumAdvanceFramework
- Playwright framework repo: https://github.com/PramodDutta/Advance-Playwright-Framework	
- Test cases (~5,000): CSV / XLSX (e.g., testdata.csv)
- JIRA tickets: Live via JIRA MCP connection + JQL
- Company docs: PDF, MD
- Figma designs: ER diagrams, user guides, wireframes (Figma exports)
- Meeting notes & recordings: Text transcripts
- Lucid charts: Exported to text
- PRD / SRS / BRD / FRD: PDF
- Jenkins logs & results: Log / text files

**Phase 2: Advanced UI Chatbot**
- Advanced UI Chatbot based on the RAG pipeline with an AI Engine. 
- Showcase all the ingested data (i.e., directory_name) in the UI.
- Add an ingestion cycle screen where the user can manually click to start ingestion.
- Tech Stack: Use Vite + React for the UI. It should be light and white-themed, with a beautiful and user-friendly UI/UX design compatible with desktop and mobile versions. Use Tailwind CSS for styling and smooth micro-animations.
- Maintain a clear nomenclature and structure. The UI must be very clean, user-friendly, and easy to navigate.
- Showcase user chat conversation history, tagged with project_name and version.
- Project details must be clearly visible in the UI.
- Showcase a projects list in the UI, displaying project_name and total versions ingested.
- Must have a clear, persistent Chat box where the user can input queries.
- Persona: Responses from the AI should be professional, acting like a senior mentor interacting with students.
- Formatting: Responses should be clear text with a user-friendly font size, proper formatting (bold, italic, underline, bullets, etc.), and line spacing to improve readability.
- Metadata Display: Showcase the response time taken for each query (do not show this directly in the Markdown output, display it as UI metadata).
- Code Snippets: Responses should provide short code snippets for code-related queries (e.g., if a user asks for pytest code, provide it in a formatted code block with proper indentation and syntax highlighting).
- Visuals: Responses can include visual diagrams if requested or as a summary for large retrieved content (e.g., histograms, knowledge maps, charts, tabular data).
- Access Control (RBAC): Ensure the chatbot respects Role-Based Access Control, only returning data the user is permitted to see.
- Settings/Config: The UI must include an environment configuration panel where we can set:
    - Qdrant URL
    - Mistral API key
    - Jira MCP details (URL, email ID, API key)
    - Confluence MCP details (URL, email ID, API key)
    - Github MCP details (URL, API key)
    - Figma MCP details (URL, API key)
    - Jenkins MCP details (URL, username, password)
    - Lucid MCP details (URL, API key)
    - Google Colab MCP details (URL, API key)
    - Google Cloud Storage MCP details (URL, API key)
- UI will be deployed on vercel which i will provide vercel key.


**Guardrails**
- Your answers must be confined to the provided knowledge base only.
- Never assume anything that is not in the knowledge base.
- If clarification is required from the user, actively ask for it.
- If you do not find relevant data, tell the user: "Sorry, details not found."
- Do not hallucinate data.
- If the user asks for code, always provide it in the proper format with appropriate comments and indentation.
- If the user asks for a diagram, always provide it in the proper format.
- If the user asks for data, always provide it in the proper format, utilizing tabular layouts where appropriate.
- If the user asks for data exceeding 100 lines, always summarize it in bullet points and tabular format, include a visual summary, and if it relates to test cases or code, provide inline comments in the code blocks.
