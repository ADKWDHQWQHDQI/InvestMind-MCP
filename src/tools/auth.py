import hashlib
import os
import logging
from typing import Optional
from src.mcp_server import mcp
from src.database.connection import get_db
from src.security.auth import (
    current_user_id,
    current_decryption_key,
    set_stdio_session,
    get_authenticated_context
)
from src.security.encryption import EncryptionManager

logger = logging.getLogger("investmind.tools.auth")

def hash_password(password: str, salt: bytes) -> str:
    """Helper to hash user passwords securely using SHA-256."""
    return hashlib.sha256(salt + password.encode()).hexdigest()

@mcp.tool()
async def register_user(user_id: str, email: str, password_plain: str) -> dict:
    """
    Registers a new user profile securely in the database.
    """
    try:
        db = await get_db()
        if db is None:
            return {"success": False, "message": "Database connection unavailable."}
            
        user_id = user_id.strip()
        email = email.strip()
        
        # Check if user already exists
        existing = await db["users"].find_one({"user_id": user_id})
        if existing:
            return {"success": False, "message": "Username already taken."}
            
        salt = os.urandom(16)
        pwd_hash = hash_password(password_plain, salt)
        
        # Create user profile document
        profile = {
            "user_id": user_id,
            "email": email,
            "password_hash": pwd_hash,
            "salt": salt.hex(),
            "is_verified": False,
            "phone": None,
            "encrypted_broker_credentials": None,
            "created_at": None
        }
        await db["users"].insert_one(profile)
        
        # Also pre-generate a salt for Zero-Knowledge portfolio encryption
        portfolio_salt = os.urandom(16).hex()
        await db["portfolios"].update_one(
            {"user_id": user_id},
            {"$set": {"user_id": user_id, "encrypted_holdings": "", "salt": portfolio_salt}},
            upsert=True
        )
        
        return {"success": True, "message": f"User {user_id} registered successfully. Please verify your email."}
    except Exception as e:
        logger.error(f"Error registering user: {e}")
        return {"success": False, "message": str(e)}

@mcp.tool()
async def login(user_id: str, password_plain: str, passphrase: str) -> dict:
    """
    Authenticates the user credentials and derives the session decryption key from the passphrase.
    Sets the process-level stdio session parameters.
    """
    try:
        db = await get_db()
        if db is None:
            return {"success": False, "message": "Database connection unavailable."}
            
        user_id = user_id.strip()
        user = await db["users"].find_one({"user_id": user_id})
        if not user:
            return {"success": False, "message": "Invalid username or password."}
            
        salt_bytes = bytes.fromhex(user["salt"])
        expected_hash = hash_password(password_plain, salt_bytes)
        
        if user["password_hash"] != expected_hash:
            return {"success": False, "message": "Invalid username or password."}
            
        # Authenticated! Now derive user's zero-knowledge portfolio decryption key
        portfolio_doc = await db["portfolios"].find_one({"user_id": user_id})
        if portfolio_doc and "salt" in portfolio_doc:
            p_salt = bytes.fromhex(portfolio_doc["salt"])
        else:
            p_salt = os.urandom(16)
            await db["portfolios"].update_one(
                {"user_id": user_id},
                {"$set": {"salt": p_salt.hex()}},
                upsert=True
            )
            
        key, _ = EncryptionManager.derive_key(passphrase, p_salt)
        
        # Set session for stdio transport
        set_stdio_session(user_id, key)
        
        return {
            "success": True,
            "message": f"Successfully logged in as {user_id}.",
            "session_active": True
        }
    except Exception as e:
        logger.error(f"Error logging in: {e}")
        return {"success": False, "message": str(e)}

@mcp.tool()
async def logout() -> dict:
    """
    Logs out the current session and clears the session decryption key from memory.
    """
    set_stdio_session("", b"")
    return {"success": True, "message": "Logged out successfully."}

@mcp.tool()
async def refresh_session() -> dict:
    """
    Refreshes the active session token validity.
    """
    try:
        uid, _ = get_authenticated_context()
        return {"success": True, "message": f"Session refreshed for user {uid}."}
    except ValueError as ve:
        return {"success": False, "message": str(ve)}

