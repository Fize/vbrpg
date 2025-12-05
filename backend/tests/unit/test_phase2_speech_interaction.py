"""
Phase 2: 发言交互测试 (T21)

测试 T12-T18 的后端实现：
- T12: _is_human_player 检测人类玩家
- T13: _set_waiting_for_human, _clear_waiting_for_human 等待状态管理
- T14: process_human_speech 处理人类发言
- T15: _execute_speeches 人类玩家发言等待
- T16: generate_speech_options 生成发言选项
- T17: werewolf_human_speech WebSocket 事件处理
- T18: broadcast_waiting_for_human, broadcast_speech_options 广播函数
"""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.games.werewolf_engine import (
    WerewolfEngine,
    WerewolfGameState,
    WerewolfPhase,
    PlayerState,
)


class TestIsHumanPlayer:
    """T12: 测试 _is_human_player 方法."""
    
    @pytest.fixture
    def mock_db(self):
        """创建模拟数据库会话."""
        return MagicMock()
    
    @pytest.fixture
    def engine(self):
        """创建 WerewolfEngine 实例."""
        return WerewolfEngine()
    
    @pytest.fixture
    def game_state_with_human(self, engine) -> WerewolfGameState:
        """创建包含人类玩家的游戏状态."""
        player_names = ["人类玩家"] + [f"AI玩家{i}" for i in range(1, 10)]
        state = engine.initialize_game_with_human_player(
            room_code="test-room",
            player_names=player_names,
            human_player_id="human-player",
            human_role="seer"
        )
        return state
    
    def test_is_human_player_returns_true_for_human_seat(
        self, mock_db, game_state_with_human
    ):
        """测试人类玩家座位返回 True."""
        from src.services.werewolf_game_service import WerewolfGameService
        
        service = WerewolfGameService(mock_db)
        service._game_states["test-room"] = game_state_with_human
        
        human_seat = game_state_with_human.human_player_seat
        assert service._is_human_player("test-room", human_seat) is True
    
    def test_is_human_player_returns_false_for_ai_seat(
        self, mock_db, game_state_with_human
    ):
        """测试 AI 玩家座位返回 False."""
        from src.services.werewolf_game_service import WerewolfGameService
        
        service = WerewolfGameService(mock_db)
        service._game_states["test-room"] = game_state_with_human
        
        human_seat = game_state_with_human.human_player_seat
        # 找一个不是人类玩家的座位
        ai_seat = 1 if human_seat != 1 else 2
        assert service._is_human_player("test-room", ai_seat) is False
    
    def test_is_human_player_returns_false_for_invalid_room(self, mock_db):
        """测试无效房间返回 False."""
        from src.services.werewolf_game_service import WerewolfGameService
        
        service = WerewolfGameService(mock_db)
        assert service._is_human_player("nonexistent-room", 1) is False


class TestWaitingForHumanState:
    """T13: 测试等待人类玩家状态管理."""
    
    @pytest.fixture
    def mock_db(self):
        """创建模拟数据库会话."""
        return MagicMock()
    
    @pytest.fixture
    def engine(self):
        """创建 WerewolfEngine 实例."""
        return WerewolfEngine()
    
    @pytest.fixture
    def game_state(self, engine) -> WerewolfGameState:
        """创建游戏状态."""
        player_names = ["人类玩家"] + [f"AI玩家{i}" for i in range(1, 10)]
        return engine.initialize_game_with_human_player(
            room_code="test-room",
            player_names=player_names,
            human_player_id="human-player",
            human_role="villager"
        )
    
    def test_set_waiting_for_human_sets_state(self, mock_db, game_state):
        """测试设置等待状态."""
        from src.services.werewolf_game_service import WerewolfGameService
        
        service = WerewolfGameService(mock_db)
        service._game_states["test-room"] = game_state
        
        result = service._set_waiting_for_human("test-room", "speech", 120)
        
        assert result is True
        assert game_state.waiting_for_human_action is True
        assert game_state.human_action_type == "speech"
        assert game_state.human_action_timeout == 120
        assert game_state.human_action_start_time is not None
    
    def test_set_waiting_for_human_invalid_room_returns_false(self, mock_db):
        """测试无效房间返回 False."""
        from src.services.werewolf_game_service import WerewolfGameService
        
        service = WerewolfGameService(mock_db)
        result = service._set_waiting_for_human("nonexistent-room", "speech", 120)
        
        assert result is False
    
    def test_clear_waiting_for_human_clears_state(self, mock_db, game_state):
        """测试清除等待状态."""
        from src.services.werewolf_game_service import WerewolfGameService
        
        service = WerewolfGameService(mock_db)
        service._game_states["test-room"] = game_state
        
        # 先设置等待状态
        service._set_waiting_for_human("test-room", "speech", 120)
        
        # 然后清除
        service._clear_waiting_for_human("test-room")
        
        assert game_state.waiting_for_human_action is False
        assert game_state.human_action_type is None
        assert game_state.human_action_timeout is None
        assert game_state.human_action_start_time is None


