import json
import psycopg
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Literal, List

from backend.core.auth.deps import get_current_user, CurrentUser
from backend.core.config import settings

# orchestrator_app is imported lazily inside the endpoint to avoid
# loading all LangChain/LangGraph providers (~3-4 min) at startup.
_orchestrator_app = None

def get_orchestrator():
    global _orchestrator_app
    if _orchestrator_app is None:
        from backend.core.orchestrator_graph import orchestrator_app
        _orchestrator_app = orchestrator_app
    return _orchestrator_app

router = APIRouter(prefix="/api/orchestrator", tags=["Orchestrator"])

class MessageRequest(BaseModel):
    thread_id: str
    project_name: str
    message: str
    selected_tool: Optional[Literal["ui_automation", "api_automation", "chat"]] = None

@router.post("/message")
def orchestrator_message(req: MessageRequest, user: CurrentUser = Depends(get_current_user)):
    """
    The ONE endpoint the frontend chat/tool-selector UI calls for every user turn.
    """
    if req.project_name not in user.projects:
        raise HTTPException(status_code=403, detail="Not assigned to this project.")
        
    # Check for pending proposals in durable DB (mocked query for scaffolding)
    # This logic checks Redis/Postgres for an open interrupt_before checkpoint
    pending_proposal = None
    
    # We build the orchestrator state
    initial_state = {
        "thread_id": req.thread_id,
        "project_name": req.project_name,
        "username": user.username,
        "user_message": req.message,
        "selected_tool": req.selected_tool,
        "pending_proposal": pending_proposal,
        "active_subgraph": None
    }
    
    # LangGraph Config (uses redis checkpointer based on thread_id)
    config = {"configurable": {"thread_id": req.thread_id}}
    
    # Invoke orchestrator (loads LangChain/LangGraph on first call)
    result_state = get_orchestrator().invoke(initial_state, config=config)
    
    handled_by = result_state.get("active_subgraph", "unknown")
    
    # Extract the last message from the result state if generated
    response_content = "Action completed."
    if "messages" in result_state and result_state["messages"]:
        last_msg = result_state["messages"][-1]
        response_content = last_msg.content
    
    return {
        "status": "success",
        "handled_by": handled_by,
        "response": response_content
    }

@router.get("/thread/{thread_id}")
def get_thread(thread_id: str, project_name: str, user: CurrentUser = Depends(get_current_user)):
    if project_name not in user.projects:
        raise HTTPException(status_code=403, detail="Not assigned to this project.")
        
    messages = []
    try:
        with psycopg.connect(settings.POSTGRES_URL) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT role, content, initiator, created_at 
                    FROM chat_messages 
                    WHERE thread_id = %s AND project_name = %s
                    ORDER BY created_at ASC
                    """,
                    (thread_id, project_name)
                )
                for row in cur.fetchall():
                    messages.append({
                        "role": row[0],
                        "content": row[1],
                        "initiator": row[2],
                        "timestamp": row[3]
                    })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    return {"thread_id": thread_id, "messages": messages, "pending_proposal": None}

@router.get("/chat/{thread_id}/download")
def download_chat(thread_id: str, project_name: str, user: CurrentUser = Depends(get_current_user)):
    if project_name not in user.projects:
        raise HTTPException(status_code=403, detail="Not assigned to this project.")
        
    def stream_markdown():
        yield f"# Chat Transcript: {thread_id}\n\n"
        with psycopg.connect(settings.POSTGRES_URL) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT role, content 
                    FROM chat_messages 
                    WHERE thread_id = %s AND project_name = %s
                    ORDER BY created_at ASC
                    """,
                    (thread_id, project_name)
                )
                for row in cur.fetchall():
                    yield f"**{row[0].upper()}**:\n{row[1]}\n\n"
                    
    return StreamingResponse(
        stream_markdown(), 
        media_type="text/markdown", 
        headers={"Content-Disposition": f"attachment; filename=chat_{thread_id}.md"}
    )

@router.get("/approvals/pending")
def get_pending_approvals(user: CurrentUser = Depends(get_current_user)):
    # Returns all pending proposals across the caller's accessible projects
    # Currently mocked empty until Batches 08/09/10
    return {"pending_approvals": []}
