# QA Buddy: Architectural Knowledge Map

This document outlines the system architecture, design principles, and technologies that power **QA Buddy**, the advanced Hybrid RAG (Retrieval-Augmented Generation) knowledge system.

> [!NOTE]
> This system is designed to provide highly accurate, cited answers strictly grounded in your team's QA artifacts, preventing LLM hallucinations.

## 1. High-Level Architecture Flow

The system follows a strict 4-step pipeline whenever a user asks a question, utilizing both Graph relationships and Dense/Sparse vector embeddings to ensure maximum retrieval accuracy.

```mermaid
graph TD
    classDef frontend fill:#FCFBF9,stroke:#D95F4D,stroke-width:2px,color:#333;
    classDef backend fill:#E5E0D8,stroke:#1F2937,stroke-width:2px,color:#333;
    classDef db fill:#D95F4D,stroke:#fff,stroke-width:2px,color:#fff;
    classDef llm fill:#10B981,stroke:#fff,stroke-width:2px,color:#fff;
    classDef source fill:#F9FAFB,stroke:#E5E7EB,stroke-width:1px,color:#6B7280;

    User([👤 QA Engineer]) -->|Asks Question| UI[Frontend: React + Vite]:::frontend
    UI -->|JSON HTTP POST| API[Backend: FastAPI]:::backend

    subgraph "Backend Engine"
        API -->|1. Understand| Graph[(Graph DB / Neo4j)]:::db
        Graph -.->|Expands Context| Vector
        
        API -->|2. Hybrid Search| Vector[(Qdrant Vector DB)]:::db
        Vector -.->|Dense: Semantics| Fusion
        Vector -.->|Sparse: BM25 Keywords| Fusion
        
        Fusion[3. Cross-Encoder Rerank]:::backend -->|Top K Chunks| LLM
        LLM((4. Mistral AI)):::llm -->|Generates Answer| API
    end

    subgraph "Ingested Data Sources"
        S1[Selenium Repo]:::source -.-> Vector
        S2[Playwright Repo]:::source -.-> Vector
        S3[5,000+ Test Cases]:::source -.-> Vector
        S4[JIRA Tickets]:::source -.-> Vector
        S5[PRDs & Docs]:::source -.-> Vector
    end
    
    API -->|Streams Cited Response| UI
```

## 2. Technology Stack

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Frontend** | React 18, Vite, TailwindCSS | Provides a blazingly fast, premium "Apple-like" interface. Uses `react-markdown` to render formatted LLM responses. |
| **Design System** | Glassmorphism, Inter/Playfair | Combines warm backgrounds (`#FCFBF9`) with frosted glass components (`backdrop-blur`) and deep orange accents (`#D95F4D`). |
| **Backend** | Python, FastAPI | Serves as the orchestration layer, handling state, chunking, and API routing asynchronously. |
| **Vector Search** | Qdrant | Stores chunked documents as high-dimensional vectors and performs Hybrid (Dense + BM25 Sparse) search. |
| **Knowledge Graph** | Neo4j (GraphRAG) | Maps entities (e.g., *Login Feature* &rarr; *Test Case #504* &rarr; *JIRA-102*) for complex multi-hop reasoning. |
| **LLM Engine** | Mistral AI | Responsible for embedding creation and final synthesized generation strictly from retrieved context. |

## 3. The 4-Step Retrieval Process

> [!TIP]
> The backend employs **Reciprocal Rank Fusion (RRF)** to combine the results from the Dense search (meaning) and the Sparse search (exact keyword match), ensuring things like specific Exception IDs or Variable Names are never missed.

1. **Understand**: The user's raw question is passed to a query-rewriter which expands it into multiple variants to maximize search surface area.
2. **Hybrid Search**: Qdrant executes two simultaneous searches:
   - *Dense*: Looks for semantic meaning (e.g. "how does checkout fail" matches "payment processing errors").
   - *Sparse*: Looks for exact keyword matches (e.g. "Error 504", "click_login_button").
3. **Fuse & Rerank**: The results are merged. A Cross-Encoder model scores the top chunks against the user's question, keeping only the absolute most relevant data.
4. **Cited Answer**: Mistral AI generates the final response, injecting `[n]` citations that point back to the exact file, JIRA ticket, or script line number the fact was extracted from.

## 4. UI/UX Paradigm

> [!IMPORTANT]
> The frontend is built to inspire confidence. When an LLM interface looks cheap, users distrust the data. 

- **Floating Input**: The input bar is detached and floats above a subtle gradient, ensuring it always feels accessible.
- **Micro-interactions**: Hovering over the Send button or Suggestion Chips triggers smooth, 300ms transitions.
- **Empty State Hero**: Welcomes the user with a massive typography-driven explanation of capabilities before they even type a word.
- **Real-time Synchronization**: The sidebar actively polls the FastAPI `/progress` endpoint to keep the chunk counts and extraction status strictly mapped to the physical Qdrant database state.
