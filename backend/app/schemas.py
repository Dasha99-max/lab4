import re
import string
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

LOGIN_RE = re.compile(r"^[A-Za-z0-9._-]{3,32}$")


class RegisterIn(BaseModel):
    login: str
    password: str

    @field_validator("login")
    @classmethod
    def check_login(cls, v: str) -> str:
        if not LOGIN_RE.fullmatch(v):
            raise ValueError(
                "Логин: от 3 до 32 символов, только латинские буквы, цифры, точка, подчёркивание и дефис"
            )
        return v

    @field_validator("password")
    @classmethod
    def check_password(cls, v: str) -> str:
        problems = []
        if len(v) < 8:
            problems.append("минимум 8 символов")
        if len(v) > 128:
            problems.append("максимум 128 символов")
        if not any(c.isupper() for c in v):
            problems.append("одну заглавную букву")
        if not any(c.islower() for c in v):
            problems.append("одну строчную букву")
        if not any(c.isdigit() for c in v):
            problems.append("одну цифру")
        if not any(c in string.punctuation for c in v):
            problems.append("один специальный символ")
        if problems:
            raise ValueError("Слабый пароль, требуется: " + ", ".join(problems))
        return v


class LoginIn(BaseModel):
    login: str = Field(max_length=64)
    password: str = Field(max_length=128)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    login: str


class ResourceIn(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    content: str = Field(default="", max_length=5000)


class PermissionIn(BaseModel):
    login: str = Field(min_length=1, max_length=64)
    can_read: bool = False
    can_update: bool = False
    can_delete: bool = False


class PermissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    login: str
    can_read: bool
    can_update: bool
    can_delete: bool


class Perms(BaseModel):
    read: bool
    update: bool
    delete: bool


class ResourceListItem(BaseModel):
    id: int
    title: str
    owner_login: str
    is_owner: bool
    my_permissions: Perms


class ResourceOut(BaseModel):
    id: int
    title: str
    content: str
    owner_login: str
    created_at: datetime
    updated_at: datetime
