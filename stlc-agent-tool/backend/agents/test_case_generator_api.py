import logging
from typing import Dict, Any, List
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict

from backend.utils.api_parsers import parse_postman_collection, parse_curl
from backend.utils.test_writers import detect_lifecycle_pairs, generate_conftest, generate_api_tests

logger = logging.getLogger(__name__)

class ApiGenState(TypedDict):
    input_format: str
    raw_content: str
    brief: str
    project_name: str
    username: str
    parsed_collection: List[Dict[str, Any]]
    lifecycle_pairs: List[Dict[str, Any]]
    field_aliases: Dict[str, str]
    taxonomy_plan: Dict[str, Any]
    user_confirmed: bool
    generated_code: Dict[str, str]

def parse_inputs_node(state: ApiGenState) -> Dict[str, Any]:
    fmt = state.get("input_format", "postman")
    raw = state.get("raw_content", "")
    
    if fmt == "curl":
        parsed = parse_curl(raw)
    elif fmt == "postman":
        parsed = parse_postman_collection(raw)
    else:
        # Swagger mock
        parsed = parse_postman_collection(raw)
        
    pairs = detect_lifecycle_pairs(parsed)
    
    # Instead of mock taxonomy, use LLM
    from backend.core.llm_client import CentralizedLLMClient
    import json
    
    llm = CentralizedLLMClient(
        username=state.get("username", "system"), 
        project_name=state.get("project_name", "default"), 
        agent_name="test_case_generator"
    )
    
    prompt = f"""
You are an API testing expert. I have parsed an API collection with the following endpoints:
{parsed}

Generate a taxonomy plan (number of positive, negative, and boundary test cases per endpoint)
and identify any field aliases (e.g. Msisdn -> msisdn) that should be standardized.

Return ONLY a JSON dictionary exactly like this:
{{
  "taxonomy": {{"positive": 5, "negative": 10, "boundary": 5}},
  "aliases": {{"Msisdn": "msisdn", "SubscriberKey": "msisdn"}}
}}
"""
    try:
        resp = llm.invoke([{"role": "user", "content": prompt}])
        # Very basic JSON extraction
        content = resp.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        data = json.loads(content)
        taxonomy = data.get("taxonomy", {"positive": len(parsed), "negative": len(parsed)*2, "boundary": len(parsed)})
        aliases = data.get("aliases", {})
    except Exception as e:
        logger.error(f"LLM taxonomy extraction failed: {e}")
        taxonomy = {"positive": len(parsed), "negative": len(parsed)*2, "boundary": len(parsed)}
        aliases = {}
    
    return {
        "parsed_collection": parsed,
        "lifecycle_pairs": pairs,
        "taxonomy_plan": taxonomy,
        "field_aliases": aliases,
        "user_confirmed": False
    }

def human_review_node(state: ApiGenState) -> Dict[str, Any]:
    # This node acts as an interrupt boundary. In a real langgraph setup,
    # the graph pauses here using `interrupt` or `checkpointer` waiting for UI input.
    # For now, it just passes through or blocks if not confirmed.
    logger.info("Paused for human review of Create/Delete pairs and Taxonomy.")
    return {}

def code_gen_node(state: ApiGenState) -> Dict[str, Any]:
    # If not confirmed, we abort
    if not state.get("user_confirmed"):
        return {"generated_code": {"error": "User rejected the plan"}}
        
    conftest = generate_conftest(state["lifecycle_pairs"])
    tests = generate_api_tests(state["parsed_collection"], state["field_aliases"])
    
    from pathlib import Path
    
    project_name = state.get("project_name", "default")
    base_dir = Path(__file__).resolve().parent.parent.parent / "projects" / project_name
    api_tests_dir = base_dir / "tests" / "api"
    api_tests_dir.mkdir(parents=True, exist_ok=True)
    
    (api_tests_dir / "conftest.py").write_text(conftest)
    (api_tests_dir / "test_api.py").write_text(tests)
    
    return {
        "generated_code": {
            "conftest.py": conftest,
            "test_api.py": tests
        }
    }

def build_api_gen_graph():
    builder = StateGraph(ApiGenState)
    builder.add_node("parse_inputs", parse_inputs_node)
    builder.add_node("human_review", human_review_node)
    builder.add_node("code_gen", code_gen_node)
    
    builder.add_edge(START, "parse_inputs")
    builder.add_edge("parse_inputs", "human_review")
    builder.add_edge("human_review", "code_gen")
    builder.add_edge("code_gen", END)
    
    # Using checkpointer is standard for interrupts, but we return the compiled graph
    return builder.compile()

api_gen_app = build_api_gen_graph()
