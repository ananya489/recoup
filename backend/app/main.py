from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.cases import router as cases_router
from app.api.dashboard import router as dashboard_router
from app.api.recovery import router as recovery_router
from app.recovery.actions_repository import (
    ensure_indexes as ensure_action_indexes,
)
from app.webhooks.repository import (
    ensure_indexes as ensure_webhook_indexes,
)
from app.webhooks.router import router as webhook_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Initialize required MongoDB indexes when the API starts.
    """

    await ensure_webhook_indexes()
    await ensure_action_indexes()

    yield


app = FastAPI(
    title="Recoup",
    lifespan=lifespan,
)


# -------------------------------------------------------------
# CORS
# -------------------------------------------------------------
#
# The React frontend will normally run on another origin,
# for example:
#
#   http://localhost:5173
#
# Allow local development origins here.
#

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------------------------------------------------
# Existing Batch 1-3 routers
# -------------------------------------------------------------

app.include_router(
    webhook_router
)

app.include_router(
    recovery_router
)


# -------------------------------------------------------------
# Batch 4 Sub-batch A routers
# -------------------------------------------------------------

app.include_router(
    cases_router
)

app.include_router(
    dashboard_router
)


# -------------------------------------------------------------
# Health
# -------------------------------------------------------------

@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "recoup-backend",
    }