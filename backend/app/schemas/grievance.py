from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from app.models.grievance import PriorityEnum

class DistrictResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name_en: str
    name_hi: str
    is_active: bool

class DepartmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    code: str
    name_en: str
    name_hi: str
    is_active: bool

class CategoryDepartmentMappingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    category_id: str
    department_id: str
    department: Optional[DepartmentResponse] = None
    is_active: bool

class SLARuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    category_id: str
    priority: PriorityEnum
    multiplier: float
    resolution_deadline_hours: float

class SimpleCategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    code: str
    name_en: str
    name_hi: str
    default_sla_hours: float
    is_active: bool

class CategoryResponse(SimpleCategoryResponse):
    mappings: Optional[List[CategoryDepartmentMappingResponse]] = None

class CategoryCreateRequest(BaseModel):
    code: str
    name_en: str
    name_hi: str
    department_id: str
    default_sla_hours: float = 48.0

class CategoryUpdateRequest(BaseModel):
    name_en: Optional[str] = None
    name_hi: Optional[str] = None
    department_id: Optional[str] = None
    default_sla_hours: Optional[float] = None
    is_active: Optional[bool] = None
