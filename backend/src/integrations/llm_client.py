"""LangChain LLM integration for AI agent decision-making."""

import logging
import os
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)


class LLMClient:
    """Client for interacting with LLM services via LangChain.
    
    Handles:
    - OpenAI API integration
    - Prompt template management
    - Error handling (timeouts, connection errors, rate limits)
    - Response parsing
    """

    def __init__(
        self,
        model_name: str = "gpt-4o-mini",
        temperature: float = 0.7,
        timeout: int = 10,
        max_retries: int = 2
    ):
        """Initialize LLM client.
        
        Args:
            model_name: OpenAI model to use
            temperature: Sampling temperature (0.0-1.0)
            timeout: Request timeout in seconds
            max_retries: Number of retry attempts on failure
        """
        self.model_name = model_name
        self.temperature = temperature
        self.timeout = timeout
        self.max_retries = max_retries

        # Initialize ChatOpenAI client
        api_key = os.getenv("OPENAI_API_KEY", "sk-test-key-for-testing")
        if api_key == "sk-test-key-for-testing":
            logger.warning("Using test API key - LLM functionality will not work")

        self.llm = ChatOpenAI(
            model=model_name,
            temperature=temperature,
            timeout=timeout,
            max_retries=max_retries,
            openai_api_key=api_key  # Use explicit parameter name
        )

        logger.info(f"LLM client initialized with model={model_name}, temperature={temperature}")

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
