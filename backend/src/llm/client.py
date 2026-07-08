"""Simplified OpenAI-compatible LLM client — no langchain dependency."""

import logging
import time
from typing import AsyncIterator, Optional

from openai import AsyncOpenAI
from openai import (
    APIError,
    APITimeoutError,
    APIConnectionError,
    RateLimitError,
)

from src.utils.ai_logger import get_ai_logger
from src.utils.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Custom exception hierarchy
# ---------------------------------------------------------------------------

class LLMError(Exception):
    """Base exception for LLM errors."""


class LLMTimeoutError(LLMError):
    """LLM request timed out."""


class LLMConnectionError(LLMError):
    """Failed to connect to LLM service."""


class LLMRateLimitError(LLMError):
    """LLM rate limit exceeded."""


# ---------------------------------------------------------------------------
# LLM Client
# ---------------------------------------------------------------------------

class LLMClient:
    """Async LLM client backed by the OpenAI Python SDK.

    Supports any OpenAI-compatible API (DeepSeek, local proxies, etc.).
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
        timeout: Optional[int] = None,
        max_retries: Optional[int] = None,
        api_base_url: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> None:
        self.model_name = model_name or settings.AI_MODEL
        self.temperature = (
            temperature if temperature is not None else settings.AI_TEMPERATURE
        )
        self.timeout = timeout if timeout is not None else settings.AI_TIMEOUT
        self.max_retries = max_retries if max_retries is not None else settings.AI_MAX_RETRIES
        self.api_base_url = api_base_url or settings.AI_API_BASE_URL
        self.api_key = api_key or settings.AI_API_KEY

        self.ai_logger = get_ai_logger()

        if not self.api_key:
            logger.warning(
                "No AI_API_KEY configured — LLM functionality will not work"
            )

        client_kwargs: dict = {
            "api_key": self.api_key or "sk-placeholder",
            "timeout": float(self.timeout),
            "max_retries": self.max_retries,
        }
        if self.api_base_url:
            client_kwargs["base_url"] = self.api_base_url

        self._client = AsyncOpenAI(**client_kwargs)

        logger.info(
            "LLM client initialized — model=%s temperature=%.2f base_url=%s",
            self.model_name,
            self.temperature,
            self.api_base_url or "(default)",
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def generate(self, messages: list[dict]) -> str:
        """Send a chat-completion request and return the full response.

        Args:
            messages: List of dicts with ``role`` and ``content`` keys.
                      Roles: ``"system"``, ``"user"``.

        Returns:
            The generated text content.

        Raises:
            LLMError: Wrapper for any underlying OpenAI / transport error.
        """
        start_time = time.time()
        request_id = self.ai_logger.log_request(
            model=self.model_name,
            messages=messages,
            temperature=self.temperature,
        )

        try:
            response = await self._client.chat.completions.create(
                model=self.model_name,
                messages=messages,  # type: ignore[arg-type]
                temperature=self.temperature,
            )

            latency_ms = (time.time() - start_time) * 1000
            content = response.choices[0].message.content or ""

            usage = response.usage
            self.ai_logger.log_response(
                request_id=request_id,
                response_content=content,
                model=self.model_name,
                prompt_tokens=usage.prompt_tokens if usage else None,
                completion_tokens=usage.completion_tokens if usage else None,
                total_tokens=usage.total_tokens if usage else None,
                latency_ms=latency_ms,
                is_stream=False,
            )

            return content

        except Exception as exc:
            latency_ms = (time.time() - start_time) * 1000
            self.ai_logger.log_error(
                request_id=request_id,
                error=exc,
                model=self.model_name,
                latency_ms=latency_ms,
            )
            raise _wrap_exception(exc) from exc

    async def generate_stream(
        self, messages: list[dict]
    ) -> AsyncIterator[str]:
        """Stream a chat-completion response, yielding text chunks.

        Args:
            messages: List of dicts with ``role`` and ``content`` keys.

        Yields:
            Chunks of generated text.

        Raises:
            LLMError: Wrapper for any underlying OpenAI / transport error.
        """
        start_time = time.time()
        request_id = self.ai_logger.log_request(
            model=self.model_name,
            messages=messages,
            temperature=self.temperature,
            extra={"streaming": True},
        )

        self.ai_logger.log_stream_start(request_id, self.model_name)

        full_content = ""
        chunk_count = 0

        try:
            stream = await self._client.chat.completions.create(
                model=self.model_name,
                messages=messages,  # type: ignore[arg-type]
                temperature=self.temperature,
                stream=True,
            )

            async for chunk in stream:
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta and delta.content:
                    full_content += delta.content
                    chunk_count += 1
                    yield delta.content

            latency_ms = (time.time() - start_time) * 1000
            self.ai_logger.log_stream_end(
                request_id=request_id,
                model=self.model_name,
                total_chunks=chunk_count,
                total_content_length=len(full_content),
                latency_ms=latency_ms,
            )

        except Exception as exc:
            latency_ms = (time.time() - start_time) * 1000
            self.ai_logger.log_error(
                request_id=request_id,
                error=exc,
                model=self.model_name,
                latency_ms=latency_ms,
            )
            raise _wrap_exception(exc) from exc


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _wrap_exception(exc: Exception) -> LLMError:
    """Map an OpenAI / transport exception to a domain-specific LLMError."""
    if isinstance(exc, APITimeoutError):
        return LLMTimeoutError(str(exc))
    if isinstance(exc, APIConnectionError):
        return LLMConnectionError(str(exc))
    if isinstance(exc, RateLimitError):
        return LLMRateLimitError(str(exc))
    if isinstance(exc, APIError):
        return LLMError(str(exc))
    # Non-OpenAI exceptions (network, etc.)
    msg = str(exc).lower()
    if "timeout" in msg:
        return LLMTimeoutError(str(exc))
    if "connection" in msg:
        return LLMConnectionError(str(exc))
    if "rate limit" in msg:
        return LLMRateLimitError(str(exc))
    return LLMError(str(exc))
