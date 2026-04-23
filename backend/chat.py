# ============================================================
# backend/chat.py
# ------------------------------------------------------------
# Endpoint POST /chat — odpowiada na pytania użytkownika
# w oparciu o wiedzę z pliku `data_samples/test_firma.txt`.
#
# Przepływ jednego zapytania:
#   1. Widget wysyła POST /chat z JSON {"question": "...", "company_id": "..."}
#   2. Pydantic waliduje body → ChatRequest
#   3. Budujemy prompt: SYSTEM_PROMPT (instrukcje) + CONTEXT (wiedza o firmie) + pytanie
#   4. Wysyłamy do Ollamy (lokalny serwer LLM) → Bielik generuje odpowiedź
#   5. Zwracamy JSON {"answer": "...", "company_id": "..."}
#
# DOCELOWO (gdy będzie ChromaDB):
#   Zamiast doklejać cały plik CONTEXT do promptu, zrobimy retrieval:
#   znajdziemy w bazie wektorowej 3-5 najbardziej pasujących chunków
#   do pytania i tylko one polecą do modelu. Plusy: szybciej, taniej,
#   skaluje się do setek stron dokumentów.
# ============================================================

from fastapi import APIRouter
from pydantic import BaseModel
from pathlib import Path
import ollama
from backend.config import LLM_MODEL

# Router = "mini-aplikacja" z własnym zestawem endpointów.
# Potem w main.py robimy app.include_router(router), żeby
# dołączyć je do głównej aplikacji FastAPI.
router = APIRouter()


# Schemat danych wejściowych. Pydantic automatycznie:
#  - sparsuje JSON z requestu,
#  - zwaliduje typy (question MUSI być stringiem),
#  - zwróci 422 Unprocessable Entity, jak coś się nie zgadza.
# `company_id` ma default "test", więc widget może go nie wysyłać.
class ChatRequest(BaseModel):
    question: str
    company_id: str = "test"


# ------------------------------------------------------------
# Kontekst (wiedza o firmie)
# ------------------------------------------------------------
# Na razie czytamy JEDEN plik TXT i wstrzykujemy CAŁĄ jego treść
# do każdego promptu. To prymitywne, ale wystarczy do prototypu:
#  - plik ma ~30 linii, mieści się swobodnie w kontekście modelu,
#  - łatwo edytować — zmieniasz plik, restart uvicorna i działa.
#
# Path(__file__).resolve().parent.parent =
#   __file__                          = .../backend/chat.py
#   .resolve().parent                 = .../backend
#   .resolve().parent.parent          = .../chatbot  (root projektu)
# Dzięki temu ścieżka działa niezależnie od tego, skąd odpalamy
# uvicorna (z roota, z backendu, z IDE, cokolwiek).
#
# read_text() wykonuje się RAZ, przy starcie aplikacji. Plik NIE
# jest czytany przy każdym requeście — I/O tylko raz.
CONTEXT_FILE = Path(__file__).resolve().parent.parent / "data_samples" / "test_firma.txt"
CONTEXT = CONTEXT_FILE.read_text(encoding="utf-8")


# System prompt = instrukcje "kim jesteś i jak się zachowuj".
# Model dostaje to z rolą "system" — ma to wyższy priorytet niż
# zwykła wiadomość użytkownika. Tu wymuszamy:
#  - odpowiadaj TYLKO z kontekstu (nie halucynuj),
#  - jak nie wiesz → standardowa grzeczna odmowa,
#  - po polsku, zwięźle.
SYSTEM_PROMPT = """Jesteś asystentem obsługi klienta.
Odpowiadaj WYŁĄCZNIE na podstawie podanego kontekstu.
Jeśli odpowiedzi nie ma w kontekście, napisz:
'Nie mam tej informacji, proszę skontaktować się z obsługą.'
Odpowiadaj po polsku, zwięźle i uprzejmie."""


@router.post("/chat")
async def chat(request: ChatRequest):
    # Budujemy prompt użytkownika: kontekst + pytanie.
    # Model dostanie to jako wiadomość z rolą "user" (patrz niżej).
    prompt = f"""Kontekst:
{CONTEXT}

Pytanie: {request.question}"""

    # Wywołanie Ollamy. Biblioteka `ollama` w Pythonie robi pod spodem
    # HTTP request do localhost:11434 (Ollama serwer) i czeka na odpowiedź.
    # Format `messages` to ten sam standard co OpenAI Chat API:
    # lista wiadomości, każda z rolą ("system"/"user"/"assistant") i treścią.
    #
    # UWAGA: to jest BLOKUJĄCE wywołanie — na CPU Bielik potrafi
    # odpowiadać 5-30 sekund. Docelowo warto dodać streaming
    # (stream=True) albo timeout, żeby widget nie wisiał w nieskończoność.
    response = ollama.chat(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
    )

    # Zwracamy JSON w formacie, którego oczekuje widget:
    # { "answer": "...", "company_id": "..." }
    # Pole `answer` jest kluczowe — widget czyta je i wyświetla w bąbelku.
    return {
        "answer": response["message"]["content"],
        "company_id": request.company_id
    }
