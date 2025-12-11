# -*- coding: utf-8 -*-

"""Tests for human timeout and AI takeover in WerewolfGameService (T57-T63)."""
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.werewolf_game_service import WerewolfGameService
from src.services.games.werewolf_engine import WerewolfGameState, PlayerState


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    return db


@pytest.fixture
def game_service(mock_db):
    return WerewolfGameService(db=mock_db)


def _build_basic_state(action_type: str) -> WerewolfGameState:
    state = WerewolfGameState(room_code="TEST")
    state.game_id = "GAME1"
    state.day_number = 1
    state.human_player_seat = 1
    state.waiting_for_human_action = True
    state.human_action_type = action_type
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
@patch.object(WerewolfGameService, "_ai_takeover_speech", new_callable=AsyncMock)
async def test_check_human_timeout_dispatches_speech(takeover_mock, game_service):
    state = _build_basic_state("speech")
    game_service._game_states["TEST"] = state

    takeover_mock.side_effect = lambda *args, **kwargs: game_service._clear_waiting_for_human("TEST")

    triggered = await game_service._check_human_timeout("TEST", "GAME1")

    assert triggered is True
    takeover_mock.assert_awaited_once()
    assert state.waiting_for_human_action is False


@pytest.mark.asyncio
@patch.object(WerewolfGameService, "_ai_takeover_night_action", new_callable=AsyncMock)
async def test_check_human_timeout_dispatches_night_action(takeover_mock, game_service):
    state = _build_basic_state("werewolf_kill")
    game_service._game_states["TEST"] = state

    takeover_mock.side_effect = lambda *args, **kwargs: game_service._clear_waiting_for_human("TEST")

    triggered = await game_service._check_human_timeout("TEST", "GAME1")

    assert triggered is True
    takeover_mock.assert_awaited_once()
    assert state.waiting_for_human_action is False


@pytest.mark.asyncio
@patch("src.services.werewolf_game_service.broadcast_ai_takeover", new_callable=AsyncMock)
@patch("src.services.werewolf_game_service.broadcast_human_vote_complete", new_callable=AsyncMock)
@patch("src.services.werewolf_game_service.broadcast_vote_update", new_callable=AsyncMock)
async def test_ai_takeover_vote_updates_state(mock_update, mock_complete, mock_takeover, game_service):
    state = _build_basic_state("vote")
    state.game_logs = []
    game_service._game_states["TEST"] = state

    agent = MagicMock()
    agent.decide_vote = AsyncMock(return_value={"target": 2})

    game_service._create_temp_agent = MagicMock(return_value=agent)
    game_service.engine.process_vote = MagicMock()

    await game_service._ai_takeover_vote("TEST", state, state.players[1])

    game_service.engine.process_vote.assert_called_once_with(state, 1, 2)
    mock_update.assert_awaited()
    mock_complete.assert_awaited()
    mock_takeover.assert_awaited_once()
    assert any("AI代打" in log for log in state.game_logs)
    assert state.waiting_for_human_action is False
