# WhistleDrop — Speak Without Being Seen

> Secure, anonymous confidential reporting backend built for the GDG on Campus SRM 2026 technical recruitment task.

---

## 1. Project Title
**WhistleDrop** — *Speak Without Being Seen*

## 2. Short Project Description
WhistleDrop is a privacy-first backend REST API that enables individuals to submit confidential incident reports completely anonymously, track report progress using a one-time cryptographic case code, and empowers authorized moderators to investigate, update, search, and permanently close cases under strict workflow validation.

## 3. Problem Statement
Traditional reporting and whistleblower systems frequently require user registration, log IP addresses, or maintain session fingerprints. Fear of retaliation and lack of true anonymity prevent individuals from reporting critical safety, ethical, harassment, or security violations. WhistleDrop solves this by providing a zero-identity, zero-account reporting channel with cryptographic case tracking.

## 4. Key Features
- **Zero-Account Anonymous Reporting**: Submit reports across categories (`Security`, `Harassment`, `Corruption`, `Technical`, `Other`) with optional evidence reference URLs without registration or authentication.
- **Cryptographic Case Tracking**: Reporters receive an unguessable 24-byte URL-safe token. The system only stores a one-way SHA-256 hash. Plaintext codes are never stored in the database or server logs.
- **Role-Based Moderator Operations**: Protected endpoints secured with JWT authentication (bcrypt password hashing, expiry validation, active-status enforcement).
- **Audit History & Status Workflow**: Every status transition generates an immutable `StatusUpdate` audit note. Workflow transitions are strictly enforced:
  `SUBMITTED` &rarr; `UNDER_REVIEW` &rarr; `RESOLVED` / `DISMISSED` &rarr; `CLOSED`.
- **Permanent Case Closure**: Cases finalized as `RESOLVED` or `DISMISSED` can be permanently `CLOSED`, preventing reopening or alteration (HTTP 409 guard).
- **Safe Moderator Search & Filtering**: Filter reports by status, category, and text search across safe fields (`description` and `category`). `case_code_hash` is never exposed or searchable.
- **Defensive Security & Rate Limiting**: In-memory rate limiting via SlowAPI (5/min on submissions and logins, 20/min on tracking), strict HTTP security headers (`nosniff`, `DENY`, `CSP`, `HSTS`), and sanitized generic 500 error handlers.

## 5. Technology Stack
- **Language & Runtime**: Python 3.10+
- **Framework**: FastAPI (Starlette + Pydantic v2)
- **ASGI Server**: Uvicorn
- **Database & ORM**: PostgreSQL (or SQLite for local test runs), SQLAlchemy 2.0+
- **Database Migrations**: Alembic
- **Security & Cryptography**: Bcrypt (passwords), PyJWT (tokens), hashlib SHA-256 (case codes), secrets (CSPRNG token generation)
- **Rate Limiting**: SlowAPI (token bucket / limits)
- **Testing**: Pytest, HTTPX

## 6. Architecture & Project Structure
```
WhistleDrop/
├── .gitignore
├── README.md
└── backend/
    ├── .env.example
    ├── .gitignore
    ├── alembic.ini
    ├── requirements.txt
    ├── alembic/
    │   ├── env.py
    │   └── script.py.mako
    ├── app/
    │   ├── main.py
    │   ├── api/
    │   │   └── routes/
    │   │       ├── auth.py
    │   │       ├── moderator.py
    │   │       └── reports.py
    │   ├── core/
    │   │   ├── config.py
    │   │   ├── database.py
    │   │   ├── limiter.py
    │   │   └── security.py
    │   ├── db/
    │   │   └── base.py
    │   ├── models/
    │   │   ├── moderator.py
    │   │   └── report.py
    │   ├── schemas/
    │   │   ├── moderator.py
    │   │   ├── moderator_report.py
    │   │   └── report.py
    │   └── services/
    │       ├── moderator_report_service.py
    │       ├── moderator_service.py
    │       └── report_service.py
    └── tests/
        ├── test_m3.py
        ├── test_m4.py
        ├── test_m5.py
        ├── test_m6.py
        ├── test_m7.py
        └── test_m8.py
```

## 7. Setup Instructions

### Prerequisites
- Python 3.10 or higher
- Git

### 1. Clone repository & navigate to backend
```bash
git clone <repo-url>
cd WhistleDrop/backend
```

### 2. Create and activate a virtual environment
```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies
```bash
python -m pip install -r requirements.txt
```

## 8. Environment Variables
Create a `.env` file in the `backend/` directory by copying `.env.example`:
```bash
cp .env.example .env
```

| Variable | Description | Default / Example |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection URL | `postgresql://user:pass@localhost:5432/whistledrop` |
| `JWT_SECRET_KEY` | Secret key used for signing JWTs | *(Set a cryptographically strong secret)* |
| `JWT_ALGORITHM` | JWT signing algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Lifetime of moderator access tokens | `60` |

*Note: For local automated tests, an in-memory SQLite database is automatically utilized.*

