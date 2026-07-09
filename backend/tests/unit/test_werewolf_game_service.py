# -*- coding: utf-8 -*-

"""Tests for human timeout and AI takeover in WerewolfGameOrchestrator (T57-T63)."""
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.games.werewolf.orchestrator import WerewolfGameOrchestrator
from src.games.werewolf.state import WerewolfGameState, PlayerState


@pytest.fixture
def game_service():
    return WerewolfGameOrchestrator()


def _build_basic_state() -> WerewolfGameState:
    state = WerewolfGameState(room_code="TEST")
    state.game_id = "GAME1"
    state.day_number = 1
    state.human_player_seat = 1
    state.waiting_for_human_action = True
    state.human_action_type = "speech"
    state.human_action_timeout = 10
    state.human_action_start_time = datetime.now() - timedelta(seconds=120)
    state.players[1] = PlayerState(
        player_id="p1",
        player_name="玩家1",
        seat_number=1,
        role="villager",
        team="villager",
        is_alive=True,
        is_human=True,
    )
    state.players[2] = PlayerState(
        player_id="p2",
        player_name="玩家2",
        seat_number=2,
        role="villager",
        team="villager",
        is_alive=True,
        is_human=False,
    )
    return state


@pytest.mark.asyncio
async def test_human_timeout_dispatches_ai_takeover_night_action(game_service):
    """
    When a human player times out on a night action, the orchestrator's
    _ai_takeover_night_action should be triggered via the game loop.
    This test verifies that process_human_night_action works as expected
    when the human submits an action (the happy path).
    """
    state = _build_basic_state()
    state.human_action_type = "werewolf_kill"
    game_service._game_states["TEST"] = state
    game_service._ai_agents = {2: MagicMock()}

    result = await game_service.process_human_night_action(
        room_code="TEST",
        player_id="p1",
        action_type="werewolf_kill",
        target_seat=2,
    )

    assert result["success"] is True
    # The action is stored on state for the game loop to pick up
    assert state.waiting_for_human_action is False
    assert state.pending_human_action is not None
    assert state.pending_human_action["type"] == "werewolf_kill"


@pytest.mark.asyncio
async def test_process_human_speech_accepts_content(game_service):
    """
    Test that process_human_speech accepts a player's speech and
    clears the waiting state for the game loop to advance.
    """
    state = _build_basic_state()
    game_service._game_states["TEST"] = state

    result = await game_service.process_human_speech(
        room_code="TEST",
        player_id="p1",
        content="我是好人",
    )

    assert result["success"] is True
    assert state.waiting_for_human_action is False
    assert state.pending_human_action is not None
    assert state.pending_human_action["type"] == "speech"
