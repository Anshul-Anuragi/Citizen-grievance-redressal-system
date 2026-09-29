import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, Float, ForeignKey, Enum
from sqlalchemy.orm import relationship
from app.core.database import Base

class PriorityEnum(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

class District(Base):
    __tablename__ = "districts"

    code = Column(String(10), primary_key=True)  # e.g. IND, BHO, GWL, JAB
    name_en = Column(String(100), nullable=False)
    name_hi = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

class Department(Base):
    __tablename__ = "departments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code = Column(String(50), unique=True, nullable=False)  # e.g. PWD, MPPKVVCL, NAGAR_NIGAM
    name_en = Column(String(150), nullable=False)
    name_hi = Column(String(150), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

class Category(Base):
    __tablename__ = "categories"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code = Column(String(50), unique=True, nullable=False)
    name_en = Column(String(150), nullable=False)
    name_hi = Column(String(150), nullable=False)
    default_sla_hours = Column(Float, default=48.0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    mappings = relationship("CategoryDepartmentMapping", back_populates="category", cascade="all, delete-orphan")
    sla_rules = relationship("SLARule", back_populates="category", cascade="all, delete-orphan")

class CategoryDepartmentMapping(Base):
    __tablename__ = "category_department_mappings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    category_id = Column(String(36), ForeignKey("categories.id", ondelete="CASCADE"), nullable=False, index=True)
    department_id = Column(String(36), ForeignKey("departments.id", ondelete="CASCADE"), nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    category = relationship("Category", back_populates="mappings")
    department = relationship("Department")

class SLARule(Base):
    __tablename__ = "sla_rules"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    category_id = Column(String(36), ForeignKey("categories.id", ondelete="CASCADE"), nullable=False, index=True)
    priority = Column(Enum(PriorityEnum), nullable=False)
    multiplier = Column(Float, default=1.0, nullable=False)  # HIGH: 0.5, MEDIUM: 1.0, LOW: 1.5
    resolution_deadline_hours = Column(Float, nullable=False)

    category = relationship("Category", back_populates="sla_rules")
