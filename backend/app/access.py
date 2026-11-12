"""Дискреционная модель доступа: решение принимается только на backend.

- владелец ресурса имеет все права (read/update/delete) и один может выдавать права другим;
- не-владелец имеет ровно те права, которые отмечены в resource_permissions;
- всё остальное запрещено (403). """

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .logging_config import event
import logging
from .models import Resource, ResourcePermission, User

ACTIONS = {"read": "чтение", "update": "изменение", "delete": "удаление"}


def effective_permissions(db: Session, resource: Resource, user: User) -> dict[str, bool]:
    if resource.owner_id == user.id:
        return {"read": True, "update": True, "delete": True}
    perm = db.scalar(
        select(ResourcePermission).where(
            ResourcePermission.user_id == user.id, ResourcePermission.resource_id == resource.id
        )
    )
    if perm is None:
        return {"read": False, "update": False, "delete": False}
    return {"read": perm.can_read, "update": perm.can_update, "delete": perm.can_delete}


def load_resource(db: Session, resource_id: int) -> Resource:
    resource = db.get(Resource, resource_id)
    if resource is None:
        raise HTTPException(404, "Ресурс не найден")
    return resource


def authorize(db: Session, resource_id: int, user: User, action: str) -> Resource:
    resource = load_resource(db, resource_id)
    if not effective_permissions(db, resource, user)[action]:
        event(logging.INFO, "access_denied", user=user.login, resource_id=resource_id, action=action)
        raise HTTPException(403, f"Доступ запрещён: у вас нет права на {ACTIONS[action]} этого ресурса")
    return resource


def authorize_owner(db: Session, resource_id: int, user: User) -> Resource:
    resource = load_resource(db, resource_id)
    if resource.owner_id != user.id:
        event(logging.INFO, "access_denied", user=user.login, resource_id=resource_id, action="grant")
        raise HTTPException(403, "Доступ запрещён: выдавать права может только владелец ресурса")
    return resource
