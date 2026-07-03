import os
import base64
import json
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

class EncryptionManager:
    @staticmethod
    def derive_key(passphrase: str, salt: bytes = None) -> tuple[bytes, bytes]:
        """
        Derive a 32-byte key from a passphrase using PBKDF2-HMAC-SHA256.
        Returns a tuple of (derived_key, salt).
        """
        if salt is None:
            salt = os.urandom(16)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = kdf.derive(passphrase.encode())
        return key, salt

    @staticmethod
    def encrypt(data: str, key: bytes) -> str:
        """
        Encrypt a UTF-8 string using AES-256-GCM.
        Returns a base64 encoded JSON string containing the nonce and ciphertext.
        """
        aesgcm = AESGCM(key)
        nonce = os.urandom(12)  # Recommended nonce length for AES-GCM
        ciphertext = aesgcm.encrypt(nonce, data.encode('utf-8'), None)
        
        payload = {
            "nonce": base64.b64encode(nonce).decode('utf-8'),
            "ciphertext": base64.b64encode(ciphertext).decode('utf-8')
        }
        return json.dumps(payload)

    @staticmethod
    def decrypt(encrypted_payload_str: str, key: bytes) -> str:
        """
        Decrypt an AES-256-GCM encrypted payload JSON string.
        Returns the decrypted UTF-8 string.
        """
        payload = json.loads(encrypted_payload_str)
        nonce = base64.b64decode(payload["nonce"])
        ciphertext = base64.b64decode(payload["ciphertext"])
        
        aesgcm = AESGCM(key)
        decrypted_bytes = aesgcm.decrypt(nonce, ciphertext, None)
        return decrypted_bytes.decode('utf-8')
