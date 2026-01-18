from fastapi import FastAPI

from app.api.briefings import router as briefings_router
from app.api.commitments import router as commitments_router
from app.api.ingestion import router as ingestion_router
from app.api.status import router as status_router
from app.api.people import router as people_router
from app.db import init_db

app = FastAPI(title="Custos Core API")
app.include_router(ingestion_router)
app.include_router(briefings_router)
app.include_router(commitments_router)
app.include_router(status_router)
app.include_router(people_router)


@app.on_event("startup")
def startup() -> None:
    init_db()
