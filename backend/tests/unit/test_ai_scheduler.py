"""Tests for AI scheduler.

Tests AI turn scheduling, timeout handling, and task management.
"""
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from src.services.ai_service import AIScheduler


@pytest.fixture
def mock_ai_service():
    """Mock AI agent service."""
    service = Mock()
    service.decide_action = AsyncMock(return_value={
        "type": "investigate",
        "location": "library"
    })
    return service


@pytest.fixture
def mock_game_state_service():
    """Mock game state service."""
    service = Mock()
    service.get_current_state = AsyncMock(return_value=Mock(
        game_data='{"current_player": "agent_1", "turn": 1}'
    ))
    service.update_state = AsyncMock()
    service.handle_timeout = AsyncMock()
    return service


@pytest.fixture
def scheduler(mock_ai_service, mock_game_state_service):
    """Create AI scheduler."""
    return AIScheduler(
        ai_service=mock_ai_service,
        game_state_service=mock_game_state_service,
        timeout_seconds=2
    )


class TestAISchedulerInit:
    """Test scheduler initialization."""
    
    def test_init_with_defaults(self, mock_ai_service, mock_game_state_service):
        """Test initialization with default timeout."""
        scheduler = AIScheduler(mock_ai_service, mock_game_state_service)
        assert scheduler.ai_service == mock_ai_service
        assert scheduler.game_state_service == mock_game_state_service
        assert scheduler.timeout_seconds == 10
        assert scheduler._active_tasks == {}
    
    def test_init_with_custom_timeout(self, mock_ai_service, mock_game_state_service):
        """Test initialization with custom timeout."""
        scheduler = AIScheduler(mock_ai_service, mock_game_state_service, timeout_seconds=5)
        assert scheduler.timeout_seconds == 5


class TestScheduleAITurn:
    """Test AI turn scheduling."""
    
    @pytest.mark.asyncio
    async def test_schedule_turn_success(self, scheduler, mock_ai_service, mock_game_state_service):
        """Test successful AI turn scheduling."""
        game_room_id = uuid4()
        agent_id = "agent_1"
        personality = "analytical"
        
        with patch('src.services.games.crime_scene_engine.CrimeSceneEngine') as mock_engine_class:
            mock_engine = Mock()
            mock_engine.get_valid_actions.return_value = [
                {"type": "investigate", "location": "library"}
            ]
            mock_engine_class.return_value = mock_engine
            
            decision = await scheduler.schedule_ai_turn(game_room_id, agent_id, personality)
            
            assert decision == {"type": "investigate", "location": "library"}
            mock_ai_service.decide_action.assert_called_once()
            mock_game_state_service.update_state.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_schedule_turn_timeout(self, mock_ai_service, mock_game_state_service):
        """Test AI turn timeout handling."""
        # Make AI service slow
        async def slow_decide(*args, **kwargs):
            await asyncio.sleep(5)
            return {"type": "investigate"}
        
        mock_ai_service.decide_action = slow_decide
        scheduler = AIScheduler(mock_ai_service, mock_game_state_service, timeout_seconds=0.1)
        
        game_room_id = uuid4()
        
        with patch('src.services.games.crime_scene_engine.CrimeSceneEngine'):
            decision = await scheduler.schedule_ai_turn(game_room_id, "agent_1", "analytical")
            
            assert decision is None
            mock_game_state_service.handle_timeout.assert_called_once_with(game_room_id)
    
    @pytest.mark.asyncio
    async def test_schedule_turn_cancels_existing(self, scheduler):
        """Test scheduling cancels existing task for same agent."""
        game_room_id = uuid4()
        agent_id = "agent_1"
        
        with patch('src.services.games.crime_scene_engine.CrimeSceneEngine'):
            # Schedule first turn
            task1 = asyncio.create_task(
                scheduler.schedule_ai_turn(game_room_id, agent_id, "analytical")
            )
            await asyncio.sleep(0.01)  # Let it start
            
            # Schedule second turn (should cancel first)
            task2 = asyncio.create_task(
                scheduler.schedule_ai_turn(game_room_id, agent_id, "aggressive")
            )
            
            # Wait for tasks
            decision2 = await task2
            
            # First task should be cancelled
            assert task1.cancelled() or task1.done()
            assert decision2 is not None
    
    @pytest.mark.asyncio
    async def test_schedule_turn_error_handling(self, mock_ai_service, mock_game_state_service):
        """Test error handling during AI turn."""
        mock_ai_service.decide_action = AsyncMock(side_effect=Exception("AI error"))
        scheduler = AIScheduler(mock_ai_service, mock_game_state_service)
        
        game_room_id = uuid4()
        
        with patch('src.services.games.crime_scene_engine.CrimeSceneEngine'):
            decision = await scheduler.schedule_ai_turn(game_room_id, "agent_1", "analytical")
            
            assert decision is None
    
    @pytest.mark.asyncio
    async def test_schedule_turn_cleanup(self, scheduler):
        """Test task cleanup after completion."""
        game_room_id = uuid4()
        agent_id = "agent_1"
        
        with patch('src.services.games.crime_scene_engine.CrimeSceneEngine'):
            await scheduler.schedule_ai_turn(game_room_id, agent_id, "analytical")
            
            # Task should be cleaned up
            assert len(scheduler._active_tasks) == 0


