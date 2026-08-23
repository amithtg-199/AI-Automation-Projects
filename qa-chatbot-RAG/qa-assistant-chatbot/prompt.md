# 🚀 Master AI Prompt: Enterprise QA-Assistant-Chatbot & Adaptive Qdrant RAG Suite

Copy and paste the prompt below into any advanced AI coding assistant (such as v0 by Vercel, Cursor, Bolt.new, Claude 3.5 Sonnet, ChatGPT, or Gemini 3.1 Pro) to generate the exact, fully functional **QA-Assistant-Chatbot** application:

---

You are an Principal Frontend Architect and AI Systems Engineer. Your task is to build a production-ready, ultra-premium single-page web application called **"QA-Assistant-Chatbot (`Adaptive Qdrant Hybrid RAG Suite`)"** using React 18+ (Vite + JSX) and modern Vanilla CSS / Tailwind with Lucide React icons.

## 🌟 1. Core Visual Aesthetics & Design System (`index.css`)
Implement a stunning, futuristic **Glassmorphism Dark Mode** theme that wows enterprise users at first glance:
- **Color Palette**:
  - `Body Background`: Deep dark space (`#0b0f19`) with multi-point glowing radial gradient meshes (`rgba(99, 102, 241, 0.12)`, `rgba(236, 72, 153, 0.1)`, `rgba(16, 185, 129, 0.05)`).
  - `Card Background (`.glass-panel`)`: Semi-transparent dark slate (`rgba(30, 41, 59, 0.6)`) with `backdrop-filter: blur(16px)` and delicate 1px border (`rgba(255, 255, 255, 0.08)`).
  - `Text Colors`: Primary `#f8fafc`, Secondary `#94a3b8`, Muted `#64748b`.
  - `Accents`: Indigo (`#6366f1`), Pink/Rose (`#ec4899`), Emerald (`#10b981`), Blue (`#3b82f6`), Amber (`#f59e0b`).
  - `Primary Gradient Glow`: `linear-gradient(135deg, #6366f1 0%, #ec4899 50%, #3b82f6 100%)`.
- **Typography**: Import Google Fonts `'Outfit'` for headings and `'Inter'` for body text.
- **Components & Micro-Animations**:
  - Glowing primary buttons (`.btn-primary`) with subtle lift on hover and glowing shadow (`0 4px 15px rgba(99, 102, 241, 0.35)`).
  - Custom scrollbars, pulsing status badges (`animate-pulse-glow`), smooth fade-in transitions (`animate-fade-in`), and interactive hover glows on panels (`hover:border-indigo-500/50`).

---

## 🏛️ 2. Global State & Real-Time Qdrant API Synchronization (`App.jsx` & `Header.jsx`)
- **Main State Variables**:
  - `activeTab`: Default `'workspace'` (`'workspace'`, `'chat'`, `'env'`).
  - `projectName`: Default `'ecommerce_test_cases'`.
  - `totalChunks`: Persisted via `localStorage('qa_total_chunks')` (or synced from live API).
  - `ingestionStatus`: E.g., `'Ready / Checked Live'`, `'Indexed & Active'`, or `'Collection Empty / Purged'`.
- **Live Qdrant REST API Sync Logic (`syncLiveQdrantStatus`)**:
  - On mount or when `projectName` changes, make a live `GET http://localhost:6333/collections/${projectName}` request.
  - If the collection exists (`status === 200`), extract `result.points_count`, set `totalChunks = points_count`, set `ingestionStatus = 'Indexed & Active'`, and update `localStorage`.
  - If `status === 404` or offline, gracefully fallback or display `'Collection Deleted / Not Found in Qdrant'` / `0 Chunks`.
- **Header (`Header.jsx`)**:
  - Displays brand logo (`Sparkles`), title **`QA-Assistant-Chatbot`** with glowing gradient text, and an active badge (`ShieldCheck Active & Grounded`).
  - Includes a **Project & Connection Pill** on the right showing the `Active Collection: ecommerce_test_cases` and live indexed status (`Cpu` icon + green/red text indicating chunk count).
  - **Navigation Tabs**: 3 distinct glassmorphic tabs (`Database Ingestion & Metadata`, `MessageSquareCode Retrieval & Chat Output Studio`, `Settings Environment & MCPs`).

