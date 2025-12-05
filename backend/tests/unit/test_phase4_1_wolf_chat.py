"""
Phase 4.1: 狼人私密讨论后端单元测试

测试内容：
- T40: WerewolfGameState werewolf_private_chat 字段
- T41: process_werewolf_chat 方法
- T42: broadcast_wolf_chat_message 广播方法
- T45: 游戏结束时公开讨论记录
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock
from src.services.games.werewolf_engine import (
    WerewolfEngine,
    WerewolfGameState,
    WerewolfPhase,
    PlayerState,
)
from src.services.werewolf_game_service import WerewolfGameService


class TestWerewolfPrivateChatField:
    """T40: 测试 WerewolfGameState 的 werewolf_private_chat 字段"""
    
    def test_werewolf_private_chat_default_empty(self):
        """werewolf_private_chat 默认应为空列表"""
        state = WerewolfGameState(room_code="TEST")
        assert state.werewolf_private_chat == []
        assert isinstance(state.werewolf_private_chat, list)
    
    def test_werewolf_private_chat_can_append(self):
        """werewolf_private_chat 应该可以添加消息"""
        state = WerewolfGameState(room_code="TEST")
        
        message = {
            "night_number": 1,
            "seat_number": 1,
            "player_name": "玩家1",
            "content": "我建议杀3号",
            "timestamp": datetime.now().isoformat()
        }
        state.werewolf_private_chat.append(message)
        
        assert len(state.werewolf_private_chat) == 1
        assert state.werewolf_private_chat[0]["content"] == "我建议杀3号"
    
    def test_werewolf_private_chat_multiple_messages(self):
        """werewolf_private_chat 应该支持多条消息"""
        state = WerewolfGameState(room_code="TEST")
        
        messages = [
            {"night_number": 1, "seat_number": 1, "content": "杀谁？"},
            {"night_number": 1, "seat_number": 2, "content": "杀3号"},
            {"night_number": 1, "seat_number": 1, "content": "同意"},
        ]
        for msg in messages:
            state.werewolf_private_chat.append(msg)
        
        assert len(state.werewolf_private_chat) == 3


class TestWerewolfChatHelperMethods:
    """T41: 测试狼人讨论相关辅助方法"""
    
    @pytest.fixture
    def mock_db(self):
        """创建模拟数据库会话"""
        return AsyncMock()
    
    @pytest.fixture
    def game_service(self, mock_db):
        """创建游戏服务实例"""
        return WerewolfGameService(mock_db)
    
    @pytest.fixture
    def game_state_with_werewolves(self, game_service):
        """创建包含狼人的游戏状态"""
        state = WerewolfGameState(room_code="TEST")
        state.phase = WerewolfPhase.NIGHT_WEREWOLF
        state.day_number = 1
        state.human_player_seat = 1
        
        # 创建10个玩家，其中座位1、2、3是狼人
        for i in range(1, 11):
            role = "werewolf" if i <= 3 else "villager"
            team = "werewolf" if i <= 3 else "villager"
            state.players[i] = PlayerState(
                seat_number=i,
                player_id=f"player_{i}",
                player_name=f"玩家{i}",
                role=role,
                team=team,
                is_alive=True,
                is_human=(i == 1)
            )
        
        game_service._game_states["TEST"] = state
        return state
    
    def test_get_werewolf_teammates(self, game_service, game_state_with_werewolves):
        """_get_werewolf_teammates 应返回狼队友列表"""
        teammates = game_service._get_werewolf_teammates("TEST", 1)
        
        assert len(teammates) == 2
        seat_numbers = [t["seat_number"] for t in teammates]
        assert 2 in seat_numbers
        assert 3 in seat_numbers
        assert 1 not in seat_numbers  # 自己不在队友列表中
    
    def test_get_werewolf_teammates_excludes_dead(self, game_service, game_state_with_werewolves):
        """_get_werewolf_teammates 应排除已死亡的狼人"""
        # 标记2号狼人死亡
        game_state_with_werewolves.players[2].is_alive = False
        
        teammates = game_service._get_werewolf_teammates("TEST", 1)
        
        assert len(teammates) == 1
        assert teammates[0]["seat_number"] == 3
    
    def test_get_all_werewolves(self, game_service, game_state_with_werewolves):
        """_get_all_werewolves 应返回所有存活狼人"""
        werewolves = game_service._get_all_werewolves("TEST")
        
        assert len(werewolves) == 3
        for wolf in werewolves:
            assert wolf["seat_number"] in [1, 2, 3]
    
    def test_get_all_werewolves_excludes_dead(self, game_service, game_state_with_werewolves):
        """_get_all_werewolves 应排除已死亡的狼人"""
        game_state_with_werewolves.players[1].is_alive = False
        game_state_with_werewolves.players[2].is_alive = False
        
        werewolves = game_service._get_all_werewolves("TEST")
        
        assert len(werewolves) == 1
        assert werewolves[0]["seat_number"] == 3


class TestProcessWerewolfChat:
    """T41: 测试 process_werewolf_chat 方法"""
    
    @pytest.fixture
    def mock_db(self):
        return AsyncMock()
    
    @pytest.fixture
    def game_service(self, mock_db):
        return WerewolfGameService(mock_db)
    
    @pytest.fixture
    def game_state_with_werewolves(self, game_service):
        state = WerewolfGameState(room_code="TEST")
        state.phase = WerewolfPhase.NIGHT_WEREWOLF
        state.day_number = 1
        state.human_player_seat = 1
        
        for i in range(1, 11):
            role = "werewolf" if i <= 3 else "villager"
            team = "werewolf" if i <= 3 else "villager"
            state.players[i] = PlayerState(
                seat_number=i,
                player_id=f"player_{i}",
                player_name=f"玩家{i}",
                role=role,
                team=team,
                is_alive=True,
                is_human=(i == 1)
            )
        
        game_service._game_states["TEST"] = state
        return state
    
    @pytest.mark.asyncio
    async def test_process_werewolf_chat_success(self, game_service, game_state_with_werewolves):
        """狼人应能成功发送讨论消息"""
        with patch('src.websocket.werewolf_handlers.broadcast_wolf_chat_message', new_callable=AsyncMock):
            result = await game_service.process_werewolf_chat(
                room_code="TEST",
                player_id="player_1",
                content="我建议杀5号"
            )
        
        assert result["success"] is True
        assert result["seat_number"] == 1
        assert result["content"] == "我建议杀5号"
        assert len(game_state_with_werewolves.werewolf_private_chat) == 1
    
    @pytest.mark.asyncio
    async def test_process_werewolf_chat_non_werewolf_rejected(self, game_service, game_state_with_werewolves):
        """非狼人不能发送讨论消息"""
        result = await game_service.process_werewolf_chat(
            room_code="TEST",
            player_id="player_5",  # 村民
            content="我是狼人"
        )
        
        assert result["success"] is False
        assert "只有狼人" in result["error"]
    
    @pytest.mark.asyncio
    async def test_process_werewolf_chat_wrong_phase(self, game_service, game_state_with_werewolves):
        """非狼人行动阶段不能发送讨论消息"""
        game_state_with_werewolves.phase = WerewolfPhase.DAY_DISCUSSION
        
        result = await game_service.process_werewolf_chat(
            room_code="TEST",
            player_id="player_1",
            content="测试消息"
        )
        
        assert result["success"] is False
        assert "不是狼人行动阶段" in result["error"]
    
    @pytest.mark.asyncio
    async def test_process_werewolf_chat_empty_content(self, game_service, game_state_with_werewolves):
        """空消息应被拒绝"""
        result = await game_service.process_werewolf_chat(
            room_code="TEST",
            player_id="player_1",
            content="   "
        )
        
        assert result["success"] is False
        assert "不能为空" in result["error"]
    
    @pytest.mark.asyncio
    async def test_process_werewolf_chat_dead_player(self, game_service, game_state_with_werewolves):
        """已死亡的狼人不能发送讨论消息"""
        game_state_with_werewolves.players[1].is_alive = False
        
        result = await game_service.process_werewolf_chat(
            room_code="TEST",
            player_id="player_1",
            content="测试消息"
        )
        
        assert result["success"] is False
        assert "已死亡" in result["error"]


class TestGetWerewolfChatHistory:
    """测试 get_werewolf_chat_history 方法"""
    
    @pytest.fixture
    def mock_db(self):
        return AsyncMock()
    
    @pytest.fixture
    def game_service(self, mock_db):
        return WerewolfGameService(mock_db)
    
    @pytest.fixture
    def game_state_with_chat(self, game_service):
        state = WerewolfGameState(room_code="TEST")
        state.werewolf_private_chat = [
            {"night_number": 1, "seat_number": 1, "content": "第一夜消息1"},
            {"night_number": 1, "seat_number": 2, "content": "第一夜消息2"},
            {"night_number": 2, "seat_number": 1, "content": "第二夜消息1"},
        ]
        game_service._game_states["TEST"] = state
        return state
    
    def test_get_all_history(self, game_service, game_state_with_chat):
        """不指定夜晚时应返回所有消息"""
        history = game_service.get_werewolf_chat_history("TEST")
        assert len(history) == 3
    
    def test_get_history_by_night(self, game_service, game_state_with_chat):
        """指定夜晚时应只返回该夜消息"""
        history = game_service.get_werewolf_chat_history("TEST", night_number=1)
        assert len(history) == 2
        
        history = game_service.get_werewolf_chat_history("TEST", night_number=2)
        assert len(history) == 1
    
    def test_get_history_nonexistent_room(self, game_service):
        """不存在的房间应返回空列表"""
        history = game_service.get_werewolf_chat_history("NONEXISTENT")
        assert history == []


class TestPublishChatOnGameEnd:
    """T45: 测试游戏结束时公开讨论记录"""
    
    @pytest.fixture
    def mock_db(self):
        return AsyncMock()
    
    @pytest.fixture
    def game_service(self, mock_db):
        return WerewolfGameService(mock_db)
    
    @pytest.fixture
    def game_state_with_chat(self, game_service):
        state = WerewolfGameState(room_code="TEST")
        state.phase = WerewolfPhase.DAY_DISCUSSION
        state.day_number = 3
        
        # 添加玩家
        for i in range(1, 11):
            role = "werewolf" if i <= 3 else "villager"
            team = "werewolf" if i <= 3 else "villager"
            state.players[i] = PlayerState(
                seat_number=i,
                player_id=f"player_{i}",
                player_name=f"玩家{i}",
                role=role,
                team=team,
                is_alive=True
            )
        
        # 添加狼人讨论记录
        state.werewolf_private_chat = [
            {
                "night_number": 1,
                "seat_number": 1,
                "player_name": "玩家1",
                "content": "杀谁？",
                "is_human": True
            },
            {
                "night_number": 1,
                "seat_number": 2,
                "player_name": "玩家2",
                "content": "杀5号",
                "is_human": False
            },
            {
                "night_number": 2,
                "seat_number": 1,
                "player_name": "玩家1",
                "content": "这次杀7号",
                "is_human": True
            },
        ]
        
        state.game_logs = []
        game_service._game_states["TEST"] = state
        game_service.engine.state = state
        return state
    
    @pytest.mark.asyncio
    async def test_chat_published_on_game_end(self, game_service, game_state_with_chat):
        """游戏结束时应公开狼人讨论记录"""
        with patch('src.services.werewolf_game_service.broadcast_phase_change', new_callable=AsyncMock), \
             patch('src.services.werewolf_game_service.stream_host_announcement', new_callable=AsyncMock), \
             patch('src.services.werewolf_game_service.broadcast_game_over', new_callable=AsyncMock):
            
            await game_service._end_game("TEST", "werewolf")
        
        # 检查日志中是否包含讨论记录
        logs = game_state_with_chat.game_logs
        log_content = "\n".join(str(log) for log in logs)
        
        assert "狼人私密讨论记录" in log_content
        assert "第1夜" in log_content
        assert "第2夜" in log_content
        assert "杀谁？" in log_content
        assert "杀5号" in log_content
        assert "[人类]" in log_content
        assert "[AI]" in log_content
    
    @pytest.mark.asyncio
    async def test_no_chat_no_publish(self, game_service, game_state_with_chat):
        """没有讨论记录时不应添加相关日志"""
        game_state_with_chat.werewolf_private_chat = []
        
        with patch('src.services.werewolf_game_service.broadcast_phase_change', new_callable=AsyncMock), \
             patch('src.services.werewolf_game_service.stream_host_announcement', new_callable=AsyncMock), \
             patch('src.services.werewolf_game_service.broadcast_game_over', new_callable=AsyncMock):
            
            await game_service._end_game("TEST", "werewolf")
        
        logs = game_state_with_chat.game_logs
        log_content = "\n".join(str(log) for log in logs)
        
        assert "狼人私密讨论记录" not in log_content


class TestBroadcastWolfChatMessage:
    """T42: 测试 broadcast_wolf_chat_message 广播方法"""
    
    @pytest.mark.asyncio
    async def test_broadcast_wolf_chat_message(self):
        """应向所有狼人广播消息"""
        from src.websocket.werewolf_handlers import broadcast_wolf_chat_message
        
        with patch('src.websocket.werewolf_handlers.sio') as mock_sio, \
             patch('src.websocket.werewolf_handlers._get_sid_by_player_id') as mock_get_sid:
            
            mock_sio.emit = AsyncMock()
            mock_get_sid.side_effect = lambda pid: f"sid_{pid}"
            
            await broadcast_wolf_chat_message(
                room_code="TEST",
                sender_seat=1,
                sender_name="玩家1",
                content="杀5号",
                werewolf_player_ids=["player_1", "player_2", "player_3"]
            )
            
            # 应该向每个狼人发送消息
            assert mock_sio.emit.call_count == 3
            
            # 检查调用参数
            calls = mock_sio.emit.call_args_list
            for call in calls:
                assert call[0][0] == "werewolf:wolf_chat_message"
                data = call[0][1]
                assert data["sender_seat"] == 1
                assert data["sender_name"] == "玩家1"
                assert data["content"] == "杀5号"
