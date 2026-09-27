import sys
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import get_db, Base


def run_m4_checks():
    # Setup test DB
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

    # 1. Create a report using POST /reports
    payload = {
        "category": "Harassment",
        "description": "Witnessed harassment in workspace",
        "evidence_url": "https://example.com/log.pdf",
    }
    create_res = client.post("/reports", json=payload)
    assert create_res.status_code == 201, f"Expected 201, got {create_res.status_code}"
    create_data = create_res.json()
    case_code = create_data["case_code"]
    assert case_code

    # 2. Use returned case_code with GET /reports/track/{case_code}
    track_res = client.get(f"/reports/track/{case_code}")
    assert track_res.status_code == 200, f"Expected 200, got {track_res.status_code}"
    track_data = track_res.json()

    # 3. Confirm correct status and initial status update returned
    assert track_data["status"] == "SUBMITTED"
    assert "created_at" in track_data
    assert "updated_at" in track_data
    assert "updates" in track_data
    assert len(track_data["updates"]) == 1
    update_entry = track_data["updates"][0]
    assert update_entry["status"] == "SUBMITTED"
    assert update_entry["note"] == "Report submitted anonymously."
    assert "created_at" in update_entry

    # 4. Confirm invalid case codes return generic 404
    invalid_codes = [
        "completely_wrong_case_code_xyz123",
        "nonexistent-code",
        "   ",
        "invalid!chars@#$",
    ]
    for inv_code in invalid_codes:
        bad_res = client.get(f"/reports/track/{inv_code}")
        assert bad_res.status_code == 404, f"Expected 404 for {inv_code}, got {bad_res.status_code}"
        assert bad_res.json() == {"detail": "Report not found"}

    # 5. Confirm case_code_hash is NEVER returned
    assert "case_code_hash" not in track_data
    assert "case_code" not in track_data
    track_str = str(track_data)
    assert "hash" not in track_str.lower()

    # 6. Confirm no reporter identity or database internal IDs are returned
    forbidden_keys = [
        "id", "user_id", "reporter_id", "reporter_name", "email",
        "ip", "user_agent", "device", "session_id", "account_id",
        "moderator_id", "password_hash"
    ]
    for key in forbidden_keys:
        assert key not in track_data
        assert key not in update_entry

    # 7. Confirm /health and /docs still work
    h = client.get("/health")
    assert h.status_code == 200
    assert h.json() == {"status": "ok"}

    d = client.get("/docs")
    assert d.status_code == 200

    print("ALL M4 TRACKING CHECKS PASSED SUCCESSFULLY")


test_m4_checks = run_m4_checks

if __name__ == "__main__":
    run_m4_checks()
