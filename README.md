# WhistleDrop — Confidential Reporting Backend

WhistleDrop is a **backend-only anonymous reporting system** designed to allow whistleblowers to submit confidential reports and track their progress without creating an account or directly identifying themselves.

The system provides two roles:

* **Whistleblower** — submits and tracks reports anonymously using a secure case code.
* **Moderator** — authenticates using JWT and manages submitted reports through a controlled status workflow.

> **Scope:** WhistleDrop is a backend/API project. No frontend or UI is required.

---

## Features

### Anonymous Reporting

* No user account is required to submit a report.
* No email address is required.
* Reports do not store reporter IP addresses or browser fingerprints.
* Each report receives a randomly generated case code.
* The plaintext case code is returned to the whistleblower after submission.

### Secure Case-Code Tracking

The plaintext case code is **not stored in the database**.

Instead:

1. A cryptographically random case code is generated.
2. The plaintext code is returned to the whistleblower.
3. The backend calculates a SHA-256 hash of the case code.
4. Only the hash is stored in the database.
5. When tracking a report, the supplied case code is hashed and compared with the stored hash.

This means the database does not contain the plaintext tracking code.

### Moderator Authentication

Moderator endpoints are protected using:

* JWT access tokens
* Bearer authentication
* Password hashing with bcrypt
* Rate limiting on the login endpoint
* Timing-attack mitigation during username verification

### Report Lifecycle

Reports follow a controlled state machine:

```text
SUBMITTED
    |
    v
UNDER_REVIEW
   / \
  v   v
RESOLVED  DISMISSED
   \       /
    v     v
      CLOSED
```

Once a report reaches `CLOSED`, it cannot be modified or reopened.

### Status History

Every status transition is recorded with:

* Status
* Moderator note
* Timestamp

This provides a complete history of the report's lifecycle.

### Anti-Enumeration Protection

The tracking endpoint does not reveal whether an invalid case code partially matches or exists.

Unknown or invalid case codes return a generic:

```text
404 Not Found
```

### Rate Limiting

The API uses `slowapi` to limit sensitive endpoints and reduce brute-force attempts.

---

# Technology Stack

| Component           | Technology          |
| ------------------- | ------------------- |
| Language            | Python 3.9+         |
| API Framework       | FastAPI             |
| ASGI Server         | Uvicorn             |
| Database            | PostgreSQL          |
| Cloud Database      | Supabase PostgreSQL |
| ORM                 | SQLAlchemy          |
| Database Migrations | Alembic             |
| Authentication      | JWT                 |
| Password Hashing    | bcrypt              |
| Rate Limiting       | SlowAPI             |
| API Documentation   | Swagger UI / ReDoc  |

---

# Project Structure

```text
WhistleDrop/
│
├── backend/
│   │
│   ├── app/
│   │   ├── api/
│   │   │   └── routes/
│   │   │       ├── reports.py
│   │   │       └── moderator.py
│   │   │
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── database.py
│   │   │   └── limiter.py
│   │   │
│   │   ├── models/
│   │   │   ├── report.py
│   │   │   └── moderator.py
│   │   │
│   │   ├── schemas/
│   │   │   ├── report.py
│   │   │   ├── moderator.py
│   │   │   └── moderator_report.py
│   │   │
│   │   ├── services/
│   │   │   ├── report_service.py
│   │   │   ├── moderator_service.py
│   │   │   └── moderator_report_service.py
│   │   │
│   │   └── main.py
│   │
│   ├── alembic/
│   │   ├── versions/
│   │   └── env.py
│   │
│   ├── seed_moderator.py
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── .env
│   └── .env.example
│
└── README.md
```

---

# Requirements

Before running the project, install:

* Python 3.9 or newer
* PostgreSQL database
* A PostgreSQL-compatible database such as Supabase
* Git

---

# Environment Variables

Create a `.env` file inside the backend directory.

Example:

