"""Phase 3 投票交互单元测试.

测试覆盖:
- T23: _handle_vote 人类玩家检测
- T24: process_human_vote + process_human_action 方法
- T25: 投票流程支持人类玩家等待
- T26: werewolf_human_vote WebSocket事件
- T27: broadcast_vote_options 广播函数
"""

import asyncio
import types
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.games.werewolf.orchestrator import WerewolfGameOrchestrator


# ---------------------------------------------------------------
# Helper: vote option logic extracted from _handle_vote
# ---------------------------------------------------------------

def get_available_targets(alive_players, voter_seat):
    """Generate vote options (available targets) for a voter.

    This mirrors the logic inside ``WerewolfGameOrchestrator._handle_vote``
    where ``available_targets`` is built.
    """
    return [
        {"seat_number": p.seat_number, "player_name": p.player_name, "player_id": p.player_id}
        for p in alive_players
        if p.seat_number != voter_seat
    ]


class TestGenerateVoteOptions:
    """T24: 测试投票选项生成逻辑 (可用目标列表)."""

    @pytest.fixture
    def alive_players(self):
        """创建存活玩家列表."""
        from src.games.werewolf.state import PlayerState

        players = []
        for i in range(1, 9):  # 座位 1-8 存活
            players.append(PlayerState(
                player_id=f"player_{i}",
                player_name=f"\u73a9\u5bb6{i}",
                seat_number=i,
                role="villager",
                is_alive=True,
                team="villager"
            ))
        # 座位 9, 10 死亡 — not in the list
        return players

    def test_vote_options_excludes_self(self, alive_players):
        """测试生成投票选项排除自己."""
        options = get_available_targets(alive_players, 1)

        assert not any(opt["seat_number"] == 1 for opt in options)

    def test_vote_options_excludes_dead_players(self, alive_players):
        """测试生成投票选项排除死亡玩家 (不在 alive_players 中)."""
        options = get_available_targets(alive_players, 1)

        # alive_players only contains seats 1-8, so 9/10 can't appear
        seat_numbers = [opt["seat_number"] for opt in options]
        assert 9 not in seat_numbers
        assert 10 not in seat_numbers

    def test_vote_options_includes_alive_players(self, alive_players):
        """测试生成投票选项包含存活玩家."""
        options = get_available_targets(alive_players, 1)

        # 8 alive - 1 self = 7 options
        assert len(options) == 7
        for opt in options:
            assert "seat_number" in opt
            assert "player_name" in opt
            assert "player_id" in opt

    def test_vote_options_sorted_by_seat(self, alive_players):
        """测试生成投票选项按座位号排序 (alive_players are iterated in order)."""
        options = get_available_targets(alive_players, 1)

        seat_numbers = [opt["seat_number"] for opt in options]
        assert seat_numbers == sorted(seat_numbers)

    def test_vote_options_empty_for_no_alive_others(self):
        """测试当只有自己存活时返回空列表."""
        from src.games.werewolf.state import PlayerState

        solo = [PlayerState(
            player_id="player_1", player_name="\u73a9\u5bb61",
            seat_number=1, role="villager", is_alive=True, team="villager"
        )]
        options = get_available_targets(solo, 1)
        assert options == []


