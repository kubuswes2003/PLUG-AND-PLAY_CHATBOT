# ============================================================
# backend/ingest.py
# ------------------------------------------------------------
# Moduł odpowiedzialny za "ładowanie wiedzy" do bazy wektorowej ChromaDB.
#
# Przepływ ingestu:
#   1. Wczytaj treść pliku .txt z bazą wiedzy danej firmy.
#   2. Podziel tekst na chunki ~500 znaków z overlapem 50 znaków.
#   3. Każdy chunk zamień na wektor (embedding) przez nomic-embed-text
#      uruchomiony lokalnie w Ollamie.
#   4. Zapisz (chunk + embedding + metadane) do ChromaDB pod kolekcją
#      o nazwie `company_{company_id}`.
#
# Eksportowane funkcje (do użycia z innych modułów, np. z chat.py):
#   - ingest_company_data(company_id, text)  → liczba zapisanych chunków
#   - query_collection(company_id, question) → lista pasujących chunków
#
# Endpoint FastAPI:
#   POST /ingest/{company_id}
#       Body: surowy tekst UTF-8 (Content-Type: text/plain)
#       Zwraca: {"status": "ok", "company_id": ..., "chunks_saved": N}
#
# Uwaga projektowa: nie używamy `multipart/form-data` (UploadFile),
# żeby nie wymagać dodatkowej zależności `python-multipart`.
# Surowy body jest prostszy i wystarczy dla pliku tekstowego.
# ============================================================

from __future__ import annotations  # Pozwala używać "list[str]" itd. w runtimie na Pythonie 3.9+, dla zgodności.

from pathlib import Path  # Path do bezpiecznego budowania ścieżek względem pliku ingest.py.
from typing import Any  # Any używamy tylko tam, gdzie typ wynika ze schematu zewnętrznej biblioteki.

import chromadb  # Klient bazy wektorowej — przechowuje chunki + ich embeddingi i robi semantic search.
import ollama  # Klient Ollamy — używamy go do liczenia embeddingów przez nomic-embed-text.
from fastapi import APIRouter, HTTPException, Request  # Request pozwala odczytać surowy body bez multipart.

from backend.config import EMBEDDING_MODEL  # Centralna nazwa modelu embeddingów — zmiana w jednym miejscu.

# ------------------------------------------------------------
# Stałe modułu
# ------------------------------------------------------------

# Ścieżka do roota projektu — wyliczana względem TEGO pliku.
# Tak samo jak w chat.py, żeby działało niezależnie od cwd uvicorna
# (uvicorn można odpalić z dowolnego katalogu, a my chcemy stałą ścieżkę).
_PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent

# Absolutna ścieżka do folderu na dane ChromaDB (SQLite + pliki HNSW).
# Resolve() rozwiązuje wszystkie ".." i symlinki — pewność że to ten sam
# folder bez względu na cwd. Chroma sama tworzy ten folder przy 1. zapisie.
_CHROMA_PATH: Path = (_PROJECT_ROOT / "chroma_db").resolve()

# Rozmiar pojedynczego chunku w znakach.
# 500 znaków ≈ 3-5 zdań w polskim. Dobry kompromis:
#   - za małe (np. 100) → tracimy kontekst zdania, retrieval gubi sens.
#   - za duże (np. 2000) → embedding "rozmywa się" semantycznie,
#     wynik wyszukiwania mniej trafny i niepotrzebnie pchamy w prompt
#     dużo tekstu.
_CHUNK_SIZE: int = 500

# Nakładanie chunków — końcówka poprzedniego wchodzi w początek następnego.
# Zapobiega "przerwaniu zdania w połowie" na granicy chunków, dzięki czemu
# żaden fragment ważnej informacji nie jest dostępny tylko z urwanym kontekstem.
# 50 znaków ≈ 1 krótkie zdanie — wystarczy żeby zachować ciągłość.
_CHUNK_OVERLAP: int = 50

# Domyślna liczba chunków zwracanych przy zapytaniu retrieval.
# 3 chunki × 500 znaków ≈ 1500 znaków = bezpiecznie mieści się w prompcie
# Bielika i wciąż daje 3 różne fragmenty kontekstu na pytanie.
_DEFAULT_N_RESULTS: int = 3

