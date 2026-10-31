"""Followthrough FastAPI entrypoint."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import init_db
from .jobs.scheduler import start_scheduler
from .routes.wispr import router as wispr_router
from .routes.ingest import router as ingest_router
from .routes.review import router as review_router
from .routes.post import router as post_router
from .routes.command import router as command_router
from .routes.jobs import router as jobs_router

app = FastAPI(title="Followthrough", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "*",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(wispr_router)
app.include_router(ingest_router)
app.include_router(review_router)
app.include_router(post_router)
app.include_router(command_router)
app.include_router(jobs_router)


@app.on_event("startup")
async def on_startup():
    await init_db()
    start_scheduler()


@app.get("/")
def root():
    return {"status": "ok", "app": "Followthrough", "version": app.version}


@app.get("/health")
def health():
    return {"status": "healthy"}