## 9. Database Setup & Migrations
WhistleDrop uses Alembic to manage database schema migrations.
```bash
# Generate initial migration
alembic revision --autogenerate -m "Initial schema"

# Apply migrations
alembic upgrade head
```

## 10. How to Run the Backend
Start the development server with Uvicorn:
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
The server will start at `http://127.0.0.1:8000`.

## 11. API Endpoint Table

| Method | Endpoint | Auth | Rate Limit | Description |
|---|---|---|---|---|
| `GET` | `/health` | None | None | Service liveness probe |
| `GET` | `/docs` | None | None | Interactive Swagger UI documentation |
| `GET` | `/openapi.json` | None | None | OpenAPI JSON schema specification |
| `POST` | `/reports` | None | 5/min | Submit an anonymous report (returns case code) |
| `GET` | `/reports/track/{case_code}` | None | 20/min | Track report status and history using case code |
| `POST` | `/moderator/login` | None | 5/min | Authenticate moderator & obtain JWT |
| `GET` | `/moderator/reports` | Bearer JWT | None | List reports (search, status, category, pagination) |
| `GET` | `/moderator/reports/{report_id}` | Bearer JWT | None | Retrieve detailed report with full audit history |
| `PATCH` | `/moderator/reports/{report_id}/status` | Bearer JWT | None | Update report status following workflow transitions |
| `PATCH` | `/moderator/reports/{report_id}/close` | Bearer JWT | None | Permanently close a resolved/dismissed report |

## 12. Request & Response Examples

### Anonymous Report Submission
**Request**: `POST /reports`
```json
{
  "category": "Security",
  "description": "Unsecured API key exposed in public repository.",
  "evidence_url": "https://example.com/evidence"
}
```
**Response** (`201 Created`):
```json
{
  "case_code": "xK82_mN92lP0qR4sT7vW1yZ3",
  "status": "SUBMITTED"
}
```

### Anonymous Case Tracking
**Request**: `GET /reports/track/xK82_mN92lP0qR4sT7vW1yZ3`
**Response** (`200 OK`):
```json
{
  "status": "UNDER_REVIEW",
  "created_at": "2026-09-27T10:00:00Z",
  "updated_at": "2026-09-27T10:15:00Z",
  "updates": [
    {
      "status": "SUBMITTED",
      "note": "Report submitted anonymously.",
      "created_at": "2026-09-27T10:00:00Z"
    },
    {
      "status": "UNDER_REVIEW",
      "note": "Assigned to security response team.",
      "created_at": "2026-09-27T10:15:00Z"
    }
  ]
}
```

### Moderator Login
**Request**: `POST /moderator/login`
```json
{
  "username": "moderator_admin",
  "password": "SecurePassword123!"
}
```
**Response** (`200 OK`):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsIn...",
  "token_type": "bearer"
}
```

### Permanent Case Closure
**Request**: `PATCH /moderator/reports/7e4544d6-fcf7-4f67-82ba-c71b69f69ce3/close`
*(Headers: `Authorization: Bearer <token>`)*
```json
{
  "note": "Case permanently resolved and closed after remediation."
}
```
**Response** (`200 OK`):
```json
{
  "id": "7e4544d6-fcf7-4f67-82ba-c71b69f69ce3",
  "category": "Security",
  "description": "Unsecured API key exposed in public repository.",
  "evidence_url": "https://example.com/evidence",
  "status": "CLOSED",
  "created_at": "2026-09-27T10:00:00Z",
  "updated_at": "2026-09-27T11:00:00Z",
  "updates": [ ... ]
}
```

## 13. Swagger Documentation
Interactive API exploration and OpenAPI specifications are available out of the box:
- **Swagger UI**: `http://127.0.0.1:8000/docs`
- **ReDoc**: `http://127.0.0.1:8000/redoc`
- **OpenAPI Schema**: `http://127.0.0.1:8000/openapi.json`

## 14. cURL Examples

```bash
# 1. Health check
curl -X GET "http://127.0.0.1:8000/health"

# 2. Submit anonymous report
curl -X POST "http://127.0.0.1:8000/reports" \
  -H "Content-Type: application/json" \
  -d '{"category": "Corruption", "description": "Bribery incident reported at facility."}'

# 3. Track report status
curl -X GET "http://127.0.0.1:8000/reports/track/<CASE_CODE>"

# 4. Moderator login
curl -X POST "http://127.0.0.1:8000/moderator/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "SecretPassword"}'

# 5. Moderator search & list reports
curl -X GET "http://127.0.0.1:8000/moderator/reports?search=facility&status=SUBMITTED" \
  -H "Authorization: Bearer <ACCESS_TOKEN>"

# 6. Close report permanently
curl -X PATCH "http://127.0.0.1:8000/moderator/reports/<REPORT_ID>/close" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"note": "Investigation complete."}'
```

## 15. Anonymous Reporting Explanation
WhistleDrop achieves privacy by architecture, not merely policy:
- Reporters never create accounts, log in, or provide identifying information.
- The reporting schema contains only `category`, `description`, and an optional `evidence_url`.
- No user identity, IP address, user-agent, or browser fingerprint is captured in the database or response schemas.
- Once submitted, the reporter's only connection to the report is a cryptographically generated, one-time case code.

