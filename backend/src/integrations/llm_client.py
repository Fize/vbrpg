"""LangChain LLM integration for AI agent decision-making."""

import logging
import time
from typing import Any, AsyncIterator, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from src.utils.ai_logger import get_ai_logger
from src.utils.config import settings

logger = logging.getLogger(__name__)


class LLMClient:
    """Client for interacting with LLM services via LangChain.

    Handles:
    - OpenAI API integration (including custom base URL)
    - Streaming response generation
    - Prompt template management
    - Error handling (timeouts, connection errors, rate limits)
    - Response parsing
    - AI call logging
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
        timeout: Optional[int] = None,
        max_retries: Optional[int] = None,
        api_base_url: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        """Initialize LLM client.

        Args:
            model_name: Model to use (defaults to settings.AI_MODEL)
            temperature: Sampling temperature (defaults to settings.AI_TEMPERATURE)
            timeout: Request timeout in seconds (defaults to settings.AI_TIMEOUT)
            max_retries: Number of retry attempts (defaults to settings.AI_MAX_RETRIES)
            api_base_url: Custom API base URL (defaults to settings.AI_API_BASE_URL)
            api_key: API key (defaults to settings.effective_ai_api_key)
        """
        self.model_name = model_name or settings.AI_MODEL
        self.temperature = temperature if temperature is not None else settings.AI_TEMPERATURE
        self.timeout = timeout if timeout is not None else settings.AI_TIMEOUT
        self.max_retries = max_retries if max_retries is not None else settings.AI_MAX_RETRIES
        self.api_base_url = api_base_url or settings.AI_API_BASE_URL or None
        self.api_key = api_key or settings.effective_ai_api_key

        # AI call logger
        self.ai_logger = get_ai_logger()

        # Initialize ChatOpenAI client
        if not self.api_key:
            logger.warning("No AI API key configured - LLM functionality will not work")
            self.api_key = "sk-test-key-for-testing"

        llm_kwargs = {
            "model": self.model_name,
            "temperature": self.temperature,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
            "openai_api_key": self.api_key,
        }

        # Add custom base URL if configured
        if self.api_base_url:
            llm_kwargs["openai_api_base"] = self.api_base_url
            logger.info(f"Using custom API base URL: {self.api_base_url}")

        # Log which API key is being used (explicit AI_API_KEY preferred, fallback to OPENAI_API_KEY)
        if settings.AI_API_KEY:
            key_source = "AI_API_KEY"
        elif settings.OPENAI_API_KEY:
            key_source = "OPENAI_API_KEY"
        else:
            key_source = "none (test fallback)"

        logger.info(f"LLM client using API key from: {key_source}")

        self.llm = ChatOpenAI(**llm_kwargs)

        logger.info(
            f"LLM client initialized with model={self.model_name}, "
            f"temperature={self.temperature}"
        )

    async def generate(
        self,
        messages: list[dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Generate a response from the LLM.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
            temperature: Override default temperature.
            max_tokens: Maximum tokens to generate.

        Returns:
            Generated text content.

        Raises:
            LLMError: On any LLM-related error.
        """
        start_time = time.time()
        request_id = self.ai_logger.log_request(
            model=self.model_name,
            messages=messages,
            temperature=temperature or self.temperature,
            max_tokens=max_tokens,
        )

        try:
            # Convert to LangChain message format
            lc_messages = self._convert_messages(messages)

            # Create temporary LLM with overridden settings if needed
            llm = self.llm
            if temperature is not None or max_tokens is not None:
                kwargs = {}
                if temperature is not None:
                    kwargs["temperature"] = temperature
                if max_tokens is not None:
                    kwargs["max_tokens"] = max_tokens
                llm = self.llm.bind(**kwargs) if kwargs else self.llm

            # Generate response
            response = await llm.ainvoke(lc_messages)

            latency_ms = (time.time() - start_time) * 1000
            content = response.content

            # Log response
            usage = getattr(response, "usage_metadata", None)
            self.ai_logger.log_response(
                request_id=request_id,
                response_content=content,
                model=self.model_name,
                prompt_tokens=usage.get("input_tokens") if usage else None,
                completion_tokens=usage.get("output_tokens") if usage else None,
                total_tokens=usage.get("total_tokens") if usage else None,
                latency_ms=latency_ms,
                is_stream=False,
            )

            return content

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            self.ai_logger.log_error(
                request_id=request_id,
                error=e,
                model=self.model_name,
                latency_ms=latency_ms,
            )
            raise self._wrap_exception(e)

    async def generate_stream(
        self,
        messages: list[dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[str]:
        """Generate a streaming response from the LLM.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
            temperature: Override default temperature.
            max_tokens: Maximum tokens to generate.

        Yields:
            Chunks of generated text.

        Raises:
            LLMError: On any LLM-related error.
        """
        start_time = time.time()
        request_id = self.ai_logger.log_request(
            model=self.model_name,
            messages=messages,
            temperature=temperature or self.temperature,
            max_tokens=max_tokens,
            extra={"streaming": True},
        )

        try:
            # Convert to LangChain message format
            lc_messages = self._convert_messages(messages)

            # Create temporary LLM with overridden settings if needed
            llm = self.llm
            if temperature is not None or max_tokens is not None:
                kwargs = {}
                if temperature is not None:
                    kwargs["temperature"] = temperature
                if max_tokens is not None:
                    kwargs["max_tokens"] = max_tokens
                llm = self.llm.bind(**kwargs) if kwargs else self.llm

            self.ai_logger.log_stream_start(request_id, self.model_name)

            # Stream response
            full_content = ""
            chunk_count = 0

            async for chunk in llm.astream(lc_messages):
                if chunk.content:
                    full_content += chunk.content
                    chunk_count += 1
                    yield chunk.content

            latency_ms = (time.time() - start_time) * 1000

            # Log stream completion
            self.ai_logger.log_stream_end(
                request_id=request_id,
                model=self.model_name,
                total_chunks=chunk_count,
                total_content_length=len(full_content),
                latency_ms=latency_ms,
            )

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            self.ai_logger.log_error(
                request_id=request_id,
                error=e,
                model=self.model_name,
                latency_ms=latency_ms,
            )
            raise self._wrap_exception(e)

    def _convert_messages(self, messages: list[dict[str, str]]) -> list:
        """Convert message dicts to LangChain message objects."""
        lc_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                lc_messages.append(SystemMessage(content=content))
            else:
                lc_messages.append(HumanMessage(content=content))

        return lc_messages

    async def generate_decision(
        self,
        game_state: dict[str, Any],
        player_role: str,
        personality: str,
        available_actions: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Generate AI decision for a game turn.
        
        Args:
            game_state: Current game state
            player_role: AI agent's role in the game
            personality: AI personality type (e.g., "logical", "chaotic")
            available_actions: List of valid actions with metadata
            
        Returns:
            Selected action with reasoning
            
        Raises:
            LLMTimeoutError: If LLM request times out
            LLMConnectionError: If connection to LLM service fails
            LLMRateLimitError: If rate limit exceeded
        """
        try:
            # Build prompt
            system_prompt = self._build_system_prompt(personality)
            human_prompt = self._build_game_prompt(game_state, player_role, available_actions)

            # Generate response
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt)
            ]

            response = await self.llm.ainvoke(messages)

            # Parse response
            decision = self._parse_decision(response.content, available_actions)

            logger.info(f"AI decision generated: {decision['action_type']}")
            return decision

        except Exception as e:
            logger.error(f"LLM decision generation failed: {e}")
            raise self._wrap_exception(e)

    def _build_system_prompt(self, personality: str) -> str:
        """Build system prompt based on AI personality."""
        personality_prompts = {
            "logical": """You are a logical and analytical AI player. 
You carefully analyze all available information and make decisions based on evidence and probability.
You prioritize consistency and strategic thinking.""",

            "chaotic": """You are an unpredictable and creative AI player.
You make bold moves and unexpected decisions that keep other players guessing.
You enjoy taking risks and creating surprising situations.""",

            "cautious": """You are a careful and conservative AI player.
You prefer safe, low-risk moves and thorough investigation before accusations.
You value accuracy over speed.""",

            "aggressive": """You are a confident and assertive AI player.
You make quick decisions and aren't afraid to make early accusations.
You trust your instincts and act decisively.""",

            "cooperative": """You are a friendly and helpful AI player.
You focus on teamwork and sharing information with others.
You make decisions that benefit the group.""",

            "deceptive": """You are a clever and strategic AI player.
You know when to withhold information and misdirect others.
You play the social game as much as the logical one."""
        }

        base_prompt = personality_prompts.get(personality, personality_prompts["logical"])

        return f"""{base_prompt}

You are playing a tabletop game. Analyze the current game state and choose the best action.
Respond with your decision in JSON format:
{{
    "action_type": "the type of action to take",
    "parameters": {{}},  // action-specific parameters
    "reasoning": "brief explanation of your choice"
}}
"""

    def _build_game_prompt(
        self,
        game_state: dict[str, Any],
        player_role: str,
        available_actions: list[dict[str, Any]]
    ) -> str:
        """Build game-specific prompt with current state."""
        return f"""Game State:
{self._format_game_state(game_state)}

Your Role: {player_role}

Available Actions:
{self._format_actions(available_actions)}

Choose one action and explain your reasoning. Return only the JSON response.
"""

    def _format_game_state(self, game_state: dict[str, Any]) -> str:
        """Format game state for prompt."""
        # Extract key information
        phase = game_state.get("phase", "Unknown")
        turn_number = game_state.get("turn_number", 0)

        # Format compactly
        return f"""- Current Phase: {phase}
- Turn Number: {turn_number}
- Game Data: {game_state.get('game_data', {})}
"""

    def _format_actions(self, actions: list[dict[str, Any]]) -> str:
        """Format available actions for prompt."""
        if not actions:
            return "No actions available"

        formatted = []
        for i, action in enumerate(actions, 1):
            formatted.append(f"{i}. {action.get('type', 'Unknown')}: {action.get('description', 'No description')}")

        return "\n".join(formatted)

    def _parse_decision(
        self,
        response_text: str,
        available_actions: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Parse LLM response into structured decision.
        
        Attempts to extract JSON from response, falls back to simple parsing.
        """
        import json

        try:
            # Try to parse as JSON
            decision = json.loads(response_text)

            # Validate action type
            action_type = decision.get("action_type")
            valid_types = [a.get("type") for a in available_actions]

            if action_type not in valid_types and available_actions:
                # Fallback to first available action
                logger.warning(f"Invalid action_type '{action_type}', using first available action")
                decision["action_type"] = available_actions[0].get("type")

            return decision

        except json.JSONDecodeError:
            logger.warning(f"Failed to parse LLM response as JSON: {response_text[:100]}")

            # Fallback: return first available action
            if available_actions:
                return {
                    "action_type": available_actions[0].get("type"),
                    "parameters": {},
                    "reasoning": "Failed to parse LLM response, using default action"
                }

            raise ValueError("Invalid LLM response and no fallback available")

    def _wrap_exception(self, e: Exception):
        """Wrap exceptions into custom error types."""
        error_msg = str(e)

        if "timeout" in error_msg.lower():
            return LLMTimeoutError(f"LLM request timed out after {self.timeout}s")
        elif "rate limit" in error_msg.lower():
            return LLMRateLimitError("LLM rate limit exceeded")
        elif "connection" in error_msg.lower() or "network" in error_msg.lower():
            return LLMConnectionError(f"Failed to connect to LLM service: {error_msg}")
        else:
            return LLMError(f"LLM error: {error_msg}")


# Custom exceptions
class LLMError(Exception):
    """Base exception for LLM errors."""
    pass


class LLMTimeoutError(LLMError):
    """LLM request timed out."""
    pass


class LLMConnectionError(LLMError):
    """Failed to connect to LLM service."""
    pass


class LLMRateLimitError(LLMError):
    """LLM rate limit exceeded."""
    pass
