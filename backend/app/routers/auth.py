import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import current_user
from ..logging_config import event
from ..models import User
from ..schemas import LoginIn, RegisterIn, TokenOut
from ..security import create_token, hash_password, verify_password

router = APIRouter(prefix="/api", tags=["auth"])

_DUMMY_HASH = hash_password("dummy-Password-1!")  # выравнивает время ответа для несуществующего логина


@router.post("/register", status_code=201)
def register(data: RegisterIn, db: Session = Depends(get_db)):
    taken = HTTPException(409, "Этот логин уже занят")
    if db.scalar(select(User.id).where(User.login == data.login)):
        event(logging.INFO, "register_login_taken", login=data.login)
        raise taken
    user = User(login=data.login, password_hash=hash_password(data.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:  # гонка: уникальный индекс защищает от дубля
        db.rollback()
        event(logging.INFO, "register_login_taken", login=data.login)
        raise taken
    event(logging.INFO, "user_registered", login=data.login, user_id=user.id)
    return {"message": "user создан"}


@router.post("/login", response_model=TokenOut)
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.login == data.login))
    ok = verify_password(data.password, user.password_hash if user else _DUMMY_HASH)
    if not user or not ok:
        event(logging.INFO, "login_failed", login=data.login[:64])
        raise HTTPException(401, "Неверный логин или пароль")
    event(logging.INFO, "login_ok", login=user.login)
    return TokenOut(access_token=create_token(user.id), login=user.login)


@router.get("/me")
def me(user: User = Depends(current_user)):
    return {"id": user.id, "login": user.login}
