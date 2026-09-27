import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import get_db, Base
from app.core.security import hash_password
from app.models.moderator import Moderator


def run_m6_checks():
    engine = sa.create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=sa.pool.StaticPool,
    )
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    MOD_USER = "mod_test"
    MOD_PASS = "ModeratorPass@123"

    db = TestingSession()
    db.add(Moderator(
        username=MOD_USER,
        password_hash=hash_password(MOD_PASS),
        is_active=True,
    ))
    db.commit()
    db.close()

    def override_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    if hasattr(app.state, "limiter"):
        app.state.limiter.reset()
    client = TestClient(app, raise_server_exceptions=True)

    # Get JWT
    login_res = client.post("/moderator/login", json={"username": MOD_USER, "password": MOD_PASS})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    auth = {"Authorization": f"Bearer {token}"}

    # 1. Anonymous access to all M6 endpoints → 401
    r1 = client.get("/moderator/reports")
    assert r1.status_code == 401, f"Expected 401 anonymous list, got {r1.status_code}"

    # Submit a report to have data
    rpt = client.post("/reports", json={"category": "Security", "description": "Test report for M6"})
    assert rpt.status_code == 201
    case_code = rpt.json()["case_code"]

    # 2. Authenticated list returns results
    list_res = client.get("/moderator/reports", headers=auth)
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total"] >= 1
    assert "results" in list_data
    report_id = list_data["results"][0]["id"]

    # 3. Status filter works
    sf_res = client.get("/moderator/reports?status=SUBMITTED", headers=auth)
    assert sf_res.status_code == 200
    assert sf_res.json()["total"] >= 1

    sf_none = client.get("/moderator/reports?status=RESOLVED", headers=auth)
    assert sf_none.status_code == 200
    assert sf_none.json()["total"] == 0

    # 4. Category filter works
    cf_res = client.get("/moderator/reports?category=Security", headers=auth)
    assert cf_res.status_code == 200
    assert cf_res.json()["total"] >= 1

    # 5. Pagination works
    pg_res = client.get("/moderator/reports?page=1&page_size=1", headers=auth)
    assert pg_res.status_code == 200
    pg_data = pg_res.json()
    assert pg_data["page"] == 1
    assert pg_data["page_size"] == 1
    assert len(pg_data["results"]) <= 1

    pg2 = client.get("/moderator/reports?page=999&page_size=10", headers=auth)
    assert pg2.status_code == 200
    assert len(pg2.json()["results"]) == 0

    # 6. Valid moderator can view report detail
    det_res = client.get(f"/moderator/reports/{report_id}", headers=auth)
    assert det_res.status_code == 200
    det = det_res.json()
    assert det["id"] == report_id
    assert "description" in det
    assert "updates" in det
    assert len(det["updates"]) >= 1

    # 7. Unknown report ID returns 404
    import uuid
    fake_id = str(uuid.uuid4())
    not_found = client.get(f"/moderator/reports/{fake_id}", headers=auth)
    assert not_found.status_code == 404

    # 8. Valid moderator can update status and note
    patch_res = client.patch(
        f"/moderator/reports/{report_id}/status",
        json={"status": "UNDER_REVIEW", "note": "Reviewing the report now."},
        headers=auth,
    )
    assert patch_res.status_code == 200, f"Expected 200, got {patch_res.status_code}: {patch_res.text}"
    patch_data = patch_res.json()
    assert patch_data["status"] == "UNDER_REVIEW"

    # 11. StatusUpdate is created
    assert len(patch_data["updates"]) >= 2  # initial + this one
    assert any(u["status"] == "UNDER_REVIEW" for u in patch_data["updates"])

    # 9. Invalid status is rejected (422)
    bad_status = client.patch(
        f"/moderator/reports/{report_id}/status",
        json={"status": "INVALID_STATUS", "note": "Test note"},
        headers=auth,
    )
    assert bad_status.status_code == 422

    # Disallowed workflow transition — UNDER_REVIEW → SUBMITTED (not allowed)
    bad_trans = client.patch(
        f"/moderator/reports/{report_id}/status",
        json={"status": "SUBMITTED", "note": "Going back"},
        headers=auth,
    )
    assert bad_trans.status_code == 422

    # 10. Empty note is rejected (422)
    empty_note = client.patch(
        f"/moderator/reports/{report_id}/status",
        json={"status": "RESOLVED", "note": "   "},
        headers=auth,
    )
    assert empty_note.status_code == 422

    # Complete workflow: UNDER_REVIEW → RESOLVED
    resolve_res = client.patch(
        f"/moderator/reports/{report_id}/status",
        json={"status": "RESOLVED", "note": "Issue has been resolved."},
        headers=auth,
    )
    assert resolve_res.status_code == 200
    assert resolve_res.json()["status"] == "RESOLVED"

    # 12. Reporter identity, case_code_hash, plaintext case code never in responses
    detail_after = client.get(f"/moderator/reports/{report_id}", headers=auth).json()
    detail_str = str(detail_after)
    assert "case_code_hash" not in detail_str
    assert case_code not in detail_str  # plaintext case code absent
    for forbidden in ["reporter", "ip_address", "user_agent", "device", "email", "phone"]:
        assert forbidden not in detail_str

    # 13. Existing M5 tests still work (login unchanged)
    assert client.post("/moderator/login", json={"username": MOD_USER, "password": MOD_PASS}).status_code == 200
    assert client.post("/moderator/login", json={"username": "wrong", "password": "bad"}).status_code == 401

    # Public endpoints still work without auth
    assert client.post("/reports", json={"category": "Other", "description": "Anon check"}).status_code == 201
    new_code = client.post("/reports", json={"category": "Other", "description": "Track check"}).json()["case_code"]
    assert client.get(f"/reports/track/{new_code}").status_code == 200

    # 14. /health and /docs
    assert client.get("/health").status_code == 200
    assert client.get("/docs").status_code == 200

    print("ALL M6 MODERATOR MANAGEMENT CHECKS PASSED SUCCESSFULLY")


test_m6_checks = run_m6_checks

if __name__ == "__main__":
    run_m6_checks()
