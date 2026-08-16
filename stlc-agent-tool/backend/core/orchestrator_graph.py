import logging
from typing import TypedDict, Optional, Literal, Dict, Any, Annotated
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, HumanMessage

from backend.core.llm_client import CentralizedLLMClient
from backend.core.rag_graph import rag_chat_app

logger = logging.getLogger(__name__)

class OrchestratorState(TypedDict):
    thread_id: str
    project_name: str
    username: str
    user_message: str
    # explicit tool selected from UI bottom-bar: "ui_automation", "api_automation", "chat", None
    selected_tool: Optional[Literal["ui_automation", "api_automation", "chat"]]
    intent: Optional[str]
    routing_signal: Optional[str]
    pending_proposal: Optional[Dict[str, Any]]
    active_subgraph: Optional[str]
    messages: Annotated[list[BaseMessage], add_messages]

def classify_intent_node(state: OrchestratorState) -> Dict[str, Any]:
    """
    LLM intent classification if no explicit tool is selected.
    Cheap call, default to RAG on low confidence.
    """
    llm = CentralizedLLMClient(
        username=state["username"], 
        project_name=state["project_name"], 
        agent_name="orchestrator_intent"
    )
    
    prompt = [
        {"role": "system", "content": "You are a classifier. The user wants to interact with a system. If their message is highly ambiguous or just a greeting/chat, return 'rag_chat'. If they clearly want to build test cases or have a specific goal but didn't select a tool, still return 'rag_chat' to clarify. Only return 'clarify' if absolutely necessary. We heavily default to 'rag_chat'."},
        {"role": "user", "content": state["user_message"]}
    ]
    
    # In a real impl, we'd force structural output. For now, simple text.
    response = llm.invoke(prompt)
    intent = response.content.strip().lower()
    
    if "clarify" not in intent:
        intent = "rag_chat"
        
    return {"intent": intent}

def route_request(state: OrchestratorState) -> str:
    """
    The orchestrator routing logic.
    """
    selected = state.get("selected_tool")
    if selected == "ui_automation":
        return "test_case_generator_ui"
    elif selected == "api_automation":
        return "test_case_generator_api"
        
    # Open proposal overrides chat
    if state.get("pending_proposal"):
        return "approval_handler"
        
    intent = state.get("intent", "rag_chat")
    return intent

# Scaffold Nodes
def rag_chat_node(state: OrchestratorState) -> Dict[str, Any]:
    # Invoke the RAG subgraph
    result = rag_chat_app.invoke({
        "thread_id": state["thread_id"],
        "project_name": state["project_name"],
        "username": state["username"],
        "user_message": state["user_message"],
        "messages": state.get("messages", [])
    })
    return {"active_subgraph": "rag_chat", "messages": result.get("messages", [])}

def test_case_generator_ui_node(state: OrchestratorState) -> Dict[str, Any]:
    from backend.agents.test_case_generator_ui import ui_gen_app
    
    # In a real app we'd map OrchestratorState -> UiGenState
    result = ui_gen_app.invoke({
        "input_type": "bdd", # Mock derived
        "requirement_text": state["user_message"],
        "codegen_script": ""
    })
    
    msg = HumanMessage(content=result.get("generated_code", "Failed to generate UI tests."))
    return {"active_subgraph": "test_case_generator_ui", "messages": [msg]}

def test_case_generator_api_node(state: OrchestratorState) -> Dict[str, Any]:
    from backend.agents.test_case_generator_api import api_gen_app
    
    # In a real app we'd map OrchestratorState -> ApiGenState, specifically detecting format
    result = api_gen_app.invoke({
        "input_format": "curl" if "curl" in state["user_message"].lower() else "postman",
        "raw_content": state["user_message"],
        "brief": state["user_message"],
        "project_name": state["project_name"],
        "username": state["username"]
    })
    
    if not result.get("user_confirmed"):
        # Simulated Interrupt returned to UI
        msg = HumanMessage(content="PENDING_REVIEW:" + str(result.get("lifecycle_pairs", [])))
    else:
        code = result.get("generated_code", {})
        msg = HumanMessage(content="API Tests Generated:\n" + str(code.keys()))
        
    return {"active_subgraph": "test_case_generator_api", "messages": [msg]}

def flaky_detector_node(state: OrchestratorState) -> Dict[str, Any]:
    # TODO (Batch 08)
    return {"active_subgraph": "flaky_detector"}

def debugger_node(state: OrchestratorState) -> Dict[str, Any]:
    # TODO (Batch 09)
    return {"active_subgraph": "debugger"}

def knowledge_hub_node(state: OrchestratorState) -> Dict[str, Any]:
    # TODO (Batch 10)
    return {"active_subgraph": "knowledge_hub"}

