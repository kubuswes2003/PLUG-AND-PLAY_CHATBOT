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

first pull:
git pull
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
# gotowe – identyczne środowisko