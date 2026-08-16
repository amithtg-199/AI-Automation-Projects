import logging
import psycopg
from typing import TypedDict, Dict, Any, Annotated
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage

from backend.core.llm_client import CentralizedLLMClient
from backend.core.retrieval import retrieve_rag_context
from backend.core.config import settings

logger = logging.getLogger(__name__)

class RAGChatState(TypedDict):
    thread_id: str
    project_name: str
    username: str
    user_message: str
    messages: Annotated[list[BaseMessage], add_messages]

def save_chat_message(thread_id: str, project_name: str, username: str, role: str, content: str, initiator: str):
    try:
        with psycopg.connect(settings.POSTGRES_URL, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO chat_messages (thread_id, project_name, username, role, content, initiator)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (thread_id, project_name, username, role, content, initiator)
                )
    except Exception as e:
        logger.error(f"Failed to save chat message: {e}")

def retrieve_node(state: RAGChatState) -> Dict[str, Any]:
    """
    RAG Retrieval step.
    """
    docs = retrieve_rag_context(state["project_name"], state["user_message"])
    
    if not docs:
        # Fast exit fallback
        return {"context": "Sorry Requested information not found."}
    
    context = "\n\n".join(docs)
    return {"context": context}

def generate_node(state: RAGChatState) -> Dict[str, Any]:
    """
    LLM Generation step.
    """
    context = state.get("context", "")
    if context == "Sorry Requested information not found.":
        msg = AIMessage(content=context)
        save_chat_message(state["thread_id"], state["project_name"], state["username"], "assistant", msg.content, "AGENT")
        return {"messages": [msg]}
        
    llm = CentralizedLLMClient(
        username=state["username"], 
        project_name=state["project_name"], 
        agent_name="rag_chat"
    )
    
    prompt = [
        {"role": "system", "content": f"You are a helpful Q&A assistant. Answer the user based ONLY on the following context:\n\n{context}"},
        # Pass history (state["messages"]) if we want multi-turn, but for this step we can just pass the latest
    ]
    # append prior messages from state
    prompt_messages = []
    for m in state["messages"]:
        if isinstance(m, HumanMessage):
            prompt_messages.append({"role": "user", "content": m.content})
        elif isinstance(m, AIMessage):
            prompt_messages.append({"role": "assistant", "content": m.content})
    prompt_messages.extend(prompt)
    
    response = llm.invoke(prompt_messages)
    
    # Save assistant message to durable store
    save_chat_message(state["thread_id"], state["project_name"], state["username"], "assistant", response.content, "AGENT")
    
    return {"messages": [response]}

builder = StateGraph(RAGChatState)

builder.add_node("retrieve", retrieve_node)
builder.add_node("generate", generate_node)

builder.add_edge(START, "retrieve")
builder.add_edge("retrieve", "generate")
builder.add_edge("generate", END)

rag_chat_app = builder.compile()