# Maksymalny rozmiar przyjmowanego pliku w endpoincie /ingest (bajty).
# 5 MB = setki tysięcy chunków. Powyżej tego użytkownik prawdopodobnie
# robi błąd (np. wysyła PDF zamiast txt) — bezpieczniej odrzucić niż
# zapchać pamięć i czekać godzinami na embeddingi.
_MAX_INGEST_BYTES: int = 5 * 1024 * 1024

# Singleton klienta ChromaDB. Tworzymy raz, na imporcie modułu, bo:
#   - PersistentClient otwiera pliki SQLite + ładuje indeks HNSW,
#     to nie jest darmowa operacja per-request.
#   - W ramach jednego procesu nie chcemy mieć wielu klientów na
#     ten sam katalog — Chroma sobie z tym poradzi, ale to marnotrawstwo.
# str(_CHROMA_PATH), bo Chroma w niektórych wersjach źle traktuje obiekt Path.
_chroma_client: chromadb.PersistentClient = chromadb.PersistentClient(
    path=str(_CHROMA_PATH)
)

# Router FastAPI dla endpointów modułu (POST /ingest/{company_id}).
# Podpinany w main.py przez app.include_router().
router = APIRouter()


# ------------------------------------------------------------
# Funkcje prywatne (prefiks `_`) — szczegóły implementacyjne
# ------------------------------------------------------------


def _chunk_text(text: str) -> list[str]:
    """Dzieli tekst na nakładające się chunki o stałej długości.

    Algorytm: okno przesuwne o szerokości `_CHUNK_SIZE` znaków,
    przesuwane o krok `_CHUNK_SIZE - _CHUNK_OVERLAP`. Dzięki temu
    `_CHUNK_OVERLAP` znaków z końca chunku N znajduje się też na
    początku chunku N+1 — granice nie urywają zdań.

    Ostatni chunk może być krótszy od `_CHUNK_SIZE` — to OK,
    nie chcemy obcinać "ogona" tekstu. Pomijamy chunki, które
    po `.strip()` są puste (np. same białe znaki).

    Args:
        text: Pełna treść do podziału.

    Returns:
        Lista niepustych chunków, w kolejności występowania w tekście.
    """
    chunks: list[str] = []  # Rosnąca lista wynikowa — append jest tani.

    # Krok = szerokość okna minus overlap. Jeśli overlap = 0, krok = szerokość
    # i chunki nie nakładają się wcale (klasyczny tumbling window).
    step: int = _CHUNK_SIZE - _CHUNK_OVERLAP

    start: int = 0  # Indeks początku bieżącego okna w `text`.
    # Pętla działa do momentu, aż `start` przekroczy długość tekstu —
    # wtedy nie ma już z czego wycinać kolejnego chunku.
    while start < len(text):
        end: int = start + _CHUNK_SIZE  # Koniec okna; slicing tolerant na end > len.
        chunk: str = text[start:end].strip()  # Strip żeby nie tworzyć chunków z samych spacji/newlinów.

        # Pomijamy puste chunki — mogłyby trafić do bazy z embeddingiem
        # liczonym z pustego stringa, co ChromaDB zaakceptuje, ale w
        # wynikach query byłby śmieć obok prawdziwych chunków.
        if chunk:
            chunks.append(chunk)

        start += step  # Przesuwamy okno o krok dalej.

    return chunks


def _get_embedding(text: str) -> list[float]:
    """Liczy wektor embedding dla podanego tekstu przez nomic-embed-text.

    `ollama.embed()` to API wprowadzone w ollama-python 0.3+ (zastąpiło
    starsze `ollama.embeddings()`). Zwraca obiekt `EmbedResponse`,
    który wspiera dostęp słownikowy (jak w chat.py używamy `response["..."]`),
    więc trzymamy się tej samej konwencji.

    Klucz "embeddings" (liczba mnoga!) to lista list — bo ollama.embed()
    może liczyć embeddingi dla wielu tekstów naraz. My pytamy o jeden,
    więc bierzemy `[0]`.

    Args:
        text: Tekst do zamienienia na wektor.

    Returns:
        Lista float — wektor embedding (dla nomic-embed-text: 768 wymiarów).

    Raises:
        ollama.ResponseError: Gdy model nie jest pobrany w Ollamie.
        ConnectionError: Gdy serwer Ollamy nie działa.
    """
    # input= (singular), bo w API Ollamy parametr jest "input" (string lub lista).
    response: Any = ollama.embed(
        model=EMBEDDING_MODEL,
        input=text,
    )
    # response["embeddings"] = list[list[float]]; nasz pojedynczy wektor jest pod [0].
    # Rzutowanie na list(...) na wszelki wypadek, gdyby Ollama zwróciła tuple
    # albo własny typ — chcemy mieć "czysty" Python list dla ChromaDB.
    return list(response["embeddings"][0])


