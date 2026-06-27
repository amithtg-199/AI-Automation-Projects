# 🚀 QA Automation Langflow Agents Directory

This directory contains a suite of **5 production-grade Langflow Agent Pipelines** designed to automate critical phases of the Quality Assurance and Software Development lifecycle. They enable rapid generation of test suites, test plan documentation, flaky test analysis, bug triaging, and Root Cause Analysis (RCA).

---

## 📋 Table of Contents
1. [Agent Overview](#-agent-overview)
   - [1. Bug Triage Agent](#1-bug-triage-agent)
   - [2. Flaky Test Case Generator](#2-flaky-test-case-generator)
   - [3. RCA Bot](#3-rca-bot)
   - [4. Test Case Generator](#4-test-case-generator)
   - [5. Test Plan Creator](#5-test-plan-creator)
2. [🔑 Configuration & JIRA Integration](#-configuration--jira-integration)
   - [Adding Atlassian API Keys](#adding-atlassian-api-keys)
   - [Project Name Isolation in Test Case Generator](#project-name-isolation-in-test-case-generator)
3. [🐳 Docker Setup & Local Deployment](#-docker-setup--local-deployment)
   - [Docker Run Command](#docker-run-command)
   - [Volume Mount Requirements for Custom Components](#volume-mount-requirements-for-custom-components)
   - [Configuring Custom Export Paths](#configuring-custom-export-paths)

---

## 🤖 Agent Overview

### 1. Bug Triage Agent (`Bug_Triage_Agent.json`)
* **Purpose**: Automates the triaging process for incoming JIRA bugs. It evaluates details such as descriptions, environment specs, and user impact, then suggests priority, severity, and categorization.
* **Core Flow & Design**:
  ```mermaid
  graph LR
      ChatInput[Chat Input: JIRA keys] --> Prompt1[Prompt Template: API Request Builder]
      Prompt1 --> APIReq[API Request: Fetch JIRA JSON]
      APIReq --> Parser[Jira Search Parser: Extract fields]
      Parser --> Prompt2[Prompt Template: Triage Prompt]
      Prompt2 --> LLM[MistralAI: Evaluate Bug]
      LLM --> ChatOutput[Chat Output: Triage Report]
  ```
* **Key Components**:
  * **Jira Search Parser (Custom Component)**: Extracts key, summary, type, description, and priority from standard JIRA API search payloads.
  * **MistralAI Model**: Handles the analytical task of triaging and categorizing findings.

---

### 2. Flaky Test Case Generator (`Flaky_Test_Case_generator.json`)
* **Purpose**: Analyzes and resolves test flakiness by comparing multiple test execution logs (e.g., Run 1 Success vs. Run 2 Failure). It identifies flaky patterns, race conditions, dynamic timing dependencies, and outputs remediation strategies.
* **Core Flow & Design**:
  ```mermaid
  graph TD
      Log1[File Upload: Run 1 Log] --> Prompt[Prompt Template: Comparison Guide]
      Log2[File Upload: Run 2 Log] --> Prompt
      Prompt --> LLM[MistralAI: Log Analyzer]
      LLM --> ChatOutput[Chat Output: Flakiness Resolution Guide]
  ```
* **Key Components**:
  * **Dual File Loaders**: Allow direct upload of raw log output or test result files.
  * **MistralAI Model**: Reasons over log anomalies and trace outputs to suggest fixes.

---

### 3. RCA Bot (`RCA-Bot.json`)
* **Purpose**: Streamlines post-incident reviews by fetching incident data from JIRA, generating structured Root Cause Analysis (RCA) documents, and exporting them directly to editable files.
* **Core Flow & Design**:
  ```mermaid
  graph LR
      ChatInput[Chat Input: JIRA Keys] --> APIReq[API Request: Fetch Issue]
      APIReq --> Parser[Jira Search Parser]
      Parser --> Prompt[Prompt Template: RCA Prompt]
      Prompt --> LLM[MistralAI: RCA Generator]
      LLM --> Exporter[RCA Exporter: Custom MD & DOCX writer]
      Exporter --> ChatOutput[Chat Output: Download Links]
  ```
* **Key Components**:
  * **RCA Exporter (Custom Component)**: Dynamically formats the generated markdown and generates active download URLs for `.md` and `.docx` formats.

---

### 4. Test Case Generator (`Test-Case-Generator.json`)
* **Purpose**: Automatically generates standard test cases alongside a complete E2E **Playwright Test Automation Framework** (including Page Object Models (POM), Custom Fixtures, Setup Files, and configurations) based on JIRA tickets or local documentation (PRD, specs, user flows).
* **Core Flow & Design**:
  ```mermaid
  graph TD
      ChatInput[Chat Input: User Story Keys] --> APIReq[API Request]
      APIReq --> JiraParser[Jira Search Parser]
      FileInput[Local File Upload: PDF/DOCX/TXT/MD] --> DocReader[Local Document Reader]
      
      JiraParser --> SrcSelector[Source Selector: Merge/Select Context]
      DocReader --> SrcSelector
      
      SrcSelector --> Prompt[Prompt Template: E2E Playwright Rules]
      Prompt --> LLM[MistralAI: Code Generator]
      LLM --> FileWriter[Multi-File Writer: Custom Component]
      FileWriter --> ChatOutput[Chat Output: Status & Sync Path]
  ```
* **Key Components**:
  * **Local Document Reader (Custom Component)**: Extracts context from PDF, DOCX, TXT, MD, and JSON files offline.
  * **Source Selector (Custom Component)**: Intelligently merges context from JIRA tickets and/or local PRDs.
  * **Multi-File Writer (Custom Component)**: Parses LLM responses, splits code into multiple files, converts generated JSON to `test-cases.csv`, and writes them to the exports directory.

---

### 5. Test Plan Creator (`Test-Plan-Creator.json`)
* **Purpose**: Generates high-level Test Plans and Test Strategies from local project spec files or JIRA Epics, automatically writing structured outputs (`test_plan.md` and `test_strategy.md`) to the local file system.
* **Core Flow & Design**:
  * Dual-Path structure allowing independent document ingestion (via Local Document Reader) or online ticket retrieval (via JIRA REST API), utilizing twin **Multi-File Writer** components to save plans.
  ```mermaid
  graph TD
      subgraph JIRA Pathway
          J_Input[JIRA Issue Key] --> J_API[JIRA API Request]
          J_API --> J_Parser[Jira Search Parser]
          J_Parser --> J_Prompt[Prompt Template]
          J_Prompt --> J_LLM[MistralAI]
          J_LLM --> J_Writer[Multi-File Writer 1]
      end

      subgraph Document Pathway
          Doc_Input[PRD / Spec File] --> Doc_Reader[Local Document Reader]
          Doc_Reader --> Doc_Prompt[Prompt Template]
          Doc_Prompt --> Doc_LLM[MistralAI]
          Doc_LLM --> Doc_Writer[Multi-File Writer 2]
      end

      J_Writer --> Output1[Chat Output 1]
      Doc_Writer --> Output2[Chat Output 2]
   ```

---

## 🔑 Configuration & JIRA Integration

### Adding Atlassian API Keys
To allow the **Bug Triage**, **RCA Bot**, **Test Case Generator**, and **Test Plan Creator** agents to pull tickets directly from JIRA, you must provide your Atlassian credentials using **JIRA Basic Authentication** (which utilizes a Base64-encoded string of your email and API token).

1. **Generate an API Token**:
   * Go to [Atlassian API Tokens Console](https://id.atlassian.com/manage-profile/security/api-tokens).
   * Click **Create API Token**, enter a label, and copy the generated token.
2. **Configure JIRA Authentication in Langflow**:
   You can configure JIRA authentication in the **API Request** component using either of the following two options:

   #### Option A: Configured in Headers Table (Recommended)
   In the **API Request** component, click on **Headers** and add/edit the following entry:
   * **Header**: `Authorization`
   * **Value**: `Basic <base64_encoded_credentials>`

   > [!NOTE]
   > `<base64_encoded_credentials>` is the Base64 representation of `your_email@domain.com:YOUR_ATLASSIAN_API_TOKEN`.
   >
   > You can generate this base64 string using:
   > * **Python**: `import base64; print(base64.b64encode(b"email:token").decode())`
   > * **Bash (Linux/macOS)**: `echo -n "email:token" | base64`
   > * **PowerShell (Windows)**: `[Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes("email:token"))`

   #### Option B: Configured via cURL command input
   If the API Request component is initialized using a `cURL` input field, use the `-u` auth parameter:
   ```bash
   -u "your_jira_email@domain.com:YOUR_ATLASSIAN_API_TOKEN"
   ```
   *(cURL automatically translates the `-u` flag into the `Authorization: Basic <base64>` header under the hood).*

---

### Project Name Isolation in Test Case Generator
The **Test Case Generator** agent contains a custom component called **Multi-File Writer** with a `project_name` parameter. This parameter enables workspace isolation for generated tests:

1. **Locate the Input**: In the Langflow Playground/UI, look for the **Project Name** parameter.
2. **Set a Custom Name**:
   * Change it from the default `"DefaultProject"` or empty value to your specific workspace directory (e.g. `MyProject`).
   * The custom component sanitizes this name and creates a distinct folder for it:
     `/app/langflow/exports/MyProject/`
   * On your local host, files will be synced to:
     `./langflow-data/exports/MyProject/`
3. **Why it matters**: This prevents the agent from overwriting existing files in the root exports folder when generating a new framework or target test suite.

---

## 🐳 Docker Setup & Local Deployment

To run Langflow locally inside Docker and ensure generated files are synced directly to your host machine, run the following setup steps:

### Docker Run Command

Run the following commands in your terminal (PowerShell, Bash, or Command Prompt):

```bash
# 1. Create the data directory on your host machine
mkdir -p langflow-data && chmod 777 langflow-data

# 2. Start the Langflow container with volume mounting
docker run -d \
  -v $(pwd)/langflow-data:/app/langflow \
  -e LANGFLOW_CONFIG_DIR=/app/flow \
  --name langflow \
  -p 7860:7860 \
  langflowai/langflow:latest
```

> [!IMPORTANT]
> The host directory permission is set to `777` (read/write/execute for all) using `chmod 777` because the Langflow user inside the Docker container runs as a non-root user (UID 1000). Without explicit permissions, the container will fail to write data to your host machine's volume mount.

---

### Volume Mount Requirements for Custom Components

The agents (e.g., **Test Case Generator** and **Test Plan Creator**) contain a custom Python component named `Multi-File Writer`. 
This component is hardcoded to output generated files inside the container's path:
`/app/langflow/exports`

Because you mounted:
`$(pwd)/langflow-data:/app/langflow`

Any files generated by the agents will automatically sync to your host machine's directory:
`./langflow-data/exports/`

If you do not mount `/app/langflow`, the agent executions will fail, or you will not be able to retrieve the generated Playwright frameworks and spreadsheets.

---

### Configuring Custom Export Paths

If you need to change the mount target or use a custom path (for example, mapping `$(pwd)/langflow-data:/data`), use one of the two options below to prevent a `Path not exists` error:

#### Option A: Container-Level Mapping (Recommended)
Keep the container-side target as `/app/langflow`, and simply change the host directory mapping.
```bash
docker run -d -v /your/custom/host/path:/app/langflow ...
```
This is the easiest option as it doesn't require modifying any agent code.

#### Option B: Component-Level Configuration (UI Edit)
If you must mount the volume to a different container path (e.g., `/data` instead of `/app/langflow`), you must adjust the custom components' Python code inside the Langflow UI:

1. Open your agent flow in the Langflow UI.
2. Locate the **Multi-File Writer** or **RCA Exporter** component.
3. Click **Code** to open the Python script editor.
4. Modify the `export_dir` variable.
   * **Change from:**
     ```python
     export_dir = "/app/langflow/exports"
     ```
   * **Change to:**
     ```python
     export_dir = "/data/exports"
     ```
5. Click **Save** and test the flow.
