# -*- coding: utf-8 -*-
"""AI call logger for tracking AI API requests and responses."""
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from src.utils.config import settings


class AICallLogger:
    """
    Logger for AI API calls.

    Records request/response details, token usage, and latency to a dedicated log file.
    """

    def __init__(
        self,
        log_file: Optional[str] = None,
        log_level: Optional[str] = None,
    ):
        """
        Initialize AI call logger.

        :param log_file: Path to the log file. Defaults to settings.AI_LOG_FILE.
        :param log_level: Log level. Defaults to settings.AI_LOG_LEVEL.
        """
        self.log_file = log_file or settings.AI_LOG_FILE
        self.log_level = log_level or settings.AI_LOG_LEVEL
        self._logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        """Set up the dedicated logger for AI calls."""
        # Ensure log directory exists
        log_path = Path(self.log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # Create a dedicated logger
        logger = logging.getLogger("ai_calls")
        logger.setLevel(getattr(logging, self.log_level.upper(), logging.INFO))

        # Remove existing handlers to avoid duplicates
        logger.handlers.clear()

        # File handler with detailed formatting
        file_handler = logging.FileHandler(self.log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

        # Console handler for errors only
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.ERROR)
        console_formatter = logging.Formatter(
            "[AI] %(levelname)s: %(message)s"
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

        return logger

    def log_request(
        self,
        model: str,
        messages: list,
        request_id: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Log an AI API request.

        :param model: Model name being used.
        :param messages: List of messages in the request.
        :param request_id: Optional unique request identifier.
        :param temperature: Temperature setting for generation.
        :param max_tokens: Maximum tokens setting.
        :param extra: Additional metadata to log.
        :return: Generated request ID.
        """
        if not request_id:
            request_id = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")

        log_data = {
            "type": "REQUEST",
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat(),
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "message_count": len(messages),
            "messages_preview": self._truncate_messages(messages),
        }

        if extra:
            log_data["extra"] = extra

        self._logger.info(json.dumps(log_data, ensure_ascii=False))
        return request_id

    def log_response(
        self,
        request_id: str,
        response_content: str,
        model: str,
        prompt_tokens: Optional[int] = None,
        completion_tokens: Optional[int] = None,
        total_tokens: Optional[int] = None,
        latency_ms: Optional[float] = None,
        is_stream: bool = False,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log an AI API response.

        :param request_id: Request identifier from log_request.
        :param response_content: The generated response content.
        :param model: Model name used.
        :param prompt_tokens: Number of tokens in the prompt.
        :param completion_tokens: Number of tokens in the completion.
        :param total_tokens: Total tokens used.
        :param latency_ms: Request latency in milliseconds.
        :param is_stream: Whether this was a streaming response.
        :param extra: Additional metadata to log.
        """
        log_data = {
            "type": "RESPONSE",
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat(),
            "model": model,
            "is_stream": is_stream,
            "latency_ms": latency_ms,
            "tokens": {
                "prompt": prompt_tokens,
                "completion": completion_tokens,
                "total": total_tokens,
            },
            "response_preview": self._truncate_text(response_content, 500),
            "response_length": len(response_content),
        }

        if extra:
            log_data["extra"] = extra

        self._logger.info(json.dumps(log_data, ensure_ascii=False))

    def log_error(
        self,
        request_id: str,
        error: Exception,
        model: str,
        latency_ms: Optional[float] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log an AI API error.

        :param request_id: Request identifier from log_request.
        :param error: The exception that occurred.
        :param model: Model name used.
        :param latency_ms: Request latency in milliseconds.
        :param extra: Additional metadata to log.
        """
        log_data = {
            "type": "ERROR",
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat(),
            "model": model,
            "latency_ms": latency_ms,
            "error_type": type(error).__name__,
            "error_message": str(error),
        }

        if extra:
            log_data["extra"] = extra

        self._logger.error(json.dumps(log_data, ensure_ascii=False))

    def log_stream_start(
        self,
        request_id: str,
        model: str,
    ) -> None:
        """
        Log the start of a streaming response.

        :param request_id: Request identifier.
        :param model: Model name being used.
        """
        log_data = {
            "type": "STREAM_START",
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat(),
            "model": model,
        }
        self._logger.debug(json.dumps(log_data, ensure_ascii=False))

    def log_stream_end(
        self,
        request_id: str,
        model: str,
        total_chunks: int,
        total_content_length: int,
        latency_ms: float,
    ) -> None:
        """
        Log the end of a streaming response.

        :param request_id: Request identifier.
        :param model: Model name used.
        :param total_chunks: Number of chunks received.
        :param total_content_length: Total length of content received.
        :param latency_ms: Total latency in milliseconds.
        """
        log_data = {
            "type": "STREAM_END",
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat(),
            "model": model,
            "total_chunks": total_chunks,
            "total_content_length": total_content_length,
            "latency_ms": latency_ms,
        }
        self._logger.info(json.dumps(log_data, ensure_ascii=False))

    def _truncate_messages(self, messages: list, max_per_message: int = 200) -> list:
        """Truncate message contents for logging."""
        truncated = []
        for msg in messages:
            truncated_msg = {"role": msg.get("role", "unknown")}
            content = msg.get("content", "")
            if isinstance(content, str):
                truncated_msg["content"] = self._truncate_text(content, max_per_message)
            else:
                truncated_msg["content"] = str(content)[:max_per_message]
            truncated.append(truncated_msg)
        return truncated

    def _truncate_text(self, text: str, max_length: int = 500) -> str:
        """Truncate text for logging."""
        if len(text) <= max_length:
            return text
        return text[:max_length] + f"... ({len(text)} chars total)"


# Global singleton instance
_ai_logger: Optional[AICallLogger] = None


def get_ai_logger() -> AICallLogger:
    """Get the global AI logger instance."""
    global _ai_logger
    if _ai_logger is None:
        _ai_logger = AICallLogger()
    return _ai_logger
