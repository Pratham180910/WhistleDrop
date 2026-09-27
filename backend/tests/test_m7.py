import sys
from pathlib import Path
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import get_db, Base
from app.core.security import hash_password
from app.models.moderator import Moderator


def run_m7_checks():
    engine = sa.create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=sa.pool.StaticPool,
    )
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    MOD_USER = "security_mod"
    MOD_PASS = "SecurePass123!"

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
    # Must preserve limits for testing
    client = TestClient(app, raise_server_exceptions=False)

    print("--- Running M7 Security Checks ---")
    if hasattr(app.state, "limiter"):
        app.state.limiter.reset()

    # 1. Test Rate Limiting for POST /reports
    for i in range(5):
        res = client.post("/reports", json={"category": "Security", "description": f"Rate limit test {i}"})
        assert res.status_code == 201, f"Failed on request {i}"
    
    # 6th should fail (5/minute)
    res_limit = client.post("/reports", json={"category": "Security", "description": "Too many"})
    assert res_limit.status_code == 429
    assert "Rate limit exceeded" in res_limit.text

    # Let's get a case code to track
    # Wait, the limits apply per IP. We can use a different 'IP' in tests or just clear limiter memory.
    # We will test track with a dummy case code first.
    for i in range(20):
        client.get("/reports/track/dummy")
    
    res_track_limit = client.get("/reports/track/dummy")
    assert res_track_limit.status_code == 429

    # Check moderator login rate limit
    for i in range(5):
        client.post("/moderator/login", json={"username": "wrong", "password": "bad"})
    
    res_mod_limit = client.post("/moderator/login", json={"username": MOD_USER, "password": MOD_PASS})
    assert res_mod_limit.status_code == 429

    # 2. Missing/Invalid/Expired JWT
    r1 = client.get("/moderator/reports")
    assert r1.status_code == 401

    r2 = client.get("/moderator/reports", headers={"Authorization": "Bearer bad_token"})
    assert r2.status_code == 401

    # 3. Security Headers check
    # Need an endpoint that isn't rate limited right now, or just /docs
    health = client.get("/health")
    assert health.status_code == 200
    assert health.headers.get("X-Content-Type-Options") == "nosniff"
    assert health.headers.get("X-Frame-Options") == "DENY"

    # 4. Input Hardening
    # Description max is 5000, let's bypass rate limit by pretending we are a new IP
    app.state.limiter.reset()

    # Oversized description
    big_desc = "A" * 6000
    res_large = client.post("/reports", json={"category": "Security", "description": big_desc})
    assert res_large.status_code == 422

    # Malformed Report ID
    mod_token = client.post("/moderator/login", json={"username": MOD_USER, "password": MOD_PASS}).json()["access_token"]
    res_bad_id = client.get("/moderator/reports/not-a-uuid", headers={"Authorization": f"Bearer {mod_token}"})
    assert res_bad_id.status_code == 422

    # Empty note
    # First submit a report, get a real case, track it, find report_id
    res_valid = client.post("/reports", json={"category": "Security", "description": "Good report"})
    assert res_valid.status_code == 201

    res_reports = client.get("/moderator/reports", headers={"Authorization": f"Bearer {mod_token}"})
    assert res_reports.status_code == 200
    rep_id = res_reports.json()["results"][0]["id"]

    res_empty_note = client.patch(f"/moderator/reports/{rep_id}/status", json={"status": "UNDER_REVIEW", "note": "  "}, headers={"Authorization": f"Bearer {mod_token}"})
    assert res_empty_note.status_code == 422

    # No Sensitive Information in responses
    detail_res = client.get(f"/moderator/reports/{rep_id}", headers={"Authorization": f"Bearer {mod_token}"})
    assert detail_res.status_code == 200
    detail_str = detail_res.text
    assert "case_code_hash" not in detail_str
    assert "password_hash" not in detail_str
    assert "reporter" not in detail_str

    print("ALL M7 SECURITY HARDENING CHECKS PASSED SUCCESSFULLY")


test_m7_checks = run_m7_checks

if __name__ == "__main__":
    run_m7_checks()
