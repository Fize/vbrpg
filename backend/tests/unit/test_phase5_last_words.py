"""
Phase 5: 遗言与观战模式测试

测试覆盖:
- T48: 遗言等待状态设置
- T49: process_human_last_words 方法
- T50: WebSocket 事件处理
- T53: 观战模式切换
"""
import pytest
from unittest.mock import AsyncMock, patch

from src.games.werewolf.orchestrator import WerewolfGameOrchestrator
from src.games.werewolf.state import (
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
    """T48: 测试遗言处理（含角色场景）"""
    
    @pytest.fixture
    def game_service(self):
        return WerewolfGameOrchestrator()
    
    @pytest.fixture
    def game_state_with_dead_player(self, game_service):
        """创建包含已死玩家的游戏状态"""
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
    
    @pytest.mark.asyncio
    async def test_process_last_words_villager(self, game_service, game_state_with_dead_player):
        """村民遗言处理"""
        game_state_with_dead_player.players[3].role = "villager"
        
        result = await game_service.process_human_last_words(
            room_code="TEST",
            player_id="player_3",
            content="我是好人，你们投错了！"
        )
        
        assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_process_last_words_werewolf(self, game_service, game_state_with_dead_player):
        """狼人遗言处理"""
        game_state_with_dead_player.players[3].role = "werewolf"
        
        result = await game_service.process_human_last_words(
            room_code="TEST",
            player_id="player_3",
            content="我是平民"
        )
        
        assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_process_last_words_seer(self, game_service, game_state_with_dead_player):
        """预言家遗言处理"""
        game_state_with_dead_player.players[3].role = "seer"
        game_state_with_dead_player.last_words_reason = "night_kill"
        
        result = await game_service.process_human_last_words(
            room_code="TEST",
            player_id="player_3",
            content="我是预言家，昨晚查了3号是狼"
        )
        
        assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_process_last_words_vote_death(self, game_service, game_state_with_dead_player):
        """投票死亡遗言处理"""
        result = await game_service.process_human_last_words(
            room_code="TEST",
            player_id="player_3",
            content="我是好人，你们投错了！"
        )
        
        assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_process_last_words_night_kill(self, game_service, game_state_with_dead_player):
        """夜杀死亡遗言处理"""
        game_state_with_dead_player.last_words_reason = "night_kill"
        
        result = await game_service.process_human_last_words(
            room_code="TEST",
            player_id="player_3",
            content="狼人今晚杀了我"
        )
        
        assert result["success"] is True


class TestProcessHumanLastWords:
    """T49: 测试 process_human_last_words 方法"""
    
    @pytest.fixture
    def game_service(self):
        return WerewolfGameOrchestrator()
    
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
        result = await game_service.process_human_last_words(
            room_code="TEST",
            player_id="player_3",
            content="我是好人，你们投错了！"
        )
        
        assert result["success"] is True
        # process_human_last_words 将动作转发给游戏循环处理
        assert game_state_waiting_for_last_words.waiting_for_human_action is False
    
    @pytest.mark.asyncio
    async def test_process_last_words_no_game(self, game_service):
        """游戏不存在时 process_human_last_words 返回 success=True（静默失败由游戏循环处理）"""
        result = await game_service.process_human_last_words(
            room_code="NONEXISTENT",
            player_id="player_1",
            content="遗言"
        )
        
        # 在新的架构中，process_human_last_words 是薄代理层，不验证游戏是否存在
        assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_process_last_words_skip(self, game_service, game_state_waiting_for_last_words):
        """跳过遗言（空内容）"""
        result = await game_service.process_human_last_words(
            room_code="TEST",
            player_id="player_3",
            content=""  # 空内容表示跳过
        )
        
        assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_process_last_words_pending_action_set(self, game_service, game_state_waiting_for_last_words):
        """遗言提交应设置 pending_human_action 并清除等待状态"""
        await game_service.process_human_last_words(
            room_code="TEST",
            player_id="player_3",
            content="这是我的遗言"
        )
        
        # 检查 pending_human_action 被设置
        assert hasattr(game_state_waiting_for_last_words, 'pending_human_action')
        assert game_state_waiting_for_last_words.pending_human_action["type"] == "last_words"
        assert game_state_waiting_for_last_words.pending_human_action["data"]["content"] == "这是我的遗言"
        assert game_state_waiting_for_last_words.waiting_for_human_action is False


class TestSpectatorModeSwitch:
    """T53: 测试观战模式切换"""
    
    @pytest.fixture
    def game_service(self):
        return WerewolfGameOrchestrator()
    
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
        """遗言后应清除等待状态（观战模式由游戏循环内部处理）"""
        result = await game_service.process_human_last_words(
            room_code="TEST",
            player_id="player_3",
            content="遗言"
        )
        
        assert result["success"] is True
        # process_human_last_words 清除等待状态，游戏循环负责后续观战模式切换
        assert game_state_human_dead.waiting_for_human_action is False
    
    @pytest.mark.asyncio
    async def test_non_human_player_last_words(self, game_service, game_state_human_dead):
        """非人类玩家的遗言仍然通过 process_human_last_words 处理（身份验证由游戏循环负责）"""
        # 修改为AI玩家
        game_state_human_dead.last_words_seat = 5
        game_state_human_dead.players[5].is_alive = False
        game_state_human_dead.players[5].player_id = "player_5"
        
        result = await game_service.process_human_last_words(
            room_code="TEST",
            player_id="player_5",
            content="遗言"
        )
        
        # process_human_last_words 是薄代理层，不区分人类/AI玩家
        assert result["success"] is True


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
