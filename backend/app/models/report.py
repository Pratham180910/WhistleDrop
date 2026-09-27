import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class ReportStatus(str, enum.Enum):
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    RESOLVED = "RESOLVED"
    DISMISSED = "DISMISSED"
    CLOSED = "CLOSED"


class Report(Base):
    __tablename__ = "reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_code_hash = Column(String(255), unique=True, index=True, nullable=False)
    category = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    evidence_url = Column(String(1024), nullable=True)
    status = Column(
        SQLEnum(ReportStatus, name="report_status_enum", native_enum=False),
        nullable=False,
        default=ReportStatus.SUBMITTED,
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationship to status history
    status_updates = relationship(
        "StatusUpdate",
        back_populates="report",
        cascade="all, delete-orphan",
        order_by="StatusUpdate.created_at",
    )


class StatusUpdate(Base):
    __tablename__ = "status_updates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id = Column(
        UUID(as_uuid=True),
        ForeignKey("reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status = Column(
        SQLEnum(ReportStatus, name="report_status_enum", native_enum=False),
        nullable=False,
    )
    note = Column(Text, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationship to parent report
    report = relationship("Report", back_populates="status_updates")