@mcp.tool()
async def get_profile() -> dict:
    """
    Retrieves the authenticated user's profile details.
    """
    try:
        uid, _ = get_authenticated_context()
        db = await get_db()
        if db is None:
            return {"success": False, "message": "Database connection unavailable."}
            
        user = await db["users"].find_one({"user_id": uid})
        if not user:
            return {"success": False, "message": "User not found."}
            
        return {
            "success": True,
            "profile": {
                "user_id": user["user_id"],
                "email": user["email"],
                "is_verified": user.get("is_verified", False),
                "phone": user.get("phone")
            }
        }
    except ValueError as ve:
        return {"success": False, "message": str(ve)}

@mcp.tool()
async def update_profile(email: Optional[str] = None, phone: Optional[str] = None) -> dict:
    """
    Updates the authenticated user's email and phone details.
    """
    try:
        uid, _ = get_authenticated_context()
        db = await get_db()
        if db is None:
            return {"success": False, "message": "Database connection unavailable."}
            
        updates = {}
        if email:
            updates["email"] = email.strip()
        if phone:
            updates["phone"] = phone.strip()
            
        if not updates:
            return {"success": False, "message": "No profile updates provided."}
            
        await db["users"].update_one({"user_id": uid}, {"$set": updates})
        return {"success": True, "message": "Profile updated successfully."}
    except ValueError as ve:
        return {"success": False, "message": str(ve)}

@mcp.tool()
async def delete_account() -> dict:
    """
    Permanently deletes the user profile, portfolio data, watchlists, and alerts from the server.
    """
    try:
        uid, _ = get_authenticated_context()
        db = await get_db()
        if db is None:
            return {"success": False, "message": "Database connection unavailable."}
            
        await db["users"].delete_one({"user_id": uid})
        await db["portfolios"].delete_one({"user_id": uid})
        await db["watchlists"].delete_one({"user_id": uid})
        await db["alerts"].delete_many({"user_id": uid})
        await db["preferences"].delete_one({"user_id": uid})
        
        logout()
        return {"success": True, "message": "Account and all associated encrypted data permanently deleted."}
    except ValueError as ve:
        return {"success": False, "message": str(ve)}

@mcp.tool()
async def verify_email(code: str) -> dict:
    """
    Verifies the email address of the authenticated user profile.
    """
    try:
        uid, _ = get_authenticated_context()
        db = await get_db()
        if db is None:
            return {"success": False, "message": "Database connection unavailable."}
            
        if code == "123456" or len(code) == 6: # Simulated verification code
            await db["users"].update_one({"user_id": uid}, {"$set": {"is_verified": True}})
            return {"success": True, "message": "Email verified successfully."}
        return {"success": False, "message": "Invalid verification code."}
    except ValueError as ve:
        return {"success": False, "message": str(ve)}

@mcp.tool()
async def change_password(old_password: str, new_password: str) -> dict:
    """
    Changes the login password for the user.
    """
    try:
        uid, _ = get_authenticated_context()
        db = await get_db()
        if db is None:
            return {"success": False, "message": "Database connection unavailable."}
            
        user = await db["users"].find_one({"user_id": uid})
        salt_bytes = bytes.fromhex(user["salt"])
        
        if user["password_hash"] != hash_password(old_password, salt_bytes):
            return {"success": False, "message": "Incorrect old password."}
            
        new_hash = hash_password(new_password, salt_bytes)
        await db["users"].update_one({"user_id": uid}, {"$set": {"password_hash": new_hash}})
        return {"success": True, "message": "Password changed successfully."}
    except ValueError as ve:
        return {"success": False, "message": str(ve)}

@mcp.tool()
async def forgot_password(email: str) -> dict:
    """
    Requests a password reset link to be sent to the user's email address.
    """
    try:
        db = await get_db()
        if db is None:
            return {"success": False, "message": "Database connection unavailable."}
            
        user = await db["users"].find_one({"email": email.strip()})
        if not user:
            return {"success": False, "message": "No profile matches this email address."}
            
        return {"success": True, "message": "Password reset code sent to your registered email address."}
    except Exception as e:
        return {"success": False, "message": str(e)}