def _collection_name(company_id: str) -> str:
    """Buduje nazwę kolekcji ChromaDB dla danej firmy.

    Konwencja `company_{company_id}` ma dwa cele:
      1. Prefix izoluje nasze kolekcje od ewentualnych kolekcji
         systemowych ChromaDB w przyszłości.
      2. Czytelność — w narzędziach do przeglądu bazy widać od razu,
         że to kolekcja klienta.

    NIE walidujemy tu `company_id` — zakładamy że wywołujący już to zrobił
    (przez `_is_valid_company_id` z chat.py). Walidacja w dwóch miejscach
    rozjeżdża się z czasem, więc trzymamy ją w jednym miejscu (chat.py).

    Args:
        company_id: Już zwalidowany identyfikator firmy.

    Returns:
        Nazwa kolekcji do użycia z ChromaDB API.
    """
    return f"company_{company_id}"


# ------------------------------------------------------------
# Publiczne funkcje (do użycia w innych modułach i w testach)
# ------------------------------------------------------------


def ingest_company_data(company_id: str, text: str) -> int:
    """Zapisuje wiedzę firmową do ChromaDB jako chunki + embeddingi.

    Strategia "wipe and replace": usuwamy starą kolekcję i tworzymy
    od nowa. Powód: gdybyśmy zrobili tylko `upsert`, a nowy plik
    miałby mniej chunków niż poprzedni (np. firma usunęła sekcję),
    stare nadmiarowe chunki by zostały i wracały w wynikach query
    jako "duchy" nieaktualnej wiedzy. Czysta kolekcja gwarantuje,
    że stan w bazie = stan w pliku.

    Args:
        company_id: Zwalidowany identyfikator firmy (klucz kolekcji).
        text: Pełna treść pliku wiedzy (zdekodowana do str).

    Returns:
        Liczba zapisanych chunków. 0 jeśli `text` po podziale nie dał
        żadnego niepustego chunku (np. plik z samymi białymi znakami).

    Raises:
        ollama.ResponseError: Ollama nie odpowiada lub model niedostępny.
        Exception: Każdy inny błąd ChromaDB (zapis, schemat itp.).
    """
    chunks: list[str] = _chunk_text(text)  # 1. Podział na chunki.

    # Edge case: pusty plik / same białe znaki → nic do ingestu.
    # Zwracamy 0 i kończymy WCZESNIE, żeby nie tworzyć pustej kolekcji.
    if not chunks:
        return 0

    name: str = _collection_name(company_id)

    # Usunięcie starej kolekcji (jeśli istnieje). delete_collection rzuca
    # wyjątek gdy nie istnieje — łapiemy szeroko, bo różne wersje ChromaDB
    # rzucają różne klasy wyjątków (NotFoundError, ValueError, InvalidCollectionException).
    try:
        _chroma_client.delete_collection(name=name)
    except Exception:  # noqa: BLE001 - świadomie szerokie, brak kolekcji nie jest błędem.
        # Brak kolekcji to NORMALNY stan przy pierwszym ingest dla danej firmy.
        # Nic nie logujemy, kontynuujemy.
        pass

    # 2. Tworzymy świeżą kolekcję. metadata={"hnsw:space": "cosine"} mówi
    # ChromaDB żeby używał odległości cosinusowej dla wyszukiwania:
    #   - cosine = mierzy KĄT między wektorami, ignoruje ich długość.
    #   - dla embeddingów tekstu to standard, bo długość wektora nie
    #     niesie informacji semantycznej (a domyślne L2 może być zaburzone).
    collection: Any = _chroma_client.create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"},
    )

    # 3. Liczymy embedding dla każdego chunku i zbieramy wszystko do
    # 4 równoległych list. Robimy ZBIORCZY upsert (jeden call do ChromaDB)
    # zamiast N osobnych — szybciej i jedna transakcja w bazie.
    ids: list[str] = []
    embeddings: list[list[float]] = []
    documents: list[str] = []
    metadatas: list[dict[str, str]] = []

    for i, chunk in enumerate(chunks):
        # ID musi być unikalny w kolekcji. Format `{company_id}_chunk_{i}`
        # jest deterministyczny — przy re-ingest tego samego pliku dostajemy
        # te same ID (choć i tak całą kolekcję usuwamy wyżej).
        ids.append(f"{company_id}_chunk_{i}")
        embeddings.append(_get_embedding(chunk))  # Wywołanie HTTP do Ollamy — wąskie gardło.
        documents.append(chunk)
        # Metadane: pomocne przy debugowaniu i ewentualnym filtrowaniu w
        # przyszłości (np. chunki z różnych źródeł). chunk_index jako string,
        # bo ChromaDB w niektórych wersjach gubi int w metadanych.
        metadatas.append({
            "source": "company_knowledge",
            "chunk_index": str(i),
            "company_id": company_id,
        })

    # 4. Zbiorczy zapis. Używamy `add` (nie `upsert`), bo kolekcja została
    # utworzona pusto kilka linii wyżej — żaden ID nie istnieje, więc
    # add nie ma szansy zderzyć się z duplikatem.
    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
    )

    return len(chunks)


