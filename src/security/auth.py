import contextvars
import jwt
import uuid
import logging
from datetime import datetime, timedelta
from fastapi import Request, HTTPException, status
from src.config import settings

logger = logging.getLogger("investmind.security.auth")

# Thread-local / Request-local context variables for the authenticated request (concurrent SSE)
current_user_id: contextvars.ContextVar[str] = contextvars.ContextVar("current_user_id", default="")
current_decryption_key: contextvars.ContextVar[bytes] = contextvars.ContextVar("current_decryption_key", default=b"")

# Process-level session state fallback (single-user stdio CLI session)
_session_user_id = ""
_session_decryption_key = b""

# In-memory secure session storage: session_id (str) -> {"user_id": str, "decryption_key": bytes, "expires_at": datetime}
_active_sessions = {}

def set_stdio_session(user_id: str, key_bytes: bytes):
    """
    Sets the global process-level session parameters for stdio transport.
    """
    global _session_user_id, _session_decryption_key
    _session_user_id = user_id
    _session_decryption_key = key_bytes

def register_session(user_id: str, key_bytes: bytes, expire_minutes: int = 60) -> str:
    """
    Registers a new session in-memory, mapping a random session ID to the derived decryption key.
    """
    # Periodic cleanup of expired sessions during new registration
    now = datetime.utcnow()
    expired_keys = [k for k, v in _active_sessions.items() if v["expires_at"] < now]
    for k in expired_keys:
        _active_sessions.pop(k, None)

    session_id = str(uuid.uuid4())
    expires_at = now + timedelta(minutes=expire_minutes)
    _active_sessions[session_id] = {
        "user_id": user_id,
        "decryption_key": key_bytes,
        "expires_at": expires_at
    }
    return session_id

def get_authenticated_context() -> tuple[str, bytes]:
    """
    Retrieves the user ID and decryption key for the current request.
    Favors Request-local contextvars, falling back to process-level stdio session state.
    """
    uid = current_user_id.get()
    key = current_decryption_key.get()
    
    if uid and key:
        return uid, key
        
    if _session_user_id and _session_decryption_key:
        return _session_user_id, _session_decryption_key
        
    raise ValueError("Unauthorized or session key missing. Please authenticate using the login tool.")

def create_access_token(user_id: str, session_id: str) -> str:
    """
    Creates a JWT access token containing the user_id and session_id (referencing key in RAM).
    """
    expire = datetime.utcnow() + timedelta(minutes=settings.TOKEN_EXPIRE_MINUTES)
    to_encode = {
        "sub": user_id,
        "sid": session_id,
        "exp": expire
    }
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> tuple[str, bytes]:
    """
    Decodes a JWT token and retrieves the decryption key from the in-memory session cache.
    """
    # Periodic cleanup of expired sessions during decode
    now = datetime.utcnow()
    expired_keys = [k for k, v in _active_sessions.items() if v["expires_at"] < now]
    for k in expired_keys:
        _active_sessions.pop(k, None)

    payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    user_id: str = payload.get("sub")
    session_id: str = payload.get("sid")
    if not user_id or not session_id:
        raise jwt.PyJWTError("Token is missing required payload claims.")
        
    session_data = _active_sessions.get(session_id)
    if not session_data:
        raise jwt.PyJWTError("Session has expired or is invalid. Please log in again.")
        
    return user_id, session_data["decryption_key"]

async def authenticate_request(request: Request) -> str:
    """
    HTTP dependency to authenticate incoming FastAPI requests.
    Validates Bearer token in Authorization header or token query parameter,
    populates the contextvars, and returns the user_id.
    """
    token = None
    
    # 1. Check Authorization header
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        token = auth_header[7:]
        
    # 2. Check query parameter fallback (for EventSource/SSE connection)
    if not token:
        token = request.query_params.get("token")
        
    if not token:
        path = request.url.path
        if path in ("/sse", "/messages"):
            uid = "local_user"
            session_data = _active_sessions.get("local_session")
            key_bytes = session_data["decryption_key"] if session_data else b""
            current_user_id.set(uid)
            current_decryption_key.set(key_bytes)
            return uid
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication token is missing. Please provide a Bearer token or a token query parameter."
            )
        
    try:
        user_id, key_bytes = decode_access_token(token)
        current_user_id.set(user_id)
        current_decryption_key.set(key_bytes)
        return user_id
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired authentication token: {str(e)}"
        )
