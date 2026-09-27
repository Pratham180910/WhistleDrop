from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.models.report import ReportStatus


# ── Moderator-safe sub-schemas ───────────────────────────────────────────────

class ModeratorStatusUpdateView(BaseModel):
    status: str
    note: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ModeratorReportSummary(BaseModel):
    """Used in list responses — no case_code_hash, no reporter identity."""
    id: UUID
    category: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ModeratorReportDetail(BaseModel):
    """Used in detail/status responses."""
    id: UUID
    category: str
    description: str
    evidence_url: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime
    updates: List[ModeratorStatusUpdateView]

    model_config = {"from_attributes": True}


class ModeratorReportListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    results: List[ModeratorReportSummary]


# ── Status update request ────────────────────────────────────────────────────

# Allowed workflow transitions
ALLOWED_TRANSITIONS: dict[ReportStatus, set[ReportStatus]] = {
    ReportStatus.SUBMITTED:    {ReportStatus.UNDER_REVIEW},
    ReportStatus.UNDER_REVIEW: {ReportStatus.RESOLVED, ReportStatus.DISMISSED},
    ReportStatus.RESOLVED:     set(),
    ReportStatus.DISMISSED:    set(),
    ReportStatus.CLOSED:       set(),
}

class CloseReportRequest(BaseModel):
    note: Optional[str] = Field(default="Case permanently closed.", max_length=2000)


class StatusUpdateRequest(BaseModel):
    status: ReportStatus
    note: str = Field(..., min_length=1, max_length=2000)

    @field_validator("note")
    @classmethod
    def note_not_whitespace(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Note cannot be empty or whitespace only.")
        return stripped
