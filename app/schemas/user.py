from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from pydantic.alias_generators import to_camel


class UserBase(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True
    )
    username: str
    full_name: str
    email: EmailStr
    phone: str
    role: str = "STAFF"  # Role code: "SUPER_ADMIN" | "ADMIN" | "STAFF" | or custom role code
    role_id: Optional[str] = None
    role_name: Optional[str] = None
    status: str = "ACTIVE"  # "ACTIVE" | "INACTIVE"
    default_branch_id: Optional[str] = None
    last_active_branch_id: Optional[str] = None
    permissions_version: Optional[int] = 1
    permissions: List[str] = Field(default_factory=list)


class UserCreate(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True
    )
    username: str
    full_name: str
    email: EmailStr
    phone: str
    role: Optional[str] = None
    role_id: Optional[str] = None
    status: str = "ACTIVE"
    default_branch_id: Optional[str] = None
    password: str = Field(min_length=6)


class UserUpdate(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True
    )
    username: Optional[str] = None
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    role: Optional[str] = None
    role_id: Optional[str] = None
    status: Optional[str] = None  # "ACTIVE" | "INACTIVE"
    default_branch_id: Optional[str] = None
    password: Optional[str] = None


class UserResponse(UserBase):
    id: str
    default_branch_name: Optional[str] = None
    created_at: datetime


class UpdateActiveBranchRequest(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True
    )
    branch_id: str


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True
    )
    token: str
    user: UserResponse
