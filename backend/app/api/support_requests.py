from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Optional
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.middleware.security import require_role
from app.models.support_request import SupportRequest
from app.models.user import User, UserRole
from app.schemas.support_request_schema import SupportRequestCreate, SupportRequestStatusUpdate
from app.models.student import StudentProfile

router = APIRouter(prefix="/api/support-requests", tags=["Support requests"])


@router.post("", status_code=status.HTTP_201_CREATED)
def create_support_request(
    data: SupportRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.student)),
):
    profile = current_user.student_profile
    if profile is None:
        raise HTTPException(status_code=404, detail="No student profile is linked to this account")
    request = SupportRequest(student_id=profile.id, request_type=data.request_type, message=data.message)
    db.add(request)
    db.commit()
    db.refresh(request)
    return {"id": request.id, "status": request.status, "created_at": request.created_at.isoformat()}


@router.get("")
def list_support_requests(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.advisor, UserRole.admin)),
):
    query = db.query(SupportRequest).join(StudentProfile).order_by(SupportRequest.created_at.desc())
    if status_filter:
        query = query.filter(SupportRequest.status == status_filter.upper())
    requests = query.limit(limit).all()
    return {"items": [{
        "id": row.id,
        "student_id": row.student_id,
        "student_name": f"{row.student.first_name} {row.student.surname}",
        "request_type": row.request_type,
        "message": row.message,
        "status": row.status,
        "created_at": row.created_at.isoformat(),
    } for row in requests]}


@router.patch("/{request_id}")
def update_support_request(
    request_id: str,
    data: SupportRequestStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.advisor, UserRole.admin)),
):
    request = db.query(SupportRequest).filter(SupportRequest.id == request_id).first()
    if request is None:
        raise HTTPException(status_code=404, detail="Support request not found")
    request.status = data.status
    db.commit()
    return {"id": request.id, "status": request.status}
