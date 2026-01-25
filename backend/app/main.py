from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.briefings import router as briefings_router
from app.api.commitments import router as commitments_router
from app.api.admin import router as admin_router
from app.api.ingestion import router as ingestion_router
from app.api.meetings import router as meetings_router
from app.api.calendar import router as calendar_router
from app.api.status import router as status_router
from app.api.people import router as people_router
from app.api.sources import router as sources_router
from app.api.memory import router as memory_router
from app.db import init_db
from app.settings import get_cors_origins

app = FastAPI(title="Custos Core API")
cors_origins = get_cors_origins()
if cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-API-Key"],
    )
app.include_router(ingestion_router)
app.include_router(briefings_router)
app.include_router(commitments_router)
app.include_router(meetings_router)
app.include_router(calendar_router)
app.include_router(status_router)
app.include_router(people_router)
app.include_router(admin_router)
app.include_router(sources_router)
app.include_router(memory_router)


@app.on_event("startup")
def startup() -> None:
    init_db()
