# STLC Agentic Platform - User Guide & Setup

Welcome to the STLC Agentic Platform! Now that your backend and frontend are running, this guide will walk you through exactly how to ingest data, trigger agents, and utilize the RAG-powered workflow to automate your testing lifecycle.

---

## 1. Data Ingestion (Feeding the RAG)
Before the AI can generate accurate tests for your specific application without hallucinating, it needs context. We must ingest data into the Qdrant (Vector) and Neo4j (Graph) databases.

### Step 1: Prepare your Context Files
Gather your historical testing artifacts. The agents accept the following file types:
- **`.json` / `.yaml`:** Swagger/OpenAPI specifications (Crucial for API test generation).
- **`.md` / `.txt`:** Product requirement documents, user stories, or internal testing guidelines.
- **`.html` / `.xml`:** Historical test execution logs or DOM snapshots.

### Step 2: Upload via the UI
1. Navigate to **Knowledge Hub** in the left sidebar of the UI (`http://localhost:5173/knowledge`).
2. Select a project from the dropdown in the top header.
3. Use the file input in the **Knowledge Hub** page to choose your `.json`, `.yaml`, or `.md` files.
4. Click **Run Ingestion Cycle** to trigger the backend Celery tasks that process the files into Qdrant and Neo4j.
5. **Behind the Scenes:** The `RAG Ingestion Agent` chunks the documents, generates embeddings via the LLM, and maps the relationships in Neo4j.

*Alternatively via API:*
You can `POST /api/knowledge-hub/upload` with `multipart/form-data` containing your files, followed by `POST /api/knowledge-hub/ingest`.

---

## 2. Generating Test Suites
Once the system has context, you can instruct the Test Case Generator Agent to build automation scripts.

### Step 1: Submit a Prompt
1. Navigate to **Chatbot** (`http://localhost:5173/chat`).
2. In the central chat prompt, describe what you want to test or ask questions about your knowledge base.
   - *Example:* "Generate a Playwright UI test that verifies the login flow using the invalid credentials provided in the PRD."
   - *Example:* "Create a Pytest suite for the /api/v1/checkout endpoint covering 400 and 200 status codes."

### Step 2: The Agentic Workflow
1. The **RAG Retrieval Agent** intercepts your prompt, querying Qdrant and Neo4j to find the exact DOM locators, API schemas, and historical "Skills" needed for the task.
2. The **Test Case Generator Agent** writes the Playwright/Pytest code using the grounded context.
3. The **RAGAS Evaluator Agent** scores the generated code to ensure it didn't hallucinate locators.

### Step 3: Review and Approve
The generated code will appear in the **Chat Rail**. 
- If the RAGAS score is high, you can click **Approve** to save it to your execution pipeline.
- If it needs tweaks, reply to the agent in the chat to refine the code.

---

## 3. Execution & Flaky Test Detection
The platform doesn't just write code; it manages its lifecycle.

### Step 1: Run the Suite
1. Navigate to **Executions** (`http://localhost:5173/executions`).
2. Click **Run** on any approved Test Suite.
3. The Orchestrator spins up an isolated Docker container to execute the Playwright/Pytest scripts.

### Step 2: Flaky Detection
You do not need to manually trigger this!
- Every night at midnight (via Celery Beat), the **Flaky Test Detector Agent** runs a statistical variance analysis across all historical executions.
- If a test passes and fails randomly without code changes, it is flagged with a `warning` tag and quarantined automatically to prevent CI/CD pipeline blocking.

---

## 4. Auto-Debugging
When an execution fails, the debugging agent automatically steps in.

1. If a test fails in the **Executions** tab, a **"Debug AI"** button will appear next to the failure log.
2. Clicking it sends the stack trace to the **Debugging Agent**.
3. *Semantic Caching:* If this exact stack trace has been fixed before, the system instantly returns the cached fix (costing $0.00 in LLM tokens).
4. If it's a new error, the LLM analyzes the RAG context and provides a root-cause analysis and a patch, which you can approve directly in the Chat Rail.

---

## 5. Cost Analytics
As your team uses the agents, LLM costs can spiral. The platform tracks every token.

1. Navigate to **Cost Analysis** (`http://localhost:5173/cost`).
2. Here you can view the Chart.js dashboard.
3. Use the dropdowns to group costs by **Agent**, **Model**, or **Provider**.
4. *Tip:* If you notice the `rag_retrieval` agent is burning too much money on GPT-4, ask your admin to enable **Self-Hosted Inference** (vLLM) to route those specific requests to a free, local LLaMA model!
