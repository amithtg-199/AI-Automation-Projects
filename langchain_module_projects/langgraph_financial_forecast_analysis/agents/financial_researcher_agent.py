from utils.llm_factory import get_llm
from langgraph.graph import StateGraph, END, START
from typing import TypedDict, Dict, Any


def llm_fallback(primary_llm: str, fallback_llms: list):
    valid_fallback_llms = [llm for llm in fallback_llms if fallback_llms is not None]

    if not primary_llm:
        if valid_fallback_llms:
            return valid_fallback_llms[0].with_fallbacks(valid_fallback_llms[1:])
        raise ValueError("No valid LLM instances available.")

    return primary_llm.with_fallbacks(valid_fallback_llms)

llm = llm_fallback(primary_llm=get_llm("mistral"), fallback_llms=[get_llm("openai"),get_llm("anthropic")])

#Setup State for the Graph.
class WorkflowState(TypedDict):
    topic: str
    financial_audit: str
    verification: str
    final_output: str

# Define Nodes.
def financial_audit_node(state: WorkflowState) -> Dict[str, Any]:
    topic = state.get("topic", "the specified company or asset")
    
    prompt = f"""You are a Lead Financial Auditor and Quantitative Equity Analyst. 
Your expertise lies in forensic accounting, live market research, corporate disclosures, and predictive financial modeling.

# CORE OBJECTIVE
Conduct an end-to-end financial audit and market analysis for {topic}. Since direct document retrieval (RAG) is not active, you must use your web search capabilities to independently query, pull, and verify live financial data, official filings, regulatory disclosures, and corporate news before performing your audit.

# DATA GATHERING INSTRUCTIONS (ACTIVE SEARCH)
Prior to synthesizing your report, execute search queries to retrieve the following core financial artifacts for {topic}:
1. Financial Statements: Latest Balance Sheet, Income Statement (P&L), and Cash Flow Statement (TTM and past 3 fiscal years).
2. Legal & Regulatory Disclosures: Ongoing or settled litigation, regulatory investigations, SEC enforcement actions, or contingent liabilities.
3. Corporate Actions: Recent/pending acquisitions, mergers, divestitures, debt issuances, or share buybacks.
4. Market Metrics: Live/latest stock price, valuation multiples (P/E, EV/EBITDA, P/B), market capitalization, EPS, and dividend yield.

# ANALYTICAL METHODOLOGY (CHAIN OF THOUGHT)
Execute your audit using the following step-by-step framework:
1. Data Ingestion & Cross-Verification: Search for and gather official financial figures. Verify data across multiple financial sources (e.g., Investor Relations, SEC filings, financial databases).
2. Balance Sheet & P&L Forensic Audit: Evaluate liquidity ratios (Current/Quick), debt structure (Debt-to-Equity, Interest Coverage), revenue growth quality, gross/operating margins, and Free Cash Flow (FCF) conversion.
3. Legal, M&A & Liability Risk Assessment: Analyze the impact of past/recent acquisitions on Goodwill and debt loads. Quantify potential earnings exposure from litigation or regulatory compliance issues.
4. Sentiment & Catalyst Extraction: Synthesize recent market news, management commentary, earnings surprises, and macro catalysts. Separate temporary market noise from fundamental structural shifts.
5. Forecasting & Valuation Alignment: Project revenue trajectory, margin performance, and capital efficiency. Determine whether the current stock price and valuation multiples accurately align with underlying audited fundamentals.

# STRICT CONSTRAINTS & GUARDRAILS
- Zero Hallucination: Never invent financial metrics, earnings figures, litigation dates, or valuation ratios. If specific financial figures cannot be found via search, explicitly write "Data unavailable."
- Mandatory Source Attribution: Reference the financial reporting periods (e.g., "Q3 2025 Filing", "FY2025 Annual Report") for reported numbers.
- Impartial Forensic Tone: Maintain an objective, analytical tone. Avoid emotional language, speculative hype, or hyperbole.

# OUTPUT SCHEMA
Structure your final deliverable using the exact sections below:

* **Executive Summary:** A concise forensic verdict on the financial health and structural stability of {topic}.
* **Balance Sheet & P&L Audit:** 
  - *Income Statement Trends:* Revenue trajectory, margin expansion/compression, and net profitability.
  - *Balance Sheet Health:* Liquidity, solvency, debt maturities, and working capital efficiency.
  - *Cash Flow Quality:* Operating Cash Flow vs. Free Cash Flow sustainability.
* **Litigation, Acquisitions & Risk Exposure:**
  - *Material Litigation & Regulatory Inquiries:* Pending legal risks, contingent liabilities, or fines.
  - *M&A & Corporate Actions:* Recent acquisitions, integration challenges, goodwill impairment risk, or capital raises.
* **Market Sentiment & Catalysts:** Key news drivers, earnings surprises, macro headwinds/tailwinds, and industry positioning.
* **Projections & Valuation Dynamics:**
  - *Forward Projections:* Expected revenue trajectory, earnings outlook, and downside risk factors.
  - *Valuation & Pricing:* Multiples analysis (P/E, EV/EBITDA, P/S) and alignment between current stock market pricing and audited fundamentals.
"""
    response = llm.invoke(prompt)
    return {"financial_audit": str(response.content)}

