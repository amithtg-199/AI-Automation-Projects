**Role**: Your a Sr. Architect, 25+ years experience in Software Industry, Specialized in building AI based applications.

**Working Directory**: D:\ai_3x_qa\git_hub_files\18072026

**Objective**: I want you to create a high end QA Mentor UI Application which will have 2 phases.

**Phase-1: Advanced Hybrid RAG pipeline (Ingestion + Retrival)**
Ingestion:
- VectorDB: Qdrant
- Embedding Model: Mistral
- BM25 Indexing.
- Document chunking: RecursiveCharacterTextSplitter
- Metadata added to the documents as per the domain
- Document formats to be processed: DOCX, PDF, TXT, URLs.
- Support to ingest multiple documents at once.
- Documents to be ingested must have metadat (project_name, version, document_type, document_name)
- Each document need to also save its Hashed and save the hash value in the database and compare the hash value while ingesting the same file again.
- Project_name will be inputed from user while ingestion. In the UI the user can select the project name from the dropdown.
- Incorporate Adaptive chunking strategy (chunking + overlapping) based on the document type and data into to avoid any data loss.
- if document size is huge and if recive 429 error during parallel ingestion batch process add a failsafe machanisum which retries the failed documents again with exponential backoff. Also log the error and the document details.
- if the ingestion fails due to any other error add a failsafe machanisum which retries the failed documents again with exponential backoff. Also log the error and the document details.
- While ingestion, use the metadata to create a unique key for each document.
- Include a caching layer for metadata and document hashes. and avoid redundant database queries.
- Add Rate Limiting to avoid 429 errors.
- During a new Ingestion of same document check the hash value of existing document with new one and only ingest the diff and update the version metdata of the document recognized by document_name like from v1 to v2.

Retrieval: 
- Should support hybrid search (Vector + BM25)
- dense-vector search + RRF (Reciprocal Rank Fusion) + sparse
- Adpative TopK retrival based on the query complexity.
- Dynamic routing to appropriate index/collection.
- Use Mistral-large for retrival.
- Incorporate a Query Expansion strategy to improve the retrieval accuracy.
- Ensure smooth fallback mechanism for failed retrival incase of data sent to LLM is large, save the chunk data in cache and then send then in small batches to LLM during retrival.

Input data source for Ingestion (These input/src folder to be created in backend where user will create project_name directory and save the files under it.)
- Selenium framework repo: 	https://github.com/PramodDutta/ATB13xSeleniumAdvanceFramework
- Playwright framework repo: 	https://github.com/PramodDutta/Advance-Playwright-Framework	
- Test cases (~5,000): 	CSV / XLSX (e.g., testdata.csv)
- JIRA tickets: 	Live via JIRA MCP connection + JQL (I will share both)
- Company docs: 	PDF, MD
- Figma designs: 	ER diagrams, user guides, wireframes	Figma exports
- Meeting notes & recordings:	Text transcripts
- Lucid charts:	Exported to text
- PRD / SRS / BRD / FRD:	PDF
- Jenkins logs & results:	Log / text files

**Phase 2 Advanced UI chatbot**
- Advanced UI Chatbot based on RAG pipeline with AI Engine. 
- Showcase all the ingested data i.e directory_name in UI.
- Add a ingestion cycle where user can manually click to start ingestion.
- Use vite + react for UI and it should light and white theamed, beautifully and user freindly UI/UX design compatible to desktop and mobile version use tailwind for styling and beautiful animations.
- Maintain a clear nomencleture and structure. UI must be very clean, userfreindly and easy to navigate.
- Showcasing user chat conversation history with project_name and version.
- Project details must be clearly visible in the UI.
- Showcases projects list in the UI, with project_name and show total versions ingested.
- Must have a clear Chat box where user can put his/her queries.
- Response from AI should be professional and like some mentor interacting with his students.
- Response should be clear text with use-friendly font size and with proper formatting (bold, italic, underline, bullets, etc.) and with line spacing to make it more readable.
- Showcasing the response time taken for each query, dont show case directly in Markdown format.
- Response can also provide short code snippets for code related queries. (e.g., If user asks for a pytest code for the test case, the AI should provide the pytest code in a code block, with proper formating and indentation).
- Response can also include Visual diagrams if user requested or as a summary after providing the content if the content retrived is large (visual digram can include, histogram, or knowledge MAP, beautiful charts, table data, or any other visual representation.)
- UI also need to include a env field where we can configure (
    - Qdrant URL, 
    - Mistral API key, 
    - Jira MCP details like Jira URL, emailid, API key
    - confulence MCP details like confulence URL, emailid, API key
    - Github MCP details like Github URL, API key
    - Figma MCP details like Figma URL, API key
    - Jenkins MCP details like Jenkins URL, username, password
    - Lucid MCP details like Lucid URL, API key
    - Google Colab MCP details like Google Colab URL, API key
    - Google Cloud Storage MCP details like Google Cloud Storage URL, API key
    )

**Gaurdrails**
- Your Answer need to be confined to provided knowledge base only.
- Never Assume anything which is not in the knowledge base.
- If required clarification from user then ask.
- If you did not find revalvant data then tell user "Sorry details not found."
- Donot hallucinate data.
- If user asking for code, always provide code in proper formate with proper comments and indentation.
- if user asking for a diagram, always provide diagram in proper formate with proper comments and indentation.
- if user asking for data, always provide data in proper formate with proper indentation and in tabular format.
- if user asking for any data more then 100 lines always provide in bullet points and in tabular format including a visual summary and if data is related to test cases or code always provide a inline comments in code blocks.