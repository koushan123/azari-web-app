from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

_password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    """Hash a bounded plaintext password with Argon2id."""
    if not password:
        raise ValueError("Password must not be empty")
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Safely verify a password without exposing verification details."""
    try:
        return _password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False
