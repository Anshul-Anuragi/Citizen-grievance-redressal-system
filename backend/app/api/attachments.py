import os
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.permissions import get_current_user_optional, security_scheme
from app.api.complaints import _authorize_complaint_access
from fastapi.security import HTTPAuthorizationCredentials
from app.models.user import User
from app.models.complaint import ComplaintAttachment, Complaint
from app.services.storage_service import StorageService

router = APIRouter(prefix="/attachments", tags=["Attachments"])

ALLOWED_MIME_TYPES = {
    "image/jpeg", "image/png", "image/webp", "image/gif",
    "application/pdf",
    "video/mp4", "video/webm", "video/quicktime",
    "audio/mpeg", "audio/wav", "audio/mp3", "audio/ogg"
}

@router.post("/upload")
async def upload_attachment(
    complaint_id: str,
    file: UploadFile = File(...),
    current_user: User | None = Depends(get_current_user_optional),
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
    db: AsyncSession = Depends(get_db)
):
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{file.content_type}'. Allowed types: Images, PDF, Video, Audio (MP3/WAV)."
        )

    complaint_result = await db.execute(select(Complaint).where(Complaint.id == complaint_id))
    complaint = complaint_result.scalar_one_or_none()
    if not complaint:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Complaint not found")
    _authorize_complaint_access(complaint, current_user, credentials)

    try:
        relative_path, mime_type, file_size = await StorageService.save_file(file)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))

    attachment = ComplaintAttachment(
        complaint_id=complaint_id,
        file_name=file.filename or "attachment",
        file_path=relative_path,
        file_type=mime_type,
        file_size=file_size,
        uploaded_by_user_id=current_user.id if current_user else None
    )
    db.add(attachment)
    await db.commit()
    await db.refresh(attachment)

    return {
        "id": attachment.id,
        "file_name": attachment.file_name,
        "file_type": attachment.file_type,
        "file_size": attachment.file_size,
        "uploaded_at": attachment.uploaded_at
    }

@router.get("/view/{attachment_id}")
async def view_attachment(
    attachment_id: str,
    current_user: User | None = Depends(get_current_user_optional),
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(ComplaintAttachment).where(ComplaintAttachment.id == attachment_id))
    attachment = result.scalar_one_or_none()
    if not attachment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")

    complaint_result = await db.execute(select(Complaint).where(Complaint.id == attachment.complaint_id))
    complaint = complaint_result.scalar_one_or_none()
    if not complaint:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Complaint not found")
    _authorize_complaint_access(complaint, current_user, credentials)

    try:
        full_path = StorageService.get_full_file_path(attachment.file_path)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid attachment path")
    if not os.path.exists(full_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File content not found on server")

    return FileResponse(
        full_path,
        media_type=attachment.file_type,
        filename=attachment.file_name
    )
