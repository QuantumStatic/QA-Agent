import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import settings
from app.rag.chroma import get_chroma_collection


def ingest_pdf(file_path: str, document_id: str, user_id: str, filename: str) -> int:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"PDF not found: {file_path}")

    loader = PyPDFLoader(file_path)
    docs = loader.load()
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )
    chunks = splitter.split_documents(docs)

    collection = get_chroma_collection()
    ids = [f"{document_id}-{i}" for i in range(len(chunks))]
    texts = [c.page_content for c in chunks]
    metadatas = [
        {
            "document_id": document_id,
            "user_id": user_id,
            "filename": filename,
            "page": c.metadata.get("page", 0),
        }
        for c in chunks
    ]
    collection.add(ids=ids, documents=texts, metadatas=metadatas)
    return len(chunks)


def delete_document_from_chroma(document_id: str):
    collection = get_chroma_collection()
    results = collection.get(where={"document_id": {"$eq": document_id}})
    if results["ids"]:
        collection.delete(ids=results["ids"])