def approval_handler_node(state: OrchestratorState) -> Dict[str, Any]:
    # Flow B/C: Handle "Approve", "Decline", "Implement <custom>"
    msg = state["user_message"].lower().strip()
    
    if msg.startswith("approve"):
        # We would apply the physical diff to disk here and rerun the test
        # mock applying
        response = "Code diff applied to tests/api/test_subscriber.py successfully. Initiating verification run..."
    elif msg.startswith("decline"):
        response = "Proposal discarded. No changes made."
    elif msg.startswith("implement"):
        # Need to RAG verify the custom implementation
        # Mocking RAG check
        if "NO_DATA" in msg:
            response = "NO_DATA_FOUND: Your implementation references custom methods not found in the RAG context. Please upload supporting documentation."
        else:
            response = "Custom implementation verified against RAG context and applied."
    else:
        response = "Please reply with Approve, Decline, or Implement."
        
    return {"active_subgraph": "approval_handler", "messages": [HumanMessage(content=response)]}

def clarify_node(state: OrchestratorState) -> Dict[str, Any]:
    msg = HumanMessage(content="Could you please clarify what you'd like to do? You can select a specific tool from the menu.")
    return {"messages": [msg]}

builder = StateGraph(OrchestratorState)

builder.add_node("classify_intent", classify_intent_node)
builder.add_node("rag_chat", rag_chat_node)
builder.add_node("test_case_generator_ui", test_case_generator_ui_node)
builder.add_node("test_case_generator_api", test_case_generator_api_node)
builder.add_node("flaky_detector", flaky_detector_node)
builder.add_node("debugger", debugger_node)
builder.add_node("knowledge_hub", knowledge_hub_node)
builder.add_node("approval_handler", approval_handler_node)
builder.add_node("clarify", clarify_node)

# Logic: Start -> (If no explicit routing, classify intent) -> route -> Subgraph
def starter_node(state: OrchestratorState):
    # Just a passthrough to allow conditional routing from start
    return {}

builder.add_node("starter", starter_node)
builder.add_edge(START, "starter")

builder.add_conditional_edges(
    "starter",
    route_request,
    {
        "test_case_generator_ui": "test_case_generator_ui",
        "test_case_generator_api": "test_case_generator_api",
        "approval_handler": "approval_handler",
        "rag_chat": "rag_chat",
        "clarify": "clarify",
        # Default to classify intent if route_request returns None
        # Wait, route_request handles this, but let's wire it so if selected_tool=None, it goes to classify_intent
    }
)

def route_from_start(state: OrchestratorState) -> str:
    selected = state.get("selected_tool")
    if selected == "ui_automation":
        return "test_case_generator_ui"
    elif selected == "api_automation":
        return "test_case_generator_api"
    elif state.get("pending_proposal"):
        return "approval_handler"
    return "classify_intent"

def route_from_intent(state: OrchestratorState) -> str:
    if state.get("intent") == "clarify":
        return "clarify"
    return "rag_chat"

# Rewire to accurately reflect the design
builder_v2 = StateGraph(OrchestratorState)
builder_v2.add_node("classify_intent", classify_intent_node)
builder_v2.add_node("rag_chat", rag_chat_node)
builder_v2.add_node("test_case_generator_ui", test_case_generator_ui_node)
builder_v2.add_node("test_case_generator_api", test_case_generator_api_node)
builder_v2.add_node("flaky_detector", flaky_detector_node)
builder_v2.add_node("debugger", debugger_node)
builder_v2.add_node("knowledge_hub", knowledge_hub_node)
builder_v2.add_node("approval_handler", approval_handler_node)
builder_v2.add_node("clarify", clarify_node)

builder_v2.add_conditional_edges(START, route_from_start, {
    "test_case_generator_ui": "test_case_generator_ui",
    "test_case_generator_api": "test_case_generator_api",
    "approval_handler": "approval_handler",
    "classify_intent": "classify_intent"
})

builder_v2.add_conditional_edges("classify_intent", route_from_intent, {
    "clarify": "clarify",
    "rag_chat": "rag_chat"
})

# All subgraphs end the orchestrator turn
builder_v2.add_edge("rag_chat", END)
builder_v2.add_edge("test_case_generator_ui", END)
builder_v2.add_edge("test_case_generator_api", END)
builder_v2.add_edge("flaky_detector", END)
builder_v2.add_edge("debugger", END)
builder_v2.add_edge("knowledge_hub", END)
builder_v2.add_edge("approval_handler", END)
builder_v2.add_edge("clarify", END)

orchestrator_app = builder_v2.compile()