```env
DATABASE_URL=postgresql://user:password@host:port/dbname

JWT_SECRET_KEY=your_super_secret_key_here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

MODERATOR_USERNAME=admin
MODERATOR_PASSWORD=secure_password_here
```

### Environment Variable Description

| Variable                      | Purpose                               |
| ----------------------------- | ------------------------------------- |
| `DATABASE_URL`                | PostgreSQL database connection string |
| `JWT_SECRET_KEY`              | Secret used to sign JWT tokens        |
| `JWT_ALGORITHM`               | JWT signing algorithm                 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT expiration time                   |
| `MODERATOR_USERNAME`          | Initial moderator username            |
| `MODERATOR_PASSWORD`          | Initial moderator password            |

> **Security:** Never commit `.env` or real credentials, passwords, JWT secrets, or database credentials to GitHub.

Add the following to `.gitignore`:

```gitignore
.env
venv/
__pycache__/
*.pyc
```

---

# Installation

Clone the repository:

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd WhistleDrop/backend
```

## 1. Create the virtual environment

### Windows

```powershell
python -m venv venv
```

Activate it:

```powershell
.\venv\Scripts\Activate.ps1
```

After activation, your terminal should show:

```text
(venv)
```

### macOS / Linux

```bash
python3 -m venv venv
source venv/bin/activate
```

---

## 2. Install dependencies

```bash
pip install -r requirements.txt
```

---

## 3. Configure the database

Add your PostgreSQL/Supabase connection string to `.env`:

```env
DATABASE_URL=postgresql://...
```

The application normalizes supported PostgreSQL connection-string formats for SQLAlchemy compatibility.

---

## 4. Run database migrations

```bash
alembic upgrade head
```

This creates the required database tables.

---

## 5. Create the initial moderator

Run:

```bash
python seed_moderator.py
```

The script creates the initial moderator account using the configured moderator credentials.

---

## 6. Start the server

```bash
uvicorn app.main:app --reload
```

The backend will run at:

```text
http://127.0.0.1:8000
```

---

# API Documentation

Once the server is running:

### Swagger UI

```text
http://127.0.0.1:8000/docs
```

### ReDoc

```text
http://127.0.0.1:8000/redoc
```

### OpenAPI Specification

```text
http://127.0.0.1:8000/openapi.json
```

---

# API Endpoints

## Public Endpoints

These endpoints do not require authentication.

### Create Report

```http
POST /reports
```

Creates a new anonymous report.

Example request:

```json
{
  "category": "Security",
  "description": "I found a vulnerability in the payment gateway.",
  "evidence_url": "https://example.com/evidence"
}
```

Example response:

```json
{
  "case_code": "2O1rw4_GiTXAIa7Lza-udEr4FCHO9ko5",
  "status": "SUBMITTED"
}
```

### Important

The returned `case_code` should be saved by the whistleblower.

The plaintext case code is not stored in the database and should be treated as the credential required to track the report.

---

## Track Report

```http
GET /reports/track/{case_code}
```

Tracks an anonymous report using the plaintext case code.

Example:

```http
GET /reports/track/2O1rw4_GiTXAIa7Lza-udEr4FCHO9ko5
```

Example response:

```json
{
  "status": "UNDER_REVIEW",
  "created_at": "2026-10-01T13:18:35.294Z",
  "updated_at": "2026-10-01T13:33:26.764Z",
  "updates": [
    {
      "status": "SUBMITTED",
      "note": "Report submitted anonymously.",
      "created_at": "2026-10-01T13:18:35.596Z"
    },
    {
      "status": "UNDER_REVIEW",
      "note": "Moderator review started.",
      "created_at": "2026-10-01T13:33:26.764Z"
    }
  ]
}
```

If the case code is invalid or unknown, the API returns a generic `404 Not Found`.

---

# Moderator API

Moderator endpoints require:

```http
Authorization: Bearer <JWT_ACCESS_TOKEN>
```

---

## Moderator Login

```http
POST /moderator/login
```

Authenticates a moderator and returns a JWT access token.

Example request:

```json
{
  "username": "admin",
  "password": "secure_password_here"
}
```

The returned access token can be supplied to protected endpoints using:

```http
Authorization: Bearer <token>
```

---

## List Reports

```http
GET /moderator/reports
```

Returns reports available to the authenticated moderator.

Supported query parameters include:

```text
status
category
search
page
page_size
```

Example:

```http
GET /moderator/reports?status=SUBMITTED&page=1&page_size=20
```

---

## Get Report Details

```http
GET /moderator/reports/{report_id}
```

Returns detailed information about a report, including its status history.

Example:

```http
GET /moderator/reports/996c7514-a49d-4c36-afca-0a9d0a7e564a
```

The `report_id` is the internal PostgreSQL UUID.

---

## Update Report Status

```http
PATCH /moderator/reports/{report_id}/status
```

Updates the status according to the allowed state transitions.

Example:

```json
{
  "status": "UNDER_REVIEW",
  "note": "Moderator review started."
}
```

Allowed workflow:

```text
SUBMITTED → UNDER_REVIEW

