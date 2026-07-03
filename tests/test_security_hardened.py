"""
Hardened security tests for InvestMind MCP Server.
Covers: PBKDF2 password hashing, email verification codes, production registration block,
broker overwrite safety, and ISIN checksum validation.
"""
import pytest
import os
import hashlib
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock


# ─── PBKDF2 Password Hashing ────────────────────────────────────────────────

def hash_password(password: str, salt: bytes) -> str:
    """Mirror of the production hash_password for testing."""
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000).hex()


def test_pbkdf2_hash_is_deterministic():
    """Same password + salt must always produce the same hash."""
    salt = b"\x00" * 16
    h1 = hash_password("my-secure-password", salt)
    h2 = hash_password("my-secure-password", salt)
    assert h1 == h2


def test_pbkdf2_different_passwords_produce_different_hashes():
    """Different passwords must produce different hashes."""
    salt = os.urandom(16)
    h1 = hash_password("password-a", salt)
    h2 = hash_password("password-b", salt)
    assert h1 != h2


def test_pbkdf2_different_salts_produce_different_hashes():
    """Same password with different salts must produce different hashes."""
    h1 = hash_password("same-password", b"\x00" * 16)
    h2 = hash_password("same-password", b"\xff" * 16)
    assert h1 != h2


def test_pbkdf2_hash_length():
    """PBKDF2-HMAC-SHA256 with 32-byte key should produce 64-char hex string."""
    salt = os.urandom(16)
    h = hash_password("test-password", salt)
    assert len(h) == 64  # 32 bytes = 64 hex chars


# ─── Email Verification Codes ───────────────────────────────────────────────

@pytest.mark.anyio
async def test_verify_email_correct_code():
    """Correct verification code within expiry should succeed."""
    from src.tools.auth import hash_password as prod_hash, verify_email
    from src.security.auth import current_user_id, current_decryption_key
    from src.security.encryption import EncryptionManager

    uid = "test_verify_user"
    salt = os.urandom(16)
    code = "482917"
    code_hash = prod_hash(code, salt)
    expiry = datetime.utcnow() + timedelta(minutes=15)

    key, _ = EncryptionManager.derive_key("test-passphrase")
    current_user_id.set(uid)
    current_decryption_key.set(key)

    mock_user = {
        "user_id": uid,
        "salt": salt.hex(),
        "email_verification_hash": code_hash,
        "email_verification_expires_at": expiry
    }

    mock_db = MagicMock()
    mock_db["users"].find_one = AsyncMock(return_value=mock_user)
    mock_db["users"].update_one = AsyncMock()

    with patch("src.tools.auth.get_db", return_value=mock_db):
        result = await verify_email(code)
        assert result["success"] is True
        assert "verified" in result["message"].lower()


@pytest.mark.anyio
async def test_verify_email_wrong_code():
    """Wrong verification code should fail."""
    from src.tools.auth import hash_password as prod_hash, verify_email
    from src.security.auth import current_user_id, current_decryption_key
    from src.security.encryption import EncryptionManager

    uid = "test_verify_user_wrong"
    salt = os.urandom(16)
    correct_code = "482917"
    code_hash = prod_hash(correct_code, salt)
    expiry = datetime.utcnow() + timedelta(minutes=15)

    key, _ = EncryptionManager.derive_key("test-passphrase")
    current_user_id.set(uid)
    current_decryption_key.set(key)

    mock_user = {
        "user_id": uid,
        "salt": salt.hex(),
        "email_verification_hash": code_hash,
        "email_verification_expires_at": expiry
    }

    mock_db = MagicMock()
    mock_db["users"].find_one = AsyncMock(return_value=mock_user)

    with patch("src.tools.auth.get_db", return_value=mock_db):
        result = await verify_email("000000")  # Wrong code
        assert result["success"] is False
        assert "invalid" in result["message"].lower()


