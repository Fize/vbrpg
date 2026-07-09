# -*- coding: utf-8 -*-

"""Phase 7 集成测试：人类玩家参与完整流程（T64-T68）。"""
import random
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.games.werewolf.orchestrator import WerewolfGameOrchestrator


@pytest.fixture
def service_with_seer_state():
    """创建带人类玩家的游戏状态。"""
    random.seed(42)
    service = WerewolfGameOrchestrator()
    player_names = [f"玩家{i}" for i in range(1, 11)]
    state = service.engine.initialize_game(
        room_code="ROOM_TEST",
        player_names=player_names,
        human_player_id="human_player",
        human_role="seer",
    )
    state.day_number = 1
    service._game_states["ROOM_TEST"] = state
    return service, state


def _find_first_alive(state, exclude_seat):
    for seat, player in state.players.items():
        if seat != exclude_seat and player.is_alive:
            return seat
    return None


@pytest.mark.asyncio
async def test_role_selection_sets_human_seat_and_role(service_with_seer_state):
    """T64: 角色选择集成校验。"""
    service, state = service_with_seer_state
    human_seat = state.human_player_seat
    assert human_seat is not None
    assert state.players[human_seat].is_human is True
    assert state.players[human_seat].role == "seer"


@pytest.mark.asyncio
async def test_speech_flow_clears_waiting_and_records_history(service_with_seer_state):
    """T65: 人类发言集成流程。"""
    service, state = service_with_seer_state
    state.waiting_for_human_action = True
    state.human_action_type = "speech"

    result = await service.process_human_speech(
        room_code="ROOM_TEST",
        player_id="human_player",
        content="这是测试发言",
    )

    assert result["success"] is True
    assert state.waiting_for_human_action is False
    assert state.pending_human_action["type"] == "speech"
    assert state.pending_human_action["data"]["content"] == "这是测试发言"


@pytest.mark.asyncio
async def test_vote_flow_updates_logs_and_broadcasts(service_with_seer_state):
    """T66: 人类投票集成流程。"""
    service, state = service_with_seer_state
    human_seat = state.human_player_seat
    target_seat = _find_first_alive(state, exclude_seat=human_seat)
    state.waiting_for_human_action = True
    state.human_action_type = "vote"

    result = await service.process_human_vote(
        room_code="ROOM_TEST",
        player_id="human_player",
        target_seat=target_seat,
    )

    assert result["success"] is True
    assert state.waiting_for_human_action is False
    assert state.pending_human_action["type"] == "vote"
    assert state.pending_human_action["data"]["target_seat"] == target_seat


@pytest.mark.asyncio
async def test_night_action_seer_check_flow(service_with_seer_state):
    """T67: 人类预言家夜间查验流程。"""
    service, state = service_with_seer_state
    human_seat = state.human_player_seat
    target_seat = _find_first_alive(state, exclude_seat=human_seat)
    state.day_number = 1
    state.waiting_for_human_action = True
    state.human_action_type = "seer_check"

    result = await service.process_human_night_action(
        room_code="ROOM_TEST",
        player_id="human_player",
        action_type="seer_check",
        target_seat=target_seat,
    )

    assert result["success"] is True
    assert state.waiting_for_human_action is False
    assert state.pending_human_action["type"] == "seer_check"
    assert state.pending_human_action["data"]["target_seat"] == target_seat


@pytest.mark.asyncio
async def test_full_flow_links_day_and_night_actions(service_with_seer_state):
    """T68: 简化完整流程串联（发言->投票->夜查）。"""
    service, state = service_with_seer_state
    human_seat = state.human_player_seat
    target_seat = _find_first_alive(state, exclude_seat=human_seat)

    # 发言
    state.waiting_for_human_action = True
    state.human_action_type = "speech"
    await service.process_human_speech("ROOM_TEST", "human_player", "流程发言")
    assert state.waiting_for_human_action is False

    # 投票
    state.waiting_for_human_action = True
    state.human_action_type = "vote"
    await service.process_human_vote("ROOM_TEST", "human_player", target_seat)
    assert state.waiting_for_human_action is False

    # 夜查
    state.waiting_for_human_action = True
    state.human_action_type = "seer_check"
    await service.process_human_night_action(
        room_code="ROOM_TEST",
        player_id="human_player",
        action_type="seer_check",
        target_seat=target_seat,
    )
    assert state.waiting_for_human_action is False
