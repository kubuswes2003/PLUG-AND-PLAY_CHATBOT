# ============================================================
# backend/main.py
# ------------------------------------------------------------
# Główny punkt wejścia aplikacji FastAPI.
# Tutaj tworzymy instancję `app`, podpinamy middleware (CORS)
# i włączamy routery z innych plików (np. /chat z chat.py).
#
# Uruchamianie:
#     uvicorn backend.main:app --reload --port 8000
#
# Struktura projektu:
#     backend/
#       main.py      <-- TEN PLIK (start aplikacji)
#       chat.py      <-- endpoint /chat (pyta Bielika)
#       ingest.py    <-- (TODO) endpoint ładujący pliki do ChromaDB
#       config.py    <-- ustawienia (nazwa modelu, ścieżki, itp.)
# ============================================================

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.chat import router as chat_router

# Tworzymy instancję aplikacji. `title` pokaże się w auto-generowanej
# dokumentacji Swaggera pod http://localhost:8000/docs
app = FastAPI(title="Plug-and-Play Chatbot API")

# CORS = Cross-Origin Resource Sharing.
# Widget czatu jest serwowany z innego portu (np. 8080 — statyczny
# http.server), a backend chodzi na 8000. Bez CORS przeglądarka
# blokuje takie requesty z powodów bezpieczeństwa.
# `allow_origins=["*"]` = zezwalamy wszystkim — OK na czas developmentu,
# ale PRZED DEPLOYEM na produkcję trzeba to zawęzić do konkretnych
# domen klientów (np. ["https://techsklep.pl"]).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Podpinamy router z chat.py. Wszystkie endpointy zdefiniowane
# w chat.py (np. POST /chat) staną się dostępne w aplikacji.
app.include_router(chat_router)


# Health-check — prosty endpoint do sprawdzenia czy backend żyje.
# Używany np. przez `curl http://localhost:8000/health` albo przez
# systemy monitoringu (load balancer, uptime checker).
@app.get("/health")
async def health():
    return {"status": "ok", "model": "bielik"}
