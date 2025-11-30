# -*- coding: utf-8 -*-
"""Base class for game host AI agents."""

import logging
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, Optional

from src.integrations.llm_client import LLMClient

logger = logging.getLogger(__name__)


class BaseGameHost(ABC):
    """
    Base class for game host AI agents.

    The host is responsible for:
    - Narrating the game flow
    - Announcing game events
    - Managing phase transitions
    - Creating atmosphere
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
    ):
        """
        Initialize the game host.

        :param llm_client: LLM client for generating announcements.
        """
        self.llm_client = llm_client or LLMClient()

    @abstractmethod
    def get_system_prompt(self) -> str:
        """
        Get the system prompt for the host.

        :return: System prompt string.
        """
        pass

    @abstractmethod
    async def announce(
        self,
        announcement_type: str,
        context: Dict[str, Any],
    ) -> str:
        """
        Generate an announcement.

        :param announcement_type: Type of announcement.
        :param context: Context data for the announcement.
        :return: Generated announcement text.
        """
        pass

    @abstractmethod
    async def announce_stream(
        self,
        announcement_type: str,
        context: Dict[str, Any],
    ) -> AsyncIterator[str]:
        """
        Generate a streaming announcement.

        :param announcement_type: Type of announcement.
        :param context: Context data for the announcement.
        :yields: Chunks of announcement text.
        """
        pass

    async def _generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        Generate text using LLM.

        :param prompt: User prompt.
        :param system_prompt: Optional system prompt override.
        :return: Generated text.
        """
        messages = [
            {"role": "system", "content": system_prompt or self.get_system_prompt()},
            {"role": "user", "content": prompt},
        ]

        try:
            return await self.llm_client.generate(messages)
        except Exception as e:
            logger.error(f"Host announcement generation failed: {e}")
            raise

    async def _generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """
        Generate streaming text using LLM.

        :param prompt: User prompt.
        :param system_prompt: Optional system prompt override.
        :yields: Text chunks.
        """
        messages = [
            {"role": "system", "content": system_prompt or self.get_system_prompt()},
            {"role": "user", "content": prompt},
        ]

        try:
            async for chunk in self.llm_client.generate_stream(messages):
                yield chunk
        except Exception as e:
            logger.error(f"Host streaming announcement failed: {e}")
            raise
