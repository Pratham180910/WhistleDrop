from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, HttpUrl, field_validator


class ReportCategory(str, Enum):
    SECURITY = "Security"
    HARASSMENT = "Harassment"
    CORRUPTION = "Corruption"
    TECHNICAL = "Technical"
    OTHER = "Other"


class ReportCreate(BaseModel):
    category: ReportCategory
    description: str = Field(..., min_length=1, max_length=5000)
    evidence_url: Optional[HttpUrl] = None

    @field_validator("description")
    @classmethod
    def validate_description_not_empty(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Description cannot be empty or contain only whitespace.")
        return stripped


class ReportCreateResponse(BaseModel):
    case_code: str
    status: str = "SUBMITTED"


class StatusUpdateResponse(BaseModel):
    status: str
    note: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ReportTrackResponse(BaseModel):
    status: str
    created_at: datetime
    updated_at: datetime
    updates: List[StatusUpdateResponse]

    model_config = {"from_attributes": True}
