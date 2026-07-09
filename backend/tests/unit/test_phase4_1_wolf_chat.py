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
from src.games.werewolf.engine import WerewolfEngine
from src.games.werewolf.state import (
    WerewolfGameState,
    WerewolfPhase,
    PlayerState,
)
from src.games.werewolf.orchestrator import WerewolfGameOrchestrator


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
        return WerewolfGameOrchestrator()
    
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
        game_service.engine.state = state
        return state
    
    def test_get_werewolf_teammates(self, game_service, game_state_with_werewolves):
        """engine.get_werewolf_teammates 应返回狼队友列表（PlayerState对象）"""
        teammates = game_service.engine.get_werewolf_teammates(1)
        
        assert len(teammates) == 2
        seat_numbers = [t.seat_number for t in teammates]
        assert 2 in seat_numbers
        assert 3 in seat_numbers
        assert 1 not in seat_numbers  # 自己不在队友列表中
    
    def test_get_werewolf_teammates_excludes_dead(self, game_service, game_state_with_werewolves):
        """get_werewolf_teammates 不按is_alive过滤——返回所有狼人队友"""
        # 标记2号狼人死亡
        game_state_with_werewolves.players[2].is_alive = False
        
        teammates = game_service.engine.get_werewolf_teammates(1)
        
        # engine.get_werewolf_teammates 不检查 is_alive，仍返回所有狼人
        assert len(teammates) == 2
        seat_numbers = [t.seat_number for t in teammates]
        assert 2 in seat_numbers
        assert 3 in seat_numbers
    
    def test_get_all_werewolves(self, game_service, game_state_with_werewolves):
        """通过 state.players 列表推导获取所有存活狼人"""
        state = game_state_with_werewolves
        werewolves = [p for p in state.players.values() if p.role == "werewolf" and p.is_alive]
        
        assert len(werewolves) == 3
        for wolf in werewolves:
            assert wolf.seat_number in [1, 2, 3]
    
    def test_get_all_werewolves_excludes_dead(self, game_service, game_state_with_werewolves):
        """列表推导应排除已死亡的狼人"""
        state = game_state_with_werewolves
        state.players[1].is_alive = False
        state.players[2].is_alive = False
        
        werewolves = [p for p in state.players.values() if p.role == "werewolf" and p.is_alive]
        
        assert len(werewolves) == 1
        assert werewolves[0].seat_number == 3


class TestProcessWerewolfChat:
    """T41: 测试 process_werewolf_chat 方法（当前API不做phase/role/alive校验）"""
    
    @pytest.fixture
    def mock_db(self):
        return AsyncMock()
    
    @pytest.fixture
    def game_service(self, mock_db):
        return WerewolfGameOrchestrator()
    
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
        result = await game_service.process_werewolf_chat(
            room_code="TEST",
            player_id="player_1",
            content="我建议杀5号"
        )
        
        assert result["success"] is True
        assert result["chat_entry"]["seat_number"] == 1
        assert result["chat_entry"]["content"] == "我建议杀5号"
        assert len(game_state_with_werewolves.werewolf_private_chat) == 1
    
    @pytest.mark.asyncio
    async def test_process_werewolf_chat_non_werewolf_accepted(self, game_service, game_state_with_werewolves):
        """非狼人也能发送讨论消息（当前API不做role校验）"""
        result = await game_service.process_werewolf_chat(
            room_code="TEST",
            player_id="player_5",  # 村民
            content="我是狼人"
        )
        
        assert result["success"] is True
        assert result["chat_entry"]["seat_number"] == 5
        assert len(game_state_with_werewolves.werewolf_private_chat) == 1
    
    @pytest.mark.asyncio
    async def test_process_werewolf_chat_wrong_phase(self, game_service, game_state_with_werewolves):
        """非狼人行动阶段也能发送讨论消息（当前API不做phase校验）"""
        game_state_with_werewolves.phase = WerewolfPhase.DAY_DISCUSSION
        
        result = await game_service.process_werewolf_chat(
            room_code="TEST",
            player_id="player_1",
            content="测试消息"
        )
        
        assert result["success"] is True
        assert result["chat_entry"]["content"] == "测试消息"
        assert len(game_state_with_werewolves.werewolf_private_chat) == 1
    
    @pytest.mark.asyncio
    async def test_process_werewolf_chat_empty_content(self, game_service, game_state_with_werewolves):
        """空消息也会被接受（当前API不做内容校验）"""
        result = await game_service.process_werewolf_chat(
            room_code="TEST",
            player_id="player_1",
            content="   "
        )
        
        assert result["success"] is True
        assert result["chat_entry"]["content"] == "   "
        assert len(game_state_with_werewolves.werewolf_private_chat) == 1
    
    @pytest.mark.asyncio
    async def test_process_werewolf_chat_dead_player(self, game_service, game_state_with_werewolves):
        """已死亡的玩家也能发送讨论消息（当前API不做alive校验）"""
        game_state_with_werewolves.players[1].is_alive = False
        
        result = await game_service.process_werewolf_chat(
            room_code="TEST",
            player_id="player_1",
            content="测试消息"
        )
        
        assert result["success"] is True
        assert result["chat_entry"]["content"] == "测试消息"
        assert len(game_state_with_werewolves.werewolf_private_chat) == 1


class TestGetWerewolfChatHistory:
    """测试通过 state.werewolf_private_chat 直接访问讨论历史"""
    
    @pytest.fixture
    def mock_db(self):
        return AsyncMock()
    
    @pytest.fixture
    def game_service(self, mock_db):
        return WerewolfGameOrchestrator()
    
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
        """state.werewolf_private_chat 应包含所有消息"""
        history = game_state_with_chat.werewolf_private_chat
        assert len(history) == 3
    
    def test_get_history_by_night(self, game_service, game_state_with_chat):
        """可通过列表推导按夜晚筛选消息"""
        history_1 = [m for m in game_state_with_chat.werewolf_private_chat if m["night_number"] == 1]
        assert len(history_1) == 2
        
        history_2 = [m for m in game_state_with_chat.werewolf_private_chat if m["night_number"] == 2]
        assert len(history_2) == 1
    
    def test_get_history_nonexistent_room(self, game_service):
        """不存在的房间在 _game_states 中返回 None"""
        state = game_service._game_states.get("NONEXISTENT")
        assert state is None


class TestPublishChatOnGameEnd:
    """T45: 测试游戏结束时公开讨论记录（直接检查state字段）"""
    
    @pytest.fixture
    def mock_db(self):
        return AsyncMock()
    
    @pytest.fixture
    def game_service(self, mock_db):
        return WerewolfGameOrchestrator()
    
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
        
        game_service._game_states["TEST"] = state
        return state
    
    def test_chat_records_accessible_from_state(self, game_service, game_state_with_chat):
        """狼人讨论记录可直接从 state.werewolf_private_chat 读取"""
        chat = game_state_with_chat.werewolf_private_chat
        
        assert len(chat) == 3
        assert chat[0]["night_number"] == 1
        assert chat[0]["content"] == "杀谁？"
        assert chat[0]["is_human"] is True
        assert chat[1]["content"] == "杀5号"
        assert chat[1]["is_human"] is False
        assert chat[2]["night_number"] == 2
        assert chat[2]["content"] == "这次杀7号"
    
    def test_no_chat_empty_list(self, game_service, game_state_with_chat):
        """没有讨论记录时列表为空"""
        game_state_with_chat.werewolf_private_chat = []
        
        assert game_state_with_chat.werewolf_private_chat == []


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
