# WhistleDrop — Confidential Reporting Backend

WhistleDrop is a **backend-only anonymous reporting system** designed to allow whistleblowers to submit confidential reports and track their progress without creating an account or providing identifying information.

The system provides two separate workflows:

* **Whistleblower workflow:** Submit and track an anonymous report using a secure case code.
* **Moderator workflow:** Authenticate using JWT and review, update, resolve, dismiss, and permanently close reports.

> **Note:** WhistleDrop is a backend/API project. No frontend or UI application is required.

---

## Live Production Deployment

* **API Base URL:** https://whistle-drop-ten.vercel.app
* **Health Check:** https://whistle-drop-ten.vercel.app/health
* **Interactive Documentation (Swagger):** https://whistle-drop-ten.vercel.app/docs

---

## Features

### Anonymous Reporting

* Submit reports without creating an account.
* No reporter profile is required.
* Reports contain:

  * Category
  * Description
  * Optional evidence URL
* A cryptographically random case code is generated when a report is submitted.
* The plaintext case code is returned to the reporter when the report is created.
* The backend stores only a SHA-256 hash of the case code.

### Anonymous Report Tracking

A reporter can track their report using the plaintext case code:

```text
GET /reports/track/{case_code}
```

The tracking endpoint returns:

* Current report status
* Report creation time
* Last update time
* Status update history

Invalid or unknown case codes return a generic `404 Not Found` response so that the API does not reveal whether a particular report exists.

### Moderator Authentication

Moderators authenticate through:

```text
POST /moderator/login
```

Successful authentication returns a JWT access token.

Protected moderator endpoints require:

```text
Authorization: Bearer <access_token>
```

### Moderator Report Management

Authenticated moderators can:

* List reports
* Filter reports by status
* Filter reports by category
* Search reports
* Paginate results
* View individual reports
* View status history
* Update report status
* Resolve reports
* Dismiss reports
* Permanently close reports

### Report State Machine

Reports follow a controlled lifecycle:

```text
SUBMITTED
    │
    ▼
UNDER_REVIEW
    │
    ├──────────────► RESOLVED
    │
    └──────────────► DISMISSED
                         │
                         ▼
                       CLOSED
```

Once a report reaches `CLOSED`, it cannot be modified or reopened.

Attempts to modify a closed report return:

```text
409 Conflict
```

---

# Technology Stack

* **Python 3.9+**
* **FastAPI**
* **Uvicorn**
* **SQLAlchemy**
* **PostgreSQL**
* **Supabase** as the PostgreSQL database provider
* **Alembic** for database migrations
* **JWT** for moderator authentication
* **bcrypt** for password hashing
* **SlowAPI** for rate limiting
* **Pydantic** for request/response validation

---

# Project Structure

The project follows a modular backend architecture similar to:

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
│   │   │   ├── moderator.py
│   │   │   ├── moderator_report.py
│   │   │   └── ...
│   │   │
│   │   ├── services/
│   │   │   ├── moderator_service.py
│   │   │   ├── moderator_report_service.py
│   │   │   └── ...
│   │   │
│   │   └── main.py
│   │
│   ├── alembic/
│   ├── requirements.txt
│   ├── seed_moderator.py
│   └── ...
│
└── README.md
```

---

# Requirements

Before running the project, install:

* Python 3.9 or newer
* PostgreSQL-compatible database
* Git
* A configured `.env` file

Supabase can be used as the PostgreSQL database provider.

---

# Environment Variables

Create a `.env` file in the backend directory.

Example:

```env
DATABASE_URL=postgresql://user:password@host:port/database
JWT_SECRET_KEY=your_super_secret_key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
MODERATOR_USERNAME=admin
MODERATOR_PASSWORD=your_secure_password
```

### Important

Never commit the real `.env` file or real credentials to GitHub.

Add the following to `.gitignore`:

```gitignore
.env
venv/
__pycache__/
*.pyc
```

---

# Installation

## 1. Clone the repository

```bash
git clone https://github.com/Pratham180910/WhistleDrop.git
cd WhistleDrop/backend
```

## 2. Create a virtual environment

### Windows

```powershell
python -m venv venv
```

Activate it:

```powershell
.\venv\Scripts\Activate.ps1
```

You should then see:

```text
(venv)
```

at the beginning of your terminal prompt.

### macOS/Linux

```bash
python3 -m venv venv
source venv/bin/activate
```

---

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

## 4. Configure environment variables

Create `.env` and provide the required database and authentication configuration.

---

## 5. Run database migrations

```bash
alembic upgrade head
```

This creates the required database tables.

---

## 6. Create the initial moderator

Run:

```bash
python seed_moderator.py
```

The moderator credentials are taken from the environment variables.

---

# Running the Backend

Start the FastAPI server:

```bash
uvicorn app.main:app --reload
```

The backend will be available at:

```text
http://127.0.0.1:8000
```

---

# API Documentation

FastAPI automatically provides interactive API documentation.

### Swagger UI

```text
http://127.0.0.1:8000/docs
```

### ReDoc

```text
http://127.0.0.1:8000/redoc
```

### OpenAPI specification

```text
http://127.0.0.1:8000/openapi.json
```

These interfaces are used for **API documentation and testing**. They are not a separate frontend application.

---

# Health Check

The backend provides:

```http
GET /health
```

Example response:

```json
{
  "status": "ok"
}
```

---

# API Endpoints

## Public Endpoints

These endpoints do not require moderator authentication.

### Submit a Report

```http
POST /reports
```

Example request:

```json
{
  "category": "Security",
  "description": "I found a vulnerability in the payment gateway.",
  "evidence_url": "https://example.com/evidence"
}
```

The API generates a secure case code.

Example response:

```json
{
  "case_code": "EXAMPLE_CASE_CODE",
  "status": "SUBMITTED"
}
```

The actual case code generated by the system will be different for every report.

### Track a Report

```http
GET /reports/track/{case_code}
```

Example:

```text
GET /reports/track/EXAMPLE_CASE_CODE
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

