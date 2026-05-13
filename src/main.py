from fastapi import FastAPI
from src.auth import router as auth_router
from src.db import initialize_postgres_tables
from src.messages import router as messages_router
from src.realtime import sio
import socketio


fastapi_app = FastAPI()
fastapi_app.include_router(auth_router)
fastapi_app.include_router(messages_router)


@fastapi_app.on_event("startup")
def on_startup():
    initialize_postgres_tables()




@fastapi_app.get("/health")
def health():
    return {"status": "ok"}

app = socketio.ASGIApp(sio, other_asgi_app=fastapi_app)
