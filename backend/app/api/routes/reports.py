from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.limiter import limiter
from app.schemas.report import (
    ReportCreate,
    ReportCreateResponse,
    ReportTrackResponse,
    StatusUpdateResponse,
)
from app.services.report_service import create_anonymous_report, get_report_by_case_code

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.post(
    "",
    response_model=ReportCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit an anonymous report",
)
@limiter.limit("5/minute")
def submit_report(
    request: Request,
    report_in: ReportCreate,
    db: Session = Depends(get_db),
):
    """Submits an anonymous confidential report.
    
    Generates a secure case code returned exactly once in the response.
    No reporter identity data is collected or stored.
    """
    return create_anonymous_report(db=db, report_in=report_in)


@router.get(
    "/track/{case_code}",
    response_model=ReportTrackResponse,
    summary="Track anonymous report status by case code",
)
@limiter.limit("20/minute")
def track_report(
    request: Request,
    case_code: str,
    db: Session = Depends(get_db),
):
    """Tracks an anonymous report using the plaintext case code.
    
    Returns current status and update history. If unknown or invalid,
    returns a generic 404 without leaking whether the code exists.
    """
    report = get_report_by_case_code(db=db, case_code=case_code)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    return ReportTrackResponse(
        status=report.status.value if hasattr(report.status, "value") else str(report.status),
        created_at=report.created_at,
        updated_at=report.updated_at,
        updates=[
            StatusUpdateResponse(
                status=u.status.value if hasattr(u.status, "value") else str(u.status),
                note=u.note,
                created_at=u.created_at,
            )
            for u in report.status_updates
        ],
    )