An invalid or unknown case code returns a generic:

```text
404 Not Found
```

response.

---

# Moderator Endpoints

All moderator report-management endpoints require a valid JWT access token.

## Moderator Login

```http
POST /moderator/login
```

Example request:

```json
{
  "username": "admin",
  "password": "your_password"
}
```

Example response:

```json
{
  "access_token": "YOUR_ACCESS_TOKEN",
  "token_type": "bearer"
}
```

Use the returned token with:

```text
Authorization: Bearer YOUR_ACCESS_TOKEN
```

---

## List Reports

```http
GET /moderator/reports
```

Optional query parameters include:

```text
status
category
search
page
page_size
```

Example:

```text
GET /moderator/reports?status=SUBMITTED&page=1&page_size=20
```

---

## Get Report Details

```http
GET /moderator/reports/{report_id}
```

This returns:

* Report UUID
* Category
* Description
* Evidence URL
* Current status
* Creation time
* Last update time
* Complete status update history

---

## Update Report Status

```http
PATCH /moderator/reports/{report_id}/status
```

Example:

```json
{
  "status": "UNDER_REVIEW",
  "note": "Moderator review started."
}
```

Valid workflow transitions include:

```text
SUBMITTED → UNDER_REVIEW
UNDER_REVIEW → RESOLVED
UNDER_REVIEW → DISMISSED
```

Invalid transitions are rejected by the backend.

---

## Permanently Close a Report

```http
PATCH /moderator/reports/{report_id}/close
```

A report can only be closed after reaching:

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

the report becomes immutable.

Any later modification attempt returns:

```text
409 Conflict
```

with:

```json
{
  "detail": "Report is permanently closed and cannot be modified."
}
```

---

# API Screenshots

The screenshots below document the verified API functionality and deployment.

### Health Check

![Health Check](<img width="1917" height="872" alt="heath check whistledrop" src="https://github.com/user-attachments/assets/b74cb31c-d78c-4bea-9375-a8a314fb5aa3" />
)

---

### Swagger API Documentation

![Swagger API Documentation](PASTE_SCREENSHOT_LINK_HERE)

---

### Anonymous Report Submission

![Anonymous Report Submission](PASTE_SCREENSHOT_LINK_HERE)

---

### Case Code Tracking

![Case Code Tracking](PASTE_SCREENSHOT_LINK_HERE)

---

### Moderator Login

![Moderator Login](PASTE_SCREENSHOT_LINK_HERE)

---

### Moderator Report List

![Moderator Report List](PASTE_SCREENSHOT_LINK_HERE)

---

### Moderator Report Details

![Moderator Report Details](PASTE_SCREENSHOT_LINK_HERE)

---

### Report Status Update

![Report Status Update](PASTE_SCREENSHOT_LINK_HERE)

---

### Report Resolution

![Report Resolution](PASTE_SCREENSHOT_LINK_HERE)

---

### Permanent Report Closure

![Permanent Report Closure](PASTE_SCREENSHOT_LINK_HERE)

---

### Closed Report Modification Protection

![Closed Report Protection](PASTE_SCREENSHOT_LINK_HERE)

---

### Vercel Deployment

**Live API:** https://whistle-drop-ten.vercel.app

![Vercel Deployment](PASTE_SCREENSHOT_LINK_HERE)

---

# Security Design

## 1. No Reporter Account