---

## 📦 3. Tab 1: Ingestion & Metadata Workspace (`IngestionWorkspace.jsx`)
Create a multi-card dashboard orchestrating live vector embeddings and collection versioning:
1. **Target Collection & Versioning Box**:
   - Input for `Collection Identifier` (`projectName`, default `'ecommerce_test_cases'`).
   - Input for `Version Metadata Tag` (`collectionMetadata.version`, auto-incrementing `v1`, `v2`, `v3` upon re-ingestion).
   - Badges indicating `Metadata Prefix Active` and `API Tweaks Override Enabled`.
2. **Document Upload Studio**:
   - Drag & drop file upload zone supporting `.csv, .json, .pdf, .docx, .txt`.
   - Pre-loaded mock file state: `ecommerce_test_cases.csv` (`1.1 MB`, `CSV Dataset`, `1,000 rows across 12 modules`).
3. **Ingestion Pipeline Control & API Tweaks Preview**:
   - **Live Ingestion Progress Bar**: When `Start Ingestion Process` is clicked, simulate a multi-stage Langflow/Qdrant ingestion pipeline over ~3.4 seconds:
     - Stage 1 (15%): `"Uploading document payload to Langflow Ingestion Pipeline..."`
     - Stage 2 (40%): `"Running Adaptive Chunking and assigning metadata prefix headers..."`
     - Stage 3 (75%): `"Generating Mistral vector embeddings and committing to Qdrant..."` -> Sends real REST API calls to `PUT http://localhost:6333/collections/${projectName}` (`{ vectors: { size: 1024, distance: "Cosine" } }`) and inserts vector points via `PUT http://localhost:6333/collections/${projectName}/points`.
     - Stage 4 (100%): Triggers `canvas-confetti`, updates `totalChunks` to `1,000`, increments version tag (`v2`), and sets status to `'Indexed & Active'`.
   - **Action Buttons**: `Start Ingestion Process`, `Refresh Status`, and `Purge Data` (`DELETE http://localhost:6333/collections/${projectName}`).
   - **Langflow API Tweaks Override Preview Block**: Displays formatted JSON preview:
     ```json
     {
       "tweaks": {
         "AdaptiveMultiFormatChunker": {
           "project_name": "ecommerce_test_cases",
           "version": "v1"
         }
       }
     }
     ```
4. **Collection Metadata Dashboard & Module Inventory Table**:
   - 4 summary stat cards: `Target Collection (ecommerce_test_cases)`, `Total Chunks & Modules (1,000 Chunks / 12 Modules)`, `Embedding Specification (1024-d Cosine Mistral Embed)`, `Last Ingestion Timestamp / Version`.
   - **Exact Module Breakdown Table** across all 12 modules when `totalChunks > 0`:
     | Module Name | Test Cases Indexed | Priority Level | Retrieval Mode Intercept |
     | :--- | :--- | :--- | :--- |
     | Payment | 110 test cases | Critical (Pink Badge) | Exact Scroll Match (100% Accuracy) |
     | Login | 100 test cases | Critical (Pink Badge) | Exact Scroll Match (100% Accuracy) |
     | Browser Compatibility | 90 test cases | High (Indigo Badge) | Exact Scroll Match (100% Accuracy) |
     | Dashboard | 90 test cases | High (Indigo Badge) | Exact Scroll Match (100% Accuracy) |
     | Payout | 90 test cases | High (Indigo Badge) | Exact Scroll Match (100% Accuracy) |
     | Add to Cart | 80 test cases | Critical (Pink Badge) | Exact Scroll Match (100% Accuracy) |
     | Cart | 80 test cases | Critical (Pink Badge) | Exact Scroll Match (100% Accuracy) |
     | Invoice | 80 test cases | Medium (Emerald Badge) | Exact Scroll Match (100% Accuracy) |
     | Remove from Cart | 80 test cases | Medium (Emerald Badge) | Exact Scroll Match (100% Accuracy) |
     | Search | 80 test cases | High (Indigo Badge) | Exact Scroll Match (100% Accuracy) |
     | Select Article | 80 test cases | Medium (Emerald Badge) | Exact Scroll Match (100% Accuracy) |
     | Multi Select | 40 test cases | Low (Emerald Badge) | Exact Scroll Match (100% Accuracy) |
   - When purged (`0 Chunks`), display a dashed placeholder box stating `"Collection 'ecommerce_test_cases' is currently empty or purged."`

