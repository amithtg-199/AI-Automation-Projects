# LLM Evaluation Projects

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://python.org)
[![DeepEval](https://img.shields.io/badge/DeepEval-LLM%20Evaluation-orange.svg)](https://confident-ai.com)
[![Google Gemini](https://img.shields.io/badge/LLM%20Judge-Gemini%203.6%20Flash-4285F4.svg)](https://ai.google.dev/)
[![Pytest](https://img.shields.io/badge/Test%20Framework-Pytest-0A9EDC.svg)](https://pytest.org)
[![Confident AI](https://img.shields.io/badge/Observability-Confident%20AI-purple.svg)](https://app.confident-ai.com)

A centralized suite of LLM evaluation frameworks, unit-testing modules, and benchmarking tools engineered to systematically assess, grade, and safeguard Generative AI applications, RAG pipelines, and autonomous agents.

---

## 📌 Workspace Overview

Traditional software testing relies on deterministic binary assertions. In contrast, Generative AI applications require continuous quantitative evaluation across semantic relevancy, factual faithfulness, hallucination risk, and context retrieval quality.

The **`llm_eval_projects`** directory contains modular, plug-and-play evaluation projects implementing leading evaluation frameworks like **DeepEval**, **Confident AI**, and **LLM-as-a-Judge** scoring engines.

---

## 📂 Included Evaluation Projects

| Project Directory | Description | Core Framework | LLM Judge | Key Metrics |
| :--- | :--- | :--- | :--- | :--- |
| [**`deepeval_baisc`**](./deepeval_baisc/) | Basic LLM unit testing suite with automated assertions and Confident AI observability. | DeepEval + Pytest | Google Gemini (`gemini-3.6-flash`) | Answer Relevancy |

---

## 🏗️ Monorepo LLM Evaluation Architecture

```mermaid
flowchart TD
    subgraph Suite ["llm_eval_projects Workspace"]
        P1["deepeval_baisc: Gemini Judge & Answer Relevancy"]
        P2["Future Modules: RAG Faithfulness, Multi-Modal & Hallucination Evaluators"]
    end

    subgraph Frameworks ["Evaluation Engines & Tooling"]
        DE["DeepEval Framework"]
        PY["Pytest Test Harness"]
        CF["Confident AI Cloud Platform"]
    end

    subgraph LLMJudges ["LLM-as-a-Judge Backends"]
        GEM["Google Gemini (gemini-3.6-flash / gemini-2.0-flash)"]
        OAI["OpenAI (gpt-4o / gpt-4o-mini)"]
        CL["Anthropic Claude (claude-3-5-sonnet)"]
    end

    subgraph Metrics ["Evaluation Metrics Suite"]
        M1["Answer Relevancy"]
        M2["Faithfulness (Zero Hallucination)"]
        M3["Contextual Precision & Recall"]
        M4["Hallucination Metric"]
        M5["Toxicity & Bias Guardrails"]
    end

    Suite --> Frameworks
    Frameworks --> LLMJudges
    LLMJudges --> Metrics
    Metrics --> CF
```

---

## 📊 Comprehensive Metric Taxonomy

| Metric Category | Metric Name | Evaluation Objective | Target Threshold |
| :--- | :--- | :--- | :--- |
| **Response Quality** | **Answer Relevancy** | Assesses whether the model response directly addresses the query without fluff or irrelevant tokens. | $\ge 0.80$ |
| **Response Quality** | **Summarization** | Quantifies how accurately a summary captures key insights from the original text without information distortion. | $\ge 0.85$ |
| **RAG Grounding** | **Faithfulness** | Evaluates whether every claim in the response is strictly supported by the retrieved context. | $\ge 0.90$ |
| **RAG Retrieval** | **Contextual Precision** | Measures if relevant context chunks are prioritized and ranked at the top of the retrieval results. | $\ge 0.80$ |
| **RAG Retrieval** | **Contextual Recall** | Measures whether all necessary facts from the golden truth are successfully retrieved. | $\ge 0.85$ |
| **Safety & Trust** | **Hallucination Metric** | Detects and penalizes fabricated or unverified claims. | $\le 0.05$ |
| **Safety & Trust** | **Toxicity / Bias** | Flags toxic, offensive, or biased language in conversational outputs. | $\le 0.01$ |

---

## 🚀 Quick Start Across Projects

To run evaluation suites locally:

1. **Navigate to the target project**:
   ```bash
   cd llm_eval_projects/deepeval_baisc
   ```
2. **Setup environment variables**:
   ```bash
   cp configs/.env.example configs/.env
   # Add your GOOGLE_API_KEY in configs/.env
   ```
3. **Execute the evaluation suite**:
   ```bash
   deepeval test run basic_deepeval.py
   # or
   pytest basic_deepeval.py -s -v
   ```

For detailed project-specific documentation, refer to [`deepeval_baisc/README.md`](./deepeval_baisc/README.md).
