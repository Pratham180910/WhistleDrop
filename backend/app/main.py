from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.limiter import limiter
from app.api.routes import reports, moderator


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        return response


# Initialize FastAPI application with Swagger UI configured at /docs
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="WhistleDrop is an anonymous confidential reporting backend — Speak Without Being Seen.",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Register slowapi limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Middlewares
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, this should be restricted
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Generic Exception Handler (prevent leaking stack traces)
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    # Log exception here internally if we had a logger
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


# Register routes
app.include_router(reports.router)
app.include_router(moderator.router)


@app.get("/health", tags=["Health"])
def health_check():
    """Health check endpoint returning system status."""
    return {"status": "ok"}
