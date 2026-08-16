import jwt
import psycopg
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
import re
from pydantic import BaseModel

from backend.core.config import settings
from backend.core.auth.deps import auth_backend, get_current_user, CurrentUser, SECRET_KEY, ALGORITHM
from backend.core.auth.local import pwd_context

router = APIRouter(prefix="/api/auth", tags=["auth"])

ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # 1 day

class Token(BaseModel):
    access_token: str
    token_type: str

class PasswordReset(BaseModel):
    new_password: str

class AdminCreate(BaseModel):
    username: str
    password: str

@router.post("/register-initial-admin")
def register_initial_admin(admin: AdminCreate):
    """
    Registers the first Admin user. Only succeeds if the users table is completely empty.
    Password policy: 8–12 chars, ≥1 uppercase, ≥1 digit, ≥1 special char from @#$%.
    """
    # Enforce password policy server-side (never trust only client-side)
    pw = admin.password
    if not (8 <= len(pw) <= 12) or \
       not re.search(r'[A-Z]', pw) or \
       not re.search(r'[0-9]', pw) or \
       not re.search(r'[@#$%]', pw) or \
       not re.match(r'^[A-Za-z0-9@#$%]+$', pw):
        raise HTTPException(
            status_code=400, 
            detail="Password must have min 8 max 12 char with atleast 1 caps + Alphanumeric + allowed special char (@#$%)"
        )

    try:
        with psycopg.connect(settings.POSTGRES_URL, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM users")
                count = cur.fetchone()[0]
                if count > 0:
                    raise HTTPException(status_code=403, detail="Admin already exists. Use the login screen or ask an Admin to create an account.")
                
                password_hash = pwd_context.hash(admin.password)
                cur.execute(
                    """
                    INSERT INTO users (username, password_hash, role_name, must_reset_password)
                    VALUES (%s, %s, 'Admin', FALSE)
                    """,
                    (admin.username, password_hash)
                )
    except psycopg.errors.UniqueViolation:
        raise HTTPException(status_code=400, detail="User already exists")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    return {"status": "success", "message": "Initial admin created successfully."}

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

@router.post("/login", response_model=Token)
def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    ip_address = request.client.host if request.client else "unknown"
    
    # 1. Independent IP Rate limiting logic (e.g. max 10 failed attempts from IP in 15 mins)
    # For brevity, rely mostly on account lockout, but we'll enforce the 4th attempt generic rejection.
    with psycopg.connect(settings.POSTGRES_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) FROM login_attempts 
                WHERE ip_address = %s AND success = FALSE 
                AND attempted_at > NOW() - INTERVAL '15 minutes'
            """, (ip_address,))
            failed_ip_attempts = cur.fetchone()[0]
            if failed_ip_attempts >= 10:
                raise HTTPException(status_code=429, detail="Too many failed attempts from this IP. Locked out for 15 minutes.")
                
    # 2. Authenticate
    user_identity = auth_backend.authenticate(form_data.username, form_data.password, ip_address)
    if not user_identity:
        # Check if they are locked out specifically to return a proper message per requirements
        with psycopg.connect(settings.POSTGRES_URL) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT locked_until FROM users WHERE username = %s", (form_data.username,))
                res = cur.fetchone()
                if res and res[0] and res[0] > datetime.now(timezone.utc):
                    raise HTTPException(status_code=429, detail="Account locked due to multiple failed attempts.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 3. Create token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": user_identity.username,
            "role": user_identity.role_name,
            "must_reset_password": user_identity.must_reset_password
        },
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/reset-password")
def reset_password(body: PasswordReset, current_user: CurrentUser = Depends(get_current_user)):
    # Verify new password strength (12+ chars, mixed cases, digits, symbols)
    pw = body.new_password
    if len(pw) < 12 or not any(c.islower() for c in pw) or not any(c.isupper() for c in pw) \
       or not any(c.isdigit() for c in pw) or not any(not c.isalnum() for c in pw):
        raise HTTPException(status_code=400, detail="Password does not meet complexity requirements.")

    new_hash = pwd_context.hash(pw)
    with psycopg.connect(settings.POSTGRES_URL, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE users 
                SET password_hash = %s, must_reset_password = FALSE, password_set_at = NOW() 
                WHERE username = %s
                """,
                (new_hash, current_user.username)
            )
            
    return {"status": "success", "message": "Password reset successfully."}

@router.post("/logout")
def logout():
    # Since we are using stateless JWT, logout is primarily handled client side 
    # (by discarding the token). To fully invalidate, a token blacklist is required,
    # but returning success is fine for simple logout flow.
    return {"status": "success", "message": "Logged out successfully."}
