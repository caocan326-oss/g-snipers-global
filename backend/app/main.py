import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.llm import status_label
from app.routers import ai, auth, dashboard, distribution, execution, geo, inquiries, insights, offsite, onsite, ops, seo, site_context, usage, work_orders
from app.usage import UsageLimitError

logger = logging.getLogger("gsnipers")
UNEXPECTED_FAILURE = "这次没办成，请再试一次。系统没有悄悄做完。"

app = FastAPI(title="G-Snipers Overseas", version="0.1.0")


@app.exception_handler(UsageLimitError)
def usage_limit_handler(_request: Request, exc: UsageLimitError) -> JSONResponse:
    return JSONResponse(status_code=429, content={"detail": str(exc)})


@app.exception_handler(Exception)
def unhandled_error(request: Request, exc: Exception) -> JSONResponse:
    if isinstance(exc, (HTTPException, StarletteHTTPException)):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    if isinstance(exc, RequestValidationError):
        return JSONResponse(status_code=422, content={"detail": exc.errors()})
    logger.exception("unhandled %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": UNEXPECTED_FAILURE})

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ai.router)
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(insights.router)
app.include_router(seo.router)
app.include_router(site_context.router)
app.include_router(geo.router)
app.include_router(onsite.router)
app.include_router(offsite.router)
app.include_router(distribution.router)
app.include_router(execution.router)
app.include_router(work_orders.router)
app.include_router(inquiries.router)
app.include_router(ops.router)
app.include_router(usage.router)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "llm": status_label()}
