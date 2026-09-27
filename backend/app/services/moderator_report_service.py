from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.report import Report, ReportStatus, StatusUpdate
from app.schemas.moderator_report import (
    ALLOWED_TRANSITIONS,
    ModeratorReportDetail,
    ModeratorReportListResponse,
    ModeratorReportSummary,
    ModeratorStatusUpdateView,
    StatusUpdateRequest,
)

PAGE_SIZE_DEFAULT = 20
PAGE_SIZE_MAX = 100


def _to_str(val) -> str:
    return val.value if isinstance(val, ReportStatus) else str(val)


def _build_detail(report: Report) -> ModeratorReportDetail:
    return ModeratorReportDetail(
        id=report.id,
        category=report.category,
        description=report.description,
        evidence_url=report.evidence_url,
        status=_to_str(report.status),
        created_at=report.created_at,
        updated_at=report.updated_at,
        updates=[
            ModeratorStatusUpdateView(
                status=_to_str(u.status),
                note=u.note,
                created_at=u.created_at,
            )
            for u in report.status_updates
        ],
    )


def list_reports(
    db: Session,
    status_filter: Optional[str],
    category_filter: Optional[str],
    search_filter: Optional[str],
    page: int,
    page_size: int,
) -> ModeratorReportListResponse:
    page = max(1, page)
    page_size = max(1, min(page_size, PAGE_SIZE_MAX))

    query = db.query(Report)

    if status_filter:
        try:
            s = ReportStatus(status_filter.upper())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid status filter: {status_filter}",
            )
        query = query.filter(Report.status == s)

    if category_filter:
        query = query.filter(Report.category.ilike(category_filter))

    if search_filter:
        search_pattern = f"%{search_filter}%"
        query = query.filter(
            (Report.description.ilike(search_pattern)) | 
            (Report.category.ilike(search_pattern))
        )

    total = query.count()
    reports = (
        query.order_by(Report.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return ModeratorReportListResponse(
        total=total,
        page=page,
        page_size=page_size,
        results=[
            ModeratorReportSummary(
                id=r.id,
                category=r.category,
                status=_to_str(r.status),
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
            for r in reports
        ],
    )


def get_report_detail(db: Session, report_id: UUID) -> ModeratorReportDetail:
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return _build_detail(report)


def update_report_status(
    db: Session, report_id: UUID, update: StatusUpdateRequest
) -> ModeratorReportDetail:
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    current = report.status if isinstance(report.status, ReportStatus) else ReportStatus(report.status)
    if current == ReportStatus.CLOSED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Report is permanently closed and cannot be modified."
        )

    new_status = update.status

    allowed = ALLOWED_TRANSITIONS.get(current, set())
    if new_status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Transition from {current.value} to {new_status.value} is not allowed. "
                f"Allowed transitions: {[s.value for s in allowed] or 'none'}"
            ),
        )

    report.status = new_status
    report.updated_at = datetime.now(timezone.utc)

    status_update = StatusUpdate(
        report_id=report.id,
        status=new_status,
        note=update.note,
    )
    db.add(status_update)
    db.commit()
    db.refresh(report)

    return _build_detail(report)


def close_report(
    db: Session, report_id: UUID, note: str
) -> ModeratorReportDetail:
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
        
    current = report.status if isinstance(report.status, ReportStatus) else ReportStatus(report.status)
    if current == ReportStatus.CLOSED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Report is already closed."
        )
        
    if current not in (ReportStatus.RESOLVED, ReportStatus.DISMISSED):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only RESOLVED or DISMISSED reports can be permanently closed."
        )

    report.status = ReportStatus.CLOSED
    report.updated_at = datetime.now(timezone.utc)
    
    status_update = StatusUpdate(
        report_id=report.id,
        status=ReportStatus.CLOSED,
        note=note,
    )
    db.add(status_update)
    db.commit()
    db.refresh(report)
    return _build_detail(report)
