"""Хэширование паролей (Argon2id / bcrypt) и токены доступа."""
import base64
import hashlib
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerificationError

from .config import settings

# Argon2id: соль генерируется автоматически и входит в строку хэша.
_argon = PasswordHasher(
    time_cost=settings.argon2_time_cost,
    memory_cost=settings.argon2_memory_cost,
    parallelism=settings.argon2_parallelism,
    type=Type.ID,
)


def _bcrypt_input(password: str) -> bytes:
    # bcrypt принимает максимум 72 байта: предварительно сворачиваем пароль в SHA-256 (base64).
    return base64.b64encode(hashlib.sha256(password.encode()).digest())


def hash_password(password: str) -> str:
    if settings.hash_scheme == "bcrypt":
        return bcrypt.hashpw(_bcrypt_input(password), bcrypt.gensalt(rounds=settings.bcrypt_rounds)).decode()
    return _argon.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        if password_hash.startswith("$argon2"):
            return _argon.verify(password_hash, password)
        if password_hash.startswith("$2"):
            return bcrypt.checkpw(_bcrypt_input(password), password_hash.encode())
    except (VerificationError, InvalidHashError, ValueError):
        return False
    return False


def create_token(user_id: int) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=settings.token_ttl_minutes)
    return jwt.encode({"sub": str(user_id), "exp": exp}, settings.secret_key, algorithm="HS256")


def decode_token(token: str) -> int | None:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        return int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None
