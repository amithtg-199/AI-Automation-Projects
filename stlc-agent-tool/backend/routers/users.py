from fastapi import APIRouter, Depends
from backend.core.auth.deps import get_current_user, CurrentUser

router = APIRouter(prefix="/api/users", tags=["users"])

@router.get("/me")
def get_me(user: CurrentUser = Depends(get_current_user)):
    return {
        "username": user.username,
        "role_name": user.role_name,
        "must_reset_password": user.must_reset_password,
        "assigned_projects": user.projects
    }
