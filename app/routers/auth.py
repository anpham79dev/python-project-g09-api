from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from app.dependencies import get_db, get_current_user
from app.core.security import verify_password, create_access_token
from app.models.user import User
from app.schemas.user import LoginRequest, LoginResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _build_user_response(user: User, db: Session) -> UserResponse:
    user_res = UserResponse.model_validate(user)
    user_res.role = user.role_code
    user_res.role_id = user.role_id
    user_res.role_name = user.role_name
    user_res.permissions_version = user.permissions_version
    user_res.permissions = user.get_permissions()
    if user.default_branch_id:
        from app.models.branch import Branch
        br = db.query(Branch).filter(Branch.id == user.default_branch_id).first()
        if br:
            user_res.default_branch_name = br.name
    return user_res


@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest, response: Response, db: Session = Depends(get_db)):
    """Authenticate user with username and password, returns JWT token with permissions."""
    username_clean = request.username.strip().lower()
    user = db.query(User).filter(User.username == username_clean).first()
    
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tên đăng nhập hoặc mật khẩu không chính xác!"
        )
    
    if user.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản này hiện đang bị tạm khóa!"
        )
    
    token = create_access_token(subject=user.id, role=user.role_code)
    user_res = _build_user_response(user, db)

    response.headers["X-Role-Permissions-Version"] = str(user.permissions_version)

    return LoginResponse(
        token=token,
        user=user_res
    )


@router.get("/me", response_model=UserResponse)
def get_me(response: Response, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get current authenticated user profile with latest permissions."""
    response.headers["X-Role-Permissions-Version"] = str(current_user.permissions_version)
    return _build_user_response(current_user, db)
