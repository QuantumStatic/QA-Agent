import chromadb
from app.config import settings


def get_chroma_collection():
    client = chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)
    return client.get_or_create_collection(settings.chroma_collection)
