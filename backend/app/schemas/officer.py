from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from app.schemas.grievance import DepartmentResponse, DistrictResponse
from app.schemas.auth import validate_password_strength


class OfficerCreateRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=2, max_length=255)
    mobile: Optional[str] = Field(None, max_length=20)
    district_code: str
    department_id: str

    @field_validator("password")
    @classmethod
    def password_policy(cls, v: str) -> str:
        return validate_password_strength(v)


class OfficerUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    mobile: Optional[str] = None
    department_id: Optional[str] = None
    is_available: Optional[bool] = None
    is_active: Optional[bool] = None


class OfficerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    officer_id: str
    district_code: str
    department_id: str
    is_available: bool
    is_active: bool
    active_workload: int
    department: Optional[DepartmentResponse] = None
    district: Optional[DistrictResponse] = None
