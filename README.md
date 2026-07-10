# PLUG-AND-PLAY CHATBOT

Scalable, AI-powered customer support solution delivered as a plug-and-play chatbot for business websites.

Widget osadzany jednym `<script>` na dowolnej stronie, backend FastAPI + lokalny LLM **Bielik 11B** przez Ollama, historia rozmowy, logowanie per firma i warstwa bezpieczeństwa („kaganiec") chroniąca przed halucynacjami i atakami prompt injection.

## Struktura projektu

```
backend/
├── main.py          ← punkt wejścia FastAPI + CORS
├── config.py        ← wspólne ustawienia (model, ścieżki)
├── chat.py          ← endpoint POST /chat (walidacja, prompt, Ollama, logi)
├── ingest.py        ← chunking + embeddingi + zapis do ChromaDB (POST /ingest)
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
- **Embeddings:** nomic-embed-text przez Ollama (768 wymiarów, cosine)
- **Backend:** FastAPI + Pydantic v2
- **Frontend:** czysty JavaScript (bez frameworka), CSS scope `pcb-*`
- **Logi:** standardowe `logging` + JSON Lines per firma
- **Baza wektorowa:** ChromaDB (lokalna, embedded — kolekcja `company_{id}` per firma)

## Funkcjonalności

- **RAG (retrieval + generation)** — `/chat` liczy embedding pytania, wyciąga z ChromaDB top-3 chunki najbardziej pasujące semantycznie i wstrzykuje je do system promptu zamiast całego pliku wiedzy. Fallback do pełnej treści `test_firma.txt` dla firm bez ingestu (dev-only, do usunięcia przed produkcją — patrz TODO w `_get_context_for_request`).
- **Endpoint `/ingest/{company_id}`** — jednorazowe ładowanie pliku wiedzy firmy (text/plain UTF-8, max 5 MB) do ChromaDB: chunking okno przesuwne 500 znaków / overlap 50, embeddingi nomic-embed-text, wipe-and-replace kolekcji. Wywoływane przez admina/wdrożeniowca, nie przez widget.
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

# Ollama + modele (LLM + embeddings)
ollama pull SpeakLeash/bielik-11b-v2.3-instruct:Q4_K_M
ollama pull nomic-embed-text
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

Terminal 4 — jednorazowy ingest wiedzy firmy do ChromaDB (do wykonania **raz** po pierwszym starcie backendu, a potem tylko przy aktualizacji pliku wiedzy):
```bash
curl -X POST http://localhost:8000/ingest/demo \
  -H "Content-Type: text/plain; charset=utf-8" \
  --data-binary @data_samples/test_firma.txt
```
Bez tego kroku `/chat` użyje dev-fallbacku (pełny plik `test_firma.txt` w każdym prompcie).

Otwórz `http://localhost:8080` — w prawym dolnym rogu pojawi się ikona czatu.

## Szybki test API

```bash
curl -s http://localhost:8000/health

# 1) Jednorazowo — załaduj wiedzę firmy do ChromaDB (kolekcja company_demo).
#    Bez tego /chat użyje dev-fallbacku (pełny test_firma.txt).
curl -s -X POST http://localhost:8000/ingest/demo \
  -H "Content-Type: text/plain; charset=utf-8" \
  --data-binary @data_samples/test_firma.txt

# 2) Rozmowa — retrieval wyciągnie top-3 chunki z kolekcji company_demo.
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
- [x] ChromaDB + `/ingest` + retrieval w `/chat` (pełny pipeline RAG, kolekcja per firma)
- [ ] Warstwa pre/post-filter (guardrails) zamiast rozbudowanego promptu
- [ ] Usunięcie dev-fallbacku w `_get_context_for_request` (przed produkcją)
- [ ] Auth dla `/ingest` (obecnie otwarty — każdy z URL-em może nadpisać wiedzę firmy)
- [ ] Rate limiting per `company_id`
- [ ] Produkcyjny CORS (whitelista domen)
- [ ] Testy (pytest — walidatory, chunking, mockowany `/chat`)
- [ ] Deploy (Docker + reverse proxy)
