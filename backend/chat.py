# chat który pyta Bielika z kontekstem wczytanym z pliku TXT
from fastapi import APIRouter
from pydantic import BaseModel
from pathlib import Path
import ollama
from backend.config import LLM_MODEL

router = APIRouter()

class ChatRequest(BaseModel):
    question: str
    company_id: str = "test"

# Kontekst wczytywany z pliku (tymczasowo, zanim dojdzie ChromaDB)
CONTEXT_FILE = Path(__file__).resolve().parent.parent / "data_samples" / "test_firma.txt"
CONTEXT = CONTEXT_FILE.read_text(encoding="utf-8")

SYSTEM_PROMPT = """Jesteś asystentem obsługi klienta.
Odpowiadaj WYŁĄCZNIE na podstawie podanego kontekstu.
Jeśli odpowiedzi nie ma w kontekście, napisz:
'Nie mam tej informacji, proszę skontaktować się z obsługą.'
Odpowiadaj po polsku, zwięźle i uprzejmie."""

@router.post("/chat")
async def chat(request: ChatRequest):
    prompt = f"""Kontekst:
{CONTEXT}

Pytanie: {request.question}"""

    response = ollama.chat(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
    )

    return {
        "answer": response["message"]["content"],
        "company_id": request.company_id
    }