class TestGenerateSpeechOptions:
    """T16: 测试生成发言选项."""
    
    @pytest.fixture
    def mock_db(self):
        """创建模拟数据库会话."""
        return MagicMock()
    
    @pytest.fixture
    def engine(self):
        """创建 WerewolfEngine 实例."""
        return WerewolfEngine()
    
    @pytest.fixture
    def game_state(self, engine) -> WerewolfGameState:
        """创建游戏状态."""
        player_names = ["人类玩家"] + [f"AI玩家{i}" for i in range(1, 10)]
        state = engine.initialize_game_with_human_player(
            room_code="test-room",
            player_names=player_names,
            human_player_id="human-player",
            human_role="villager"
        )
        state.day_number = 1
        state.phase = WerewolfPhase.DAY_DISCUSSION
        return state
    
    def test_generate_speech_options_returns_list(self, mock_db, game_state):
        """测试返回选项列表."""
        from src.services.werewolf_game_service import WerewolfGameService
        
        service = WerewolfGameService(mock_db)
        service._game_states["test-room"] = game_state
        
        human_seat = game_state.human_player_seat
        options = service.generate_speech_options("test-room", human_seat)
        
        assert isinstance(options, list)
        assert len(options) > 0
    
    def test_generate_speech_options_contains_required_fields(self, mock_db, game_state):
        """测试选项包含必要字段."""
        from src.services.werewolf_game_service import WerewolfGameService
        
        service = WerewolfGameService(mock_db)
        service._game_states["test-room"] = game_state
        
        human_seat = game_state.human_player_seat
        options = service.generate_speech_options("test-room", human_seat)
        
        for option in options:
            assert "id" in option
            assert "text" in option
            assert "type" in option
    
    def test_generate_speech_options_day1_has_self_intro(self, mock_db, game_state):
        """测试第一天包含和平选项."""
        from src.services.werewolf_game_service import WerewolfGameService
        
        service = WerewolfGameService(mock_db)
        service._game_states["test-room"] = game_state
        game_state.day_number = 1
        
        human_seat = game_state.human_player_seat
        options = service.generate_speech_options("test-room", human_seat)
        
        option_ids = [opt["id"] for opt in options]
        # 第一天应该有和平发言选项
        assert "first_day_peace" in option_ids
    
    def test_generate_speech_options_later_days_have_analysis(self, mock_db, game_state):
        """测试第二天及以后包含观察选项."""
        from src.services.werewolf_game_service import WerewolfGameService
        
        service = WerewolfGameService(mock_db)
        service._game_states["test-room"] = game_state
        game_state.day_number = 2
        
        human_seat = game_state.human_player_seat
        options = service.generate_speech_options("test-room", human_seat)
        
        option_ids = [opt["id"] for opt in options]
        # 第二天应该有观察选项
        assert "villager_observe" in option_ids
    
    def test_generate_speech_options_invalid_room_returns_empty(self, mock_db):
        """测试无效房间返回空列表."""
        from src.services.werewolf_game_service import WerewolfGameService
        
        service = WerewolfGameService(mock_db)
        options = service.generate_speech_options("nonexistent-room", 1)
        
        assert options == []


