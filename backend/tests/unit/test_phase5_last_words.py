"""
Phase 5: 遗言与观战模式测试

测试覆盖:
- T48: 遗言等待状态设置
- T49: process_human_last_words 方法
- T50: WebSocket 事件处理
- T53: 观战模式切换
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.services.werewolf_game_service import WerewolfGameService
from src.services.games.werewolf_engine import (
    WerewolfGameState,
    WerewolfPhase,
    PlayerState,
)


class TestLastWordsStateFields:
    """T48: 测试遗言相关状态字段"""
    
    def test_game_state_has_last_words_seat_field(self):
        """游戏状态应包含 last_words_seat 字段"""
        state = WerewolfGameState(room_code="TEST")
        assert hasattr(state, 'last_words_seat')
        assert state.last_words_seat is None
    
    def test_game_state_has_last_words_reason_field(self):
        """游戏状态应包含 last_words_reason 字段"""
        state = WerewolfGameState(room_code="TEST")
        assert hasattr(state, 'last_words_reason')
        assert state.last_words_reason is None
    
    def test_game_state_has_spectator_after_death_field(self):
        """游戏状态应包含 is_spectator_after_death 字段"""
        state = WerewolfGameState(room_code="TEST")
        assert hasattr(state, 'is_spectator_after_death')
        assert state.is_spectator_after_death is False


class TestLastWordsOptionsGeneration:
    """T48: 测试遗言选项生成"""
    
    @pytest.fixture
    def mock_db(self):
        """创建 mock 数据库会话"""
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        return db
    
    @pytest.fixture
    def game_service(self, mock_db):
        return WerewolfGameService(db=mock_db)
    
    @pytest.fixture
    def game_state_with_dead_player(self, game_service):
        """创建包含已死玩家的游戏状态"""
        state = WerewolfGameState(room_code="TEST")
        state.phase = WerewolfPhase.LAST_WORDS
        state.day_number = 2
        state.human_player_seat = 3
        
        # 创建玩家
        for i in range(1, 11):
            role = "werewolf" if i <= 3 else "villager"
            if i == 4:
                role = "seer"
            elif i == 5:
                role = "witch"
            elif i == 6:
                role = "hunter"
            
            state.players[i] = PlayerState(
                player_id=f"player_{i}",
                player_name=f"玩家{i}",
                seat_number=i,
                role=role,
                team="werewolf" if role == "werewolf" else "villager",
                is_alive=True,
                is_human=(i == 3)
            )
        
        # 设置玩家3死亡
        state.players[3].is_alive = False
        
        game_service._game_states["TEST"] = state
        return state
    
    def test_generate_last_words_options_villager(self, game_service, game_state_with_dead_player):
        """村民遗言应有村民特定选项"""
        game_state_with_dead_player.players[3].role = "villager"
        
        options = game_service._generate_last_words_options(
            game_state_with_dead_player, 3, "vote"
        )
        
        assert len(options) > 0
        option_ids = [opt["id"] for opt in options]
        assert "no_words" in option_ids  # 跳过选项
        assert "innocent_plea" in option_ids  # 村民特定
    
    def test_generate_last_words_options_werewolf(self, game_service, game_state_with_dead_player):
        """狼人遗言应有狼人特定选项"""
        game_state_with_dead_player.players[3].role = "werewolf"
        
        options = game_service._generate_last_words_options(
            game_state_with_dead_player, 3, "vote"
        )
        
        option_ids = [opt["id"] for opt in options]
        assert "protect_teammate" in option_ids  # 保护队友
        assert "fake_seer" in option_ids  # 假装预言家
    
    def test_generate_last_words_options_seer(self, game_service, game_state_with_dead_player):
        """预言家遗言应有预言家特定选项"""
        game_state_with_dead_player.players[3].role = "seer"
        
        options = game_service._generate_last_words_options(
            game_state_with_dead_player, 3, "night_kill"
        )
        
        option_ids = [opt["id"] for opt in options]
        assert "reveal_identity" in option_ids  # 表明身份
        assert "share_check_result" in option_ids  # 分享验人结果
    
    def test_generate_last_words_options_vote_death(self, game_service, game_state_with_dead_player):
        """投票死亡应有特定选项"""
        options = game_service._generate_last_words_options(
            game_state_with_dead_player, 3, "vote"
        )
        
        option_ids = [opt["id"] for opt in options]
        assert "wrongful_death" in option_ids
    
    def test_generate_last_words_options_night_kill(self, game_service, game_state_with_dead_player):
        """夜杀死亡应有分析选项"""
        options = game_service._generate_last_words_options(
            game_state_with_dead_player, 3, "night_kill"
        )
        
        option_ids = [opt["id"] for opt in options]
        assert "wolf_analysis" in option_ids


class TestProcessHumanLastWords:
    """T49: 测试 process_human_last_words 方法"""
    
    @pytest.fixture
    def mock_db(self):
        """创建 mock 数据库会话"""
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        return db
    
    @pytest.fixture
    def game_service(self, mock_db):
        return WerewolfGameService(db=mock_db)
    
    @pytest.fixture
    def game_state_waiting_for_last_words(self, game_service):
        """创建等待遗言的游戏状态"""
        state = WerewolfGameState(room_code="TEST")
        state.phase = WerewolfPhase.LAST_WORDS
        state.day_number = 2
        state.human_player_seat = 3
        state.waiting_for_human_action = True
        state.human_action_type = "last_words"
        state.last_words_seat = 3
        state.last_words_reason = "vote"
        
        # 创建玩家
        for i in range(1, 11):
            state.players[i] = PlayerState(
                player_id=f"player_{i}",
                player_name=f"玩家{i}",
                seat_number=i,
                role="villager",
                team="villager",
                is_alive=True,
                is_human=(i == 3)
            )
        
        # 玩家3死亡
        state.players[3].is_alive = False
        
        game_service._game_states["TEST"] = state
        return state
    
    @pytest.mark.asyncio
    async def test_process_last_words_success(self, game_service, game_state_waiting_for_last_words):
        """成功提交遗言"""
        with patch('src.services.werewolf_game_service.broadcast_player_speech', new_callable=AsyncMock), \
             patch('src.services.werewolf_game_service.broadcast_spectator_mode', new_callable=AsyncMock):
            result = await game_service.process_human_last_words(
                room_code="TEST",
                player_id="player_3",
                content="我是好人，你们投错了！"
            )
        
        assert result["success"] is True
        assert result["seat_number"] == 3
        assert result["content"] == "我是好人，你们投错了！"
    
    @pytest.mark.asyncio
    async def test_process_last_words_no_game(self, game_service):
        """游戏不存在时应返回错误"""
        result = await game_service.process_human_last_words(
            room_code="NONEXISTENT",
            player_id="player_1",
            content="遗言"
        )
        
        assert result["success"] is False
        assert "游戏不存在" in result["error"]
    
    @pytest.mark.asyncio
    async def test_process_last_words_wrong_phase(self, game_service, game_state_waiting_for_last_words):
        """不在遗言阶段时应返回错误"""
        game_state_waiting_for_last_words.waiting_for_human_action = False
        
        result = await game_service.process_human_last_words(
            room_code="TEST",
            player_id="player_3",
            content="遗言"
        )
        
        assert result["success"] is False
        assert "不是遗言阶段" in result["error"]
    
    @pytest.mark.asyncio
    async def test_process_last_words_wrong_player(self, game_service, game_state_waiting_for_last_words):
        """非当前遗言玩家应返回错误"""
        result = await game_service.process_human_last_words(
            room_code="TEST",
            player_id="player_1",  # 不是 player_3
            content="遗言"
        )
        
        assert result["success"] is False
        assert "不是你的遗言回合" in result["error"]
    
    @pytest.mark.asyncio
    async def test_process_last_words_skip(self, game_service, game_state_waiting_for_last_words):
        """跳过遗言（空内容）"""
        with patch('src.services.werewolf_game_service.broadcast_spectator_mode', new_callable=AsyncMock):
            result = await game_service.process_human_last_words(
                room_code="TEST",
                player_id="player_3",
                content=""  # 空内容表示跳过
            )
        
        assert result["success"] is True
        assert result["content"] == ""
    
    @pytest.mark.asyncio
    async def test_process_last_words_records_to_log(self, game_service, game_state_waiting_for_last_words):
        """遗言应记录到游戏日志"""
        with patch('src.services.werewolf_game_service.broadcast_player_speech', new_callable=AsyncMock), \
             patch('src.services.werewolf_game_service.broadcast_spectator_mode', new_callable=AsyncMock):
            await game_service.process_human_last_words(
                room_code="TEST",
                player_id="player_3",
                content="这是我的遗言"
            )
        
        # 检查日志
        assert len(game_state_waiting_for_last_words.game_logs) > 0
        last_log = game_state_waiting_for_last_words.game_logs[-1]
        assert "遗言" in last_log
        assert "这是我的遗言" in last_log


class TestSpectatorModeSwitch:
    """T53: 测试观战模式切换"""
    
    @pytest.fixture
    def mock_db(self):
        """创建 mock 数据库会话"""
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        return db
    
    @pytest.fixture
    def game_service(self, mock_db):
        return WerewolfGameService(db=mock_db)
    
    @pytest.fixture
    def game_state_human_dead(self, game_service):
        """人类玩家死亡的游戏状态"""
        state = WerewolfGameState(room_code="TEST")
        state.phase = WerewolfPhase.LAST_WORDS
        state.day_number = 2
        state.human_player_seat = 3
        state.waiting_for_human_action = True
        state.human_action_type = "last_words"
        state.last_words_seat = 3
        state.last_words_reason = "vote"
        
        for i in range(1, 11):
            state.players[i] = PlayerState(
                player_id=f"player_{i}",
                player_name=f"玩家{i}",
                seat_number=i,
                role="villager",
                team="villager",
                is_alive=True,
                is_human=(i == 3)
            )
        
        state.players[3].is_alive = False
        game_service._game_states["TEST"] = state
        return state
    
    @pytest.mark.asyncio
    async def test_spectator_mode_after_last_words(self, game_service, game_state_human_dead):
        """遗言后应切换到观战模式"""
        with patch('src.services.werewolf_game_service.broadcast_player_speech', new_callable=AsyncMock), \
             patch('src.services.werewolf_game_service.broadcast_spectator_mode', new_callable=AsyncMock) as mock_spectator:
            result = await game_service.process_human_last_words(
                room_code="TEST",
                player_id="player_3",
                content="遗言"
            )
        
        assert result["is_spectator"] is True
        assert game_state_human_dead.is_spectator_after_death is True
        mock_spectator.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_non_human_player_no_spectator(self, game_service, game_state_human_dead):
        """非人类玩家死亡不应触发观战模式广播"""
        # 修改为AI玩家死亡
        game_state_human_dead.last_words_seat = 5
        game_state_human_dead.players[5].is_alive = False
        game_state_human_dead.players[5].player_id = "player_5"
        
        with patch('src.services.werewolf_game_service.broadcast_player_speech', new_callable=AsyncMock), \
             patch('src.services.werewolf_game_service.broadcast_spectator_mode', new_callable=AsyncMock) as mock_spectator:
            result = await game_service.process_human_last_words(
                room_code="TEST",
                player_id="player_5",
                content="遗言"
            )
        
        # AI玩家死亡不应触发观战模式
        assert result.get("is_spectator", False) is False
        mock_spectator.assert_not_called()


class TestBroadcastLastWordsEvents:
    """T50: 测试遗言相关广播事件"""
    
    @pytest.mark.asyncio
    async def test_broadcast_last_words_options(self):
        """测试遗言选项广播"""
        from src.websocket.werewolf_handlers import broadcast_last_words_options
        
        with patch('src.websocket.werewolf_handlers.sio.emit', new_callable=AsyncMock) as mock_emit:
            await broadcast_last_words_options(
                room_code="TEST",
                seat_number=3,
                options=[{"id": "opt1", "text": "选项1"}],
                death_reason="vote"
            )
        
        mock_emit.assert_called_once()
        call_args = mock_emit.call_args
        assert call_args[0][0] == "werewolf:last_words_options"
        assert call_args[0][1]["seat_number"] == 3
        assert call_args[0][1]["death_reason"] == "vote"
    
    @pytest.mark.asyncio
    async def test_broadcast_player_speech(self):
        """测试玩家发言（遗言）广播"""
        from src.websocket.werewolf_handlers import broadcast_player_speech
        
        with patch('src.websocket.werewolf_handlers.sio.emit', new_callable=AsyncMock) as mock_emit:
            await broadcast_player_speech(
                room_code="TEST",
                seat_number=3,
                player_name="玩家3",
                content="这是我的遗言",
                speech_type="last_words"
            )
        
        mock_emit.assert_called_once()
        call_args = mock_emit.call_args
        assert call_args[0][0] == "werewolf:player_speech"
        assert call_args[0][1]["speech_type"] == "last_words"
    
    @pytest.mark.asyncio
    async def test_broadcast_spectator_mode(self):
        """测试观战模式广播"""
        from src.websocket.werewolf_handlers import broadcast_spectator_mode
        
        with patch('src.websocket.werewolf_handlers.sio.emit', new_callable=AsyncMock) as mock_emit:
            await broadcast_spectator_mode(
                room_code="TEST",
                player_id="player_3",
                seat_number=3
            )
        
        mock_emit.assert_called_once()
        call_args = mock_emit.call_args
        assert call_args[0][0] == "werewolf:spectator_mode"
        assert call_args[0][1]["player_id"] == "player_3"
