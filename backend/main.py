# backend/main.py
from fastapi import FastAPI
from backend.chat import router as chat_router
from backend.ingest import router as ingest_router

app = FastAPI(title="Plug-and-Play Chatbot API")

app.include_router(chat_router)
app.include_router(ingest_router)

@app.get("/health")
async def health():
    return {"status": "ok", "model": "bielik"}