---

## 💬 4. Tab 2: Retrieval & Chat Output Studio (`ChatStudio.jsx`)
Implement an interactive quality assurance query studio with query intent routing, confidence guardrails, and custom markdown/table rendering:
1. **Instant Verification Prompts (`Quick Pills`)**:
   - `Count Search Module Scenarios`
   - `List Full Module Inventory`
   - `Retrieve Critical Login Workflows`
   - `Verify Guardrail Interception`
2. **Query Input Interface**:
   - Text input box asking: *"Ask about ecommerce_test_cases (e.g. 'What is the count of Search Module?', 'Show failed login steps')"* and a `Submit Query` button with spin state during retrieval (~900ms delay).
3. **Query Intent Router & Confidence Guardrails Engine**:
   - **Case A (`totalChunks === 0`)**: Intercept query, return `Confidence: 0.0` (`Storage Check Intercept`), and display warning alert: `"⚠️ Collection Empty or Purged. No test case vectors are currently indexed..."`
   - **Case B (`Irrelevant/Ungrounded Query`)**: If query contains `spaceship`, `alien`, `mars`, `recipe`, `weather` -> Trigger `Confidence Guardrail (< 0.50)`, set `guardrailTriggered: true`, and output: `"I could not find relevant information in the knowledge base to answer your question."` with red highlighted card border (`#f43f5e`).
   - **Case C (`Exact Scroll Aggregation - Search Count`)**: If query asks for `count of search` -> Return `Confidence: 1.0` (`Exact Scroll Aggregation`), output: `"There are **80 test cases** in the Search module of the **ecommerce_test_cases** project."`
   - **Case D (`Exact Scroll Aggregation - List All Modules`)**: If query asks for `all modules` -> Return `Confidence: 1.0` (`Exact Scroll Aggregation (Full Inventory)`), and output a complete markdown table listing all 12 modules (`Payment`, `Login`, `Browser Compatibility`, `Dashboard`, `Payout`, `Add to Cart`, `Cart`, `Invoice`, `Remove from Cart`, `Search`, `Select Article`, `Multi Select`) totaling `1,000 test cases`.
   - **Case E (`Hybrid Cosine Retrieval - Login & Critical Workflows`)**: If query mentions `login`, `critical`, or `cart` -> Return `Confidence: 0.94` (`Hybrid Cosine Retrieval (Top-K 15)`), and render a rich Markdown table of verified test cases:
     | Test ID (TID) | Scenario Category | Priority | Precondition | Test Steps (Exact Sequence) | Expected Result | Status |
     | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
     | **TC_LOGIN_001** | Authentication Flow | **Critical** | User is registered with valid credentials | 1. Navigate to `/login` URL.<br>2. Enter email `qa_test@domain.com` in email field.<br>3. Enter password in password field.<br>4. Click **Sign In** button. | User is authenticated and redirected to Dashboard within 1.5s. | **Passed** |
     | **TC_LOGIN_004** | Negative Security | **Critical** | User account is locked after 5 failed attempts | 1. Enter valid email for locked account.<br>2. Enter correct password.<br>3. Click **Sign In**. | System blocks login and displays warning modal: *"Account temporarily locked due to security policy."* | **Failed** (`DEF-0842`) |
     | **TC_CART_012** | Checkout Validation | **Critical** | Cart has 2 items total > $150 | 1. Click **Cart** icon.<br>2. Click **Proceed to Checkout**.<br>3. Apply discount coupon `SUMMER20`. | Cart total dynamically updates to reflect 20% discount without page reload. | **Passed** |
     - Include GitHub callout: `> [!NOTE]` / `> All statements, IDs, and steps are verified against active vector records in Qdrant.`
   - **Case F (`General Semantic Retrieval`)**: Return `Confidence: 0.88`, summarize top candidates evaluated (`15 Top-K`), primary modules (`Dashboard, Browser Compatibility, Payment`), and invite step-by-step table queries.
