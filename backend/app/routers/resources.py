import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..access import authorize, authorize_owner, effective_permissions
from ..database import get_db
from ..deps import current_user
from ..logging_config import event
from ..models import Resource, ResourcePermission, User
from ..schemas import PermissionIn, PermissionOut, Perms, ResourceIn, ResourceListItem, ResourceOut

router = APIRouter(prefix="/api", tags=["resources"])


def _out(r: Resource) -> ResourceOut:
    return ResourceOut(
        id=r.id, title=r.title, content=r.content, owner_login=r.owner.login,
        created_at=r.created_at, updated_at=r.updated_at,
    )


@router.get("/users")
def list_users(_: User = Depends(current_user), db: Session = Depends(get_db)):
    return [u.login for u in db.scalars(select(User).order_by(User.login))]


@router.post("/resources", status_code=201, response_model=ResourceOut)
def create_resource(data: ResourceIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    r = Resource(owner_id=user.id, title=data.title, content=data.content)
    db.add(r)
    db.commit()
    db.refresh(r)
    event(logging.INFO, "resource_created", user=user.login, resource_id=r.id)
    return _out(r)


@router.get("/resources", response_model=list[ResourceListItem])
def list_resources(user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Свои ресурсы и те, где у пользователя есть хотя бы одно право. Содержимое здесь не отдаётся."""
    shared_ids = select(ResourcePermission.resource_id).where(
        ResourcePermission.user_id == user.id,
        (ResourcePermission.can_read | ResourcePermission.can_update | ResourcePermission.can_delete),
    )
    rows = db.scalars(
        select(Resource).where((Resource.owner_id == user.id) | Resource.id.in_(shared_ids)).order_by(Resource.id)
    ).all()
    return [
        ResourceListItem(
            id=r.id, title=r.title, owner_login=r.owner.login, is_owner=r.owner_id == user.id,
            my_permissions=Perms(**effective_permissions(db, r, user)),
        )
        for r in rows
    ]


@router.get("/resources/{resource_id}", response_model=ResourceOut)
def read_resource(resource_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    r = authorize(db, resource_id, user, "read")
    event(logging.INFO, "resource_read", user=user.login, resource_id=r.id)
    return _out(r)


@router.put("/resources/{resource_id}", response_model=ResourceOut)
def update_resource(
    resource_id: int, data: ResourceIn, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    r = authorize(db, resource_id, user, "update")
    r.title, r.content, r.updated_at = data.title, data.content, datetime.now(timezone.utc)
    db.commit()
    db.refresh(r)
    event(logging.INFO, "resource_updated", user=user.login, resource_id=r.id)
    return _out(r)


@router.delete("/resources/{resource_id}", status_code=204)
def delete_resource(resource_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    r = authorize(db, resource_id, user, "delete")
    db.delete(r)
    db.commit()
    event(logging.INFO, "resource_deleted", user=user.login, resource_id=resource_id)
    return Response(status_code=204)


@router.get("/resources/{resource_id}/permissions", response_model=list[PermissionOut])
def list_permissions(resource_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    authorize_owner(db, resource_id, user)
    perms = db.scalars(select(ResourcePermission).where(ResourcePermission.resource_id == resource_id)).all()
    return [
        PermissionOut(login=p.user.login, can_read=p.can_read, can_update=p.can_update, can_delete=p.can_delete)
        for p in perms
    ]


@router.put("/resources/{resource_id}/permissions", response_model=PermissionOut)
def grant_permission(
    resource_id: int, data: PermissionIn, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    """Владелец выдаёт/меняет права другому пользователю. Все три флага False = право отозвано."""
    r = authorize_owner(db, resource_id, user)
    target = db.scalar(select(User).where(User.login == data.login))
    if target is None:
        raise HTTPException(404, "Пользователь не найден")
    if target.id == r.owner_id:
        raise HTTPException(400, "Владелец и так имеет все права на свой ресурс")
    perm = db.scalar(
        select(ResourcePermission).where(
            ResourcePermission.user_id == target.id, ResourcePermission.resource_id == r.id
        )
    )
    if perm is None:
        perm = ResourcePermission(user_id=target.id, resource_id=r.id)
        db.add(perm)
    perm.can_read, perm.can_update, perm.can_delete = data.can_read, data.can_update, data.can_delete
    db.commit()
    event(
        logging.INFO, "permission_granted", owner=user.login, grantee=target.login, resource_id=r.id,
        can_read=data.can_read, can_update=data.can_update, can_delete=data.can_delete,
    )
    return PermissionOut(login=target.login, **data.model_dump(exclude={"login"}))
