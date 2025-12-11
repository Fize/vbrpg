# -*- coding: utf-8 -*-

"""Phase 7 集成测试：人类玩家参与完整流程（T64-T68）。"""
import random
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.werewolf_game_service import WerewolfGameService


@pytest.fixture
def service_with_seer_state():
    """创建带人类玩家的游戏状态，固定随机种子保证座位与角色可预期。"""
    random.seed(42)
    service = WerewolfGameService(db=MagicMock())
    player_names = [f"玩家{i}" for i in range(1, 11)]
    state = service.engine.initialize_game_with_human_player(
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
    """T64: 角色选择集成校验，人类座位与角色正确写入状态。"""
    service, state = service_with_seer_state
    human_seat = state.human_player_seat

    assert human_seat is not None
    assert state.players[human_seat].is_human is True
    assert state.players[human_seat].role == "seer"
    assert state.user_seat_number == human_seat


@pytest.mark.asyncio
async def test_speech_flow_clears_waiting_and_records_history(service_with_seer_state):
    """T65: 人类发言集成流程，写入历史并清除等待状态。"""
    service, state = service_with_seer_state
    human_seat = state.human_player_seat
    service._set_waiting_for_human("ROOM_TEST", "speech", timeout=5)

    result = await service.process_human_speech(
        room_code="ROOM_TEST",
        player_id="human_player",
        content="这是测试发言",
    )

    assert result["success"] is True
    assert state.waiting_for_human_action is False
    assert len(state.speech_history) == 1
    entry = state.speech_history[-1]
    assert entry["seat_number"] == human_seat
    assert entry["content"] == "这是测试发言"


@pytest.mark.asyncio
async def test_vote_flow_updates_logs_and_broadcasts(service_with_seer_state):
    """T66: 人类投票集成流程，投票成功、日志记录、清理等待。"""
    service, state = service_with_seer_state
    human_seat = state.human_player_seat
    target_seat = _find_first_alive(state, exclude_seat=human_seat)
    service._set_waiting_for_human("ROOM_TEST", "vote", timeout=5)

    with patch(
        "src.services.werewolf_game_service.broadcast_vote_update",
        new_callable=AsyncMock,
    ) as mock_update, patch(
        "src.services.werewolf_game_service.broadcast_human_vote_complete",
        new_callable=AsyncMock,
    ) as mock_complete:
        result = await service.process_human_vote(
            room_code="ROOM_TEST",
            player_id="human_player",
            target_seat=target_seat,
        )

    assert result["success"] is True
    assert state.waiting_for_human_action is False
    assert any("投票" in log for log in state.game_logs)
    mock_update.assert_awaited_once()
    mock_complete.assert_awaited_once()


@pytest.mark.asyncio
async def test_night_action_seer_check_flow(service_with_seer_state):
    """T67: 人类预言家夜间查验流程，返回查验结果并清理等待。"""
    service, state = service_with_seer_state
    human_seat = state.human_player_seat
    target_seat = _find_first_alive(state, exclude_seat=human_seat)
    state.day_number = 1
    service._set_waiting_for_human("ROOM_TEST", "seer_check", timeout=5)

    with patch(
        "src.services.werewolf_game_service.broadcast_human_night_action_complete",
        new_callable=AsyncMock,
    ) as mock_complete:
        result = await service.process_human_night_action(
            room_code="ROOM_TEST",
            player_id="human_player",
            action_type="seer_check",
            target_seat=target_seat,
        )

    assert result["success"] is True
    assert result["target_seat"] == target_seat
    assert result.get("check_result") in {"狼人", "好人"}
    assert state.waiting_for_human_action is False
    mock_complete.assert_awaited_once()


@pytest.mark.asyncio
async def test_full_flow_links_day_and_night_actions(service_with_seer_state):
    """T68: 简化完整流程串联（发言->投票->夜查），每步清理等待并写日志。"""
    service, state = service_with_seer_state
    human_seat = state.human_player_seat
    target_seat = _find_first_alive(state, exclude_seat=human_seat)

    # 发言
    service._set_waiting_for_human("ROOM_TEST", "speech", timeout=5)
    await service.process_human_speech("ROOM_TEST", "human_player", "流程发言")
    assert state.waiting_for_human_action is False

    # 投票
    service._set_waiting_for_human("ROOM_TEST", "vote", timeout=5)
    with patch(
        "src.services.werewolf_game_service.broadcast_vote_update",
        new_callable=AsyncMock,
    ), patch(
        "src.services.werewolf_game_service.broadcast_human_vote_complete",
        new_callable=AsyncMock,
    ):
        await service.process_human_vote("ROOM_TEST", "human_player", target_seat)
    assert state.waiting_for_human_action is False

    # 夜查
    service._set_waiting_for_human("ROOM_TEST", "seer_check", timeout=5)
    with patch(
        "src.services.werewolf_game_service.broadcast_human_night_action_complete",
        new_callable=AsyncMock,
    ):
        await service.process_human_night_action(
            room_code="ROOM_TEST",
            player_id="human_player",
            action_type="seer_check",
            target_seat=target_seat,
        )
    assert state.waiting_for_human_action is False
    assert len(state.game_logs) >= 2
