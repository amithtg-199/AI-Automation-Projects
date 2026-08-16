import string
import secrets
import psycopg
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from backend.core.config import settings, GLOBAL_ENV_FILE
from backend.core.auth.deps import require_role
from backend.core.auth.local import pwd_context

router = APIRouter(prefix="/api/admin", tags=["admin"])

# Only Admins can access these routes
admin_only = Depends(require_role(["Admin"]))

class UserCreate(BaseModel):
    username: str
    role_name: str

class ProjectAssign(BaseModel):
    projects: List[str]

class GlobalEnvConfig(BaseModel):
    llmProvider: str
    modelName: str
    qdrantUrl: str
    celeryWorkers: int
    celeryConcurrency: int
    llmApiKey: Optional[str] = None
    embeddingModel: str = "text-embedding-3-small"
    maxRetryCount: int = 3
    maxBatches: int = 10
    fallbackSeconds: int = 10
    jiraUrl: Optional[str] = None
    jiraEmail: Optional[str] = None
    jiraApiKey: Optional[str] = None

@router.post("/global-env", dependencies=[admin_only])
def save_global_env(config: GlobalEnvConfig):
    # Write to .env
    env_content = f"""LLM_PROVIDER={config.llmProvider}
LLM_MODEL={config.modelName}
QDRANT_URL={config.qdrantUrl}
CELERY_WORKERS={config.celeryWorkers}
CELERY_CONCURRENCY={config.celeryConcurrency}
LLM_EMBEDDING_MODEL={config.embeddingModel}
MAX_RETRIES={config.maxRetryCount}
MAX_BATCHES={config.maxBatches}
FALLBACK_SECONDS={config.fallbackSeconds}
"""
    if config.llmApiKey:
        # Avoid logging the raw key
        env_content += f"LLM_API_KEY={config.llmApiKey}\n"
        
    if config.jiraUrl:
        env_content += f"JIRA_URL={config.jiraUrl}\n"
    if config.jiraEmail:
        env_content += f"JIRA_EMAIL={config.jiraEmail}\n"
    if config.jiraApiKey:
        env_content += f"JIRA_API_KEY={config.jiraApiKey}\n"

    GLOBAL_ENV_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(GLOBAL_ENV_FILE, "w") as f:
        f.write(env_content)
        
    return {"status": "success", "message": "Global Env saved"}

@router.get("/global-env", dependencies=[admin_only])
def get_global_env():
    # Read from settings (which are loaded from .env)
    return {
        "llmProvider": settings.LLM_PROVIDER,
        "modelName": settings.LLM_MODEL,
        "qdrantUrl": settings.QDRANT_URL,
        "celeryWorkers": settings.CELERY_WORKERS,
        "celeryConcurrency": settings.CELERY_CONCURRENCY,
        "embeddingModel": settings.LLM_EMBEDDING_MODEL,
        "maxRetryCount": settings.MAX_RETRIES,
        "maxBatches": settings.MAX_BATCHES,
        "fallbackSeconds": settings.FALLBACK_SECONDS,
        "jiraUrl": settings.JIRA_URL or "",
        "jiraEmail": settings.JIRA_EMAIL or "",
        "jiraApiKey": settings.JIRA_API_KEY or ""
    }

class UserCreate(BaseModel):
    username: str
    role_name: str

class ProjectAssign(BaseModel):
    projects: List[str]

def generate_secure_password(length=14):
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()_+-="
    while True:
        password = ''.join(secrets.choice(alphabet) for i in range(length))
        if (any(c.islower() for c in password)
                and any(c.isupper() for c in password)
                and sum(c.isdigit() for c in password) >= 2
                and any(not c.isalnum() for c in password)):
            break
    return password

@router.post("/users", dependencies=[admin_only])
def create_user(user: UserCreate):
    password = generate_secure_password()
    password_hash = pwd_context.hash(password)
    
    try:
        with psycopg.connect(settings.POSTGRES_URL, autocommit=True) as conn:
            with conn.cursor() as cur:
                # Check if role exists
                cur.execute("SELECT role_name FROM roles WHERE role_name = %s", (user.role_name,))
                if not cur.fetchone():
                    raise HTTPException(status_code=400, detail="Invalid role name")
                    
                cur.execute(
                    """
                    INSERT INTO users (username, password_hash, role_name, must_reset_password)
                    VALUES (%s, %s, %s, TRUE)
                    """,
                    (user.username, password_hash, user.role_name)
                )
    except psycopg.errors.UniqueViolation:
        raise HTTPException(status_code=400, detail="User already exists")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    # Return the generated password ONCE so the admin can securely transmit it to the user.
    return {"status": "success", "username": user.username, "temporary_password": password}

