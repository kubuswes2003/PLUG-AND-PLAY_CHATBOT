# to co claude podopiwedział 


# from fastapi import APIRouter, UploadFile, File
# from pydantic import BaseModel
# import chromadb
# import ollama
# import os
# from backend.config import CHROMA_PATH, EMBEDDING_MODEL

# router = APIRouter()

# client = chromadb.PersistentClient(path=CHROMA_PATH)

# def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50):
#     """Dzieli tekst na kawałki z nakładaniem"""
#     chunks = []
#     start = 0
#     while start < len(text):
#         end = start + chunk_size
#         chunks.append(text[start:end])
#         start = end - overlap
#     return chunks

# def get_embedding(text: str):
#     """Zamienia tekst na wektor przez Ollamę"""
#     response = ollama.embeddings(
#         model=EMBEDDING_MODEL,
#         prompt=text
#     )
#     return response["embedding"]

# @router.post("/ingest/{company_id}")
# async def ingest(company_id: str, file: UploadFile = File(...)):
#     """Przyjmuje plik TXT i zapisuje do ChromaDB"""
    
#     # Czytaj plik
#     content = await file.read()
#     text = content.decode("utf-8")
    
#     # Podziel na chunki
#     chunks = chunk_text(text)
    
#     # Stwórz lub pobierz kolekcję dla tej firmy
#     collection = client.get_or_create_collection(
#         name=f"company_{company_id}"
#     )
    
#     # Zapisz każdy chunk z embeddingiem
#     for i, chunk in enumerate(chunks):
#         embedding = get_embedding(chunk)
#         collection.add(
#             documents=[chunk],
#             embeddings=[embedding],
#             ids=[f"{company_id}_chunk_{i}"]
#         )
    
#     return {
#         "status": "ok",
#         "company_id": company_id,
#         "chunks_saved": len(chunks)
#     }