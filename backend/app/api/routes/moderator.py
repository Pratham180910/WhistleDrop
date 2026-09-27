from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, status, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.limiter import limiter
from app.models.moderator import Moderator
from app.schemas.moderator_report import (
    CloseReportRequest,
    ModeratorReportDetail,
    ModeratorReportListResponse,
    StatusUpdateRequest,
)
from app.services.moderator_report_service import (
    PAGE_SIZE_DEFAULT,
    close_report,
    get_report_detail,
    list_reports,
    update_report_status,
)
from app.services.moderator_service import require_moderator

router = APIRouter(prefix="/moderator", tags=["Moderator"])


# ── POST /moderator/login is in a separate import; auth endpoints stay here ──
# Login route is registered in routes/moderator.py — this file extends that router.
# We keep a single router object to avoid prefix duplication.

from app.schemas.moderator import ModeratorLogin, TokenResponse  # noqa: E402
from app.services.moderator_service import login_moderator  # noqa: E402


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Moderator login",
)
@limiter.limit("5/minute")
def moderator_login(
    request: Request,
    login_data: ModeratorLogin,
    db: Session = Depends(get_db),
):
    """Authenticates a moderator and returns a JWT access token."""
    return login_moderator(db=db, login=login_data)


# ── Report management (JWT required) ─────────────────────────────────────────

@router.get(
    "/reports",
    response_model=ModeratorReportListResponse,
    summary="List all reports (moderator only)",
)
def list_all_reports(
    status: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = PAGE_SIZE_DEFAULT,
    db: Session = Depends(get_db),
    _moderator: Moderator = Depends(require_moderator),
):
    """Lists reports with optional status/category filters and pagination."""
    return list_reports(
        db=db,
        status_filter=status,
        category_filter=category,
        search_filter=search,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/reports/{report_id}",
    response_model=ModeratorReportDetail,
    summary="Get report detail (moderator only)",
)
def get_report(
    report_id: UUID,
    db: Session = Depends(get_db),
    _moderator: Moderator = Depends(require_moderator),
):
    """Returns a specific report with full status update history."""
    return get_report_detail(db=db, report_id=report_id)


@router.patch(
    "/reports/{report_id}/status",
    response_model=ModeratorReportDetail,
    summary="Update report status (moderator only)",
)
def patch_report_status(
    report_id: UUID,
    update: StatusUpdateRequest,
    db: Session = Depends(get_db),
    _moderator: Moderator = Depends(require_moderator),
):
    """Updates a report's status following the allowed workflow transitions.
    
    SUBMITTED → UNDER_REVIEW
    UNDER_REVIEW → RESOLVED | DISMISSED
    """
    return update_report_status(db=db, report_id=report_id, update=update)


@router.patch(
    "/reports/{report_id}/close",
    response_model=ModeratorReportDetail,
    summary="Permanently close a report (moderator only)",
)
def patch_report_close(
    report_id: UUID,
    close_req: CloseReportRequest,
    db: Session = Depends(get_db),
    _moderator: Moderator = Depends(require_moderator),
):
    """Permanently closes a report if it is RESOLVED or DISMISSED.
    
    Once closed, the report cannot be modified or reopened.
    """
    note = close_req.note if close_req.note else "Case permanently closed."
    return close_report(db=db, report_id=report_id, note=note)
