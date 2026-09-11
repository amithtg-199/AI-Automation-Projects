"""Smoke test verifying DeepEval framework, metrics catalog, target runners, and judge instantiation."""
import os
import pytest
from metrics_catalog import METRICS_CATALOG, METRIC_MAP
from targets import run_chatbot, run_rag
from llm_providers import get_judge

def test_metrics_catalog_count():
    assert len(METRICS_CATALOG) == 25, f"Expected 25 metrics, got {len(METRICS_CATALOG)}"

def test_chatbot_target_runner():
    res = run_chatbot("How long do I have to return an item?")
    assert "reply" in res
    assert "usage" in res
    assert len(res["reply"]) > 10

def test_rag_target_runner():
    res = run_rag("What is the return window?")
    assert "answer" in res
    assert "retrieval_context" in res
    assert len(res["retrieval_context"]) > 0

def test_judge_instantiation():
    j_gemini = get_judge("gemini")
    assert j_gemini.get_model_name() == "gemini:gemini-3.6-flash"

    j_mistral = get_judge("mistral")
    assert j_mistral.get_model_name() == "mistral:mistral-small-latest"

    j_mock = get_judge("mock")
    assert j_mock.provider == "mock"
