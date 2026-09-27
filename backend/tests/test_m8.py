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

def test_m8_features():
    engine = sa.create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=sa.pool.StaticPool,
    )
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    MOD_USER = "mod_m8"
    MOD_PASS = "ModeratorPass@M8"

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
    client = TestClient(app, raise_server_exceptions=False)

    # Login
    login_res = client.post("/moderator/login", json={"username": MOD_USER, "password": MOD_PASS})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    auth = {"Authorization": f"Bearer {token}"}

    # 1. Create a report and transition it to RESOLVED -> CLOSED
    rpt = client.post("/reports", json={"category": "Security", "description": "This is a search target."})
    assert rpt.status_code == 201
    case_code_1 = rpt.json()["case_code"]
    
    # Get ID
    list_res = client.get("/moderator/reports", headers=auth)
    report_id_1 = list_res.json()["results"][0]["id"]
    
    client.patch(f"/moderator/reports/{report_id_1}/status", json={"status": "UNDER_REVIEW", "note": "ok"}, headers=auth)
    client.patch(f"/moderator/reports/{report_id_1}/status", json={"status": "RESOLVED", "note": "ok"}, headers=auth)

    close_res = client.patch(f"/moderator/reports/{report_id_1}/close", json={"note": "Permanent close"}, headers=auth)
    assert close_res.status_code == 200
    assert close_res.json()["status"] == "CLOSED"
    
    # Verify CLOSED cannot be modified
    mod_res = client.patch(f"/moderator/reports/{report_id_1}/status", json={"status": "UNDER_REVIEW", "note": "reopen"}, headers=auth)
    assert mod_res.status_code == 409
    
    # Verify CLOSED cannot be re-closed
    reclose_res = client.patch(f"/moderator/reports/{report_id_1}/close", json={"note": "close again"}, headers=auth)
    assert reclose_res.status_code == 409
    
    # Unauthorized closure returns 401
    unauth_close = client.patch(f"/moderator/reports/{report_id_1}/close", json={"note": "Permanent close"})
    assert unauth_close.status_code == 401
    
    # 2. Test DISMISSED -> CLOSED
    rpt2 = client.post("/reports", json={"category": "Other", "description": "Another report"})
    list_res2 = client.get("/moderator/reports", headers=auth)
    report_id_2 = [r["id"] for r in list_res2.json()["results"] if r["category"] == "Other"][0]
    
    client.patch(f"/moderator/reports/{report_id_2}/status", json={"status": "UNDER_REVIEW", "note": "ok"}, headers=auth)
    client.patch(f"/moderator/reports/{report_id_2}/status", json={"status": "DISMISSED", "note": "ok"}, headers=auth)
    close_res2 = client.patch(f"/moderator/reports/{report_id_2}/close", json={"note": "Close"}, headers=auth)
    assert close_res2.status_code == 200
    assert close_res2.json()["status"] == "CLOSED"

    # 3. Test Search
    client.post("/reports", json={"category": "Harassment", "description": "Unique finding word"})
    search_res = client.get("/moderator/reports?search=target", headers=auth)
    assert search_res.status_code == 200
    assert search_res.json()["total"] == 1
    
    search_res2 = client.get("/moderator/reports?search=finding", headers=auth)
    assert search_res2.status_code == 200
    assert search_res2.json()["total"] == 1
    
    # Search doesn't leak or search hash
    search_empty = client.get("/moderator/reports?search=XYZ123HASH", headers=auth)
    assert search_empty.status_code == 200
    assert search_empty.json()["total"] == 0
    
    # 4. Check Privacy
    det = client.get(f"/moderator/reports/{report_id_1}", headers=auth).json()
    det_str = str(det)
    for forbidden in ["case_code_hash", case_code_1, "reporter", "ip_address", "user_agent", "device", "email", "phone", "password_hash", "database"]:
        assert forbidden not in det_str
        
    # 5. Check Swagger still works
    assert client.get("/openapi.json").status_code == 200

    print("ALL M8 CHECKS PASSED SUCCESSFULLY")

if __name__ == "__main__":
    test_m8_features()
