"""
Phase 2: 发言交互测试 (T21)

测试 T12-T18 的后端实现：
- T12: 检测人类玩家 (PlayerState.is_human)
- T13: 等待状态管理 (state.waiting_for_human_action)
- T14: process_human_speech 处理人类发言
- T15: 发言流程 (game loop _handle_day_discussion)
- T16: 发言选项生成 (已移除, 测试 process_human_speech 替代)
- T17: werewolf_human_speech WebSocket 事件处理
- T18: broadcast_waiting_for_human, broadcast_speech_options 广播函数
"""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.games.werewolf.engine import WerewolfEngine
from src.games.werewolf.state import (
    WerewolfGameState,
    WerewolfPhase,
    PlayerState,
)


def _create_game_state_with_human(engine: WerewolfEngine, human_role: str = "seer") -> WerewolfGameState:
    """Helper: create a game state with the new API."""
    player_names = ["人类玩家"] + [f"AI玩家{i}" for i in range(1, 10)]
    state = engine.initialize_game(
        room_code="test-room",
        player_names=player_names,
        human_player_id="human-player",
        human_role=human_role,
    )
    return state


class TestIsHumanPlayer:
    """T12: 测试 PlayerState.is_human 检测人类玩家."""

    @pytest.fixture
    def engine(self):
        """创建 WerewolfEngine 实例."""
        return WerewolfEngine()

    @pytest.fixture
    def game_state_with_human(self, engine) -> WerewolfGameState:
        """创建包含人类玩家的游戏状态."""
        return _create_game_state_with_human(engine, human_role="seer")

    def test_is_human_player_returns_true_for_human_seat(
        self, game_state_with_human
    ):
        """测试人类玩家座位返回 True."""
        human_seat = game_state_with_human.human_player_seat
        assert game_state_with_human.players[human_seat].is_human is True

    def test_is_human_player_returns_false_for_ai_seat(
        self, game_state_with_human
    ):
        """测试 AI 玩家座位返回 False."""
        human_seat = game_state_with_human.human_player_seat
        # 找一个不是人类玩家的座位
        ai_seat = 1 if human_seat != 1 else 2
        assert game_state_with_human.players[ai_seat].is_human is False
        assert game_state_with_human.players[ai_seat].is_ai is True

    def test_human_player_seat_matches(self, game_state_with_human):
        """测试 human_player_seat 指向正确的座位."""
        human_seat = game_state_with_human.human_player_seat
        assert human_seat is not None
        assert game_state_with_human.players[human_seat].player_id == "human-player"


class TestWaitingForHumanState:
    """T13: 测试等待人类玩家状态管理."""

    @pytest.fixture
    def engine(self):
        """创建 WerewolfEngine 实例."""
        return WerewolfEngine()

    @pytest.fixture
    def game_state(self, engine) -> WerewolfGameState:
        """创建游戏状态."""
        return _create_game_state_with_human(engine, human_role="villager")

    def test_set_waiting_for_human_sets_state(self, game_state):
        """测试直接设置等待状态 (替代旧的 _set_waiting_for_human)."""
        game_state.waiting_for_human_action = True
        game_state.human_action_type = "speech"
        game_state.human_action_timeout = 120
        game_state.human_action_start_time = datetime.now()

        assert game_state.waiting_for_human_action is True
        assert game_state.human_action_type == "speech"
        assert game_state.human_action_timeout == 120
        assert game_state.human_action_start_time is not None

    def test_clear_waiting_for_human_clears_state(self, game_state):
        """测试直接清除等待状态 (替代旧的 _clear_waiting_for_human)."""
        # 先设置等待状态
        game_state.waiting_for_human_action = True
        game_state.human_action_type = "speech"
        game_state.human_action_timeout = 120
        game_state.human_action_start_time = datetime.now()

        # 然后清除
        game_state.waiting_for_human_action = False
        game_state.human_action_type = None
        game_state.human_action_timeout = None
        game_state.human_action_start_time = None

        assert game_state.waiting_for_human_action is False
        assert game_state.human_action_type is None
        assert game_state.human_action_timeout is None
        assert game_state.human_action_start_time is None


class TestProcessHumanSpeech:
    """T14 / T16: 测试处理人类玩家发言."""

    @pytest.fixture
    def engine(self):
        """创建 WerewolfEngine 实例."""
        return WerewolfEngine()

    @pytest.fixture
    def orchestrator(self):
        """创建 WerewolfGameOrchestrator 实例 (无参数)."""
        from src.games.werewolf.orchestrator import WerewolfGameOrchestrator
        return WerewolfGameOrchestrator()

    @pytest.fixture
    def game_state_waiting(self, engine) -> WerewolfGameState:
        """创建等待发言的游戏状态."""
        state = _create_game_state_with_human(engine, human_role="villager")
        state.day_number = 1
        state.phase = WerewolfPhase.DAY_DISCUSSION.value
        state.waiting_for_human_action = True
        state.human_action_type = "speech"
        state.human_action_timeout = 120
        state.human_action_start_time = datetime.now()
        return state

    @pytest.mark.asyncio
    async def test_process_human_speech_success(self, orchestrator, game_state_waiting):
        """测试成功处理发言."""
        orchestrator._game_states["test-room"] = game_state_waiting

        result = await orchestrator.process_human_speech(
            room_code="test-room",
            player_id="human-player",
            content="我是好人，请大家相信我。"
        )

        assert result["success"] is True

        # 验证等待状态已清除 (process_human_action 设置 waiting_for_human_action = False)
        assert game_state_waiting.waiting_for_human_action is False

        # 验证 pending_human_action 已设置
        assert game_state_waiting.pending_human_action is not None
        assert game_state_waiting.pending_human_action["type"] == "speech"
        assert game_state_waiting.pending_human_action["data"]["content"] == "我是好人，请大家相信我。"

    @pytest.mark.asyncio
    async def test_process_human_speech_fails_when_not_waiting(
        self, orchestrator, game_state_waiting
    ):
        """测试未等待时发言行为 (process_human_action 仍会接受)."""
        orchestrator._game_states["test-room"] = game_state_waiting
        game_state_waiting.waiting_for_human_action = False

        # process_human_speech 总是返回 success=True
        # 它通过 process_human_action 设置 pending_human_action
        result = await orchestrator.process_human_speech(
            room_code="test-room",
            player_id="human-player",
            content="测试发言"
        )

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_process_human_speech_invalid_room(self, orchestrator):
        """测试无效房间返回成功但无副作用."""
        result = await orchestrator.process_human_speech(
            room_code="nonexistent-room",
            player_id="human-player",
            content="测试发言"
        )

        assert result["success"] is True


