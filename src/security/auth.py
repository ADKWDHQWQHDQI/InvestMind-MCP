import contextvars
import jwt
from datetime import datetime, timedelta
from fastapi import Request, HTTPException, status
from src.config import settings

# Thread-local / Request-local context variables for the authenticated request (concurrent SSE)
current_user_id: contextvars.ContextVar[str] = contextvars.ContextVar("current_user_id", default="")
current_decryption_key: contextvars.ContextVar[bytes] = contextvars.ContextVar("current_decryption_key", default=b"")

# Process-level session state fallback (single-user stdio CLI session)
_session_user_id = ""
_session_decryption_key = b""

def set_stdio_session(user_id: str, key_bytes: bytes):
    """
    Sets the global process-level session parameters for stdio transport.
    """
    global _session_user_id, _session_decryption_key
    _session_user_id = user_id
    _session_decryption_key = key_bytes

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

def create_access_token(user_id: str, derived_key_hex: str) -> str:
    """
    Creates a JWT access token containing the user_id and the derived encryption key.
    The derived key is stored in the client-held token for session duration.
    """
    expire = datetime.utcnow() + timedelta(minutes=settings.TOKEN_EXPIRE_MINUTES)
    to_encode = {
        "sub": user_id,
        "key": derived_key_hex,
        "exp": expire
    }
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> tuple[str, bytes]:
    """
    Decodes and validates a JWT token.
    Returns a tuple of (user_id, derived_key_bytes).
    Raises jwt.PyJWTError if validation fails.
    """
    payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    user_id: str = payload.get("sub")
    key_hex: str = payload.get("key")
    if not user_id or not key_hex:
        raise jwt.PyJWTError("Token is missing required payload claims.")
    return user_id, bytes.fromhex(key_hex)

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
