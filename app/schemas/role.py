from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class PermissionResponse(BaseModel):
    id: str
    code: str
    name: str
    module: str
    description: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class RoleBase(BaseModel):
    code: str = Field(..., description="Role unique code, e.g. BRANCH_MANAGER")
    name: str = Field(..., description="Human readable display name")
    description: Optional[str] = None


class RoleCreate(RoleBase):
    permission_ids: List[str] = Field(default_factory=list, description="List of permission IDs to assign")


class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    permission_ids: Optional[List[str]] = None


class RoleResponse(BaseModel):
    id: str
    code: str
    name: str
    description: Optional[str] = None
    is_system: bool = False
    permissions_version: int = 1
    permissions: List[PermissionResponse] = Field(default_factory=list)
    user_count: int = 0
    created_at: Optional[datetime] = Field(default=None, serialization_alias="createdAt")
    updated_at: Optional[datetime] = Field(default=None, serialization_alias="updatedAt")

    class Config:
        from_attributes = True
        populate_by_name = True


class AuditLogResponse(BaseModel):
    id: str
    user_id: str
    user_name: str
    action: str
    target_type: str
    target_id: str
    target_name: str
    changes_summary: str
    details_json: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
