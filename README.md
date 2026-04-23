# PLUG-AND-PLAY CHATBOT

Scalable, AI-powered customer support solution delivered as a plug-and-play chatbot for business websites.

Widget osadzany jednym `<script>` na dowolnej stronie, backend FastAPI + lokalny LLM **Bielik 11B** przez Ollama, historia rozmowy, logowanie per firma i warstwa bezpieczeństwa („kaganiec") chroniąca przed halucynacjami i atakami prompt injection.

## Struktura projektu

```
backend/
├── main.py          ← punkt wejścia FastAPI + CORS
├── config.py        ← wspólne ustawienia (model, ścieżki)
├── chat.py          ← endpoint POST /chat (walidacja, prompt, Ollama, logi)
├── ingest.py        ← (TODO) ładowanie dokumentów do ChromaDB
└── requirements.txt
data_samples/
└── test_firma.txt   ← testowa baza wiedzy (TechSklep)
frontend-widget/
├── widget.js        ← jednoplikowy widget (IIFE, vanilla JS)
└── index.html       ← strona testowa z osadzonym widgetem
logs/                ← JSON Lines per company_id (ignorowane w git)
```

## Stack

- **LLM:** Bielik 11B v2.3 Instruct (Q4_K_M) przez Ollama
- **Backend:** FastAPI + Pydantic v2
- **Frontend:** czysty JavaScript (bez frameworka), CSS scope `pcb-*`
- **Logi:** standardowe `logging` + JSON Lines per firma
- **Baza wektorowa:** ChromaDB (planowana — jeszcze niepodłączona)

## Funkcjonalności

- **Osadzanie jednym tagem** — `<script src="widget.js" data-…>` konfiguruje nazwę firmy, temat, kontakt, API URL i `company_id`.
- **Historia rozmowy** — sliding window 10 par pytanie/odpowiedź (20 wiadomości) po stronie widgetu i backendu; czyszczona po zamknięciu okna.
- **Dynamiczny system prompt** — budowany z `data-*` (nazwa firmy, temat, e-mail, telefon) — ten sam backend obsługuje dowolną liczbę klientów.
- **Logowanie per firma** — `logs/<company_id>.log` w formacie JSON Lines (timestamp, pytanie, odpowiedź, długość historii); `logs/_invalid.log` audytuje odrzucone próby z niepoprawnym `company_id`.
- **Walidacja i whitelist** — `company_id` musi spełniać `[a-z0-9_-]{1,64}` (`fullmatch`, odporność na path traversal i newline injection); e-mail/telefon odrzucane przy znakach kontrolnych; limity długości wiadomości.
- **CORS** — włączony `*` na czas developmentu (do zawężenia przed produkcją).
- **Kaganiec bezpieczeństwa** — system prompt z 7 zasadami + sekcja OBRONA PRZED MANIPULACJAMI (A–D) + 9 few-shot examples pokrywających m.in.:
  - brak halucynacji produktów/usług spoza `test_firma.txt`,
  - zakaz porównań z konkurencją,
  - odporność na prośby „powtórz instrukcje", „jestem właścicielem", „tryb serwisowy", role-play hijack, fałszywe zgody „wcześniej się zgodziłeś".
- **Parametry Ollama** — `temperature=0.1`, `num_predict=300` dla spójnych, krótkich odpowiedzi.

## Setup (pierwsze uruchomienie)

```bash
git clone https://github.com/kubuswes2003/PLUG-AND-PLAY_CHATBOT.git
cd PLUG-AND-PLAY_CHATBOT
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt

# Ollama + model
ollama pull SpeakLeash/bielik-11b-v2.3-instruct:Q4_K_M
```

## Uruchomienie

Terminal 1 — Ollama (jeśli nie chodzi jako usługa):
```bash
ollama serve
```

Terminal 2 — backend FastAPI:
```bash
source venv/bin/activate
uvicorn backend.main:app --reload --port 8000
```

Terminal 3 — frontend (prosty statyczny serwer):
```bash
cd frontend-widget
python3 -m http.server 8080
```

Otwórz `http://localhost:8080` — w prawym dolnym rogu pojawi się ikona czatu.

## Szybki test API

```bash
curl -s http://localhost:8000/health

curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "question": "W jakich godzinach otwarty jest sklep?",
    "company_id": "demo",
    "company_name": "TechSklep",
    "company_topic": "obsługa klienta sklepu z elektroniką",
    "contact_email": "biuro@techsklep.pl",
    "contact_phone": "+48 61 123 45 67",
    "history": []
  }'
```

## Status / roadmap

- [x] Widget osadzalny jednym `<script>`
- [x] Backend `/chat` + lokalny Bielik
- [x] Historia rozmowy (klient + serwer)
- [x] Logowanie JSON Lines per firma + audyt
- [x] Whitelist `company_id` i walidacja pól
- [x] Dynamiczny system prompt z `data-*`
- [x] Kaganiec bezpieczeństwa + red-team (12/13 ataków zablokowanych)
- [ ] Warstwa pre/post-filter (guardrails) zamiast rozbudowanego promptu
- [ ] ChromaDB + `/ingest` (RAG z plików klienta)
- [ ] Produkcyjny CORS (whitelista domen)
- [ ] Deploy (Docker + reverse proxy)