def query_collection(
    company_id: str,
    question: str,
    n_results: int = _DEFAULT_N_RESULTS,
) -> list[str]:
    """Wyszukuje top-N chunków najbardziej semantycznie pasujących do pytania.

    Przeznaczona do wywołania z chat.py przy każdym requeście do /chat.
    Zamiast wysyłać do LLM cały plik z wiedzą, wysyłamy tylko fragmenty
    rzeczywiście dotyczące pytania użytkownika — to jest sedno RAG-u.

    Funkcja jest "łaskawa" przy braku danych: jeśli kolekcja dla danej
    firmy nie istnieje (firma nie zrobiła ingestu) lub jest pusta, zwraca
    pustą listę zamiast rzucać wyjątek. Dzięki temu chat.py może spokojnie
    fallback'ować do innego źródła kontekstu.

    Args:
        company_id: Identyfikator firmy (klucz kolekcji).
        question: Aktualne pytanie użytkownika (do zamiany na embedding).
        n_results: Maksymalna liczba zwracanych chunków. Defaultowo
            `_DEFAULT_N_RESULTS`. Funkcja sama przytnie do faktycznej
            liczby chunków w kolekcji (żeby nie rzucało przy małych bazach).

    Returns:
        Lista stringów (treści chunków) posortowana od najbardziej do
        najmniej trafnego. Pusta lista przy braku kolekcji / pustej kolekcji.

    Raises:
        ollama.ResponseError: Gdy nie udało się policzyć embeddingu pytania.
    """
    name: str = _collection_name(company_id)

    # Próbujemy pobrać kolekcję. ChromaDB rzuca wyjątek gdy nie istnieje
    # (różne klasy w różnych wersjach), więc łapiemy szeroko i mapujemy
    # na "pusty wynik". To jest świadoma decyzja — chat.py ma się obronić,
    # nie wywalić, gdy admin nie zrobił ingestu.
    try:
        collection: Any = _chroma_client.get_collection(name=name)
    except Exception:  # noqa: BLE001 - brak kolekcji NIE jest błędem aplikacji.
        return []

    # count() pozwala uniknąć dwóch problemów:
    #   1. ChromaDB rzuca jeśli n_results > count w niektórych wersjach.
    #   2. Pytanie pustej kolekcji o cokolwiek = strata czasu na embedding.
    count: int = collection.count()
    if count == 0:
        return []

    # Min(n_results, count) → nigdy nie poprosimy o więcej niż jest w bazie.
    actual_n: int = min(n_results, count)

    # Embedding pytania liczymy DOPIERO po sprawdzeniu, że jest w czym szukać.
    # Liczenie embeddingu to wywołanie HTTP do Ollamy — drogie, więc skipujemy
    # gdy z góry wiadomo, że nic nie znajdziemy.
    question_embedding: list[float] = _get_embedding(question)

    # query() zwraca dict z kluczami documents/metadatas/distances/embeddings,
    # każdy jako list[list[...]] (zewnętrzna lista po query, wewnętrzna po wynikach).
    # `include=["documents"]` mówi ChromaDB żeby zwrócił tylko treści — bez
    # embeddingów (ciężkie) i metadanych (niepotrzebne na razie).
    results: dict[str, Any] = collection.query(
        query_embeddings=[question_embedding],
        n_results=actual_n,
        include=["documents"],
    )

    # results["documents"] = [[chunk1, chunk2, chunk3]] — jedno query, więc [0].
    # Defensywne `or []` na wypadek gdyby ChromaDB zwróciło None (zdarzało się
    # w starszych wersjach przy 0 wynikach, choć tu już sprawdziliśmy count > 0).
    documents: list[str] = results["documents"][0] or []
    return documents


