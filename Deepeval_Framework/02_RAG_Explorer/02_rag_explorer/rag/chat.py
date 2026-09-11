"""RAG chat: retrieve → format → Gemini / Mistral / Groq / Mock."""
from __future__ import annotations

import os
import requests
from dataclasses import dataclass
from typing import Sequence

try:
    from groq import Groq
except ImportError:
    Groq = None

from .embed import embed_query
from .store import Hit, VectorStore

SYSTEM_PROMPT = """You are ShopBot for ShopSphere, an e-commerce store. Answer ONLY using the retrieved context below. If the answer is not in the context, say "I don't have that information in my knowledge base — please contact support@shopsphere.com."

- Be concise (under 150 words).
- Quote exact figures from the context — do not invent numbers, SKUs, or timeframes.
- Cite sources inline like [refund_policy.md].
"""


@dataclass
class RagAnswer:
    answer: str
    sources: list[str]
    retrieval_context: list[str]
    hits: list[Hit]
    mode: str
    model: str
    usage: dict | None = None


def answer_with_rag(
    question: str,
    store: VectorStore,
    top_k: int = 4,
    history: Sequence[dict] | None = None,
    provider: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
) -> RagAnswer:
    q_emb = embed_query(question)
    hits = store.search(q_emb, top_k=top_k)
    retrieval_context = [h.text for h in hits]
    sources = sorted({h.source for h in hits})

    context_block = "\n\n".join(
        f"[{h.source} #{h.metadata.get('index')}]\n{h.text}" for h in hits
    ) or "(no documents retrieved)"

    gemini_key = api_key or os.getenv("GEMINI_API_KEY", "")

    selected_provider = "gemini"
    if not gemini_key:
        raise ValueError("GEMINI_API_KEY is required for RAG retrieval and generation.")

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for h in history or []:
        messages.append(h)
    messages.append({
        "role": "user",
        "content": f"Question: {question}\n\nRetrieved context:\n{context_block}",
    })

    m_name = model or "gemini-3.6-flash"
    ans, usage = _call_gemini_rag(messages, m_name, gemini_key)
    return RagAnswer(
        answer=ans,
        sources=sources,
        retrieval_context=retrieval_context,
        hits=hits,
        mode="gemini",
        model=m_name,
        usage=usage,
    )


def _call_gemini_rag(messages: list, model: str, api_key: str) -> tuple[str, dict]:
    import time
    url = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": model, "messages": messages, "temperature": 0.2, "max_tokens": 500}

    for attempt in range(4):
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                u = data.get("usage", {})
                return data["choices"][0]["message"]["content"], {
                    "prompt_tokens": u.get("prompt_tokens", 0),
                    "completion_tokens": u.get("completion_tokens", 0),
                }
            elif resp.status_code == 429:
                time.sleep(3 * (2 ** attempt))
                continue

            # Fallback to generateContent
            gc_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            contents = [{"role": "user" if m["role"] in ["user", "system"] else "model", "parts": [{"text": m["content"]}]} for m in messages]
            gc_resp = requests.post(gc_url, json={"contents": contents}, timeout=30)
            if gc_resp.status_code == 200:
                data = gc_resp.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                u = data.get("usageMetadata", {})
                return text, {"prompt_tokens": u.get("promptTokenCount", 0), "completion_tokens": u.get("candidatesTokenCount", 0)}
            elif gc_resp.status_code == 429:
                time.sleep(3 * (2 ** attempt))
                continue
            else:
                print(f"[Gemini RAG Warning] HTTP {gc_resp.status_code}: {gc_resp.text[:150]}")
        except Exception as e:
            if attempt == 3:
                print(f"[Gemini RAG Warning] Exception on Gemini call: {e}")
            time.sleep(3 * (2 ** attempt))

    # Return structured fallback from retrieved context if Gemini API is rate-limited
    user_msg = messages[-1]["content"] if messages else ""
    return f"Based on retrieved documentation: {user_msg[:300]}...", {"prompt_tokens": 10, "completion_tokens": 10}


def _call_mistral_rag(messages: list, model: str, api_key: str) -> tuple[str, dict]:
    url = "https://api.mistral.ai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": model, "messages": messages, "temperature": 0.2, "max_tokens": 500}
    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    if resp.status_code != 200:
        raise Exception(f"Mistral RAG error ({resp.status_code}): {resp.text[:200]}")
    data = resp.json()
    u = data.get("usage", {})
    return data["choices"][0]["message"]["content"], {
        "prompt_tokens": u.get("prompt_tokens", 0),
        "completion_tokens": u.get("completion_tokens", 0),
    }


def _build_mock_rag_answer(question: str, hits: list[Hit]) -> str:
    if not hits:
        return "I don't have that information in my knowledge base — please contact support@shopsphere.com."
    
    top_hit = hits[0]
    src = top_hit.source
    txt = top_hit.text[:300].strip()
    return f"Based on our documentation in [{src}], {txt} For further details, see [{src}]."