4. **Custom Markdown & Table Renderer (`MarkdownRenderer` component)**:
   - Parse markdown tables (`| col | col |`), rendering styled header bars (`linear-gradient(90deg, rgba(30, 41, 59, 0.95), rgba(49, 46, 129, 0.9))`) with alternating dark row backgrounds.
   - Automatically transform keywords inside table cells: `**Passed**` -> Green badge (`badge-emerald`), `**Failed**` -> Red badge (`#f43f5e` background/border), `**Critical**` -> Amber badge (`#fbbf24`), and backticks `` `code` `` -> Monospace blue chip (`#38bdf8`).
   - Parse blockquotes (`> [!NOTE]`, `> [!WARNING]`) into custom glassmorphic callout boxes with appropriate colored border accents (`#10b981` green or `#f59e0b` amber) and Lucide icons (`ShieldCheck`, `AlertTriangle`).
5. **Report Utility Bar**:
   - Each message card contains `Copy Markdown` (`navigator.clipboard`) and `Export Report` (`Download` icon triggering a `.md` Blob file download named `QA_Report_${Date.now()}.md`).

---

## ⚙️ 5. Tab 3: Environment & MCPs (`EnvironmentTabs.jsx`)
Create an interactive configuration panel allowing developers to manage LLM credentials, vector specs, and Model Context Protocol (MCP) servers:
1. **Language Generation Model & Provider Card**:
   - `Provider Selection`: Dropdown with `MistralAI (Recommended Enterprise Engine)`, `Vercel AI Gateway (Unified Proxy via AI_GATEWAY_API_KEY)`, `OpenAI (GPT-4o)`, `Anthropic (Claude 3.5 Sonnet)`, `Ollama (Local Llama-3)`.
   - `Model Identifier`: Dropdown with `codestral-latest (Optimized for code & QA tables)`, `mistral-large-latest`, `open-mistral-nemo`.
   - `Authentication Secret Key`: Password field (`mistral_apikey_************************` or `vck_...`).
   - Security banner verifying in-memory key encryption.
2. **Vector Store & Embedding Specifications Card**:
   - `Vector Embedding Model`: Text input (`mistral-embed`).
   - `Vector Dimension`: Dropdown (`1024 (Mistral Embed Default)`, `1536`, `768`).
   - `Distance Metric`: Dropdown (`Cosine (Recommended)`, `Euclidean`, `Dot`).
   - `Orchestration Server Base URL`: Input (`http://localhost:7860`).
   - Verification banner: `"Verified: mistral-embed (1024-d Cosine) matches target collection schema."`
3. **Model Context Protocol (MCP) Integrations Dashboard**:
   - List 5 distinct integration cards (`Jira`, `Confluence`, `GitHub`, `Qdrant`, `Slack`), stored in `localStorage('qa_mcps_config')`:
     - **Atlassian Jira Server & Cloud Integration**: `Auto-create bug tickets (DEF-xxxx) and synchronize test run execution statuses...` (`Status: Not Configured`).
     - **Confluence Knowledge Base Connector**: `Ingest product requirement documents, architecture specifications, and API docs...` (`Status: Not Configured`).
     - **GitHub Repository & CI/CD Orchestrator**: `Analyze pull request code diffs, trigger automated validation suites via GitHub Actions...` (`Status: Not Configured`).
     - **Qdrant Vector Database Connector**: `High-performance hybrid vector retrieval, metadata prefix filtering, and direct collection snapshots.` (`Status: Connected`, Base URL: `http://qdrant:6333`).
     - **Slack Notification Webhook Service**: `Broadcast real-time QA alert digests when critical test cases fail or guardrails trigger repeatedly.` (`Status: Not Configured`).
   - **Connect / Disconnect Toggle Logic**: Clicking `Connect Integration` validates that both `Server Base Endpoint` and `Authentication Token` inputs are non-empty (unless `qdrant`). If empty, show a dismissible red error banner (`AlertCircle`): *"Please enter a valid Server Endpoint URL for [Name] before connecting."* When valid, toggle state between `Connected` (Green badge) and `Not Configured` (Amber badge).
4. **Save Bar**:
   - `Save Environment Configuration` button writes `envConfig` and `mcps` to `localStorage` and displays a live confirmation pill: `"CheckCircle2 Environment Settings Saved Live!"` for 2.5 seconds.
