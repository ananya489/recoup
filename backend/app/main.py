from contextlib import asynccontextmanager

from fastapi import FastAPI

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
    await ensure_webhook_indexes()
    await ensure_action_indexes()
    yield


app = FastAPI(
    title="Recoup",
    lifespan=lifespan,
)

app.include_router(webhook_router)
app.include_router(recovery_router)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "recoup-backend",
    }