The reporting workflow does not require a reporter account.

The report model does not require:

* Username
* Email address
* Reporter account
* Password

---

## 2. Case Code Hashing

A random case code is generated when a report is submitted.

The plaintext case code is returned to the reporter but is not stored directly in the database.

Instead, the backend stores a SHA-256 hash:

```text
plaintext case code
        │
        ▼
     SHA-256
        │
        ▼
  case_code_hash
```

The database therefore does not contain the plaintext tracking code.

---

## 3. Anti-Enumeration Protection

When tracking a report:

```text
case code
    ↓
SHA-256 hash
    ↓
database lookup
```

If the hash does not match an existing report, the API returns a generic `404 Not Found`.

This prevents the tracking endpoint from revealing whether a particular case code exists.

---

## 4. Rate Limiting

The API uses SlowAPI for rate limiting.

Rate limits are applied to sensitive endpoints to reduce brute-force and abuse attempts.

---

## 5. JWT Authentication

Moderator endpoints are protected using JWT authentication.

A valid token must be supplied using:

```http
Authorization: Bearer <token>
```

The token is issued only after successful moderator authentication.

---

## 6. Password Hashing

Moderator passwords are stored using bcrypt hashing rather than plaintext passwords.

---

## 7. UUID Report IDs

Reports use UUID primary keys rather than sequential integer IDs.

Example:

```text
996c7514-a49d-4c36-afca-0a9d0a7e564a
```

This avoids exposing simple sequential report identifiers.

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

## Reports

The `reports` table contains information such as:

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

The report status uses the following values:

```text
SUBMITTED
UNDER_REVIEW
RESOLVED
DISMISSED
CLOSED
```

---

## Status Updates

The `status_updates` table stores the history of report status changes.

Each update contains:

```text
id
report_id
status
note
created_at
```

This allows moderators and reporters to see the progression of a report without exposing the reporter's identity.

---

# Verified API Lifecycle

The core backend lifecycle has been tested successfully.

### 1. Anonymous report creation

A report was successfully created and assigned a case code.

### 2. Case-code tracking

The generated case code successfully returned the report's current status and history.

### 3. Invalid case-code handling

Invalid/unknown case codes return a generic `404 Not Found`.

### 4. Moderator authentication

Moderator login successfully generated JWT access tokens.

### 5. Moderator report retrieval

Authenticated moderators successfully retrieved reports using their UUID.

### 6. Status transition

The following transition was successfully tested:

```text
SUBMITTED
     ↓
UNDER_REVIEW
```

### 7. Resolution

The following transition was successfully tested:

```text
UNDER_REVIEW
     ↓
RESOLVED
```

### 8. Permanent closure

The following transition was successfully tested:

```text
RESOLVED
     ↓
CLOSED
```

### 9. Closed-report protection

An attempt to modify a closed report correctly returned:

```text
409 Conflict
```

confirming that closed reports cannot be reopened or modified.

---

# Example Complete Lifecycle

```text
Anonymous Reporter
        │
        │ POST /reports
        ▼
    SUBMITTED
        │
        │ Moderator authentication
        ▼
  UNDER_REVIEW
        │
        ├───────────────┐
        ▼               ▼
    RESOLVED         DISMISSED
        │               │
        └───────┬───────┘
                ▼
              CLOSED
                │
                ▼
       Permanently Locked
```

The reporter can independently track the report throughout the process using the case code.

---

# Important Security Notes

### Never commit secrets

Do not commit:

```text
.env
JWT secrets
Database passwords
Moderator passwords
Access tokens
```

### Never publish real case codes

Case codes provide access to anonymous report tracking. Treat them as confidential credentials.

### Never publish real database credentials

Use environment variables for database configuration.

---

# Development Commands

Activate the virtual environment:

### Windows PowerShell

```powershell
.\venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

Run migrations:

```powershell
alembic upgrade head
```

Seed the moderator:

```powershell
python seed_moderator.py
```

Start the backend:

```powershell
uvicorn app.main:app --reload
```

Stop the server:

```text
CTRL + C
```

---

# Project Status

The core backend API has been implemented and verified.

### Verified

* Anonymous report creation
* Secure case-code generation
* Case-code hashing
* Anonymous report tracking
* Invalid case-code handling
* Moderator authentication
* JWT authorization
* Moderator report listing
* Moderator report retrieval
* Status history
* Status transitions
* Report resolution
* Report dismissal workflow
* Permanent report closure
* Closed-report immutability
* Database persistence
* API security headers
* Rate limiting
* Database migrations

The project is intentionally **backend/API-only**. No frontend application is required for the system's intended functionality.

---

# License

This project is intended for academic/project development purposes.
