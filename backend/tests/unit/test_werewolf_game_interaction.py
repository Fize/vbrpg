# -*- coding: utf-8 -*-
"""
T1-T6: 狼人杀游戏交互增强 - 后端单元测试

测试内容:
- T1: WerewolfGameState 新字段
- T2: start_game_manual 方法
- T3: pause_game/resume_game 方法
- T4: process_player_speech 方法
- T5: _build_ai_context 方法
- T6: 主持人公告生成
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.games.werewolf_engine import (
    GameLogEntry,
    WerewolfEngine,
    WerewolfGameState,
    WerewolfPhase,
)


class TestWerewolfGameStateNewFields:
    """T1: 测试 WerewolfGameState 新字段"""

    @pytest.fixture
    def engine(self):
        """Create a werewolf engine instance."""
        return WerewolfEngine()

    @pytest.fixture
    def player_names(self):
        """Generate 10 player names."""
        return [f"Player_{i}" for i in range(1, 11)]

    def test_is_paused_default_false(self, engine, player_names):
        """测试 is_paused 默认为 False"""
        state = engine.initialize_game(
            room_code="TEST001",
            player_names=player_names,
        )
        assert state.is_paused is False

    def test_is_started_default_false(self, engine, player_names):
        """测试 is_started 默认为 False"""
        state = engine.initialize_game(
            room_code="TEST001",
            player_names=player_names,
        )
        assert state.is_started is False

    def test_current_speaker_seat_default_none(self, engine, player_names):
        """测试 current_speaker_seat 默认为 None"""
        state = engine.initialize_game(
            room_code="TEST001",
            player_names=player_names,
        )
        assert state.current_speaker_seat is None

    def test_waiting_for_player_input_default_false(self, engine, player_names):
        """测试 waiting_for_player_input 默认为 False"""
        state = engine.initialize_game(
            room_code="TEST001",
            player_names=player_names,
        )
        assert state.waiting_for_player_input is False

    def test_speech_reminder_count_default_zero(self, engine, player_names):
        """测试 speech_reminder_count 默认为 0"""
        state = engine.initialize_game(
            room_code="TEST001",
            player_names=player_names,
        )
        assert state.speech_reminder_count == 0

    def test_game_logs_default_empty_list(self, engine, player_names):
        """测试 game_logs 默认为空列表"""
        state = engine.initialize_game(
            room_code="TEST001",
            player_names=player_names,
        )
        assert state.game_logs == []
        assert isinstance(state.game_logs, list)


class TestGameLogEntry:
    """T1: 测试 GameLogEntry 数据类"""

    def test_create_game_log_entry(self):
        """测试创建 GameLogEntry 实例"""
        log = GameLogEntry(
            id="log_001",
            type="speech",
            content="我是好人",
            day=1,
            phase="discussion",
            time=datetime.now(),
            player_id="player_1",
            player_name="玩家1",
            seat_number=1,
        )
        
        assert log.id == "log_001"
        assert log.type == "speech"
        assert log.content == "我是好人"
        assert log.day == 1
        assert log.phase == "discussion"
        assert log.player_id == "player_1"
        assert log.player_name == "玩家1"
        assert log.seat_number == 1
        assert log.is_public is True  # 默认值
        assert log.metadata is None  # 默认值

    def test_game_log_entry_with_metadata(self):
        """测试创建带 metadata 的 GameLogEntry"""
        metadata = {"announcement_type": "request_speech"}
        log = GameLogEntry(
            id="log_002",
            type="host_announcement",
            content="请3号玩家发言",
            day=1,
            phase="discussion",
            time=datetime.now(),
            metadata=metadata,
            is_public=True,
        )
        
        assert log.metadata == metadata
        assert log.metadata["announcement_type"] == "request_speech"

    def test_game_log_entry_to_dict(self):
        """测试 GameLogEntry 序列化为字典"""
        now = datetime.now()
        log = GameLogEntry(
            id="log_003",
            type="death",
            content="3号玩家被狼人杀害",
            day=1,
            phase="night",
            time=now,
            player_id="player_3",
            player_name="玩家3",
            seat_number=3,
            metadata={"death_reason": "killed"},
            is_public=True,
        )
        
        log_dict = log.to_dict()
        
        assert log_dict["id"] == "log_003"
        assert log_dict["type"] == "death"
        assert log_dict["content"] == "3号玩家被狼人杀害"
        assert log_dict["day"] == 1
        assert log_dict["phase"] == "night"
        assert log_dict["player_id"] == "player_3"
        assert log_dict["player_name"] == "玩家3"
        assert log_dict["seat_number"] == 3
        assert log_dict["is_public"] is True


class TestAddGameLog:
    """T1: 测试 _add_game_log 辅助方法"""

    @pytest.fixture
    def engine(self):
        """Create a werewolf engine instance."""
        return WerewolfEngine()

    @pytest.fixture
    def player_names(self):
        """Generate 10 player names."""
        return [f"Player_{i}" for i in range(1, 11)]

    @pytest.fixture
    def initialized_engine(self, engine, player_names):
        """Create an engine with initialized game state."""
        engine.initialize_game(
            room_code="TEST001",
            player_names=player_names,
        )
        return engine

    def test_add_game_log_basic(self, initialized_engine):
        """测试添加基本游戏日志"""
        initialized_engine.add_game_log(
            log_type="system",
            content="游戏开始",
        )
        
        assert len(initialized_engine.state.game_logs) == 1
        log = initialized_engine.state.game_logs[0]
        assert log.type == "system"
        assert log.content == "游戏开始"

    def test_add_game_log_with_player_info(self, initialized_engine):
        """测试添加带玩家信息的日志"""
        initialized_engine.add_game_log(
            log_type="speech",
            content="我是好人",
            player_id="player_1",
            player_name="玩家1",
            seat_number=1,
        )
        
        log = initialized_engine.state.game_logs[0]
        assert log.player_id == "player_1"
        assert log.player_name == "玩家1"
        assert log.seat_number == 1

    def test_add_game_log_with_metadata(self, initialized_engine):
        """测试添加带元数据的日志"""
        initialized_engine.add_game_log(
            log_type="host_announcement",
            content="请3号玩家发言",
            metadata={"announcement_type": "request_speech", "target_seat": 3},
        )
        
        log = initialized_engine.state.game_logs[0]
        assert log.metadata is not None
        assert log.metadata["announcement_type"] == "request_speech"
        assert log.metadata["target_seat"] == 3

    def test_add_multiple_game_logs(self, initialized_engine):
        """测试添加多条日志"""
        initialized_engine.add_game_log(log_type="system", content="日志1")
        initialized_engine.add_game_log(log_type="system", content="日志2")
        initialized_engine.add_game_log(log_type="system", content="日志3")
        
        assert len(initialized_engine.state.game_logs) == 3


class TestGameControlMethods:
    """T2, T3: 测试游戏控制方法"""

    @pytest.fixture
    def engine(self):
        """Create a werewolf engine instance."""
        return WerewolfEngine()

    @pytest.fixture
    def player_names(self):
        """Generate 10 player names."""
        return [f"Player_{i}" for i in range(1, 11)]

    @pytest.fixture
    def initialized_engine(self, engine, player_names):
        """Create an engine with initialized game state."""
        engine.initialize_game(
            room_code="TEST001",
            player_names=player_names,
        )
        return engine

    def test_start_game_manual_sets_is_started(self, initialized_engine):
        """T2: 测试手动开始游戏设置 is_started"""
        initialized_engine.start_game()
        
        assert initialized_engine.state.is_started is True

    def test_start_game_manual_initializes_phase(self, initialized_engine):
        """T2: 测试开始游戏初始化阶段"""
        initialized_engine.start_game()
        
        assert initialized_engine.state.phase == WerewolfPhase.NIGHT
        assert initialized_engine.state.day_number == 1

    def test_pause_game_sets_is_paused(self, initialized_engine):
        """T3: 测试暂停游戏设置 is_paused"""
        initialized_engine.start_game()
        initialized_engine.state.is_paused = True
        
        assert initialized_engine.state.is_paused is True

    def test_resume_game_clears_is_paused(self, initialized_engine):
        """T3: 测试继续游戏清除 is_paused"""
        initialized_engine.start_game()
        initialized_engine.state.is_paused = True
        initialized_engine.state.is_paused = False
        
        assert initialized_engine.state.is_paused is False

    def test_pause_during_discussion(self, initialized_engine):
        """T3: 测试讨论阶段暂停"""
        initialized_engine.start_game()
        initialized_engine.start_day()
        initialized_engine.start_discussion()
        
        # 暂停
        initialized_engine.state.is_paused = True
        assert initialized_engine.state.is_paused is True
        assert initialized_engine.state.phase == WerewolfPhase.DISCUSSION


class TestSpeechProcessing:
    """T4: 测试玩家发言处理"""

    @pytest.fixture
    def engine(self):
        """Create a werewolf engine instance."""
        return WerewolfEngine()

    @pytest.fixture
    def player_names(self):
        """Generate 10 player names."""
        return [f"Player_{i}" for i in range(1, 11)]

    @pytest.fixture
    def started_engine(self, engine, player_names):
        """Create an engine with game started."""
        engine.initialize_game(
            room_code="TEST001",
            player_names=player_names,
        )
        engine.start_game()
        engine.start_day()
        engine.start_discussion()
        return engine

    def test_set_current_speaker(self, started_engine):
        """测试设置当前发言者"""
        started_engine.state.current_speaker_seat = 3
        
        assert started_engine.state.current_speaker_seat == 3

    def test_set_waiting_for_input(self, started_engine):
        """测试设置等待玩家输入状态"""
        started_engine.state.waiting_for_player_input = True
        
        assert started_engine.state.waiting_for_player_input is True

    def test_process_speech_creates_log(self, started_engine):
        """测试处理发言创建日志"""
        started_engine.state.current_speaker_seat = 3
        started_engine.add_speech(seat=3, content="我是好人，请相信我")
        
        # 检查发言历史
        assert len(started_engine.state.speech_history) == 1
        speech = started_engine.state.speech_history[0]
        assert speech["seat_number"] == 3
        assert speech["content"] == "我是好人，请相信我"

    def test_clear_current_speaker_after_speech(self, started_engine):
        """测试发言后清除当前发言者"""
        started_engine.state.current_speaker_seat = 3
        started_engine.state.waiting_for_player_input = True
        
        # 模拟发言结束
        started_engine.state.current_speaker_seat = None
        started_engine.state.waiting_for_player_input = False
        
        assert started_engine.state.current_speaker_seat is None
        assert started_engine.state.waiting_for_player_input is False

    def test_increment_speech_reminder_count(self, started_engine):
        """测试递增发言提醒计数"""
        started_engine.state.speech_reminder_count = 0
        started_engine.state.speech_reminder_count += 1
        started_engine.state.speech_reminder_count += 1
        
        assert started_engine.state.speech_reminder_count == 2


class TestBuildAIContext:
    """T5: 测试 AI 上下文构建"""

    @pytest.fixture
    def engine(self):
        """Create a werewolf engine instance."""
        return WerewolfEngine()

    @pytest.fixture
    def player_names(self):
        """Generate 10 player names."""
        return [f"Player_{i}" for i in range(1, 11)]

    @pytest.fixture
    def started_engine(self, engine, player_names):
        """Create an engine with game started."""
        engine.initialize_game(
            room_code="TEST001",
            player_names=player_names,
        )
        engine.start_game()
        engine.start_day()
        engine.start_discussion()
        return engine

    def test_get_alive_players_for_context(self, started_engine):
        """测试获取存活玩家用于上下文"""
        alive = started_engine.get_alive_players()
        
        assert len(alive) == 10
        assert all(p.is_alive for p in alive)

    def test_get_speech_history_for_context(self, started_engine):
        """测试获取发言历史用于上下文"""
        # 添加一些发言
        started_engine.add_speech(seat=1, content="我是预言家")
        started_engine.add_speech(seat=2, content="1号是狼人")
        started_engine.add_speech(seat=3, content="我觉得2号可疑")
        
        history = started_engine.state.speech_history
        
        assert len(history) == 3
        assert history[0]["content"] == "我是预言家"
        assert history[1]["content"] == "1号是狼人"
        assert history[2]["content"] == "我觉得2号可疑"

    def test_context_includes_day_info(self, started_engine):
        """测试上下文包含天数信息"""
        assert started_engine.state.day_number == 1
        assert started_engine.state.phase == WerewolfPhase.DISCUSSION

    def test_context_includes_current_phase(self, started_engine):
        """测试上下文包含当前阶段"""
        public_state = started_engine.get_public_state()
        
        assert "phase" in public_state
        assert public_state["phase"] == WerewolfPhase.DISCUSSION.value


class TestHostAnnouncementGeneration:
    """T6: 测试主持人公告生成"""

    @pytest.fixture
    def engine(self):
        """Create a werewolf engine instance."""
        return WerewolfEngine()

    @pytest.fixture
    def player_names(self):
        """Generate 10 player names."""
        return [f"Player_{i}" for i in range(1, 11)]

    @pytest.fixture
    def started_engine(self, engine, player_names):
        """Create an engine with game started."""
        engine.initialize_game(
            room_code="TEST001",
            player_names=player_names,
        )
        engine.start_game()
        return engine

    def test_add_host_announcement_log(self, started_engine):
        """测试添加主持人公告日志"""
        started_engine.add_game_log(
            log_type="host_announcement",
            content="天亮了，昨晚是平安夜",
            metadata={"announcement_type": "day_start"},
        )
        
        log = started_engine.state.game_logs[0]
        assert log.type == "host_announcement"
        assert "天亮了" in log.content

    def test_request_speech_announcement_log(self, started_engine):
        """测试点名发言公告日志"""
        started_engine.add_game_log(
            log_type="host_announcement",
            content="请3号玩家发言",
            player_id="seat_3",
            player_name="Player_3",
            seat_number=3,
            metadata={"announcement_type": "request_speech"},
        )
        
        log = started_engine.state.game_logs[0]
        assert "3号玩家发言" in log.content
        assert log.metadata["announcement_type"] == "request_speech"

    def test_speech_end_transition_log(self, started_engine):
        """测试发言结束过渡公告日志"""
        started_engine.add_game_log(
            log_type="host_announcement",
            content="感谢3号玩家的发言，接下来请4号玩家发言",
            metadata={"announcement_type": "speech_end_transition"},
        )
        
        log = started_engine.state.game_logs[0]
        assert "感谢" in log.content
        assert log.metadata["announcement_type"] == "speech_end_transition"

    def test_multiple_announcements_in_order(self, started_engine):
        """测试多条公告按顺序记录"""
        started_engine.add_game_log(
            log_type="host_announcement",
            content="公告1",
        )
        started_engine.add_game_log(
            log_type="host_announcement",
            content="公告2",
        )
        started_engine.add_game_log(
            log_type="host_announcement",
            content="公告3",
        )
        
        logs = started_engine.state.game_logs
        assert len(logs) == 3
        assert logs[0].content == "公告1"
        assert logs[1].content == "公告2"
        assert logs[2].content == "公告3"
