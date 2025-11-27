"""AI Service module for managing AI players and turn scheduling.

This module consolidates all AI-related functionality:
- AIAgentService: Managing AI players, filling slots, decision making
- AIScheduler: Turn scheduling with timeout handling
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.integrations.llm_client import LLMClient
from src.models.game import GameRoom, GameRoomParticipant
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

# AI personality types
AI_PERSONALITIES = [
    "analytical_detective",
    "intuitive_investigator",
    "cautious_observer",
    "bold_risk_taker",
    "strategic_thinker",
    "empathetic_listener"
]

# Map to LLM personality types
PERSONALITY_MAP = {
    "analytical_detective": "logical",
    "intuitive_investigator": "chaotic",
    "cautious_observer": "cautious",
    "bold_risk_taker": "aggressive",
    "strategic_thinker": "logical",
    "empathetic_listener": "cooperative"
}


# =============================================================================
# AIAgentService
# =============================================================================

class AIAgentService:
    """Service for AI agent operations."""

    def __init__(self, db: AsyncSession, llm_client: Optional[LLMClient] = None):
        self.db = db
        self.llm_client = llm_client or LLMClient()

    async def fill_empty_slots(self, room: GameRoom) -> list[GameRoomParticipant]:
        """
        Fill empty player slots with AI agents.
        
        Args:
            room: Game room to fill
            
        Returns:
            List of created AI participants
        """
        active_count = room.get_active_participants_count()
        slots_to_fill = room.min_players - active_count

        if slots_to_fill <= 0:
            logger.info(f"Room {room.code} has enough players, no AI agents needed")
            return []

        logger.info(f"Filling {slots_to_fill} empty slots with AI agents in room {room.code}")

        ai_participants = []
        for i in range(slots_to_fill):
            personality = AI_PERSONALITIES[i % len(AI_PERSONALITIES)]

            participant = GameRoomParticipant(
                game_room_id=room.id,
                player_id=None,
                is_ai_agent=True,
                ai_personality=personality
            )
            self.db.add(participant)
            ai_participants.append(participant)

        await self.db.commit()

        logger.info(f"Added {len(ai_participants)} AI agents to room {room.code}")
        return ai_participants

    async def replace_disconnected_player(
        self,
        room: GameRoom,
        player_id: str
    ) -> GameRoomParticipant:
        """
        Replace a disconnected player with an AI agent.
        
        Args:
            room: Game room
            player_id: Player to replace
            
        Returns:
            New AI participant
        """
        # Find the disconnected participant
        participant = None
        for p in room.participants:
            if p.player_id == player_id and not p.is_active():
                participant = p
                break

        if participant:
            participant.replaced_by_ai = True

        # Create AI replacement
        personality = AI_PERSONALITIES[0]  # Use first personality as default
        ai_participant = GameRoomParticipant(
            game_room_id=room.id,
            player_id=None,
            is_ai_agent=True,
            ai_personality=personality
        )
        self.db.add(ai_participant)
        await self.db.commit()

        logger.info(f"Replaced player {player_id} with AI agent in room {room.code}")
        return ai_participant

    async def decide_action(
        self,
        agent_id: str,
        game_state: dict[str, Any],
        available_actions: list[dict[str, Any]],
        personality: Optional[str] = None
    ) -> dict[str, Any]:
        """Generate AI decision for a game turn using LLM.
        
        Args:
            agent_id: AI agent identifier
            game_state: Current game state
            available_actions: List of valid actions
            personality: AI personality type (defaults to first available)
            
        Returns:
            Selected action with reasoning
            
        Raises:
            LLMError: If LLM service fails
        """
        if not personality:
            personality = AI_PERSONALITIES[0]

        # Map to LLM personality
        llm_personality = PERSONALITY_MAP.get(personality, "logical")

        # Determine role based on game state
        player_role = self._get_player_role(game_state, agent_id)

        # Generate decision using LLM
        try:
            decision = await self.llm_client.generate_decision(
                game_state=game_state,
                player_role=player_role,
                personality=llm_personality,
                available_actions=available_actions
            )

            logger.info(f"AI agent {agent_id} decided: {decision['action_type']}")
            return decision

        except Exception as e:
            logger.error(f"AI decision failed for agent {agent_id}: {e}")
            # Fallback: select first available action
            if available_actions:
                return {
                    "action_type": available_actions[0]["type"],
                    "parameters": available_actions[0].get("parameters", {}),
                    "reasoning": "LLM service unavailable, using fallback action"
                }
            raise

    def _get_player_role(self, game_state: dict[str, Any], player_id: str) -> str:
        """Determine player's role based on game state.
        
        Args:
            game_state: Current game state
            player_id: Player to get role for
            
        Returns:
            Role description
        """
        # For Crime Scene, role is generic investigator
        return f"调查员 (Player {player_id})"


# =============================================================================
# AIScheduler
# =============================================================================

class AIScheduler:
    """Scheduler for AI agent turns.
    
    Manages the execution of AI turns with timeout handling.
    """

    def __init__(
        self,
        ai_service: AIAgentService,
        game_state_service: "GameStateService",
        timeout_seconds: int = 10
    ):
        """Initialize scheduler.
        
        Args:
            ai_service: AI agent service
            game_state_service: Game state service
            timeout_seconds: Max time for AI to decide (default 10s)
        """
        self.ai_service = ai_service
        self.game_state_service = game_state_service
        self.timeout_seconds = timeout_seconds
        self._active_tasks: dict[str, asyncio.Task] = {}

    async def schedule_ai_turn(
        self,
        game_room_id: UUID,
        agent_id: str,
        personality: str
    ) -> Optional[dict[str, Any]]:
        """Schedule AI turn with timeout.
        
        Args:
            game_room_id: Game room
            agent_id: AI agent identifier
            personality: AI personality type
            
        Returns:
            AI decision or None if timeout
        """
        task_id = f"{game_room_id}_{agent_id}"

        # Cancel any existing task for this agent
        if task_id in self._active_tasks:
            self._active_tasks[task_id].cancel()

        try:
            # Create task with timeout
            task = asyncio.create_task(
                self._execute_ai_turn(game_room_id, agent_id, personality)
            )
            self._active_tasks[task_id] = task

            # Wait with timeout
            decision = await asyncio.wait_for(task, timeout=self.timeout_seconds)

            logger.info(f"AI turn completed for {agent_id} in room {game_room_id}")
            return decision

        except asyncio.TimeoutError:
            logger.warning(f"AI turn timeout for {agent_id} in room {game_room_id}")
            # Handle timeout
            await self.game_state_service.handle_timeout(game_room_id)
            return None

        except Exception as e:
            logger.error(f"AI turn failed for {agent_id}: {e}")
            return None

        finally:
            # Cleanup
            if task_id in self._active_tasks:
                del self._active_tasks[task_id]

    async def _execute_ai_turn(
        self,
        game_room_id: UUID,
        agent_id: str,
        personality: str
    ) -> dict[str, Any]:
        """Execute AI turn.
        
        Args:
            game_room_id: Game room
            agent_id: AI agent identifier
            personality: AI personality type
            
        Returns:
            AI decision
        """
        import json

        from src.services.games.crime_scene_engine import CrimeSceneEngine

        # Get current game state
        state = await self.game_state_service.get_current_state(game_room_id)
        game_data = json.loads(state.game_data)

        # Get available actions
        engine = CrimeSceneEngine()
        available_actions = engine.get_valid_actions(game_data, agent_id)

        # Get AI decision
        decision = await self.ai_service.decide_action(
            agent_id=agent_id,
            game_state=game_data,
            available_actions=available_actions,
            personality=personality
        )

        # Apply action
        await self.game_state_service.update_state(
            game_room_id=game_room_id,
            player_id=agent_id,
            action=decision
        )

        return decision

    def cancel_all(self):
        """Cancel all active AI tasks."""
        for task in self._active_tasks.values():
            task.cancel()
        self._active_tasks.clear()
        logger.info("All AI tasks cancelled")


if TYPE_CHECKING:
    from src.services.game_state_service import GameStateService
