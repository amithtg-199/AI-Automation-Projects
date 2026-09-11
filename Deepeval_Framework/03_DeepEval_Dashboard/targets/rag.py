"""Target runner for Subsystem B (RAG Explorer, port 8202)."""
import requests
import os
from token_meter import token_meter

RAG_URL = os.getenv("RAG_URL", "http://localhost:8202/api/chat")

def run_rag(message: str, top_k: int = 4, history: list = None, provider: str = None, model: str = None, api_key: str = None) -> dict:
    payload = {
        "message": message,
        "top_k": top_k,
        "history": history or [],
        "provider": provider,
        "model": model,
        "api_key": api_key
    }
    headers = {}
    if api_key:
        headers["X-Gemini-Key"] = api_key
        headers["X-Mistral-Key"] = api_key

    resp = requests.post(RAG_URL, json=payload, headers=headers, timeout=60)
    if resp.status_code == 200:
        data = resp.json()
        token_meter.add_target_usage(data.get("usage"))
        return data

    raise ConnectionError(f"RAG target endpoint ({RAG_URL}) returned HTTP {resp.status_code}: {resp.text[:200]}")
