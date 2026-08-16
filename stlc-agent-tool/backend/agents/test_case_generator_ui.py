import logging
from typing import Dict, Any
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict

logger = logging.getLogger(__name__)

class UiGenState(TypedDict):
    input_type: str # "codegen" or "bdd"
    requirement_text: str
    codegen_script: str # only for Option 1
    generated_code: str

def map_requirement_node(state: UiGenState) -> Dict[str, Any]:
    # Mock Neo4j lookup for requirement-unique-id
    req = state.get("requirement_text", "")
    return {"requirement_id": "custom-uuid-1234"}

def route_mcp_node(state: UiGenState) -> Dict[str, Any]:
    # In a full implementation, this uses MCP SDK to call Playwright Server
    # For MVP, we simulate the code generation based on Track 1 vs Track 2
    
    if state["input_type"] == "codegen":
        # Track 1
        return {"generated_code": "# Track 1 POM Generated\nclass LoginPage:\n    pass"}
    else:
        # Track 2 (BDD)
        return {"generated_code": "# Track 2 Zero-Shot POM\nclass ExplorationPage:\n    pass"}

def build_ui_gen_graph():
    builder = StateGraph(UiGenState)
    builder.add_node("map_req", map_requirement_node)
    builder.add_node("route_mcp", route_mcp_node)
    
    builder.add_edge(START, "map_req")
    builder.add_edge("map_req", "route_mcp")
    builder.add_edge("route_mcp", END)
    
    return builder.compile()

ui_gen_app = build_ui_gen_graph()
