from typing import Optional, List
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User, UserRole, DistrictAdminProfile, OfficerProfile

security_scheme = HTTPBearer(auto_error=False)

async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    if not credentials:
        return None
    
    token = credentials.credentials
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        return None
    
    user_id = payload.get("sub")
    if not user_id:
        return None
    
    result = await db.execute(
        select(User)
        .options(selectinload(User.district_admin_profile), selectinload(User.officer_profile))
        .where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    return user

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = await get_current_user_optional(credentials, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated"
        )
    
    return user

def require_roles(allowed_roles: List[UserRole]):
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User with role '{current_user.role.value}' is not authorized to perform this operation"
            )
        return current_user
    return role_checker

require_citizen = require_roles([UserRole.CITIZEN])
require_district_admin = require_roles([UserRole.DISTRICT_ADMIN])
require_officer = require_roles([UserRole.OFFICER])
require_admin_or_officer = require_roles([UserRole.DISTRICT_ADMIN, UserRole.OFFICER])

def enforce_district_isolation(user: User, target_district_code: str) -> str:
    """
    Enforces strict district isolation.
    District Admin & Officers can ONLY access data in their assigned district.
    Citizens are restricted by ownership.
    """
    if user.role == UserRole.DISTRICT_ADMIN:
        if not user.district_admin_profile or user.district_admin_profile.district_code != target_district_code:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. District Admin is isolated to district '{user.district_admin_profile.district_code if user.district_admin_profile else 'Unassigned'}'"
            )
    elif user.role == UserRole.OFFICER:
        if not user.officer_profile or user.officer_profile.district_code != target_district_code:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Officer is isolated to district '{user.officer_profile.district_code if user.officer_profile else 'Unassigned'}'"
            )
    return target_district_code
