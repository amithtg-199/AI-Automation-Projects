from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from backend.core.auth.deps import get_current_user, CurrentUser
from backend.core.report_builder import generate_report

router = APIRouter(prefix="/api/reports", tags=["Reports"])

@router.get("/{project_name}", response_class=HTMLResponse)
def get_report(project_name: str, user: CurrentUser = Depends(get_current_user)):
    """
    Returns the generated HTML report for the project.
    """
    if project_name not in user.projects:
        raise HTTPException(status_code=403, detail="Forbidden: You do not have access to this project's reports.")
        
    try:
        html_content = generate_report(project_name)
        return html_content
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")
