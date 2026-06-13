from contextlib import asynccontextmanager

from fastapi import FastAPI

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from db import init_pool, close_pool
from routers import containers, zones, history, routes, analytics, dashboard, gamification, ml, reports
from routers.ml import load_model


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_pool()
    load_model()
    yield
    close_pool()


app = FastAPI(
    title="ECOTRACK API",
    description="Plateforme intelligente de gestion des déchets urbains",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(containers.router, prefix="/containers", tags=["containers"])
app.include_router(zones.router,       prefix="/zones",      tags=["zones"])
app.include_router(history.router,     prefix="/history",    tags=["history"])
app.include_router(routes.router,      prefix="/routes",     tags=["routes"])
app.include_router(analytics.router,   prefix="/analytics",  tags=["analytics"])
app.include_router(dashboard.router,   prefix="/dashboard",  tags=["dashboard"])
app.include_router(gamification.router,                      tags=["gamification"])
app.include_router(ml.router,          prefix="/ml",         tags=["ml"])
app.include_router(reports.router,     prefix="/reports",    tags=["reports"])


@app.get("/health", tags=["system"])
def health_status():
    return {"status": "ok", "message": "API is running"}
