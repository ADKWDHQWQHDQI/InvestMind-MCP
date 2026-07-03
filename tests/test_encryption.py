import pytest
from src.security.encryption import EncryptionManager
from cryptography.exceptions import InvalidTag

def test_encryption_decryption_roundtrip():
    passphrase = "my-secure-password"
    data = '{"portfolio": [{"symbol": "REC", "quantity": 100}]}'
    
    # 1. Derive key
    key, salt = EncryptionManager.derive_key(passphrase)
    assert len(key) == 32
    assert len(salt) == 16
    
    # 2. Encrypt
    encrypted_payload = EncryptionManager.encrypt(data, key)
    assert "nonce" in encrypted_payload
    assert "ciphertext" in encrypted_payload
    
    # 3. Decrypt
    decrypted_data = EncryptionManager.decrypt(encrypted_payload, key)
    assert decrypted_data == data

def test_decryption_fails_with_wrong_key():
    passphrase = "my-secure-password"
    wrong_passphrase = "wrong-password"
    data = "sensitive information"
    
    key, salt = EncryptionManager.derive_key(passphrase)
    wrong_key, _ = EncryptionManager.derive_key(wrong_passphrase, salt)
    
    encrypted_payload = EncryptionManager.encrypt(data, key)
    
    # Decrypting with wrong key should raise InvalidTag (AES-GCM integrity check failure)
    with pytest.raises(InvalidTag):
        EncryptionManager.decrypt(encrypted_payload, wrong_key)

def test_key_derivation_is_consistent():
    passphrase = "test-password"
    key1, salt1 = EncryptionManager.derive_key(passphrase)
    
    # Deriving again with the same salt must yield the same key
    key2, salt2 = EncryptionManager.derive_key(passphrase, salt1)
    assert key1 == key2
    assert salt1 == salt2
