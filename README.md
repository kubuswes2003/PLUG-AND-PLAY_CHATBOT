# PLUG-AND-PLAY CHATBOT

Scalable, AI-powered customer support solution delivered as a plug-and-play chatbot for business websites.

## Struktura projektu

chatbot/
├── backend/
│   ├── main.py          ← punkt wejścia FastAPI 
│   ├── config.py        ← wspólne ustawienia
│   ├── chat.py          ← twój moduł /chat
│   ├── ingest.py        ← moduł Aleksandra /ingest
│   └── requirements.txt
├── frontend-widget/
│   └── widget.js        ← na później
├── data_samples/
│   └── test_firma.txt   ← testowa baza wiedzy
└── README.md

## Stack

- **LLM:** Bielik 11B (Ollama)
- **Embeddings:** nomic-embed-text
- **Baza wektorowa:** ChromaDB
- **Backend:** FastAPI (Python)

## Setup (pierwsze uruchomienie)

```bash
git clone https://github.com/kubuswes2003/PLUG-AND-PLAY_CHATBOT.git
cd PLUG-AND-PLAY_CHATBOT
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
```

## Uruchomienie

```bash
source venv/bin/activate
uvicorn backend.main:app --reload
```