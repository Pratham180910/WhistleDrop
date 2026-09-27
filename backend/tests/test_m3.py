import sys
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import hashlib
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import get_db, Base
from app.models.report import Report, ReportStatus


def run_checks():
    # 1. Setup in-memory test DB
    engine = sa.create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=sa.pool.StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    if hasattr(app.state, "limiter"):
        app.state.limiter.reset()
    client = TestClient(app)

    # 2. Test validation failures
    r_bad_cat = client.post("/reports", json={"category": "InvalidCategory", "description": "Valid description"})
    assert r_bad_cat.status_code == 422, f"Expected 422 for bad category, got {r_bad_cat.status_code}"

    r_empty_desc = client.post("/reports", json={"category": "Security", "description": "   "})
    assert r_empty_desc.status_code == 422, f"Expected 422 for empty desc, got {r_empty_desc.status_code}"

    r_bad_url = client.post("/reports", json={"category": "Security", "description": "Valid desc", "evidence_url": "not-a-url"})
    assert r_bad_url.status_code == 422, f"Expected 422 for bad URL, got {r_bad_url.status_code}"

    # 3. Test successful report creation (HTTP 201 + case_code)
    payload = {
        "category": "Security",
        "description": "Confidential security breach report",
        "evidence_url": "https://example.com/evidence",
    }
    res = client.post("/reports", json=payload)
    assert res.status_code == 201, f"Expected 201, got {res.status_code}"
    data = res.json()
    assert "case_code" in data, "case_code missing in response"
    assert data["status"] == "SUBMITTED"
    case_code = data["case_code"]
    assert len(case_code) >= 24

    # 4. Verify DB stores only SHA-256 hash, not plaintext case code
    expected_hash = hashlib.sha256(case_code.encode("utf-8")).hexdigest()
    db = TestingSessionLocal()
    report = db.query(Report).first()
    assert report is not None, "Report not found in DB"
    assert report.case_code_hash == expected_hash, "Hash does not match expected SHA-256!"
    assert case_code != report.case_code_hash, "Plaintext case code was saved directly!"
    assert case_code not in report.case_code_hash
    assert report.category == "Security"
    assert report.description == payload["description"]
    assert report.evidence_url == payload["evidence_url"]
    assert report.status == ReportStatus.SUBMITTED
    assert len(report.status_updates) == 1
    assert report.status_updates[0].status == ReportStatus.SUBMITTED
    db.close()

    # 5. Verify /health
    r_health = client.get("/health")
    assert r_health.status_code == 200
    assert r_health.json() == {"status": "ok"}

    # 6. Verify /docs
    r_docs = client.get("/docs")
    assert r_docs.status_code == 200

    print("ALL M3 CHECKS COMPLETED SUCCESSFULLY")


test_m3_checks = run_checks

if __name__ == "__main__":
    run_checks()