@pytest.mark.anyio
async def test_verify_email_expired_code():
    """Expired verification code should fail."""
    from src.tools.auth import hash_password as prod_hash, verify_email
    from src.security.auth import current_user_id, current_decryption_key
    from src.security.encryption import EncryptionManager

    uid = "test_verify_user_expired"
    salt = os.urandom(16)
    code = "482917"
    code_hash = prod_hash(code, salt)
    expiry = datetime.utcnow() - timedelta(minutes=1)  # Already expired

    key, _ = EncryptionManager.derive_key("test-passphrase")
    current_user_id.set(uid)
    current_decryption_key.set(key)

    mock_user = {
        "user_id": uid,
        "salt": salt.hex(),
        "email_verification_hash": code_hash,
        "email_verification_expires_at": expiry
    }

    mock_db = MagicMock()
    mock_db["users"].find_one = AsyncMock(return_value=mock_user)

    with patch("src.tools.auth.get_db", return_value=mock_db):
        result = await verify_email(code)
        assert result["success"] is False
        assert "expired" in result["message"].lower()


# ─── Production Registration Block ──────────────────────────────────────────

@pytest.mark.anyio
async def test_register_user_blocked_in_production():
    """register_user should refuse when ENV=production."""
    from src.tools.auth import register_user

    with patch.dict(os.environ, {"ENV": "production"}):
        result = await register_user("newuser", "new@example.com", "password123")
        assert result["success"] is False
        assert "disabled" in result["message"].lower() or "production" in result["message"].lower()


@pytest.mark.anyio
async def test_register_user_allowed_in_development():
    """register_user should work when ENV is not production."""
    from src.tools.auth import register_user

    mock_db = MagicMock()
    mock_db["users"].find_one = AsyncMock(return_value=None)  # No existing user
    mock_db["users"].insert_one = AsyncMock()
    mock_db["portfolios"].update_one = AsyncMock()

    with patch.dict(os.environ, {"ENV": "development"}, clear=False):
        with patch("src.tools.auth.get_db", return_value=mock_db):
            result = await register_user("devuser", "dev@example.com", "devpassword")
            assert result["success"] is True
            assert "registered" in result["message"].lower()


# ─── Broker Overwrite Safety ────────────────────────────────────────────────

@pytest.mark.anyio
async def test_refresh_portfolio_does_not_save_mock_data():
    """refresh_portfolio for mock brokers must NOT call save_portfolio."""
    from src.tools.portfolio_conn import refresh_portfolio
    from src.security.auth import current_user_id, current_decryption_key
    from src.security.encryption import EncryptionManager

    uid = "broker_test_user"
    key, _ = EncryptionManager.derive_key("test-passphrase")
    current_user_id.set(uid)
    current_decryption_key.set(key)

    with patch("src.tools.portfolio_conn.get_connection_status") as mock_status, \
         patch("src.tools.portfolio_conn.save_portfolio") as mock_save:

        mock_status.return_value = {"connected": True, "type": "Zerodha"}

        result = await refresh_portfolio()

        # save_portfolio should NEVER be called for mock broker data
        mock_save.assert_not_called()
        assert result["success"] is True
        assert result.get("is_simulated") is True


# ─── ISIN Checksum Validation ───────────────────────────────────────────────

def test_valid_isin_rec():
    """INE020B01018 (REC Ltd) should pass ISIN checksum validation."""
    from src.parser.cas_parser import validate_isin
    assert validate_isin("INE020B01018") is True


def test_valid_isin_infy():
    """INE009A01021 (Infosys) should pass ISIN checksum validation."""
    from src.parser.cas_parser import validate_isin
    assert validate_isin("INE009A01021") is True


def test_invalid_isin_bad_checkdigit():
    """ISIN with wrong check digit should fail."""
    from src.parser.cas_parser import validate_isin
    assert validate_isin("INE020B01019") is False  # 9 instead of 8


def test_invalid_isin_too_short():
    """Short ISIN should fail."""
    from src.parser.cas_parser import validate_isin
    assert validate_isin("INE020B010") is False


def test_invalid_isin_non_indian():
    """Non-Indian ISIN should fail."""
    from src.parser.cas_parser import validate_isin
    assert validate_isin("US0378331005") is False
