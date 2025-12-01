#!/usr/bin/env python3
"""Quick script to test LLM connectivity using the configured AI provider.

Usage:
  # From backend/ folder
  export AI_API_KEY="sk-..."
  export AI_API_BASE_URL="https://api.deepseek.example"
  python3 scripts/test_deepseek_llm.py

The script sends a simple prompt and prints the response. This is useful for validating
that Deepseek (or any OpenAI-compatible provider) is reachable and that the API key/base URL are correctly configured.
"""
import asyncio
import sys
from src.integrations.llm_client import LLMClient
from src.utils.config import settings

async def main():
    if not settings.effective_ai_api_key:
        print("No AI API key configured. Set AI_API_KEY or OPENAI_API_KEY in environment/.env")
        sys.exit(1)

    if not settings.AI_API_BASE_URL:
        print("No AI_API_BASE_URL configured. Set AI_API_BASE_URL to point to your OpenAI-compatible provider (Deepseek) if needed.")
        print("If your provider is the public OpenAI API, this may be left blank.")

    client = LLMClient()

    prompt_messages = [
        {"role": "system", "content": "You are a helpful assistant that replies in short sentences."},
        {"role": "user", "content": "What's 1 + 1?"}
    ]

    try:
        print("Sending test prompt...")
        resp = await client.generate(prompt_messages)
        print("Response:\n", resp)
    except Exception as e:
        print("LLM request failed:", e)

if __name__ == '__main__':
    asyncio.run(main())
