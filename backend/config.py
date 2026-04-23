# ============================================================
# backend/config.py
# ------------------------------------------------------------
# Centralne miejsce na ustawienia aplikacji.
# Wszystkie "magiczne" wartości (adresy, nazwy modeli, ścieżki)
# trzymamy tutaj, żeby nie były rozsiane po kodzie. Jak coś
# trzeba zmienić — zmieniamy w jednym miejscu.
# ============================================================

# Adres lokalnej instancji Ollamy (serwera LLM-ów lokalnych).
# Ollama domyślnie słucha na porcie 11434. Na razie nie używamy
# go bezpośrednio — biblioteka `ollama` w Pythonie sama wie gdzie
# szukać. Zmienna jest tu "na zapas", gdybyśmy chcieli explicite
# wskazać inny host (np. zdalny serwer z GPU).
OLLAMA_URL = "http://localhost:11434"

# Model LLM używany do generowania odpowiedzi w /chat.
# Bielik to polski model 11B (od SpeakLeash), kwantyzacja Q4_K_M
# = kompromis między jakością a wielkością pamięci (~7 GB RAM).
# Musi być wcześniej pobrany przez: `ollama pull SpeakLeash/bielik-...`
LLM_MODEL = "SpeakLeash/bielik-11b-v2.3-instruct:Q4_K_M"

# Model do zamieniania tekstu na wektory (embeddings).
# Potrzebny dopiero przy ChromaDB — dla każdego chunku dokumentu
# liczymy wektor i zapisujemy w bazie. Na razie nieużywany.
EMBEDDING_MODEL = "nomic-embed-text"

# Ścieżka do lokalnej bazy wektorowej ChromaDB (folder na dysku).
# Chroma sama tworzy tu pliki SQLite + dane. Nieużywane dopóki
# nie włączymy `ingest.py` i retrievalu w `chat.py`.
CHROMA_PATH = "./chroma_db"
