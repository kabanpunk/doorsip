import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .database import engine, Base
from .routers import rooms, games, websocket

Base.metadata.create_all(bind=engine)

app = FastAPI(title="DoOrSip API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CARDS_PATH = os.getenv("CARDS_PATH", "./data/cards")
if os.path.exists(CARDS_PATH):
    app.mount("/cards", StaticFiles(directory=CARDS_PATH), name="cards")

app.include_router(games.router, prefix="/api/games", tags=["games"])
app.include_router(rooms.router, prefix="/api/rooms", tags=["rooms"])
app.include_router(websocket.router, prefix="/ws", tags=["websocket"])


@app.get("/api/health")
def health_check():
    return {"status": "ok"}