@router.post("/users/{username}/projects", dependencies=[admin_only])
def assign_projects(username: str, assignment: ProjectAssign):
    try:
        with psycopg.connect(settings.POSTGRES_URL, autocommit=True) as conn:
            with conn.cursor() as cur:
                # First delete existing mappings
                cur.execute("DELETE FROM user_projects WHERE username = %s", (username,))
                # Then insert new ones
                for project in assignment.projects:
                    cur.execute(
                        """
                        INSERT INTO user_projects (username, project_name)
                        VALUES (%s, %s)
                        ON CONFLICT DO NOTHING
                        """,
                        (username, project)
                    )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    return {"status": "success", "message": f"Projects updated for {username}"}

@router.get("/users", dependencies=[admin_only])
def get_users():
    try:
        with psycopg.connect(settings.POSTGRES_URL) as conn:
            with conn.cursor() as cur:
                # Get users with their assigned projects
                cur.execute("""
                    SELECT u.username, u.role_name, array_remove(array_agg(up.project_name), NULL) as assigned_projects
                    FROM users u
                    LEFT JOIN user_projects up ON u.username = up.username
                    GROUP BY u.username, u.role_name
                """)
                cols = [desc[0] for desc in cur.description]
                users = [dict(zip(cols, row)) for row in cur.fetchall()]
        return {"users": users}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class ProjectCreate(BaseModel):
    name: str

@router.post("/projects", dependencies=[admin_only])
def create_project(project: ProjectCreate):
    try:
        with psycopg.connect(settings.POSTGRES_URL, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO projects (name, is_active) VALUES (%s, TRUE) ON CONFLICT (name) DO NOTHING",
                    (project.name,)
                )
                
        # Physically create the directory structure under 'projects/'
        base_dir = Path(__file__).resolve().parent.parent.parent.parent / "projects" / project.name
        base_dir.mkdir(parents=True, exist_ok=True)
        (base_dir / "docs" / "API").mkdir(parents=True, exist_ok=True)
        (base_dir / "docs" / "PRD").mkdir(parents=True, exist_ok=True)
        (base_dir / "docs" / "JIRA").mkdir(parents=True, exist_ok=True)
        (base_dir / "test_case_result").mkdir(exist_ok=True)
        (base_dir / "tests").mkdir(exist_ok=True)
        (base_dir / "clients").mkdir(exist_ok=True)
        (base_dir / "fixtures").mkdir(exist_ok=True)
        (base_dir / "pages").mkdir(exist_ok=True)
        (base_dir / "models").mkdir(exist_ok=True)
        (base_dir / "utils").mkdir(exist_ok=True)
        
        yaml_path = base_dir / "input_folder.yaml"
        if not yaml_path.exists():
            yaml_path.write_text("API: docs/API\nPRD: docs/PRD\nJIRA: docs/JIRA\n")
            
        return {"status": "success", "message": f"Project {project.name} created."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/projects", dependencies=[admin_only])
def get_projects():
    try:
        with psycopg.connect(settings.POSTGRES_URL) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT name, created_at, is_active FROM projects")
                cols = [desc[0] for desc in cur.description]
                projects = [dict(zip(cols, row)) for row in cur.fetchall()]
        return {"projects": projects}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/audit-logs", dependencies=[admin_only])
def get_audit_logs(
    project_name: Optional[str] = None,
    username: Optional[str] = None,
    limit: int = Query(50, le=1000),
    offset: int = 0
):
    try:
        with psycopg.connect(settings.POSTGRES_URL) as conn:
            with conn.cursor() as cur:
                query = "SELECT id, username, project_name, action, details, ip_address, created_at FROM audit_logs WHERE 1=1"
                params = []
                
                if project_name:
                    query += " AND project_name = %s"
                    params.append(project_name)
                if username:
                    query += " AND username = %s"
                    params.append(username)
                    
                query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
                params.extend([limit, offset])
                
                cur.execute(query, params)
                cols = [desc[0] for desc in cur.description]
                logs = [dict(zip(cols, row)) for row in cur.fetchall()]
                
        return {"logs": logs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
