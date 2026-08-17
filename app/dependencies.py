from typing import Generator, Optional, List
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.core.security import decode_access_token
from app.models.user import User

security_scheme = HTTPBearer(auto_error=False)


def get_db() -> Generator[Session, None, None]:
    """Database session generator with auto-close."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user_optional(
    auth_header: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Extract and validate current user if token is provided."""
    if not auth_header:
        return None
    token = auth_header.credentials
    payload = decode_access_token(token)
    if not payload:
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None
    user = db.query(User).filter(User.id == user_id, User.status == "ACTIVE").first()
    return user


def get_current_user(
    user: Optional[User] = Depends(get_current_user_optional)
) -> User:
    """Enforce authentication requirement."""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Phiên đăng nhập không hợp lệ hoặc đã hết hạn. Vui lòng đăng nhập lại!",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return user


def require_permission(required_permission: str):
    """
    PBAC Dependency: Enforce atomic permission (e.g. 'products:write').
    SUPER_ADMIN always passes. Other roles must have the permission assigned in database.
    """
    def permission_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role_code == "SUPER_ADMIN":
            return current_user

        user_perms = current_user.get_permissions()
        if required_permission not in user_perms:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Tài khoản không đủ quyền thực hiện thao tác này (Yêu cầu quyền: '{required_permission}')!"
            )
        return current_user
    return permission_checker


def require_any_permission(permission_codes: List[str]):
    """
    PBAC Dependency: Enforce that user has AT LEAST ONE of the listed permissions.
    """
    def permission_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role_code == "SUPER_ADMIN":
            return current_user

        user_perms = set(current_user.get_permissions())
        if not any(code in user_perms for code in permission_codes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Tài khoản không đủ quyền thực hiện thao tác này (Yêu cầu một trong các quyền: {', '.join(permission_codes)})!"
            )
        return current_user
    return permission_checker


def require_role(allowed_roles: List[str]):
    """
    Legacy Role Enforcer with PBAC and SUPER_ADMIN hierarchy fallback.
    """
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        effective_roles = set(allowed_roles)
        if "ADMIN" in effective_roles or "STAFF" in effective_roles:
            effective_roles.add("SUPER_ADMIN")

        if current_user.role_code not in effective_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Tài khoản không đủ quyền thực hiện thao tác này (Yêu cầu: {', '.join(allowed_roles)})!"
            )
        return current_user
    return role_checker