UNDER_REVIEW → RESOLVED
UNDER_REVIEW → DISMISSED

RESOLVED → CLOSED
DISMISSED → CLOSED
```

Invalid transitions are rejected by the backend.

---

## Permanently Close a Report

```http
PATCH /moderator/reports/{report_id}/close
```

A report can only be permanently closed after reaching:

```text
RESOLVED
```

or:

```text
DISMISSED
```

Example request:

```json
{
  "note": "Case permanently closed."
}
```

After closing:

```text
CLOSED
```

The report cannot be modified or reopened.

Attempts to modify a closed report return:

```http
409 Conflict
```

Example:

```json
{
  "detail": "Report is permanently closed and cannot be modified."
}
```

---

# Security Design

## 1. No Reporter Identity Storage

The reporting system does not require reporter accounts.

The report model does not associate reports with:

* Email addresses
* User accounts
* IP addresses
* Browser fingerprints

This supports anonymous reporting.

---

## 2. Hashed Case Codes

Case codes are generated randomly and are intended to be shown to the whistleblower.

Only the SHA-256 digest is stored in the database.

Conceptually:

```text
Plaintext Case Code
        |
        v
     SHA-256
        |
        v
Database Hash
```

During tracking:

```text
User Case Code
      |
      v
    SHA-256
      |
      v
Compare with stored hash
```

---

## 3. UUID Report IDs

Reports use UUID primary keys instead of sequential integer IDs.

Example:

```text
996c7514-a49d-4c36-afca-0a9d0a7e564a
```

This avoids simple sequential ID enumeration.

---

## 4. JWT Authentication

Moderator endpoints require a valid JWT access token.

Example:

```http
Authorization: Bearer eyJhbGciOi...
```

Expired or invalid tokens are rejected.

---

## 5. Password Hashing

Moderator passwords are stored using bcrypt hashing rather than plaintext passwords.

---

## 6. Timing-Attack Mitigation

Moderator authentication performs password-hash verification even when a supplied username does not exist.

This helps reduce timing differences that could otherwise assist username enumeration.

---

## 7. Rate Limiting

Sensitive endpoints use `slowapi` rate limiting.

This helps reduce:

* Brute-force login attempts
* Case-code guessing
* Excessive API requests

---

## 8. Security Headers

The FastAPI application applies security-related HTTP headers including:

```text
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security
Content-Security-Policy
```

---

# Database Model

The main report model contains information such as:

```text
id
case_code_hash
category
description
evidence_url
status
created_at
updated_at
```

Status history is stored separately and linked to the report.

```text
Report
  |
  +── StatusUpdate
  +── StatusUpdate
  +── StatusUpdate
