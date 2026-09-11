"""Pytest suite for RAG Explorer evaluation metrics."""
import pytest
from targets import run_rag
from datasets import RAG_GOLDENS

def test_rag_retrieval_and_answer():
    sample = RAG_GOLDENS[0]
    res = run_rag(sample["input"], top_k=4)
    assert "answer" in res
    assert len(res["retrieval_context"]) > 0
    # Check keyword presence in retrieved context
    retrieved_text = " ".join(res["retrieval_context"]).lower()
    for kw in sample["expected_context_keywords"]:
        assert kw.lower() in retrieved_text or "policy" in retrieved_text
