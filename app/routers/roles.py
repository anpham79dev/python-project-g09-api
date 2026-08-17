import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from app.dependencies import get_db, require_permission, get_current_user
from app.models.role import Role, role_permissions
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
from app.core.rbac_config import ALL_PERMISSIONS, SYSTEM_ROLES_CONFIG

router = APIRouter(tags=["Roles & Permissions"])


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
    result = []
    for r in roles:
        # Count users with this role
        user_count = db.query(User).filter(
            (User.role_id == r.id) | (User.role == r.code)
        ).count()
        res = RoleResponse(
            id=r.id,
            code=r.code,
            name=r.name,
            description=r.description,
            is_system=r.is_system,
            permissions_version=r.permissions_version,
            permissions=[
                PermissionResponse.model_validate(p) for p in r.permissions
            ],
            user_count=user_count,
            created_at=r.created_at,
            updated_at=r.updated_at
        )
        result.append(res)
    return result


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

    user_count = db.query(User).filter(
        (User.role_id == role.id) | (User.role == role.code)
    ).count()

    return RoleResponse(
        id=role.id,
        code=role.code,
        name=role.name,
        description=role.description,
        is_system=role.is_system,
        permissions_version=role.permissions_version,
        permissions=[PermissionResponse.model_validate(p) for p in role.permissions],
        user_count=user_count,
        created_at=role.created_at,
        updated_at=role.updated_at
    )


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

    # Audit log
    perm_codes = [p.code for p in new_role.permissions]
    audit = AuditLog(
        user_id=current_user.id,
        user_name=current_user.full_name,
        action="ROLE_CREATE",
        target_type="ROLE",
        target_id=new_role.id,
        target_name=new_role.name,
        changes_summary=f"Tạo vai trò mới '{new_role.name}' ({new_role.code}) với {len(perm_codes)} quyền",
        details_json=json.dumps({"after_permissions": perm_codes, "code": new_role.code}),
        ip_address=req.client.host if req.client else None
    )
    db.add(audit)
    db.commit()

    return RoleResponse(
        id=new_role.id,
        code=new_role.code,
        name=new_role.name,
        description=new_role.description,
        is_system=new_role.is_system,
        permissions_version=new_role.permissions_version,
        permissions=[PermissionResponse.model_validate(p) for p in new_role.permissions],
        user_count=0,
        created_at=new_role.created_at,
        updated_at=new_role.updated_at
    )


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

    # Record Audit Log
    diff_added = list(set(new_perm_codes) - set(old_perm_codes))
    diff_removed = list(set(old_perm_codes) - set(new_perm_codes))
    summary_parts = []
    if diff_added:
        summary_parts.append(f"Gán thêm {len(diff_added)} quyền ({', '.join(diff_added)})")
    if diff_removed:
        summary_parts.append(f"Thu hồi {len(diff_removed)} quyền ({', '.join(diff_removed)})")
    if not summary_parts:
        summary_parts.append("Cập nhật thông tin vai trò")

    audit = AuditLog(
        user_id=current_user.id,
        user_name=current_user.full_name,
        action="ROLE_UPDATE_PERMISSIONS",
        target_type="ROLE",
        target_id=role.id,
        target_name=role.name,
        changes_summary="; ".join(summary_parts),
        details_json=json.dumps({
            "before": old_perm_codes,
            "after": new_perm_codes,
            "diff_added": diff_added,
            "diff_removed": diff_removed,
            "version": role.permissions_version
        }),
        ip_address=req.client.host if req.client else None
    )
    db.add(audit)
    db.commit()

    user_count = db.query(User).filter(
        (User.role_id == role.id) | (User.role == role.code)
    ).count()

    return RoleResponse(
        id=role.id,
        code=role.code,
        name=role.name,
        description=role.description,
        is_system=role.is_system,
        permissions_version=role.permissions_version,
        permissions=[PermissionResponse.model_validate(p) for p in role.permissions],
        user_count=user_count,
        created_at=role.created_at,
        updated_at=role.updated_at
    )


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

    user_count = db.query(User).filter(
        (User.role_id == role.id) | (User.role == role.code)
    ).count()
    if user_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Không thể xóa vai trò '{role.name}' vì đang có {user_count} người dùng đang được gán!"
        )

    role_name = role.name
    role_code = role.code

    db.delete(role)
    db.commit()

    # Record Audit Log
    audit = AuditLog(
        user_id=current_user.id,
        user_name=current_user.full_name,
        action="ROLE_DELETE",
        target_type="ROLE",
        target_id=role_id,
        target_name=role_name,
        changes_summary=f"Xóa vai trò tùy biến '{role_name}' ({role_code})",
        details_json=json.dumps({"deleted_role_code": role_code}),
        ip_address=req.client.host if req.client else None
    )
    db.add(audit)
    db.commit()

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