```

Each status update contains:

```text
id
report_id
status
note
created_at
```

---

# Report State Machine

The report lifecycle is intentionally restricted.

```text
                 ┌──────────────┐
                 │   SUBMITTED  │
                 └──────┬───────┘
                        │
                        v
                 ┌──────────────┐
                 │ UNDER_REVIEW │
                 └──────┬───────┘
                        │
                 ┌──────┴──────┐
                 │             │
                 v             v
          ┌───────────┐  ┌───────────┐
          │ RESOLVED  │  │ DISMISSED │
          └─────┬─────┘  └─────┬─────┘
                │               │
                └───────┬───────┘
                        v
                 ┌──────────────┐
                 │    CLOSED    │
                 └──────────────┘
```

Once the state becomes:

```text
CLOSED
```

the backend rejects further modifications.

---

# Error Handling

The API uses appropriate HTTP status codes.

Examples:

| Status | Meaning                                           |
| ------ | ------------------------------------------------- |
| `200`  | Successful request                                |
| `201`  | Report successfully created                       |
| `401`  | Authentication failed or token is invalid         |
| `404`  | Resource not found / invalid tracking code        |
| `409`  | Operation conflicts with the current report state |
| `422`  | Validation error or invalid status transition     |
| `500`  | Internal server error                             |

For tracking, invalid case codes intentionally return a generic `404` response to avoid revealing whether a case code exists.

---

# Testing the Backend

After starting the server, open:

```text
http://127.0.0.1:8000/docs
```

The Swagger interface can be used to test all API endpoints.

A typical verification flow is:

```text
1. Create anonymous report
        ↓
2. Save returned case_code
        ↓
3. Track report using case_code
        ↓
4. Login as moderator
        ↓
5. Obtain JWT access token
        ↓
6. Authorize Swagger using Bearer token
        ↓
7. List reports
        ↓
8. Retrieve report details
        ↓
9. SUBMITTED → UNDER_REVIEW
        ↓
10. UNDER_REVIEW → RESOLVED/DISMISSED
        ↓
11. RESOLVED/DISMISSED → CLOSED
        ↓
12. Verify CLOSED report cannot be modified
```

---

# Verified Backend Functionality

The following core functionality has been tested during development:

* PostgreSQL/Supabase database connectivity
* Database migrations
* Anonymous report creation
* Secure case-code generation
* Case-code hashing
* Anonymous report tracking
* Generic response for invalid tracking codes
* Moderator account provisioning
* Moderator JWT authentication
* Protected moderator endpoints
* Report listing
* Report detail retrieval
* Status transitions
* Status history recording
* Report resolution
* Permanent report closure
* Protection against modification of closed reports
* API security headers
* Rate limiting

Example verified lifecycle:

```text
SUBMITTED
    ↓
UNDER_REVIEW
    ↓
RESOLVED
    ↓
CLOSED
```

A subsequent modification attempt after `CLOSED` is rejected with:

```http
409 Conflict
```

---

# Running the Backend Again

When returning to the project:

```powershell
cd C:\Users\Dell\OneDrive\Desktop\WhistleDrop\backend
```

Activate the virtual environment:

```powershell
.\venv\Scripts\Activate.ps1
```

Start the server:

```powershell
uvicorn app.main:app --reload
```

Then open:

```text
http://127.0.0.1:8000/docs
```

---

# Development Notes

The project is intentionally focused on the backend API and security requirements.

There is **no frontend/UI requirement** for this project.

Swagger UI and ReDoc are used only as API documentation and testing interfaces provided by FastAPI.

---

# Security Notes

For production deployment:

* Use a strong randomly generated `JWT_SECRET_KEY`.
* Never commit `.env` files.
* Use a secure PostgreSQL connection.
* Restrict CORS origins instead of allowing all origins.
* Use HTTPS.
* Store production secrets using the deployment platform's secret-management system.
* Use appropriate database permissions.
* Review rate limits according to expected traffic.
* Keep Python and dependencies updated.

---

# License

Add the project's chosen license here if applicable.

Example:

```text
MIT License
```

If no license has been selected, this section can be removed.
