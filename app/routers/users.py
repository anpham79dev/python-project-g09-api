from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.dependencies import get_db, require_permission, get_current_user
from app.core.security import get_password_hash
from app.models.user import User
from app.models.branch import Branch
from app.models.role import Role
from app.schemas.user import (
    UserCreate,
    UserUpdate,
    UserResponse,
    UpdateActiveBranchRequest,
)

router = APIRouter(prefix="/users", tags=["Users"])


def _resolve_user_response(user: User, db: Session) -> UserResponse:
    res = UserResponse.model_validate(user)
    res.role = user.role_code
    res.role_id = user.role_id
    res.role_name = user.role_name
    res.permissions_version = user.permissions_version
    res.permissions = user.get_permissions()
    if user.default_branch_id:
        br = db.query(Branch).filter(Branch.id == user.default_branch_id).first()
        if br:
            res.default_branch_name = br.name
    return res


@router.get("", response_model=List[UserResponse])
def get_users(
    db: Session = Depends(get_db),
    admin: User = Depends(require_permission("users:read"))
):
    """List all users (PBAC: users:read)."""
    users = db.query(User).order_by(User.created_at.desc()).all()
    branch_map = {b.id: b.name for b in db.query(Branch).all()}
    
    results = []
    for u in users:
        res = _resolve_user_response(u, db)
        if u.default_branch_id and u.default_branch_id in branch_map:
            res.default_branch_name = branch_map[u.default_branch_id]
        results.append(res)
    return results


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    user_in: UserCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_permission("users:manage"))
):
    """Create a new staff, admin, or custom role user (PBAC: users:manage)."""
    username_clean = user_in.username.strip().lower()
    email_clean = user_in.email.strip().lower()

    # Check unique username
    existing_username = db.query(User).filter(User.username == username_clean).first()
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tên đăng nhập '{username_clean}' đã được sử dụng!"
        )

    # Check unique email
    existing_email = db.query(User).filter(User.email == email_clean).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Địa chỉ email '{email_clean}' đã được đăng ký!"
        )

    # Resolve Role
    role_id = user_in.role_id
    role_code = (user_in.role or "STAFF").strip().upper()
    if role_id:
        role_obj = db.query(Role).filter(Role.id == role_id).first()
        if role_obj:
            role_code = role_obj.code
    else:
        role_obj = db.query(Role).filter(Role.code == role_code).first()
        if role_obj:
            role_id = role_obj.id

    user = User(
        username=username_clean,
        hashed_password=get_password_hash(user_in.password),
        full_name=user_in.full_name.strip(),
        email=email_clean,
        phone=user_in.phone.strip(),
        role_id=role_id,
        role=role_code,
        status=user_in.status.upper(),
        default_branch_id=user_in.default_branch_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return _resolve_user_response(user, db)


@router.patch("/me/active-branch", response_model=UserResponse)
def update_user_active_branch(
    req: UpdateActiveBranchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Persist the user's active branch selection in the Database.
    Admin / SuperAdmin / Users with branch permissions can switch freely; Staff is locked to their default_branch_id.
    """
    if current_user.role_code in ["SUPER_ADMIN", "ADMIN"] or "branches:read" in current_user.get_permissions() or req.branch_id == current_user.default_branch_id:
        current_user.last_active_branch_id = req.branch_id
        db.commit()
        db.refresh(current_user)

    return _resolve_user_response(current_user, db)


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: str,
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_permission("users:manage"))
):
    """Update user fields (PBAC: users:manage)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy tài khoản người dùng '{user_id}'!"
        )

    # Validate unique username if provided and changed
    if user_in.username is not None:
        username_clean = user_in.username.strip().lower()
        if username_clean != user.username:
            existing_username = db.query(User).filter(User.username == username_clean, User.id != user_id).first()
            if existing_username:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Tên đăng nhập '{username_clean}' đã được sử dụng!"
                )
            user.username = username_clean

    # Validate unique email if provided and changed
    if user_in.email is not None:
        email_clean = str(user_in.email).strip().lower()
        if email_clean != user.email:
            existing_email = db.query(User).filter(User.email == email_clean, User.id != user_id).first()
            if existing_email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Địa chỉ email '{email_clean}' đã được đăng ký!"
                )
            user.email = email_clean

    if user_in.full_name is not None:
        user.full_name = user_in.full_name.strip()

    if user_in.phone is not None:
        user.phone = user_in.phone.strip()

    if user_in.role_id is not None:
        role_obj = db.query(Role).filter(Role.id == user_in.role_id).first()
        if role_obj:
            user.role_id = role_obj.id
            user.role = role_obj.code
    elif user_in.role is not None:
        user.role = user_in.role.upper()
        role_obj = db.query(Role).filter(Role.code == user.role).first()
        if role_obj:
            user.role_id = role_obj.id

    if user_in.status is not None:
        user.status = user_in.status.upper()

    if "default_branch_id" in user_in.model_fields_set:
        user.default_branch_id = user_in.default_branch_id

    if user_in.password:
        if len(user_in.password.strip()) < 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mật khẩu mới phải có ít nhất 6 ký tự!"
            )
        user.hashed_password = get_password_hash(user_in.password.strip())

    db.commit()
    db.refresh(user)

    return _resolve_user_response(user, db)


@router.delete("/{user_id}", response_model=UserResponse)
def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_permission("users:manage"))
):
    """Soft delete user by setting status='INACTIVE' (PBAC: users:manage)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy tài khoản người dùng '{user_id}'!"
        )

    if user.id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không thể tự vô hiệu hóa tài khoản của chính mình!"
        )

    user.status = "INACTIVE"
    db.commit()
    db.refresh(user)

    return _resolve_user_response(user, db)
