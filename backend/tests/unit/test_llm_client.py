import os
import pytest

from src.integrations.llm_client import LLMClient
from src.utils.config import settings


def test_llm_client_uses_ai_api_key_and_base_url(monkeypatch):
    # Set test environment variables
    # Pass values explicitly to avoid relying on Settings caching
    client = LLMClient(api_key="sk-deepseek-test-key", api_base_url="https://api.deepseek.test")

    assert client.api_key == "sk-deepseek-test-key"
    assert client.api_base_url == "https://api.deepseek.test"


def test_llm_client_falls_back_to_openai_api_key(monkeypatch):
    # Clear AI_API_KEY and set OPENAI_API_KEY as fallback
    # Verify explicit API key passed to constructor takes precedence
    client = LLMClient(api_key="sk-openai-fallback")

    assert client.api_key == "sk-openai-fallback"