from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import admin, auth, threads
from app.db.session import init_db

app = FastAPI(title="AI Operations Assistant")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(threads.router)
app.include_router(admin.router)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/health")
def health():
    return {"status": "ok"}
