import os
import json
import uuid
import hashlib
import psycopg
import logging
from typing import List, Dict, Any, Optional
from backend.core.config import settings
from backend.core.llm_client import CentralizedLLMClient

logger = logging.getLogger(__name__)

# This would typically be a Celery task
def debug_failed_tests(project_name: str, username: str = "system"):
    """
    Scans for genuine test failures, queries the LLM (with semantic caching),
    and generates a debugging proposal.
    """
    failures = scan_failures(project_name)
    
    if not failures:
        logger.info("No genuine failures detected.")
        return
        
    llm = CentralizedLLMClient(username=username, project_name=project_name, agent_name="debugger")
    
    for test in failures:
        proposal = generate_or_fetch_proposal(llm, project_name, test)
        if proposal:
            inject_proposal(project_name, test["suite_id"], proposal, username)

def scan_failures(project_name: str) -> List[Dict[str, Any]]:
    # Scans the most recent test_case_result JSON for genuine failures
    from backend.core.report_builder import get_latest_execution_data
    from pathlib import Path
    
    exec_data = get_latest_execution_data(project_name)
    failures = []
    
    # Resolving physical paths
    base_dir = Path(__file__).resolve().parent.parent.parent / "projects" / project_name
    
    for f in exec_data.get("failures", []):
        node_id = f["id"]
        # typical node id: tests/api/test_foo.py::test_bar
        file_part = node_id.split("::")[0] if "::" in node_id else "tests/api/test_unknown.py"
        test_file_path = base_dir / file_part
        
        failures.append({
            "test_id": node_id.split("::")[-1] if "::" in node_id else node_id,
            "suite_id": file_part,
            "test_file": str(test_file_path),
            "error_logs": f["error"]
        })
        
    return failures

def compute_cache_key(error_logs: str, script_content: str) -> str:
    # sha256(normalized_error_signature + test_script_hash)
    signature = f"{error_logs.strip()}||{script_content.strip()}".encode('utf-8')
    return hashlib.sha256(signature).hexdigest()

def check_cache(cache_key: str) -> Optional[str]:
    try:
        with psycopg.connect(settings.POSTGRES_URL) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT proposal_data, seen_count FROM debug_cache WHERE cache_key = %s",
                    (cache_key,)
                )
                row = cur.fetchone()
                if row:
                    proposal_data = row[0]
                    seen_count = row[1]
                    
                    # Increment seen count
                    cur.execute(
                        "UPDATE debug_cache SET seen_count = seen_count + 1, last_seen_at = CURRENT_TIMESTAMP WHERE cache_key = %s",
                        (cache_key,)
                    )
                    return f"[CACHED DIAGNOSIS - Seen {seen_count + 1} times]\n{proposal_data['text']}"
    except Exception as e:
        logger.error(f"Cache check failed: {e}")
    return None

def store_in_cache(cache_key: str, proposal_text: str):
    try:
        with psycopg.connect(settings.POSTGRES_URL) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO debug_cache (cache_key, proposal_data, seen_count)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (cache_key) DO UPDATE 
                    SET seen_count = debug_cache.seen_count + 1, last_seen_at = CURRENT_TIMESTAMP
                    """,
                    (cache_key, json.dumps({"text": proposal_text}), 1)
                )
    except Exception as e:
        logger.error(f"Cache store failed: {e}")

def execute_rag_query(query: str) -> str:
    # Mocking a call to Batch 03's RAG retrieval pipeline
    logger.info(f"Executing RAG Query: {query}")
    return "MOCK RAG CONTEXT: The backend API /auth was recently updated to return 500 instead of 401 if the Bearer token is completely missing."

def generate_or_fetch_proposal(llm: CentralizedLLMClient, project_name: str, test: Dict[str, Any]) -> str:
    # Read the physical files
    error_logs = test["error_logs"]
    test_file_path = test["test_file"]
    
    try:
        with open(test_file_path, "r") as f:
            test_script = f.read()
    except Exception:
        test_script = f"# Could not read script at {test_file_path}"
        
    # Read conftest
    from pathlib import Path
    conftest_path = Path(__file__).resolve().parent.parent.parent / "projects" / project_name / "tests" / "api" / "conftest.py"
    try:
        with open(conftest_path, "r") as f:
            conftest = f.read()
    except Exception:
        conftest = "# No conftest found"
    
    cache_key = compute_cache_key(error_logs, test_script)
    
    cached_proposal = check_cache(cache_key)
    if cached_proposal:
        logger.info(f"Cache hit for {cache_key}")
        return cached_proposal
        
    logger.info(f"Cache miss for {cache_key}, invoking LLM.")
    
    prompt = f"""
You are a Senior QA Automation Engineer debugging a failed Playwright Python test case.
Your task is to analyze the failure logs, identify the root cause, and provide a fix.

[Input]
- test_failure_logs: {error_logs}
- test_script: {test_script}
- test_fixtures: {conftest}

[Instructions]
1. Analyze the inputs line-by-line: cross-reference the error tracebacks with the
   provided test script and fixtures.
2. Determine if the failure is due to a locator issue, timing/timeout, data state, or a
   genuine application bug.
3. Decide your next step based on the available context:
   - OPTION A (Context Sufficient): If the root cause is clear from the code and logs,
     provide a detailed explanation of the failure and suggest a code solution.
   - OPTION B (More Context Needed): If the failure is ambiguous (e.g., you suspect a UI
     change, require API docs, or need to see past successful execution logs), formulate
     a clear search query to retrieve data from our RAG knowledge base.
4. Format your response clearly. If you choose Option B, explicitly output:
   "RAG QUERY: [Your specific search query]".
5. CRITICAL: Only output suggestions or solutions. Do NOT execute code, make direct
   changes to the test script, or assume automatic application of your fix. Wait for user
   approval.
    """
    
    # First pass
    messages = [{"role": "user", "content": prompt}]
    resp = llm.invoke(messages)
    content = resp.content
    
    # Check for RAG Query
    if "RAG QUERY:" in content:
        # Extract query
        query_parts = content.split("RAG QUERY:")
        query_string = query_parts[1].strip().split("\n")[0]
        
        # Execute query
        rag_context = execute_rag_query(query_string)
        
        # Second pass (re-prompt)
        messages.append({"role": "assistant", "content": content})
        messages.append({"role": "user", "content": f"RAG Search Results:\n{rag_context}\n\nPlease provide the final code solution based on this new context."})
        
        resp2 = llm.invoke(messages)
        content = resp2.content
        
    store_in_cache(cache_key, content)
    return content

def inject_proposal(project_name: str, suite_id: str, proposal_text: str, username: str):
    # Thread ID for the relevant suite
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
                    (proposal_id, thread_id, project_name, "debugger", json.dumps({"text": proposal_text}), "pending")
                )
                
                # 2. Inject message into the chat thread
                cur.execute(
                    """
                    INSERT INTO chat_messages (thread_id, project_name, role, content, initiator)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (thread_id, project_name, "assistant", f"DEBUG_ALERT: Proposal {proposal_id}\n\n{proposal_text}", "AGENT")
                )
        logger.info(f"Successfully injected Debug proposal {proposal_id}")
    except Exception as e:
        logger.error(f"Failed to inject debug proposal: {e}")
