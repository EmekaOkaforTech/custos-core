from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.briefings import router as briefings_router
from app.api.commitments import router as commitments_router
from app.api.admin import router as admin_router
from app.api.ingestion import router as ingestion_router
from app.api.meetings import router as meetings_router
from app.api.calendar import router as calendar_router
from app.api.email import router as email_router
from app.api.chat import router as chat_router
from app.api.status import router as status_router
from app.api.summarization import router as summarization_router
from app.api.analytics import router as analytics_router
from app.api.export import router as export_router
from app.api.users import router as users_router
from app.api.query import router as query_router
from app.api.backup import router as backup_router
from app.api.people import router as people_router
from app.api.sources import router as sources_router
from app.api.memory import router as memory_router
from app.api.network import router as network_router
from app.api.inference import router as inference_router
from app.api.sync import router as sync_router
from app.api.models import router as models_router
from app.api.audio import router as audio_router
from app.db import init_db
from app.settings import get_cors_origins
from app.ops.sync_scheduler import start_sync_scheduler
from app.ops.backup_scheduler import start_backup_scheduler
from app.ops.inference_queue import start_inference_queue

app = FastAPI(title="Custos Core API")
cors_origins = get_cors_origins()
if cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-API-Key"],
    )
app.include_router(ingestion_router)
app.include_router(briefings_router)
app.include_router(commitments_router)
app.include_router(meetings_router)
app.include_router(calendar_router)
app.include_router(email_router)
app.include_router(chat_router)
app.include_router(status_router)
app.include_router(analytics_router)
app.include_router(export_router)
app.include_router(users_router)
app.include_router(summarization_router)
app.include_router(backup_router)
app.include_router(people_router)
app.include_router(admin_router)
app.include_router(sources_router)
app.include_router(memory_router)
app.include_router(query_router)
app.include_router(network_router)
app.include_router(inference_router)
app.include_router(sync_router)
app.include_router(models_router)
app.include_router(audio_router)


@app.on_event("startup")
def startup() -> None:
    init_db()
    start_sync_scheduler()
    start_backup_scheduler()
    start_inference_queue()