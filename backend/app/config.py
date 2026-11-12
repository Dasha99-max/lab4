"""Конфигурация из переменных окружения (.env)."""
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_env: str = os.getenv("APP_ENV", "development")
    port: int = int(os.getenv("PORT", "8000"))
    database_url: str = os.getenv("DATABASE_URL", "sqlite://")
    secret_key: str = os.getenv("SECRET_KEY", "dev-only-secret-change-me")
    token_ttl_minutes: int = int(os.getenv("TOKEN_TTL_MINUTES", "60"))
    hash_scheme: str = os.getenv("HASH_SCHEME", "argon2id").lower()
    argon2_time_cost: int = int(os.getenv("ARGON2_TIME_COST", "3"))
    argon2_memory_cost: int = int(os.getenv("ARGON2_MEMORY_COST", "65536"))
    argon2_parallelism: int = int(os.getenv("ARGON2_PARALLELISM", "4"))
    bcrypt_rounds: int = int(os.getenv("BCRYPT_ROUNDS", "12"))


settings = Settings()
