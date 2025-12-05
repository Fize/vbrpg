"""
Phase 4: 夜间行动人类玩家参与测试

任务覆盖:
- T31: 狼人夜间行动等待人类
- T32: 预言家夜间行动等待人类
- T33: 女巫夜间行动等待人类
- T34: 猎人夜间行动等待人类
- T35: process_human_night_action 方法
- T36: werewolf_human_night_action 事件处理器
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.services.werewolf_game_service import WerewolfGameService
from src.services.games.werewolf_engine import WerewolfGameState, PlayerState, WerewolfPhase


@pytest.fixture
def mock_db():
    """创建模拟数据库会话."""
    db = AsyncMock()
    db.commit = AsyncMock()
    return db


@pytest.fixture
def game_state():
    """创建测试用游戏状态."""
    state = WerewolfGameState(
        room_code="test-room",
        game_id="test-game-id",
        phase=WerewolfPhase.NIGHT_WEREWOLF,
        day_number=1
    )
    
    # 角色配置
    roles = [
        ("werewolf", "werewolf"),
        ("werewolf", "werewolf"),
        ("seer", "villager"),
        ("witch", "villager"),
        ("hunter", "villager"),
        ("villager", "villager"),
    ]
    
    # 添加6个玩家
    for i in range(1, 7):
        role, team = roles[i - 1]
        player = PlayerState(
            player_id=f"player-{i}",
            player_name=f"玩家{i}",
            seat_number=i,
            role=role,
            team=team,
            is_alive=True
        )
        state.players[i] = player
    
    # 女巫药水状态
    state.witch_has_antidote = True
    state.witch_has_poison = True
    
    # 人类玩家座位
    state.human_player_seat = 1
    
    return state


class TestProcessHumanNightAction:
    """测试 process_human_night_action 方法."""
    
    @pytest.mark.asyncio
    async def test_werewolf_kill_success(self, mock_db, game_state):
        """测试狼人杀人成功."""
        service = WerewolfGameService(mock_db)
        service._game_states["test-room"] = game_state
        service._ai_agents = {2: MagicMock()}  # 另一个狼人是 AI
        
        # 设置等待状态
        game_state.waiting_for_human_action = True
        game_state.human_action_type = "werewolf_kill"
        
        with patch("src.services.werewolf_game_service.broadcast_human_night_action_complete", new_callable=AsyncMock):
            result = await service.process_human_night_action(
                room_code="test-room",
                player_id="player-1",
                action_type="werewolf_kill",
                target_seat=6
            )
        
        assert result["success"] is True
        assert result["target_seat"] == 6
        assert result["action"] == "kill"
    
    @pytest.mark.asyncio
    async def test_werewolf_empty_kill(self, mock_db, game_state):
        """测试狼人空刀."""
        service = WerewolfGameService(mock_db)
        service._game_states["test-room"] = game_state
        service._ai_agents = {2: MagicMock()}
        
        game_state.waiting_for_human_action = True
        game_state.human_action_type = "werewolf_kill"
        
        with patch("src.services.werewolf_game_service.broadcast_human_night_action_complete", new_callable=AsyncMock):
            result = await service.process_human_night_action(
                room_code="test-room",
                player_id="player-1",
                action_type="werewolf_kill",
                target_seat=None
            )
        
        assert result["success"] is True
        assert result["target_seat"] is None
        assert result["action"] == "skip"
    
    @pytest.mark.asyncio
    async def test_werewolf_cannot_kill_teammate(self, mock_db, game_state):
        """测试狼人不能杀队友."""
        service = WerewolfGameService(mock_db)
        service._game_states["test-room"] = game_state
        service._ai_agents = {2: MagicMock()}
        
        game_state.waiting_for_human_action = True
        game_state.human_action_type = "werewolf_kill"
        
        result = await service.process_human_night_action(
            room_code="test-room",
            player_id="player-1",
            action_type="werewolf_kill",
            target_seat=2  # 另一个狼人
        )
        
        assert result["success"] is False
        assert "狼人同伴" in result["error"]
    
    @pytest.mark.asyncio
    async def test_seer_check_success(self, mock_db, game_state):
        """测试预言家查验成功."""
        service = WerewolfGameService(mock_db)
        service._game_states["test-room"] = game_state
        service._ai_agents = {i: MagicMock() for i in range(1, 7) if i != 3}
        
        game_state.human_player_seat = 3
        game_state.waiting_for_human_action = True
        game_state.human_action_type = "seer_check"
        game_state.phase = WerewolfPhase.NIGHT_SEER
        
        with patch("src.services.werewolf_game_service.broadcast_human_night_action_complete", new_callable=AsyncMock):
            result = await service.process_human_night_action(
                room_code="test-room",
                player_id="player-3",
                action_type="seer_check",
                target_seat=1
            )
        
        assert result["success"] is True
        assert result["target_seat"] == 1
        assert result["is_werewolf"] is True
        assert result["check_result"] == "狼人"
    
    @pytest.mark.asyncio
    async def test_seer_check_villager(self, mock_db, game_state):
        """测试预言家查验村民（好人）."""
        service = WerewolfGameService(mock_db)
        service._game_states["test-room"] = game_state
        service._ai_agents = {i: MagicMock() for i in range(1, 7) if i != 3}
        
        game_state.human_player_seat = 3
        game_state.waiting_for_human_action = True
        game_state.human_action_type = "seer_check"
        game_state.phase = WerewolfPhase.NIGHT_SEER
        
        with patch("src.services.werewolf_game_service.broadcast_human_night_action_complete", new_callable=AsyncMock):
            result = await service.process_human_night_action(
                room_code="test-room",
                player_id="player-3",
                action_type="seer_check",
                target_seat=6  # 村民
            )
        
        assert result["success"] is True
        assert result["target_seat"] == 6
        assert result["is_werewolf"] is False
        assert result["check_result"] == "好人"
    
    @pytest.mark.asyncio
    async def test_seer_cannot_check_self(self, mock_db, game_state):
        """测试预言家不能查验自己."""
        service = WerewolfGameService(mock_db)
        service._game_states["test-room"] = game_state
        service._ai_agents = {i: MagicMock() for i in range(1, 7) if i != 3}
        
        game_state.human_player_seat = 3
        game_state.waiting_for_human_action = True
        game_state.human_action_type = "seer_check"
        
        result = await service.process_human_night_action(
            room_code="test-room",
            player_id="player-3",
            action_type="seer_check",
            target_seat=3  # 自己
        )
        
        assert result["success"] is False
        assert "自己" in result["error"]
    
    @pytest.mark.asyncio
    async def test_witch_save_success(self, mock_db, game_state):
        """测试女巫救人成功."""
        service = WerewolfGameService(mock_db)
        service._game_states["test-room"] = game_state
        service._ai_agents = {i: MagicMock() for i in range(1, 7) if i != 4}
        
        game_state.human_player_seat = 4
        game_state.waiting_for_human_action = True
        game_state.human_action_type = "witch_action"
        game_state.phase = WerewolfPhase.NIGHT_WITCH
        game_state.current_night_actions.werewolf_kill_target = 6
        
        with patch("src.services.werewolf_game_service.broadcast_human_night_action_complete", new_callable=AsyncMock):
            result = await service.process_human_night_action(
                room_code="test-room",
                player_id="player-4",
                action_type="witch_action",
                target_seat=6,
                witch_action="save"
            )
        
        assert result["success"] is True
        assert result["witch_action"] == "save"
        assert result["save_target"] == 6
        assert game_state.witch_has_antidote is False
    
    @pytest.mark.asyncio
    async def test_witch_poison_success(self, mock_db, game_state):
        """测试女巫毒人成功."""
        service = WerewolfGameService(mock_db)
        service._game_states["test-room"] = game_state
        service._ai_agents = {i: MagicMock() for i in range(1, 7) if i != 4}
        
        game_state.human_player_seat = 4
        game_state.waiting_for_human_action = True
        game_state.human_action_type = "witch_action"
        game_state.phase = WerewolfPhase.NIGHT_WITCH
        
        with patch("src.services.werewolf_game_service.broadcast_human_night_action_complete", new_callable=AsyncMock):
            result = await service.process_human_night_action(
                room_code="test-room",
                player_id="player-4",
                action_type="witch_action",
                target_seat=1,
                witch_action="poison"
            )
        
        assert result["success"] is True
        assert result["witch_action"] == "poison"
        assert result["poison_target"] == 1
        assert game_state.witch_has_poison is False
    
    @pytest.mark.asyncio
    async def test_witch_pass_success(self, mock_db, game_state):
        """测试女巫不使用药水."""
        service = WerewolfGameService(mock_db)
        service._game_states["test-room"] = game_state
        service._ai_agents = {i: MagicMock() for i in range(1, 7) if i != 4}
        
        game_state.human_player_seat = 4
        game_state.waiting_for_human_action = True
        game_state.human_action_type = "witch_action"
        game_state.phase = WerewolfPhase.NIGHT_WITCH
        
        with patch("src.services.werewolf_game_service.broadcast_human_night_action_complete", new_callable=AsyncMock):
            result = await service.process_human_night_action(
                room_code="test-room",
                player_id="player-4",
                action_type="witch_action",
                target_seat=None,
                witch_action="pass"
            )
        
        assert result["success"] is True
        assert result["witch_action"] == "pass"
        # 药水未使用
        assert game_state.witch_has_antidote is True
        assert game_state.witch_has_poison is True
    
    @pytest.mark.asyncio
    async def test_witch_save_no_antidote(self, mock_db, game_state):
        """测试女巫没有解药时不能救人."""
        service = WerewolfGameService(mock_db)
        service._game_states["test-room"] = game_state
        service._ai_agents = {i: MagicMock() for i in range(1, 7) if i != 4}
        
        game_state.human_player_seat = 4
        game_state.waiting_for_human_action = True
        game_state.human_action_type = "witch_action"
        game_state.witch_has_antidote = False
        game_state.current_night_actions.werewolf_kill_target = 6
        
        result = await service.process_human_night_action(
            room_code="test-room",
            player_id="player-4",
            action_type="witch_action",
            target_seat=6,
            witch_action="save"
        )
        
        assert result["success"] is False
        assert "解药" in result["error"]
    
    @pytest.mark.asyncio
    async def test_witch_self_save_first_night(self, mock_db, game_state):
        """测试女巫首夜可以自救."""
        service = WerewolfGameService(mock_db)
        service._game_states["test-room"] = game_state
        service._ai_agents = {i: MagicMock() for i in range(1, 7) if i != 4}
        
        game_state.human_player_seat = 4
        game_state.waiting_for_human_action = True
        game_state.human_action_type = "witch_action"
        game_state.day_number = 1
        game_state.current_night_actions.werewolf_kill_target = 4  # 女巫被杀
        
        with patch("src.services.werewolf_game_service.broadcast_human_night_action_complete", new_callable=AsyncMock):
            result = await service.process_human_night_action(
                room_code="test-room",
                player_id="player-4",
                action_type="witch_action",
                target_seat=4,
                witch_action="save"
            )
        
        assert result["success"] is True
        assert result["save_target"] == 4
    
    @pytest.mark.asyncio
    async def test_witch_no_self_save_after_first_night(self, mock_db, game_state):
        """测试女巫首夜后不能自救."""
        service = WerewolfGameService(mock_db)
        service._game_states["test-room"] = game_state
        service._ai_agents = {i: MagicMock() for i in range(1, 7) if i != 4}
        
        game_state.human_player_seat = 4
        game_state.waiting_for_human_action = True
        game_state.human_action_type = "witch_action"
        game_state.day_number = 2
        game_state.current_night_actions.werewolf_kill_target = 4
        
        result = await service.process_human_night_action(
            room_code="test-room",
            player_id="player-4",
            action_type="witch_action",
            target_seat=4,
            witch_action="save"
        )
        
        assert result["success"] is False
        assert "自救" in result["error"]
    
    @pytest.mark.asyncio
    async def test_hunter_shoot_success(self, mock_db, game_state):
        """测试猎人开枪成功."""
        service = WerewolfGameService(mock_db)
        service._game_states["test-room"] = game_state
        service._ai_agents = {i: MagicMock() for i in range(1, 7) if i != 5}
        
        game_state.human_player_seat = 5
        game_state.waiting_for_human_action = True
        game_state.human_action_type = "hunter_shoot"
        game_state.phase = WerewolfPhase.HUNTER_SHOOT
        
        with patch("src.services.werewolf_game_service.broadcast_human_night_action_complete", new_callable=AsyncMock):
            with patch("src.services.werewolf_game_service.broadcast_host_announcement", new_callable=AsyncMock):
                result = await service.process_human_night_action(
                    room_code="test-room",
                    player_id="player-5",
                    action_type="hunter_shoot",
                    target_seat=1
                )
        
        assert result["success"] is True
        assert result["target_seat"] == 1
        assert result["action"] == "shoot"
    
    @pytest.mark.asyncio
    async def test_hunter_no_shoot(self, mock_db, game_state):
        """测试猎人不开枪."""
        service = WerewolfGameService(mock_db)
        service._game_states["test-room"] = game_state
        service._ai_agents = {i: MagicMock() for i in range(1, 7) if i != 5}
        
        game_state.human_player_seat = 5
        game_state.waiting_for_human_action = True
        game_state.human_action_type = "hunter_shoot"
        game_state.phase = WerewolfPhase.HUNTER_SHOOT
        
        with patch("src.services.werewolf_game_service.broadcast_human_night_action_complete", new_callable=AsyncMock):
            result = await service.process_human_night_action(
                room_code="test-room",
                player_id="player-5",
                action_type="hunter_shoot",
                target_seat=None
            )
        
        assert result["success"] is True
        assert result["target_seat"] is None
        assert result["action"] == "skip"
    
    @pytest.mark.asyncio
    async def test_action_type_mismatch(self, mock_db, game_state):
        """测试行动类型不匹配."""
        service = WerewolfGameService(mock_db)
        service._game_states["test-room"] = game_state
        service._ai_agents = {2: MagicMock()}
        
        game_state.waiting_for_human_action = True
        game_state.human_action_type = "werewolf_kill"
        
        result = await service.process_human_night_action(
            room_code="test-room",
            player_id="player-1",
            action_type="seer_check",  # 错误的行动类型
            target_seat=3
        )
        
        assert result["success"] is False
        assert "不匹配" in result["error"]
    
    @pytest.mark.asyncio
    async def test_not_waiting_for_action(self, mock_db, game_state):
        """测试不在等待行动状态."""
        service = WerewolfGameService(mock_db)
        service._game_states["test-room"] = game_state
        
        game_state.waiting_for_human_action = False
        
        result = await service.process_human_night_action(
            room_code="test-room",
            player_id="player-1",
            action_type="werewolf_kill",
            target_seat=6
        )
        
        assert result["success"] is False
        assert "不在等待" in result["error"]
    
    @pytest.mark.asyncio
    async def test_game_not_found(self, mock_db):
        """测试游戏不存在."""
        service = WerewolfGameService(mock_db)
        
        result = await service.process_human_night_action(
            room_code="nonexistent-room",
            player_id="player-1",
            action_type="werewolf_kill",
            target_seat=6
        )
        
        assert result["success"] is False
        assert "不存在" in result["error"]


class TestBroadcastHumanNightActionComplete:
    """测试 broadcast_human_night_action_complete 函数."""
    
    @pytest.mark.asyncio
    async def test_broadcast_function_exists(self):
        """测试广播函数存在."""
        from src.websocket.werewolf_handlers import broadcast_human_night_action_complete
        
        assert callable(broadcast_human_night_action_complete)
    
    @pytest.mark.asyncio
    async def test_broadcast_emits_event(self):
        """测试广播发送正确事件."""
        from src.websocket.werewolf_handlers import (
            broadcast_human_night_action_complete,
            sio
        )
        
        with patch.object(sio, 'emit', new_callable=AsyncMock) as mock_emit:
            await broadcast_human_night_action_complete(
                room_code="test-room",
                seat_number=1,
                action_type="werewolf_kill",
                result={"target_seat": 6, "action": "kill"}
            )
            
            mock_emit.assert_called_once()
            call_args = mock_emit.call_args
            assert call_args[0][0] == "werewolf:human_night_action_complete"
            assert call_args[1]["room"] == "test-room"


class TestWerewolfHumanNightActionHandler:
    """测试 werewolf_human_night_action WebSocket 事件处理器."""
    
    def test_handler_registered(self):
        """测试事件处理器已注册."""
        # 检查函数存在于模块中
        import src.websocket.werewolf_handlers as handlers
        assert hasattr(handlers, 'werewolf_human_night_action')
        # 检查是协程函数（async def）
        import inspect
        handler = getattr(handlers, 'werewolf_human_night_action')
        assert inspect.iscoroutinefunction(handler)


class TestWebSocketImports:
    """测试 WebSocket 函数可导入."""
    
    def test_broadcast_human_night_action_complete_importable(self):
        """测试 broadcast_human_night_action_complete 可从 websocket 包导入."""
        from src.websocket import broadcast_human_night_action_complete
        assert callable(broadcast_human_night_action_complete)