## 16. Privacy & Security Design
- **No Sensitive Fields in Responses**: `case_code_hash`, `password_hash`, internal IDs, and moderator credentials never appear in API responses.
- **Generic 404 on Tracking**: Looking up an invalid or non-existent case code returns a generic `404 Report not found`, preventing brute-force enumeration of valid codes.
- **Generic 401 on Auth**: Invalid usernames, incorrect passwords, or inactive moderator accounts all return the same generic `401 Invalid credentials` response to prevent username enumeration.
- **Fail-Safe Exception Handling**: A centralized exception handler catches unhandled errors and returns a generic `{"detail": "Internal server error"}`, ensuring Python stack traces and database errors are never leaked to clients.
- **Security Headers**: Injected on all HTTP responses:
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `X-XSS-Protection: 1; mode=block`
  - `Strict-Transport-Security: max-age=31536000; includeSubDomains`
  - `Content-Security-Policy: default-src 'self'`

## 17. Case-Code Design
- **Generation**: Generated using Python's `secrets.token_urlsafe(24)`, providing cryptographically strong entropy (192 bits).
- **Storage**: When generated, the plaintext case code is hashed using `SHA-256`. Only the `case_code_hash` is persisted in the database.
- **One-Time Exposure**: The plaintext case code is returned to the reporter strictly once in the `POST /reports` response. It is never logged and cannot be recovered from the database.
- **Lookup Verification**: During tracking (`GET /reports/track/{case_code}`), the incoming case code is hashed with SHA-256 and matched against `case_code_hash`.

## 18. Moderator Authentication
- **Password Security**: Passwords are saved strictly as bcrypt hashes with salt. Plaintext passwords are never stored.
- **Stateless Tokens**: Authentication yields signed HS256 JWT access tokens containing expiration (`exp`), issued-at (`iat`), and subject (`sub`).
- **Account State Verification**: Deactivated moderators (`is_active = False`) are rejected at both login and subsequent token dependency validation.

## 19. Status Workflow
The case lifecycle follows a strict state machine:
```
  [SUBMITTED]
       │
       ▼
 [UNDER_REVIEW]
   │         │
   ▼         ▼
[RESOLVED] [DISMISSED]
   │         │
   └────┬────┘
        ▼
     [CLOSED] (Permanent & Terminal)
```
- Allowed transitions:
  - `SUBMITTED` &rarr; `UNDER_REVIEW`
  - `UNDER_REVIEW` &rarr; `RESOLVED` or `DISMISSED`
  - `RESOLVED` &rarr; `CLOSED`
  - `DISMISSED` &rarr; `CLOSED`
- **Immutability of `CLOSED`**: Once a case is marked `CLOSED`, it cannot be transitioned back, reopened, or updated. Attempts to alter a `CLOSED` case return HTTP `409 Conflict`.

## 20. Assumptions & Design Decisions
1. **Backend-First Demonstration**: The project is intentionally designed and demonstrated strictly as a REST API (Swagger/Postman/cURL) with no frontend dependencies.
2. **In-Memory Rate Limiting**: SlowAPI uses an in-memory key-value backend, which avoids requiring external infrastructure like Redis for single-instance deployments while remaining modular for Redis attachment if clustered.
3. **Tracking Data Isolation**: The tracking endpoint exposes only lifecycle status and notes (`updates`), omitting original report descriptions and evidence links from public tracking responses to minimize information disclosure if a case code is compromised.
4. **Moderator ID Privacy**: Notes in `StatusUpdate` do not record the moderator's UUID or username to avoid leaking staff identity to external parties tracking cases.

## 21. Testing Instructions
The test suite validates functionality across all milestones (M3 through M8).
Run the full test suite with pytest from the `backend/` directory:
```bash
cd backend
python -m pytest -v
```
Alternatively, individual milestone test scripts can be executed directly:
```bash
python tests/test_m3.py
python tests/test_m4.py
python tests/test_m5.py
python tests/test_m6.py
python tests/test_m7.py
python tests/test_m8.py
```

## 22. Limitations
- **Single-Host Rate Limiter**: The in-memory rate limiter does not synchronize counters across multiple horizontal instances without Redis backing.
- **Evidence URL Reference**: Evidence submission is currently restricted to reference URLs rather than direct binary file uploads to avoid storage vulnerabilities and metadata leakage.
- **Reporter Dialogue**: The current protocol allows one-way communication from moderators to reporters via status update notes, but does not yet support anonymous bidirectional messaging.

## 23. Security & Anonymity Note
> **Important Privacy Clarification**: The WhistleDrop application itself does not collect, record, or store reporter identity, IP addresses, user-agent strings, device fingerprints, or session metadata. However, external infrastructure layers (such as network routers, cloud reverse proxies, CDN gateways, and ISP logging) may retain connection metadata outside of the application's boundaries. Furthermore, any identifying information voluntarily disclosed by the reporter within the free-text description or evidence URL content is outside application control. For maximum anonymity, reporters should access the service over Tor or a privacy-preserving VPN.
