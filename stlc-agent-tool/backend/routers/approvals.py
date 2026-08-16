import psycopg
from fastapi import APIRouter, Depends, HTTPException
from backend.core.auth.deps import get_current_user, CurrentUser
from backend.core.config import settings

router = APIRouter(prefix="/api/approvals", tags=["Approvals"])

@router.get("/pending")
def get_pending_approvals(user: CurrentUser = Depends(get_current_user)):
    """
    Returns all active proposals across all threads for the user's projects.
    Used by the UI to populate the global notification bell.
    """
    if not user.projects:
        return []
        
    proposals = []
    try:
        with psycopg.connect(settings.POSTGRES_URL) as conn:
            with conn.cursor() as cur:
                # Get pending approvals for user's projects
                cur.execute(
                    """
                    SELECT id, thread_id, project_name, agent_name, status, created_at
                    FROM pending_approvals
                    WHERE project_name = ANY(%s) AND status = 'pending'
                    ORDER BY created_at DESC
                    """,
                    (user.projects,)
                )
                
                for row in cur.fetchall():
                    proposals.append({
                        "id": row[0],
                        "thread_id": row[1],
                        "project_name": row[2],
                        "agent_name": row[3],
                        "status": row[4],
                        "timestamp": row[5]
                    })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    return proposals
