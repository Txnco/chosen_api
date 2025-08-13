from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime

class RoleBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=50, description="Role name")

class RoleCreate(RoleBase):
    """Schema for creating a new role"""
    pass

class RoleUpdate(BaseModel):
    """Schema for updating an existing role"""
    name: Optional[str] = Field(None, min_length=1, max_length=50, description="Role name")

class RoleResponse(RoleBase):
    """Schema for role response"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    created_at: datetime
    updated_at: datetime

class RoleInDB(RoleResponse):
    """Schema for role stored in database"""
    pass