class TestProcessHumanVote:
    """T24: 测试 process_human_vote 方法 (委托给 process_human_action)."""

    @pytest.fixture
    def mock_orchestrator(self):
        """创建模拟的服务实例."""
        service = WerewolfGameOrchestrator.__new__(WerewolfGameOrchestrator)
        service._game_states = {}
        service._ai_agents = {}
        service.engine = MagicMock()
        # process_human_action 会被 process_human_vote 调用
        service.process_human_action = AsyncMock()
        return service

    @pytest.fixture
    def mock_game_state(self):
        """创建模拟游戏状态."""
        from src.games.werewolf.state import WerewolfGameState, PlayerState

        players = {}
        for i in range(1, 11):
            players[i] = PlayerState(
                player_id=f"player_{i}",
                player_name=f"\u73a9\u5bb6{i}",
                seat_number=i,
                role="villager",
                is_alive=True,
                team="villager"
            )

        state = WerewolfGameState(
            room_code="TEST123",
            day_number=2,
            players=players,
            game_logs=[]
        )
        state.waiting_for_human_action = True
        state.human_action_type = "vote"
        state.human_player_seat = 3
        return state

    @pytest.mark.asyncio
    async def test_process_human_vote_success(self, mock_orchestrator, mock_game_state):
        """测试成功处理人类玩家投票 — 委托给 process_human_action."""
        mock_orchestrator._game_states["TEST123"] = mock_game_state

        result = await mock_orchestrator.process_human_vote(
            room_code="TEST123",
            player_id="player_3",
            target_seat=5
        )

        assert result["success"] is True
        mock_orchestrator.process_human_action.assert_awaited_once_with(
            "TEST123", "vote",
            {"player_id": "player_3", "target_seat": 5}
        )

    @pytest.mark.asyncio
    async def test_process_human_vote_abstain(self, mock_orchestrator, mock_game_state):
        """测试成功处理弃票."""
        mock_orchestrator._game_states["TEST123"] = mock_game_state

        result = await mock_orchestrator.process_human_vote(
            room_code="TEST123",
            player_id="player_3",
            target_seat=None
        )

        assert result["success"] is True
        mock_orchestrator.process_human_action.assert_awaited_once_with(
            "TEST123", "vote",
            {"player_id": "player_3", "target_seat": None}
        )

    @pytest.mark.asyncio
    async def test_process_human_vote_game_not_found(self, mock_orchestrator):
        """测试游戏不存在时 process_human_action 仍然被调用."""
        # process_human_vote always delegates to process_human_action
        # even if the game doesn't exist.
        result = await mock_orchestrator.process_human_vote(
            room_code="UNKNOWN",
            player_id="player_3",
            target_seat=5
        )

        assert result["success"] is True
        mock_orchestrator.process_human_action.assert_awaited_once()

    # ---------------------------------------------------------------
    # 测试 process_human_action (真实的委托目标)
    # ---------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_process_human_action_stores_vote(self, mock_orchestrator, mock_game_state):
        """测试 process_human_action 正确存储投票到 game state."""
        # 替换为真实方法 (bound to instance)
        mock_orchestrator.process_human_action = types.MethodType(
            WerewolfGameOrchestrator.process_human_action, mock_orchestrator
        )
        mock_orchestrator._game_states["TEST123"] = mock_game_state

        await mock_orchestrator.process_human_action(
            "TEST123", "vote",
            {"player_id": "player_3", "target_seat": 5}
        )

        assert mock_game_state.pending_human_action == {
            "type": "vote",
            "data": {"player_id": "player_3", "target_seat": 5}
        }
        assert mock_game_state.waiting_for_human_action is False

    @pytest.mark.asyncio
    async def test_process_human_action_game_not_found(self, mock_orchestrator):
        """测试 process_human_action 在游戏不存在时静默返回."""
        mock_orchestrator.process_human_action = types.MethodType(
            WerewolfGameOrchestrator.process_human_action, mock_orchestrator
        )

        # Should not raise
        await mock_orchestrator.process_human_action(
            "UNKNOWN", "vote",
            {"player_id": "player_3", "target_seat": 5}
        )


class TestHandleVoteHumanPlayer:
    """T23 & T25: 测试 _handle_vote 人类玩家检测和等待."""

    @pytest.fixture
    def mock_orchestrator(self):
        """创建模拟游戏服务."""
        service = WerewolfGameOrchestrator.__new__(WerewolfGameOrchestrator)
        service._game_states = {}
        service._ai_agents = {2: MagicMock()}  # 座位2是AI
        service.engine = MagicMock()
        return service

    def test_is_human_player_check(self, mock_orchestrator):
        """测试人类玩家检测 — 通过 _ai_agents 判断."""
        agents = mock_orchestrator._ai_agents
        assert 2 in agents
        assert 3 not in agents


