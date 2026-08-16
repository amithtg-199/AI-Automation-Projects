import os
import json
import uuid
import psycopg
import logging
from typing import List, Dict, Any
from backend.core.config import settings
from backend.core.llm_client import CentralizedLLMClient

logger = logging.getLogger(__name__)

# This would typically be a Celery task
def detect_and_propose_flaky_fixes(project_name: str, username: str = "system"):
    """
    Scans for flaky tests and generates a proposal via LLM.
    """
    # 1. Intra-run flakiness detection (mocking the parse of a pytest-json-report)
    flaky_tests = scan_intra_run(project_name)
    
    # 2. Historical flakiness detection
    historical_flaky_tests = scan_historical(project_name)
    
    all_flaky = flaky_tests + historical_flaky_tests
    
    if not all_flaky:
        logger.info("No flaky tests detected.")
        return
        
    llm = CentralizedLLMClient(username=username, project_name=project_name, agent_name="flaky_detector")
    
    for test in all_flaky:
        proposal = generate_proposal(llm, test)
        if proposal:
            inject_proposal(project_name, test["suite_id"], proposal, username)


def scan_intra_run(project_name: str) -> List[Dict[str, Any]]:
    # Scans the most recent test_case_result JSON
    # A test is intra-run flaky if it has retries and eventually passed.
    # pytest-json-report will usually record outcome "passed" but have teardown or setup retries, or reruns field.
    from backend.core.report_builder import get_latest_execution_data
    from pathlib import Path
    import glob
    import os
    
    base_dir = Path(__file__).resolve().parent.parent.parent / "projects" / project_name / "test_case_result"
    if not base_dir.exists():
        return []
        
    json_files = glob.glob(str(base_dir / "**" / "*.json"), recursive=True)
    if not json_files:
        return []
        
    latest_file = max(json_files, key=os.path.getmtime)
    with open(latest_file, "r") as f:
        data = json.load(f)
        
    tests = data.get("tests", [])
    flaky = []
    
    proj_root = Path(__file__).resolve().parent.parent.parent / "projects" / project_name
    
    for t in tests:
        # If the test passed but had a failed setup/call before, or has reruns metadata
        # We will approximate this by looking for tests with "rerun" or if it failed and we want to try fixing it.
        # Actually, for the hackathon, we'll just extract any test that failed as flaky if the user asks.
        # Let's extract tests that have "rerun" in outcome or metadata.
        if t.get("outcome") == "rerun" or "reruns" in t:
            node_id = t.get("nodeid", "unknown")
            file_part = node_id.split("::")[0] if "::" in node_id else "tests/api/test_unknown.py"
            test_file_path = proj_root / file_part
            
            flaky.append({
                "test_id": node_id.split("::")[-1] if "::" in node_id else node_id,
                "suite_id": file_part,
                "flaky_type": "intra_run_flaky",
                "test_file": str(test_file_path),
                "error_logs": "Test was marked as rerun/flaky by pytest."
            })
            
    return flaky

def scan_historical(project_name: str) -> List[Dict[str, Any]]:
    # Mock querying Qdrant/Neo4j for the last 7 days to detect flip-flops
    return []

def generate_proposal(llm: CentralizedLLMClient, test: Dict[str, Any]) -> str:
    # Read the physical files
    flaky_test_result = json.dumps(test)
    test_file_path = test.get("test_file", "")
    
    try:
        with open(test_file_path, "r") as f:
            flaky_test_case = f.read()
    except Exception:
        flaky_test_case = f"# Could not read script at {test_file_path}"
        
    # Read conftest
    from pathlib import Path
    project_name = llm.project_name
    conftest_path = Path(__file__).resolve().parent.parent.parent / "projects" / project_name / "tests" / "api" / "conftest.py"
    try:
        with open(conftest_path, "r") as f:
            conftest = f.read()
    except Exception:
        conftest = "# No conftest found"
    
    prompt = f"""
You are a Senior QA Automation Engineer specializing in Python, Pytest, and Playwright
(`pytest-playwright`). Your task is to analyze a test case that failed on initial run and
passed on retry (tagged as "flaky" by Playwright), diagnose the root cause, and provide an
actionable refactoring solution.

[Input]
- flaky_test_result: {flaky_test_result}
- playwright_code_flaky: {flaky_test_case}
- playwright_fixtures: {conftest}

[Instructions]
1. Analyze the inputs in detail: review the error stack traces and step failures across
   retry attempts, and inspect both the test file and fixtures line-by-line.
2. Identify common flakiness triggers (e.g., missing web-first auto-retrying assertions,
   usage of standard `assert` or `time.sleep()`, race conditions, brittle selectors,
   unhandled network latency, or fixture state leakage).
3. Provide a feedback solution to eliminate the flaky execution and guarantee
   deterministic test outcomes on the first attempt.
4. Format the response strictly into the following sections:
   - Root Cause Analysis
   - Flakiness Category
   - Refactoring Strategy
   - Proposed Code Changes
5. CRITICAL: Do NOT modify the codebase directly or assume automatic approval. Present
   the solution strictly as a code proposal and wait for user approval.
    """
    
    resp = llm.invoke([{"role": "user", "content": prompt}])
    return resp.content

def inject_proposal(project_name: str, suite_id: str, proposal_text: str, username: str):
    # Thread ID for the relevant suite (in a real system we look up the orchestrator thread that created it)
    thread_id = f"thread-suite-{suite_id}"
    proposal_id = str(uuid.uuid4())
    
    try:
        with psycopg.connect(settings.POSTGRES_URL) as conn:
            with conn.cursor() as cur:
                # 1. Insert into pending_approvals
                cur.execute(
                    """
                    INSERT INTO pending_approvals (id, thread_id, project_name, agent_name, proposal_data, status)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (proposal_id, thread_id, project_name, "flaky_detector", json.dumps({"text": proposal_text}), "pending")
                )
                
                # 2. Inject message into the chat thread to trigger Flow B
                cur.execute(
                    """
                    INSERT INTO chat_messages (thread_id, project_name, role, content, initiator)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (thread_id, project_name, "assistant", f"FLAKY_ALERT: Proposal {proposal_id}\n\n{proposal_text}", "AGENT")
                )
        logger.info(f"Successfully injected Flaky Test proposal {proposal_id}")
    except Exception as e:
        logger.error(f"Failed to inject proposal: {e}")
