# chat który pyta Bielika z hardcoded kontekstem
from fastapi import APIRouter
from pydantic import BaseModel
import ollama
from backend.config import LLM_MODEL

router = APIRouter()

class ChatRequest(BaseModel):
    question: str
    company_id: str = "test"

# Hardcoded kontekst zamiast ChromaDB - na teraz
FAKE_CONTEXT = """
Sklep jest czynny poniedziałek-piątek w godzinach 9:00-17:00.
Zwroty przyjmujemy do 30 dni od daty zakupu.
Kontakt: biuro@sklep.pl
Dostawa trwa 2-3 dni robocze.
Reklamacje rozpatrujemy w ciągu 14 dni.
"""

SYSTEM_PROMPT = """Jesteś asystentem obsługi klienta.
Odpowiadaj WYŁĄCZNIE na podstawie podanego kontekstu.
Jeśli odpowiedzi nie ma w kontekście, napisz:
'Nie mam tej informacji, proszę skontaktować się z obsługą.'
Odpowiadaj po polsku, zwięźle i uprzejmie."""

@router.post("/chat")
async def chat(request: ChatRequest):
    prompt = f"""Kontekst:
{FAKE_CONTEXT}

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