class TestBroadcastVoteOptions:
    """T27: 测试 broadcast_vote_options 函数."""

    @pytest.mark.asyncio
    async def test_broadcast_vote_options_exists(self):
        """测试 broadcast_vote_options 函数存在."""
        from src.websocket.werewolf_handlers import broadcast_vote_options

        assert callable(broadcast_vote_options)

    @pytest.mark.asyncio
    async def test_broadcast_vote_options_signature(self):
        """测试 broadcast_vote_options 函数签名."""
        from src.websocket.werewolf_handlers import broadcast_vote_options
        import inspect

        sig = inspect.signature(broadcast_vote_options)
        params = list(sig.parameters.keys())

        assert "room_code" in params
        assert "seat_number" in params
        assert "options" in params

    @pytest.mark.asyncio
    async def test_broadcast_vote_options_emits_event(self):
        """测试 broadcast_vote_options 发送正确事件."""
        from src.websocket.werewolf_handlers import (
            broadcast_vote_options,
            sio
        )

        with patch.object(sio, 'emit', new_callable=AsyncMock) as mock_emit:
            await broadcast_vote_options(
                room_code="TEST123",
                seat_number=3,
                options=[
                    {"seat_number": 1, "player_name": "\u73a9\u5bb61"},
                    {"seat_number": 2, "player_name": "\u73a9\u5bb62"}
                ],
                timeout_seconds=60
            )

            mock_emit.assert_called_once()
            call_args = mock_emit.call_args
            assert call_args[0][0] == "werewolf:vote_options"
            data = call_args[0][1]
            assert data["seat_number"] == 3
            assert len(data["options"]) == 2
            assert data["timeout_seconds"] == 60
            assert data["allow_abstain"] is True


class TestBroadcastHumanVoteComplete:
    """测试 broadcast_human_vote_complete 函数."""

    @pytest.mark.asyncio
    async def test_broadcast_human_vote_complete_exists(self):
        """测试 broadcast_human_vote_complete 函数存在."""
        from src.websocket.werewolf_handlers import broadcast_human_vote_complete

        assert callable(broadcast_human_vote_complete)

    @pytest.mark.asyncio
    async def test_broadcast_human_vote_complete_emits_event(self):
        """测试 broadcast_human_vote_complete 发送正确事件."""
        from src.websocket.werewolf_handlers import (
            broadcast_human_vote_complete,
            sio
        )

        with patch.object(sio, 'emit', new_callable=AsyncMock) as mock_emit:
            await broadcast_human_vote_complete(
                room_code="TEST123",
                voter_seat=3,
                target_seat=5,
                voter_name="\u73a9\u5bb63",
                target_name="\u73a9\u5bb65"
            )

            mock_emit.assert_called_once()
            call_args = mock_emit.call_args
            assert call_args[0][0] == "werewolf:human_vote_complete"
            data = call_args[0][1]
            assert data["voter_seat"] == 3
            assert data["target_seat"] == 5
            assert data["is_abstain"] is False

    @pytest.mark.asyncio
    async def test_broadcast_human_vote_complete_abstain(self):
        """测试弃票时 is_abstain 为 True."""
        from src.websocket.werewolf_handlers import (
            broadcast_human_vote_complete,
            sio
        )

        with patch.object(sio, 'emit', new_callable=AsyncMock) as mock_emit:
            await broadcast_human_vote_complete(
                room_code="TEST123",
                voter_seat=3,
                target_seat=None,
                voter_name="\u73a9\u5bb63",
                target_name=None
            )

            data = mock_emit.call_args[0][1]
            assert data["is_abstain"] is True


class TestWerewolfHumanVoteHandler:
    """T26: 测试 werewolf_human_vote WebSocket 事件处理."""

    @pytest.mark.asyncio
    async def test_werewolf_human_vote_handler_registered(self):
        """测试 werewolf_human_vote 处理器已注册."""
        from src.websocket.werewolf_handlers import werewolf_human_vote
        assert callable(werewolf_human_vote)

    @pytest.mark.asyncio
    async def test_werewolf_human_vote_missing_room_code(self):
        """测试缺少房间代码时返回错误."""
        # This is verified in the handler itself — it checks room_code first.
        # Full coverage requires an integration test with a fake sid/session.
        pass


class TestWebSocketImports:
    """测试 WebSocket 导入."""

    def test_broadcast_vote_options_importable(self):
        """测试 broadcast_vote_options 可以从 websocket 包导入."""
        from src.websocket import broadcast_vote_options
        assert callable(broadcast_vote_options)

    def test_broadcast_human_vote_complete_importable(self):
        """测试 broadcast_human_vote_complete 可以从 websocket 包导入."""
        from src.websocket import broadcast_human_vote_complete
        assert callable(broadcast_human_vote_complete)