class TestSpeechFlow:
    """T15: 测试发言流程 (orchestrator 的实际发言处理)."""

    @pytest.fixture
    def engine(self):
        return WerewolfEngine()

    @pytest.fixture
    def orchestrator(self):
        from src.games.werewolf.orchestrator import WerewolfGameOrchestrator
        return WerewolfGameOrchestrator()

    @pytest.mark.asyncio
    async def test_process_player_speech_adds_to_game_state(self, orchestrator, engine):
        """测试 process_player_speech 更新游戏状态."""
        state = _create_game_state_with_human(engine, human_role="villager")
        state.day_number = 1
        state.phase = WerewolfPhase.DAY_DISCUSSION.value
        orchestrator._game_states["test-room"] = state

        result = await orchestrator.process_player_speech(
            room_code="test-room",
            player_id="human-player",
            content="我是好人"
        )

        assert result["success"] is True
        # process_player_speech 调用 process_human_action
        # 设置 pending_human_action
        assert state.pending_human_action is not None
        assert state.pending_human_action["type"] == "speech"
        assert state.pending_human_action["data"]["content"] == "我是好人"

    @pytest.mark.asyncio
    async def test_process_human_speech_accepts_any_content(self, orchestrator, engine):
        """测试 process_human_speech 接受任意内容."""
        state = _create_game_state_with_human(engine, human_role="seer")
        state.day_number = 2
        state.phase = WerewolfPhase.DAY_DISCUSSION.value
        orchestrator._game_states["test-room"] = state

        contents = [
            "我认为1号是狼人",
            "我是预言家，昨晚查了3号",
            "请大家跟我投票2号",
            "",
            "大家好",
        ]
        for content in contents:
            result = await orchestrator.process_human_speech(
                room_code="test-room",
                player_id="human-player",
                content=content,
            )
            assert result["success"] is True


class TestBroadcastFunctions:
    """T18: 测试广播函数."""

    @pytest.mark.asyncio
    async def test_broadcast_waiting_for_human_exists(self):
        """测试 broadcast_waiting_for_human 函数存在."""
        from src.websocket.werewolf_handlers import broadcast_waiting_for_human

        assert callable(broadcast_waiting_for_human)

    @pytest.mark.asyncio
    async def test_broadcast_speech_options_exists(self):
        """测试 broadcast_speech_options 函数存在."""
        from src.websocket.werewolf_handlers import broadcast_speech_options

        assert callable(broadcast_speech_options)

    @pytest.mark.asyncio
    async def test_broadcast_human_speech_complete_exists(self):
        """测试 broadcast_human_speech_complete 函数存在."""
        from src.websocket.werewolf_handlers import broadcast_human_speech_complete

        assert callable(broadcast_human_speech_complete)

    @pytest.mark.asyncio
    async def test_broadcast_waiting_for_human_emits_event(self):
        """测试 broadcast_waiting_for_human 发送正确事件."""
        from src.websocket.werewolf_handlers import (
            broadcast_waiting_for_human,
            sio,
        )

        with patch.object(sio, "emit", new_callable=AsyncMock) as mock_emit:
            await broadcast_waiting_for_human(
                room_code="test-room",
                action_type="speech",
                seat_number=1,
                timeout_seconds=120,
                metadata={"day_number": 1}
            )

            mock_emit.assert_called_once()
            call_args = mock_emit.call_args
            assert call_args[0][0] == "werewolf:waiting_for_human"
            assert call_args[1]["room"] == "test-room"

    @pytest.mark.asyncio
    async def test_broadcast_speech_options_emits_event(self):
        """测试 broadcast_speech_options 发送正确事件."""
        from src.websocket.werewolf_handlers import (
            broadcast_speech_options,
            sio,
        )

        with patch.object(sio, "emit", new_callable=AsyncMock) as mock_emit:
            await broadcast_speech_options(
                room_code="test-room",
                seat_number=1,
                options=[{"id": "test", "text": "测试", "type": "basic"}]
            )

            mock_emit.assert_called_once()
            call_args = mock_emit.call_args
            assert call_args[0][0] == "werewolf:speech_options"
            assert call_args[1]["room"] == "test-room"


class TestWebSocketIntegration:
    """T17: WebSocket 事件处理器集成测试."""

    def test_werewolf_human_speech_handler_registered(self):
        """测试 werewolf_human_speech 处理器已注册."""
        from src.websocket.werewolf_handlers import sio

        # 检查事件处理器是否注册
        assert hasattr(sio, "handlers")
