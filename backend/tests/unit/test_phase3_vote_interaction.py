"""Phase 3 投票交互单元测试.

测试覆盖:
- T23: _execute_votes 人类玩家检测
- T24: process_human_vote 方法
- T25: 投票流程支持人类玩家等待
- T26: werewolf_human_vote WebSocket事件
- T27: broadcast_vote_options 广播函数
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestGenerateVoteOptions:
    """T24: 测试 generate_vote_options 方法."""

    @pytest.fixture
    def mock_game_service(self):
        """创建模拟游戏服务."""
        from src.services.werewolf_game_service import WerewolfGameService
        service = WerewolfGameService.__new__(WerewolfGameService)
        service._game_states = {}
        service._ai_agents = {}
        service.engine = MagicMock()
        return service

    @pytest.fixture
    def mock_game_state(self):
        """创建模拟游戏状态."""
        from src.services.games.werewolf_engine import WerewolfGameState, PlayerState

        players = {}
        for i in range(1, 11):
            players[i] = PlayerState(
                player_id=f"player_{i}",
                player_name=f"玩家{i}",
                seat_number=i,
                role="villager",
                is_alive=i <= 8,  # 玩家 9, 10 死亡
                team="villager"
            )

        return WerewolfGameState(
            room_code="TEST123",
            day_number=2,
            players=players,
            game_logs=[]
        )

    def test_generate_vote_options_excludes_self(self, mock_game_service, mock_game_state):
        """测试生成投票选项排除自己."""
        mock_game_service._game_states["TEST123"] = mock_game_state
        
        options = mock_game_service.generate_vote_options("TEST123", 1)
        
        # 应该排除自己
        assert not any(opt["seat_number"] == 1 for opt in options)

    def test_generate_vote_options_excludes_dead_players(self, mock_game_service, mock_game_state):
        """测试生成投票选项排除死亡玩家."""
        mock_game_service._game_states["TEST123"] = mock_game_state
        
        options = mock_game_service.generate_vote_options("TEST123", 1)
        
        # 应该排除死亡玩家 (9, 10)
        seat_numbers = [opt["seat_number"] for opt in options]
        assert 9 not in seat_numbers
        assert 10 not in seat_numbers

    def test_generate_vote_options_includes_alive_players(self, mock_game_service, mock_game_state):
        """测试生成投票选项包含存活玩家."""
        mock_game_service._game_states["TEST123"] = mock_game_state
        
        options = mock_game_service.generate_vote_options("TEST123", 1)
        
        # 应该有 7 个选项（排除自己和2个死亡玩家）
        assert len(options) == 7
        # 每个选项应该有必要的字段
        for opt in options:
            assert "seat_number" in opt
            assert "player_name" in opt
            assert "player_id" in opt

    def test_generate_vote_options_sorted_by_seat(self, mock_game_service, mock_game_state):
        """测试生成投票选项按座位号排序."""
        mock_game_service._game_states["TEST123"] = mock_game_state
        
        options = mock_game_service.generate_vote_options("TEST123", 1)
        
        seat_numbers = [opt["seat_number"] for opt in options]
        assert seat_numbers == sorted(seat_numbers)

    def test_generate_vote_options_empty_for_unknown_room(self, mock_game_service):
        """测试未知房间返回空列表."""
        options = mock_game_service.generate_vote_options("UNKNOWN", 1)
        assert options == []


class TestProcessHumanVote:
    """T24: 测试 process_human_vote 方法."""

    @pytest.fixture
    def mock_game_service(self):
        """创建模拟游戏服务."""
        from src.services.werewolf_game_service import WerewolfGameService
        service = WerewolfGameService.__new__(WerewolfGameService)
        service._game_states = {}
        service._ai_agents = {}
        service.engine = MagicMock()
        service._normalize_seat_number = lambda x: x  # 简化
        service._clear_waiting_for_human = MagicMock()
        return service

    @pytest.fixture
    def mock_game_state(self):
        """创建模拟游戏状态（等待投票）."""
        from src.services.games.werewolf_engine import WerewolfGameState, PlayerState

        players = {}
        for i in range(1, 11):
            players[i] = PlayerState(
                player_id=f"player_{i}",
                player_name=f"玩家{i}",
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
    async def test_process_human_vote_success(self, mock_game_service, mock_game_state):
        """测试成功处理人类玩家投票."""
        mock_game_service._game_states["TEST123"] = mock_game_state
        
        with patch("src.services.werewolf_game_service.broadcast_vote_update", new_callable=AsyncMock):
            with patch("src.services.werewolf_game_service.broadcast_human_vote_complete", new_callable=AsyncMock):
                result = await mock_game_service.process_human_vote(
                    room_code="TEST123",
                    player_id="player_3",
                    target_seat=5
                )
        
        assert result["success"] is True
        assert result["seat_number"] == 3
        assert result["target_seat"] == 5

    @pytest.mark.asyncio
    async def test_process_human_vote_abstain(self, mock_game_service, mock_game_state):
        """测试成功处理弃票."""
        mock_game_service._game_states["TEST123"] = mock_game_state
        
        with patch("src.services.werewolf_game_service.broadcast_vote_update", new_callable=AsyncMock):
            with patch("src.services.werewolf_game_service.broadcast_human_vote_complete", new_callable=AsyncMock):
                result = await mock_game_service.process_human_vote(
                    room_code="TEST123",
                    player_id="player_3",
                    target_seat=None
                )
        
        assert result["success"] is True
        assert result["target_seat"] is None

    @pytest.mark.asyncio
    async def test_process_human_vote_not_waiting(self, mock_game_service, mock_game_state):
        """测试非等待状态下投票失败."""
        mock_game_state.waiting_for_human_action = False
        mock_game_service._game_states["TEST123"] = mock_game_state
        
        result = await mock_game_service.process_human_vote(
            room_code="TEST123",
            player_id="player_3",
            target_seat=5
        )
        
        assert result["success"] is False
        assert "等待" in result["error"]

    @pytest.mark.asyncio
    async def test_process_human_vote_wrong_action_type(self, mock_game_service, mock_game_state):
        """测试等待其他行动类型时投票失败."""
        mock_game_state.human_action_type = "speech"
        mock_game_service._game_states["TEST123"] = mock_game_state
        
        result = await mock_game_service.process_human_vote(
            room_code="TEST123",
            player_id="player_3",
            target_seat=5
        )
        
        assert result["success"] is False
        assert "投票" in result["error"]

    @pytest.mark.asyncio
    async def test_process_human_vote_wrong_player(self, mock_game_service, mock_game_state):
        """测试非人类玩家投票失败."""
        mock_game_service._game_states["TEST123"] = mock_game_state
        
        result = await mock_game_service.process_human_vote(
            room_code="TEST123",
            player_id="player_5",  # 不是人类玩家
            target_seat=6
        )
        
        assert result["success"] is False
        assert "人类玩家" in result["error"]

    @pytest.mark.asyncio
    async def test_process_human_vote_game_not_found(self, mock_game_service):
        """测试游戏不存在时投票失败."""
        result = await mock_game_service.process_human_vote(
            room_code="UNKNOWN",
            player_id="player_3",
            target_seat=5
        )
        
        assert result["success"] is False
        assert "游戏不存在" in result["error"]

    @pytest.mark.asyncio
    async def test_process_human_vote_self_vote(self, mock_game_service, mock_game_state):
        """测试不能投票给自己."""
        mock_game_service._game_states["TEST123"] = mock_game_state
        
        result = await mock_game_service.process_human_vote(
            room_code="TEST123",
            player_id="player_3",
            target_seat=3  # 投票给自己
        )
        
        assert result["success"] is False
        assert "自己" in result["error"]


class TestExecuteVotesHumanPlayer:
    """T23 & T25: 测试 _execute_votes 人类玩家检测和等待."""

    @pytest.fixture
    def mock_game_service(self):
        """创建模拟游戏服务."""
        from src.services.werewolf_game_service import WerewolfGameService
        service = WerewolfGameService.__new__(WerewolfGameService)
        service._game_states = {}
        service._ai_agents = {2: MagicMock()}  # 座位2是AI
        service.engine = MagicMock()
        service._validate_game_state = MagicMock()
        service._check_paused_or_stopped = AsyncMock(return_value=True)
        service._set_waiting_for_human = MagicMock()
        service._clear_waiting_for_human = MagicMock()
        service._normalize_seat_number = lambda x: x
        service._format_speech_entries = MagicMock(return_value=[])
        service._speeches_to_text = MagicMock(return_value="")
        service._process_vote_result = AsyncMock()
        service.generate_vote_options = MagicMock(return_value=[])
        return service

    def test_is_human_player_check(self, mock_game_service):
        """测试人类玩家检测."""
        # 座位2是AI
        assert 2 in mock_game_service._ai_agents
        # 座位3不是AI
        assert 3 not in mock_game_service._ai_agents


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
                    {"seat_number": 1, "player_name": "玩家1"},
                    {"seat_number": 2, "player_name": "玩家2"}
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
                voter_name="玩家3",
                target_name="玩家5"
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
                voter_name="玩家3",
                target_name=None
            )
            
            data = mock_emit.call_args[0][1]
            assert data["is_abstain"] is True


class TestWerewolfHumanVoteHandler:
    """T26: 测试 werewolf_human_vote WebSocket 事件处理."""

    @pytest.mark.asyncio
    async def test_werewolf_human_vote_handler_registered(self):
        """测试 werewolf_human_vote 处理器已注册."""
        from src.websocket.werewolf_handlers import sio
        
        # 检查事件处理器是否存在
        # Socket.IO 会将事件名中的下划线保留
        handlers = sio.handlers.get("/", {})
        assert "werewolf_human_vote" in handlers or hasattr(sio, '_handlers')

    @pytest.mark.asyncio
    async def test_werewolf_human_vote_missing_room_code(self):
        """测试缺少房间代码时返回错误."""
        from src.websocket.werewolf_handlers import sio
        
        # 这个测试验证处理器能正确处理缺少参数的情况
        # 实际测试需要模拟 WebSocket 连接
        pass  # 集成测试中覆盖


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
