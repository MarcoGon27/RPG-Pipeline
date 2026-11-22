"""Sentence embeddings through Ollama's OpenAI-compatible endpoint (not traced in Langfuse)."""
import os

from openai import OpenAI

OLLAMA_URL = "http://localhost:11434/v1"
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")  # ollama pull nomic-embed-text


def embed(texts):
    client = OpenAI(base_url=OLLAMA_URL, api_key="ollama")
    res = client.embeddings.create(model=EMBED_MODEL, input=texts)
    return [d.embedding for d in res.data]
