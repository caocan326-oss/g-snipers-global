from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.llm import status_label
from app.routers import ai, auth, dashboard, distribution, geo, inquiries, insights, offsite, onsite, seo, work_orders

app = FastAPI(title="G-Snipers Overseas", version="0.1.0")

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
app.include_router(geo.router)
app.include_router(onsite.router)
app.include_router(offsite.router)
app.include_router(distribution.router)
app.include_router(work_orders.router)
app.include_router(inquiries.router)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "llm": status_label()}