def verification_node(state: WorkflowState) -> Dict[str, Any]:
    topic = state.get("topic", "the specified company or asset")
    audit_report = state.get("financial_audit", "No audit report provided in the state.")
    
    prompt = f"""You are a Principal Risk Officer and Senior Financial Fact-Checker.
        Your sole objective is to independently review, stress-test, and validate the financial audit report generated for {topic}. You are the final line of defense against hallucinations, logical inconsistencies, and biased analysis.

        # EVALUATION CRITERIA
        Critically analyze the provided audit report against the following strict standards:
        1. Factuality & Hallucination: Are the financial metrics, ratios, and dates realistic? Flag any highly specific numbers that appear fabricated or lack logical grounding in the provided context. 
        2. Logical Coherence: Do the forward-looking projections actually align with the reported balance sheet health? (e.g., If free cash flow is negative, aggressive growth projections must be flagged).
        3. Tone & Objectivity: Does the report maintain a clinical, forensic tone? Flag any hyperbole, emotional language (e.g., "crushing it", "disaster"), or speculative hype.
        4. Schema Compliance: Does the report perfectly follow the required 5-part structure (Executive Summary, Fundamental Audit, Sentiment & Catalysts, Projections, Valuation Analysis)?

        # INPUT REPORT FOR REVIEW
        {audit_report}

        # OUTPUT SCHEMA
        Structure your verification deliverable exactly as follows:
        * **Status:** [PASS / NEEDS REVISION / FAIL]
        * **Critical Flags:** Itemized list of specific factual anomalies, hallucinations, or logical disconnects. If none, write "None".
        * **Tone & Formatting Violations:** Any biased language or missing structural elements.
        * **Required Revisions:** Direct, actionable instructions for the Auditor agent to fix the report. If the Status is PASS, write "Approved for final output."
        """
    response = llm.invoke(prompt)
    return {"verification": str(response.content)}

def final_output_node(state: WorkflowState) -> Dict[str, Any]:
    topic = state.get("topic", "the specified company or asset")
    audit_report = state.get("financial_audit", "No audit report provided in the state.")
    verification_result = state.get("verification", "No verification result provided in the state.")

    prompt = f"""You are a Senior Equity Research Director and Chief Financial Analyst.
        Your objective is to synthesize the primary Financial Audit Report and the Independent Verification Officer's evaluation into a definitive, executive-level Comprehensive Financial Audit & Equity Valuation Report for {topic}.

        # INPUT DATA FOR SYNTHESIS
        ---
        ## AUDIT REPORT FINDINGS
        {audit_report}

        ## VERIFICATION & RISK OFFICER REVIEW
        {verification_result}
        ---

        # CORE INSTRUCTIONS
        1. Reconcile and Integrate: Merge the foundational analysis from the Audit Report with the risk assessment, corrections, and missing gap analysis identified in the Verification Review.
        2. Address Gaps & Risks: Explicitly address any red flags, inconsistencies, or unverified claims flagged by the Risk Officer.
        3. Quantify Core Metrics: Highlight key figures including Revenue, Profits, Cash Flow, Earnings Per Share (EPS), Dividend Yield, and Valuation Multiples.
        4. Professional Tone: Maintain an authoritative, institutional equity research tone suitable for enterprise stakeholders and investors.

        # REQUIRED OUTPUT SCHEMA
        Structure your final financial report using the exact sections below:

        * **1. Executive Summary & Verdict**
        - High-level audit conclusion and overall financial health score/verdict for {topic}.
        - Key takeaways from the synthesis of the audit and risk verification.

        * **2. Core Financial Performance & Cash Flow**
        - **Revenue & Profitability:** Trailing/historical revenue growth, gross/net margins, and net profits.
        - **Cash Flow Dynamics:** Operating cash flow (OCF) and Free cash flow (FCF) sustainability.
        - **Per-Share Metrics:** Earnings Per Share (EPS), Dividend yield, and payout ratios (if applicable).

        * **3. Strategic Audit: Strengths, Weaknesses & Risk Gaps**
        - **Key Strengths:** Core competitive advantages and balance sheet strengths.
        - **Vulnerabilities & Weaknesses:** Capital structure hazards, debt load, or margin compression.
        - **Audit Gaps & Risk Flags:** Critical items, data gaps, or risk flags raised during independent verification.

        * **4. Forward-Looking Projections & Growth Trajectory**
        - Revenue and earnings growth forecasts based on validated historical trends and current industry catalysts.
        - Key downside risks and upside catalysts to projected growth.

        * **5. Stock Price, Options & Equity Valuation Analysis** (For listed entities)
        - **Current Valuation:** P/E, EV/EBITDA, P/B multiples versus industry peers.
        - **Stock Price & Expected Returns:** Price action context, projected return profile, and fair value estimate.
        - **Market Dynamics & Derivatives Context:** Stock options sentiment (Put/Call ratios/implied volatility trends if applicable) and broad equity market alignment.
        """
    response = llm.invoke(prompt)
    return {"final_output": str(response.content)}


# Build and compile state machine .

workflow = StateGraph(WorkflowState)

# Add node.
workflow.add_node("Auditor", financial_audit_node)
workflow.add_node("Verification", verification_node)
workflow.add_node("Result", final_output_node)

# Add Edge.
workflow.add_edge(START, "Auditor")
workflow.add_edge("Auditor", "Verification")
workflow.add_edge("Verification", "Result")
workflow.add_edge("Result", END)

# Complie
finance_audit_agent = workflow.compile()