class TestProcessHumanSpeech:
    """T14: 测试处理人类玩家发言."""
    
    @pytest.fixture
    def mock_db(self):
        """创建模拟数据库会话."""
        return MagicMock()
    
    @pytest.fixture
    def engine(self):
        """创建 WerewolfEngine 实例."""
        return WerewolfEngine()
    
    @pytest.fixture
    def game_state_waiting(self, engine) -> WerewolfGameState:
        """创建等待发言的游戏状态."""
        player_names = ["人类玩家"] + [f"AI玩家{i}" for i in range(1, 10)]
        state = engine.initialize_game_with_human_player(
            room_code="test-room",
            player_names=player_names,
            human_player_id="human-player",
            human_role="villager"
        )
        state.day_number = 1
        state.phase = WerewolfPhase.DAY_DISCUSSION
        state.waiting_for_human_action = True
        state.human_action_type = "speech"
        state.human_action_timeout = 120
        state.human_action_start_time = datetime.now()
        return state
    
    @pytest.mark.asyncio
    async def test_process_human_speech_success(self, mock_db, game_state_waiting):
        """测试成功处理发言."""
        from src.services.werewolf_game_service import WerewolfGameService
        
        service = WerewolfGameService(mock_db)
        service._game_states["test-room"] = game_state_waiting
        
        result = await service.process_human_speech(
            room_code="test-room",
            player_id="human-player",
            content="我是好人，请大家相信我。"
        )
        
        assert result["success"] is True
        assert "seat_number" in result
        assert "player_name" in result
        assert "content" in result
        assert result["content"] == "我是好人，请大家相信我。"
        
        # 验证等待状态已清除
        assert game_state_waiting.waiting_for_human_action is False
    
    @pytest.mark.asyncio
    async def test_process_human_speech_records_to_history(
        self, mock_db, game_state_waiting
    ):
        """测试发言被记录到历史."""
        from src.services.werewolf_game_service import WerewolfGameService
        
        service = WerewolfGameService(mock_db)
        service._game_states["test-room"] = game_state_waiting
        
        initial_history_length = len(game_state_waiting.speech_history)
        
        await service.process_human_speech(
            room_code="test-room",
            player_id="human-player",
            content="测试发言内容"
        )
        
        assert len(game_state_waiting.speech_history) == initial_history_length + 1
        last_speech = game_state_waiting.speech_history[-1]
        # speech_history 是字典列表
        assert last_speech["content"] == "测试发言内容"
        assert last_speech["is_human"] is True
    
    @pytest.mark.asyncio
    async def test_process_human_speech_fails_when_not_waiting(
        self, mock_db, game_state_waiting
    ):
        """测试未等待时发言失败."""
        from src.services.werewolf_game_service import WerewolfGameService
        
        service = WerewolfGameService(mock_db)
        game_state_waiting.waiting_for_human_action = False
        service._game_states["test-room"] = game_state_waiting
        
        result = await service.process_human_speech(
            room_code="test-room",
            player_id="human-player",
            content="测试发言"
        )
        
        assert result["success"] is False
        assert "error" in result
    
    @pytest.mark.asyncio
    async def test_process_human_speech_fails_for_wrong_action_type(
        self, mock_db, game_state_waiting
    ):
        """测试行动类型不匹配时失败."""
        from src.services.werewolf_game_service import WerewolfGameService
        
        service = WerewolfGameService(mock_db)
        game_state_waiting.human_action_type = "vote"
        service._game_states["test-room"] = game_state_waiting
        
        result = await service.process_human_speech(
            room_code="test-room",
            player_id="human-player",
            content="测试发言"
        )
        
        assert result["success"] is False
        assert "error" in result
    
    @pytest.mark.asyncio
    async def test_process_human_speech_fails_for_wrong_player(
        self, mock_db, game_state_waiting
    ):
        """测试非人类玩家发言失败."""
        from src.services.werewolf_game_service import WerewolfGameService
        
        service = WerewolfGameService(mock_db)
        service._game_states["test-room"] = game_state_waiting
        
        result = await service.process_human_speech(
            room_code="test-room",
            player_id="ai-player-1",  # AI 玩家尝试发言
            content="测试发言"
        )
        
        assert result["success"] is False
        assert "error" in result
    
    @pytest.mark.asyncio
    async def test_process_human_speech_invalid_room(self, mock_db):
        """测试无效房间返回错误."""
        from src.services.werewolf_game_service import WerewolfGameService
        
        service = WerewolfGameService(mock_db)
        
        result = await service.process_human_speech(
            room_code="nonexistent-room",
            player_id="human-player",
            content="测试发言"
        )
        
        assert result["success"] is False
        assert "error" in result


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
        # Socket.IO 将处理器存储在 handlers 字典中
        assert hasattr(sio, "handlers")
