"""AI turn scheduler for managing AI agent actions.

Handles:
- Triggering AI actions when it's their turn
- 10-second timeout for AI decisions
- Async scheduling and execution
"""

import asyncio
import logging
from typing import Any, Optional
from uuid import UUID

from src.services.ai_agent_service import AIAgentService
from src.services.game_state_service import GameStateService

logger = logging.getLogger(__name__)


class AIScheduler:
    """Scheduler for AI agent turns.
    
    Manages the execution of AI turns with timeout handling.
    """

    def __init__(
        self,
        ai_service: AIAgentService,
        game_state_service: GameStateService,
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
