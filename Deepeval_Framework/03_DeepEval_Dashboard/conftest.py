"""Pytest conftest configuration for DeepEval test suite."""
import os
import pytest
from llm_providers import GeminiMistralJudge, get_judge

@pytest.fixture(scope="session")
def judge():
    provider = os.getenv("EVAL_PROVIDER", "gemini" if os.getenv("GEMINI_API_KEY") else "mock")
    api_key = os.getenv("GEMINI_API_KEY", "") if provider == "gemini" else os.getenv("MISTRAL_API_KEY", "")
    return get_judge(provider=provider, api_key=api_key)
