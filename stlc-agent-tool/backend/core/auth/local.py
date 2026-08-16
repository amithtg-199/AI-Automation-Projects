import logging
import psycopg
from datetime import datetime, timedelta, timezone
import bcrypt
from typing import Optional, List

from backend.core.config import settings
from backend.core.auth.base import AuthBackend, UserIdentity

logger = logging.getLogger(__name__)

class PwdContext:
    def hash(self, password: str) -> str:
        # bcrypt.hashpw requires bytes
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
        
    def verify(self, password: str, hashed_password: str) -> bool:
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))

pwd_context = PwdContext()

class LocalPasswordAuthBackend(AuthBackend):
    def authenticate(self, username: str, password: str, ip_address: str) -> Optional[UserIdentity]:
        """
        Authenticates a user handling lockout logic.
        """
        try:
            with psycopg.connect(settings.POSTGRES_URL) as conn:
                with conn.cursor() as cur:
                    # Fetch user record
                    cur.execute(
                        "SELECT password_hash, role_name, must_reset_password, failed_attempts, locked_until FROM users WHERE username = %s",
                        (username,)
                    )
                    user_record = cur.fetchone()

                    if not user_record:
                        # Log attempt as failed
                        self._log_attempt(cur, username, ip_address, False)
                        conn.commit()
                        return None
                    
                    password_hash, role_name, must_reset_password, failed_attempts, locked_until = user_record
                    
                    # Check lockout
                    if locked_until and locked_until > datetime.now(timezone.utc):
                        # Still locked out
                        self._log_attempt(cur, username, ip_address, False)
                        conn.commit()
                        return None
                    
                    # Verify password
                    if not pwd_context.verify(password, password_hash):
                        failed_attempts += 1
                        new_locked_until = None
                        if failed_attempts >= 3:
                            new_locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
                        
                        cur.execute(
                            "UPDATE users SET failed_attempts = %s, locked_until = %s WHERE username = %s",
                            (failed_attempts, new_locked_until, username)
                        )
                        self._log_attempt(cur, username, ip_address, False)
                        conn.commit()
                        return None

                    # Success, reset counters
                    cur.execute(
                        "UPDATE users SET failed_attempts = 0, locked_until = NULL WHERE username = %s",
                        (username,)
                    )
                    self._log_attempt(cur, username, ip_address, True)
                    conn.commit()
                    
                    return UserIdentity(
                        username=username,
                        role_name=role_name,
                        must_reset_password=must_reset_password
                    )
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return None

    def get_user_projects(self, username: str) -> List[str]:
        try:
            with psycopg.connect(settings.POSTGRES_URL) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT project_name FROM user_projects WHERE username = %s", (username,))
                    return [row[0] for row in cur.fetchall()]
        except Exception as e:
            logger.error(f"Failed to fetch user projects: {e}")
            return []

    def _log_attempt(self, cur, username: str, ip_address: str, success: bool):
        cur.execute(
            "INSERT INTO login_attempts (username, ip_address, success) VALUES (%s, %s, %s)",
            (username, ip_address, success)
        )
