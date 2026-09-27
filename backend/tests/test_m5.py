import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import get_db, Base
from app.core.security import hash_password, decode_access_token
from app.models.moderator import Moderator


def run_m5_checks():
    # Setup in-memory test DB
    engine = sa.create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=sa.pool.StaticPool,
    )
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    # Seed moderator: password never hardcoded; we only hash it at runtime
    TEST_USERNAME = "test_moderator"
    TEST_PASSWORD = "TestSecurePass@99"
    TEST_INACTIVE_USERNAME = "inactive_mod"

    db = TestingSession()
    active_mod = Moderator(
        username=TEST_USERNAME,
        password_hash=hash_password(TEST_PASSWORD),
        is_active=True,
    )
    inactive_mod = Moderator(
        username=TEST_INACTIVE_USERNAME,
        password_hash=hash_password("AnotherPass@42"),
        is_active=False,
    )
    db.add_all([active_mod, inactive_mod])
    db.commit()
    db.close()

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    if hasattr(app.state, "limiter"):
        app.state.limiter.reset()
    client = TestClient(app)

    # 1. Successful login returns JWT
    res = client.post("/moderator/login", json={"username": TEST_USERNAME, "password": TEST_PASSWORD})
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    token = data["access_token"]

    # 2. JWT contains expiration and correct subject
    payload = decode_access_token(token)
    assert payload["sub"] == TEST_USERNAME
    assert "exp" in payload
    assert "iat" in payload
    assert payload.get("type") == "access"

    # 3. Wrong password returns generic 401
    res = client.post("/moderator/login", json={"username": TEST_USERNAME, "password": "WrongPassword!"})
    assert res.status_code == 401
    assert "access_token" not in res.text

    # 4. Unknown username returns generic 401
    res = client.post("/moderator/login", json={"username": "does_not_exist", "password": "anything"})
    assert res.status_code == 401

    # 5. Inactive moderator returns generic 401
    res = client.post("/moderator/login", json={"username": TEST_INACTIVE_USERNAME, "password": "AnotherPass@42"})
    assert res.status_code == 401

    # 6. No password_hash or internal data in any response
    for r in [
        client.post("/moderator/login", json={"username": TEST_USERNAME, "password": TEST_PASSWORD}),
        client.post("/moderator/login", json={"username": "bad", "password": "bad"}),
    ]:
        assert "password_hash" not in r.text
        assert "password" not in r.json().get("access_token", r.text)

    # 7. Public report submission still works without authentication
    report_res = client.post("/reports", json={
        "category": "Security",
        "description": "Anonymous report for regression test"
    })
    assert report_res.status_code == 201
    case_code = report_res.json()["case_code"]

    # 8. Public case tracking still works without authentication
    track_res = client.get(f"/reports/track/{case_code}")
    assert track_res.status_code == 200
    assert track_res.json()["status"] == "SUBMITTED"

    # 9. /health and /docs still work
    assert client.get("/health").status_code == 200
    assert client.get("/docs").status_code == 200

    print("ALL M5 AUTHENTICATION CHECKS PASSED SUCCESSFULLY")


test_m5_checks = run_m5_checks

if __name__ == "__main__":
    run_m5_checks()
