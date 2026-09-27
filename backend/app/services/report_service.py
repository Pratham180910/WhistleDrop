from sqlalchemy.orm import Session
from app.models.report import Report, ReportStatus, StatusUpdate
from app.schemas.report import ReportCreate, ReportCreateResponse
from app.core.security import generate_case_code, hash_case_code


def create_anonymous_report(db: Session, report_in: ReportCreate) -> ReportCreateResponse:
    """Creates a new anonymous report in the database.
    
    Generates a cryptographically random case code, hashes it using SHA-256,
    stores only the hash in the database, and returns the plaintext case code once.
    """
    case_code = generate_case_code()
    case_code_hash = hash_case_code(case_code)

    evidence_str = str(report_in.evidence_url) if report_in.evidence_url else None

    # Persist report - ONLY case_code_hash is saved
    new_report = Report(
        case_code_hash=case_code_hash,
        category=report_in.category.value,
        description=report_in.description,
        evidence_url=evidence_str,
        status=ReportStatus.SUBMITTED,
    )
    db.add(new_report)
    db.flush()

    # Initial status update history entry
    status_update = StatusUpdate(
        report_id=new_report.id,
        status=ReportStatus.SUBMITTED,
        note="Report submitted anonymously.",
    )
    db.add(status_update)
    db.commit()

    return ReportCreateResponse(
        case_code=case_code,
        status=ReportStatus.SUBMITTED.value,
    )


def get_report_by_case_code(db: Session, case_code: str):
    """Finds a report by hashing the provided case code and returning its public tracking status.
    
    Returns None if the case code is empty or not found.
    Never exposes internal IDs, reporter identity, or case_code_hash.
    """
    if not case_code or not case_code.strip():
        return None

    code_hash = hash_case_code(case_code.strip())
    report = db.query(Report).filter(Report.case_code_hash == code_hash).first()
    if not report:
        return None

    return report
