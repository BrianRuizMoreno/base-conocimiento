"""Security utilities: PIN hashing, API key generation, encryption."""

import bcrypt
import hashlib
import secrets
import string
from cryptography.fernet import Fernet
import os


def verify_pin(pin: str, hashed: str) -> bool:
    """Verify a PIN against its bcrypt hash."""
    return bcrypt.checkpw(pin.encode(), hashed.encode())


def hash_pin(pin: str) -> str:
    """Hash a PIN with bcrypt."""
    return bcrypt.hashpw(pin.encode(), bcrypt.gensalt()).decode()


def generate_api_key() -> tuple[str, str]:
    """Generate a new API key. Returns (full_key, prefix)."""
    prefix = "rk_" + secrets.token_hex(4)
    secret = secrets.token_urlsafe(32)
    full_key = f"{prefix}{secret}"
    return full_key, prefix


def hash_api_key(key: str) -> str:
    """Hash an API key with SHA256."""
    return hashlib.sha256(key.encode()).hexdigest()


def get_encryption_key() -> bytes:
    """Get or generate Fernet encryption key from SECRET_KEY."""
    import base64
    secret = os.getenv("SECRET_KEY")
    if not secret or secret == "default-secret-key":
        raise RuntimeError(
            "SECRET_KEY no esta configurada. "
            "Establece una clave segura de al menos 32 caracteres en el archivo .env"
        )
    # Derive 32-byte key from secret and encode as base64-urlsafe (Fernet requirement)
    key = hashlib.sha256(secret.encode()).digest()
    return base64.urlsafe_b64encode(key)


def encrypt_value(value: str) -> str:
    """Encrypt a value (e.g., API key)."""
    f = Fernet(get_encryption_key())
    return f.encrypt(value.encode()).decode()


def decrypt_value(encrypted: str) -> str:
    """Decrypt a value."""
    f = Fernet(get_encryption_key())
    return f.decrypt(encrypted.encode()).decode()
