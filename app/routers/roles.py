import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from app.dependencies import get_db, require_permission, get_current_user
from app.models.role import Role
from app.models.permission import Permission
from app.models.user import User
from app.models.audit_log import AuditLog
from app.schemas.role import (
    RoleCreate,
    RoleUpdate,
    RoleResponse,
    PermissionResponse,
    AuditLogResponse,
)
from app.core.rbac_config import ALL_PERMISSIONS

router = APIRouter(tags=["Roles & Permissions"])


def _count_role_users(db: Session, role: Role) -> int:
    """Số người dùng đang được gán vai trò này (theo role_id mới hoặc role code cũ)."""
    return db.query(User).filter(
        (User.role_id == role.id) | (User.role == role.code)
    ).count()


def _to_role_response(db: Session, role: Role, user_count: Optional[int] = None) -> RoleResponse:
    return RoleResponse(
        id=role.id,
        code=role.code,
        name=role.name,
        description=role.description,
        is_system=role.is_system,
        permissions_version=role.permissions_version,
        permissions=[PermissionResponse.model_validate(p) for p in role.permissions],
        user_count=user_count if user_count is not None else _count_role_users(db, role),
        created_at=role.created_at,
        updated_at=role.updated_at
    )


def _write_audit_log(
    db: Session,
    actor: User,
    req: Request,
    action: str,
    target_id: str,
    target_name: str,
    summary: str,
    details: dict,
) -> None:
    audit = AuditLog(
        user_id=actor.id,
        user_name=actor.full_name,
        action=action,
        target_type="ROLE",
        target_id=target_id,
        target_name=target_name,
        changes_summary=summary,
        details_json=json.dumps(details),
        ip_address=req.client.host if req.client else None
    )
    db.add(audit)
    db.commit()


@router.get("/permissions", response_model=List[PermissionResponse])
def list_permissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all available permissions in the system."""
    perms = db.query(Permission).order_by(Permission.module, Permission.code).all()
    if not perms:
        # If DB not seeded yet, return from config
        return [
            PermissionResponse(
                id=f"perm-{p['code'].replace(':', '-')}",
                code=p["code"],
                name=p["name"],
                module=p["module"],
                description=p["description"]
            )
            for p in ALL_PERMISSIONS
        ]
    return perms


@router.get("/roles", response_model=List[RoleResponse])
def list_roles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all roles with permissions and user count."""
    roles = db.query(Role).order_by(Role.is_system.desc(), Role.name).all()
    return [_to_role_response(db, r) for r in roles]


@router.get("/roles/{role_id}", response_model=RoleResponse)
def get_role(
    role_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get single role detail by ID."""
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy vai trò với ID '{role_id}'!"
        )
    return _to_role_response(db, role)


@router.post("/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
def create_role(
    role_in: RoleCreate,
    req: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("roles:manage"))
):
    """Create a new custom role (SuperAdmin only)."""
    clean_code = role_in.code.strip().upper().replace(" ", "_")
    existing = db.query(Role).filter(Role.code == clean_code).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Mã vai trò '{clean_code}' đã tồn tại trong hệ thống!"
        )

    new_role = Role(
        code=clean_code,
        name=role_in.name.strip(),
        description=role_in.description,
        is_system=False,
        permissions_version=1
    )

    # Attach permissions
    if role_in.permission_ids:
        perms = db.query(Permission).filter(Permission.id.in_(role_in.permission_ids)).all()
        new_role.permissions = perms

    db.add(new_role)
    db.commit()
    db.refresh(new_role)

    perm_codes = [p.code for p in new_role.permissions]
    _write_audit_log(
        db, current_user, req,
        action="ROLE_CREATE",
        target_id=new_role.id,
        target_name=new_role.name,
        summary=f"Tạo vai trò mới '{new_role.name}' ({new_role.code}) với {len(perm_codes)} quyền",
        details={"after_permissions": perm_codes, "code": new_role.code},
    )

    return _to_role_response(db, new_role, user_count=0)


@router.put("/roles/{role_id}", response_model=RoleResponse)
def update_role(
    role_id: str,
    role_in: RoleUpdate,
    req: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("roles:manage"))
):
    """Update role details and permissions (SuperAdmin only)."""
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy vai trò với ID '{role_id}'!"
        )

    old_perm_codes = [p.code for p in role.permissions]

    if role_in.name is not None:
        role.name = role_in.name.strip()
    if role_in.description is not None:
        role.description = role_in.description

    new_perm_codes = old_perm_codes
    if role_in.permission_ids is not None:
        new_perms = db.query(Permission).filter(Permission.id.in_(role_in.permission_ids)).all()
        role.permissions = new_perms
        new_perm_codes = [p.code for p in new_perms]
        # Bump permissions version to invalidate client cache immediately
        role.permissions_version += 1

    db.commit()
    db.refresh(role)

    diff_added = list(set(new_perm_codes) - set(old_perm_codes))
    diff_removed = list(set(old_perm_codes) - set(new_perm_codes))
    summary_parts = []
    if diff_added:
        summary_parts.append(f"Gán thêm {len(diff_added)} quyền ({', '.join(diff_added)})")
    if diff_removed:
        summary_parts.append(f"Thu hồi {len(diff_removed)} quyền ({', '.join(diff_removed)})")
    if not summary_parts:
        summary_parts.append("Cập nhật thông tin vai trò")

    _write_audit_log(
        db, current_user, req,
        action="ROLE_UPDATE_PERMISSIONS",
        target_id=role.id,
        target_name=role.name,
        summary="; ".join(summary_parts),
        details={
            "before": old_perm_codes,
            "after": new_perm_codes,
            "diff_added": diff_added,
            "diff_removed": diff_removed,
            "version": role.permissions_version
        },
    )

    return _to_role_response(db, role)


@router.delete("/roles/{role_id}")
def delete_role(
    role_id: str,
    req: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("roles:manage"))
):
    """Delete a custom role (SuperAdmin only). Cannot delete system roles or roles with assigned users."""
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy vai trò với ID '{role_id}'!"
        )

    if role.is_system:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Không thể xóa vai trò hệ thống '{role.name}' ({role.code})!"
        )

    user_count = _count_role_users(db, role)
    if user_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Không thể xóa vai trò '{role.name}' vì đang có {user_count} người dùng đang được gán!"
        )

    role_name = role.name
    role_code = role.code

    db.delete(role)
    db.commit()

    _write_audit_log(
        db, current_user, req,
        action="ROLE_DELETE",
        target_id=role_id,
        target_name=role_name,
        summary=f"Xóa vai trò tùy biến '{role_name}' ({role_code})",
        details={"deleted_role_code": role_code},
    )

    return {"message": f"Đã xóa vai trò '{role_name}' thành công!"}


@router.get("/audit-logs", response_model=List[AuditLogResponse])
def list_audit_logs(
    target_type: Optional[str] = Query(default=None, alias="targetType"),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("roles:manage"))
):
    """List audit trail logs for role and permission modifications."""
    query = db.query(AuditLog)
    if target_type:
        query = query.filter(AuditLog.target_type == target_type)
    logs = query.order_by(AuditLog.created_at.desc()).limit(limit).all()
    return logs
