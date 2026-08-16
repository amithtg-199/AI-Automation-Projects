import json
import psycopg
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from backend.core.config import settings

class AuditLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # We only log mutating requests
        is_mutating = request.method in ["POST", "PUT", "DELETE", "PATCH"]
        
        # Call the next middleware / endpoint
        response = await call_next(request)
        
        if is_mutating:
            # We attempt to capture context from the request scope if populated by deps
            # A more robust way is to inject username into request.state within get_current_user
            username = getattr(request.state, "username", "anonymous")
            project_name = getattr(request.state, "project_name", "unknown")
            action = request.url.path
            ip_address = request.client.host if request.client else "unknown"
            
            # Fire and forget audit log insertion
            try:
                with psycopg.connect(settings.POSTGRES_URL, autocommit=True) as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            INSERT INTO audit_logs (username, project_name, action, details, ip_address)
                            VALUES (%s, %s, %s, %s, %s)
                            """,
                            (username, project_name, action, json.dumps({"status_code": response.status_code}), ip_address)
                        )
            except Exception as e:
                # We do not fail the request if audit logging fails, but we should log it
                import logging
                logging.getLogger(__name__).error(f"Audit log insertion failed: {e}")
                
        return response