class TestExecuteAITurn:
    """Test AI turn execution."""
    
    @pytest.mark.asyncio
    async def test_execute_turn_flow(self, scheduler, mock_ai_service, mock_game_state_service):
        """Test complete AI turn execution flow."""
        game_room_id = uuid4()
        agent_id = "agent_1"
        
        with patch('src.services.games.crime_scene_engine.CrimeSceneEngine') as mock_engine_class:
            mock_engine = Mock()
            mock_engine.get_valid_actions.return_value = [
                {"type": "investigate", "location": "library"}
            ]
            mock_engine_class.return_value = mock_engine
            
            decision = await scheduler._execute_ai_turn(game_room_id, agent_id, "analytical")
            
            # Check flow
            mock_game_state_service.get_current_state.assert_called_once_with(game_room_id)
            mock_engine.get_valid_actions.assert_called_once()
            mock_ai_service.decide_action.assert_called_once()
            mock_game_state_service.update_state.assert_called_once()
            
            assert decision == {"type": "investigate", "location": "library"}
    
    @pytest.mark.asyncio
    async def test_execute_turn_with_game_data(self, scheduler, mock_ai_service):
        """Test AI turn uses correct game data."""
        game_room_id = uuid4()
        agent_id = "agent_1"
        
        with patch('src.services.games.crime_scene_engine.CrimeSceneEngine') as mock_engine_class:
            mock_engine = Mock()
            mock_engine.get_valid_actions.return_value = []
            mock_engine_class.return_value = mock_engine
            
            await scheduler._execute_ai_turn(game_room_id, agent_id, "analytical")
            
            # Check AI service received parsed game data
            call_kwargs = mock_ai_service.decide_action.call_args[1]
            assert call_kwargs['agent_id'] == agent_id
            assert call_kwargs['personality'] == "analytical"
            assert 'game_state' in call_kwargs
            assert 'available_actions' in call_kwargs


class TestCancelAll:
    """Test cancelling all AI tasks."""
    
    @pytest.mark.asyncio
    async def test_cancel_all_tasks(self, scheduler):
        """Test cancelling all active tasks."""
        game_room_id = uuid4()
        
        with patch('src.services.games.crime_scene_engine.CrimeSceneEngine'):
            # Start multiple tasks
            tasks = []
            for i in range(3):
                task = asyncio.create_task(
                    scheduler.schedule_ai_turn(game_room_id, f"agent_{i}", "analytical")
                )
                tasks.append(task)
                await asyncio.sleep(0.01)
            
            # Cancel all
            scheduler.cancel_all()
            
            # All tasks should be cancelled
            assert len(scheduler._active_tasks) == 0
    
    def test_cancel_all_empty(self, scheduler):
        """Test cancelling when no tasks active."""
        scheduler.cancel_all()
        assert len(scheduler._active_tasks) == 0


class TestConcurrency:
    """Test concurrent AI turn handling."""
    
    @pytest.mark.asyncio
    async def test_multiple_agents_concurrent(self, scheduler):
        """Test multiple agents can run concurrently."""
        game_room_id = uuid4()
        
        with patch('src.services.games.crime_scene_engine.CrimeSceneEngine'):
            # Schedule multiple agents
            tasks = [
                scheduler.schedule_ai_turn(game_room_id, f"agent_{i}", "analytical")
                for i in range(3)
            ]
            
            decisions = await asyncio.gather(*tasks)
            
            # All should complete
            assert len(decisions) == 3
            assert all(d is not None for d in decisions)
    
    @pytest.mark.asyncio
    async def test_same_agent_sequential(self, scheduler):
        """Test same agent tasks are sequential (second cancels first)."""
        game_room_id = uuid4()
        agent_id = "agent_1"
        
        with patch('src.services.games.crime_scene_engine.CrimeSceneEngine'):
            # Start first task
            task1 = asyncio.create_task(
                scheduler.schedule_ai_turn(game_room_id, agent_id, "analytical")
            )
            await asyncio.sleep(0.01)
            
            # Start second task (should cancel first)
            task2 = asyncio.create_task(
                scheduler.schedule_ai_turn(game_room_id, agent_id, "aggressive")
            )
            
            await task2
            
            # Only one task should remain in tracking
            assert len(scheduler._active_tasks) == 0