# ------------------------------------------------------------
# Endpoint FastAPI: POST /ingest/{company_id}
# ------------------------------------------------------------


@router.post("/ingest/{company_id}")
async def ingest_endpoint(company_id: str, request: Request) -> dict[str, Any]:
    """Przyjmuje surowy tekst UTF-8 w body i ładuje go do ChromaDB.

    Body to surowy `text/plain` — nie multipart, nie JSON. Powód: nie
    chcemy dodawać zależności `python-multipart` (potrzebnej do UploadFile)
    ani męczyć klienta JSON-encodowaniem dużego tekstu (escape \\n itp.).
    Klient po prostu robi:
        curl -X POST http://localhost:8000/ingest/test \\
             -H "Content-Type: text/plain; charset=utf-8" \\
             --data-binary @data_samples/test_firma.txt

    Args:
        company_id: Z URL — identyfikator firmy (musi przejść walidację).
        request: Surowy obiekt requestu, z którego czytamy body przez
            `await request.body()`.

    Returns:
        Słownik `{"status": "ok", "company_id": ..., "chunks_saved": N}`.

    Raises:
        HTTPException 400: company_id nie pasuje do whitelisty.
        HTTPException 413: body za duże (powyżej `_MAX_INGEST_BYTES`).
        HTTPException 422: body nie jest poprawnym UTF-8.
        HTTPException 502: błąd Ollamy lub ChromaDB podczas ingestu.
    """
    # Lazy import _is_valid_company_id z chat.py, żeby uniknąć cyklicznego
    # importu (chat.py mógłby w przyszłości importować z ingest.py).
    # Import w środku funkcji = wykonuje się dopiero przy wywołaniu, kiedy
    # cały moduł chat.py jest już załadowany.
    from backend.chat import _is_valid_company_id  # noqa: PLC0415

    # 1. Walidacja company_id — ta sama whitelista co w /chat (litery, cyfry,
    # myślnik, podkreślnik, 1-64 znaki). Chroni przed path traversal i bzdurami.
    if not _is_valid_company_id(company_id):
        raise HTTPException(status_code=400, detail="Invalid company_id")

    # 2. Czytamy body. await request.body() czeka na cały payload (w pamięci).
    # Dla 5 MB to OK; dla większych ingestów trzeba by streamingu, ale dla
    # bazy wiedzy firmy (zwykle kilkanaście-kilkaset KB) bez sensu komplikować.
    raw_bytes: bytes = await request.body()

    # 3. Limit rozmiaru — defense in depth. Klient mógłby zignorować limity
    # po stronie reverse proxy / Content-Length i wysłać 1 GB; my odrzucamy.
    if len(raw_bytes) > _MAX_INGEST_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Body too large (max {_MAX_INGEST_BYTES} bytes)",
        )

    # 4. Body musi być prawidłowym UTF-8. Inne kodowania (np. windows-1250
    # z polskimi znakami) odrzucamy — klient ma dostarczyć UTF-8 (standard
    # dla pliku tekstowego w 2026 roku).
    try:
        text: str = raw_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=422,
            detail="Body must be valid UTF-8 text",
        ) from exc

    # 5. Właściwy ingest. Wszystko co może pójść źle (Ollama nie żyje,
    # ChromaDB ma problem z dyskiem, model nie pobrany) łapiemy szeroko
    # i mapujemy na 502 Bad Gateway — bo prawdziwa awaria jest po stronie
    # zewnętrznych usług, nie po stronie naszego API ani klienta.
    try:
        chunks_saved: int = ingest_company_data(company_id=company_id, text=text)
    except Exception as exc:  # noqa: BLE001 - intentionally broad: każdy błąd → 502.
        raise HTTPException(
            status_code=502,
            detail=f"Ingest failed: {type(exc).__name__}: {exc}",
        ) from exc

    # 6. Sukces. Zwracamy ile chunków poszło do bazy — przydatne do
    # potwierdzenia po stronie klienta że ingest zadziałał (np. jeśli
    # dostaniemy 0 chunków, plik prawdopodobnie był pusty).
    return {
        "status": "ok",
        "company_id": company_id,
        "chunks_saved": chunks_saved,
    }
