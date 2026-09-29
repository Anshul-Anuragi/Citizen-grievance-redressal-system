from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.config import settings
from app.core.security import (
    get_password_hash, verify_password, create_access_token,
    create_refresh_token, hash_token, generate_random_token
)
from app.core.permissions import get_current_user
from app.models.user import User, UserRole, RefreshToken, PasswordResetToken, EmailVerificationToken
from app.schemas.auth import (
    RegisterRequest, LoginRequest, TokenResponse, RefreshTokenRequest,
    LogoutRequest, ForgotPasswordRequest, ResetPasswordRequest, UserResponse
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_citizen(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Check existing email
    existing = await db.execute(select(User).where(User.email == data.email.lower()))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email address already exists"
        )

    user = User(
        email=data.email.lower(),
        password_hash=get_password_hash(data.password),
        full_name=data.full_name.strip(),
        mobile=data.mobile,
        role=UserRole.CITIZEN,
        is_active=True,
        is_verified=True  # Auto-verify for standard seed/demo access
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User)
        .options(selectinload(User.district_admin_profile), selectinload(User.officer_profile))
        .where(User.email == data.email.lower())
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated"
        )

    access_token = create_access_token(subject=user.id, role=user.role.value)
    raw_refresh, token_hash, expires_at = create_refresh_token(subject=user.id, role=user.role.value)

    # Store hashed refresh token in DB
    refresh_record = RefreshToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at
    )
    db.add(refresh_record)
    await db.commit()

    # Format user response metadata
    user_resp = UserResponse.model_validate(user)
    if user.district_admin_profile:
        user_resp.district_code = user.district_admin_profile.district_code
    elif user.officer_profile:
        user_resp.district_code = user.officer_profile.district_code
        user_resp.department_id = user.officer_profile.department_id
        user_resp.officer_id = user.officer_profile.officer_id

    return TokenResponse(
        access_token=access_token,
        refresh_token=raw_refresh,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=user_resp
    )


@router.post("/refresh")
async def refresh_access_token(data: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    input_hash = hash_token(data.refresh_token)
    now = datetime.now(timezone.utc)

    result = await db.execute(
        select(RefreshToken)
        .options(selectinload(RefreshToken.user))
        .where(
            RefreshToken.token_hash == input_hash,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > now
        )
    )
    refresh_record = result.scalar_one_or_none()
    if not refresh_record or not refresh_record.user or not refresh_record.user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )

    # Revoke old refresh token & issue new pair
    refresh_record.revoked_at = now
    db.add(refresh_record)

    user = refresh_record.user
    new_access = create_access_token(subject=user.id, role=user.role.value)
    raw_new_refresh, new_hash, new_exp = create_refresh_token(subject=user.id, role=user.role.value)

    new_record = RefreshToken(
        user_id=user.id,
        token_hash=new_hash,
        expires_at=new_exp
    )
    db.add(new_record)
    await db.commit()

    return {
        "access_token": new_access,
        "refresh_token": raw_new_refresh,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    data: LogoutRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Revoke the supplied refresh token so it can no longer be used to obtain new
    access tokens.  The client is responsible for discarding its own access token
    (which remains valid until its 24-hour expiry — Phase 5 will add jti-based
    access token revocation via Redis).

    If no refresh_token is provided in the request body, all non-revoked refresh
    tokens for the current user are revoked (full session logout).
    """
    now = datetime.now(timezone.utc)

    if data.refresh_token:
        # Revoke the specific token provided
        input_hash = hash_token(data.refresh_token)
        result = await db.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == input_hash,
                RefreshToken.user_id == current_user.id,
                RefreshToken.revoked_at.is_(None),
            )
        )
        record = result.scalar_one_or_none()
        if record:
            record.revoked_at = now
            db.add(record)
            await db.commit()
    else:
        # Full logout: revoke all active refresh tokens for this user
        result = await db.execute(
            select(RefreshToken).where(
                RefreshToken.user_id == current_user.id,
                RefreshToken.revoked_at.is_(None),
                RefreshToken.expires_at > now,
            )
        )
        records = result.scalars().all()
        for record in records:
            record.revoked_at = now
            db.add(record)
        if records:
            await db.commit()

    return {"message": "Logged out successfully."}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    user_resp = UserResponse.model_validate(current_user)
    if current_user.district_admin_profile:
        user_resp.district_code = current_user.district_admin_profile.district_code
    elif current_user.officer_profile:
        user_resp.district_code = current_user.officer_profile.district_code
        user_resp.department_id = current_user.officer_profile.department_id
        user_resp.officer_id = current_user.officer_profile.officer_id
    return user_resp
