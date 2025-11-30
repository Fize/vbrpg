# -*- coding: utf-8 -*-
"""Unit tests for werewolf AI agents."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.ai_agents.base import BaseWerewolfAgent
from src.services.ai_agents.werewolf_agent import WerewolfAgent
from src.services.ai_agents.seer_agent import SeerAgent
from src.services.ai_agents.witch_agent import WitchAgent
from src.services.ai_agents.hunter_agent import HunterAgent
from src.services.ai_agents.villager_agent import VillagerAgent


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client."""
    client = MagicMock()
    client.generate = AsyncMock(return_value='{"action": "test", "target": 1, "reasoning": "test"}')
    client.generate_stream = AsyncMock(return_value=iter(["测", "试", "发", "言"]))
    return client


@pytest.fixture
def sample_game_state():
    """Create sample game state for testing."""
    return {
        "day_number": 1,
        "phase": "night",
        "alive_players": [
            {"seat_number": i, "name": f"Player_{i}", "player_id": f"p{i}"}
            for i in range(1, 11)
        ],
        "dead_players": [],
    }


@pytest.fixture
def sample_available_targets():
    """Create sample available targets."""
    return [
        {"seat_number": i, "name": f"Player_{i}", "player_id": f"p{i}"}
        for i in range(1, 11)
    ]


class TestBaseWerewolfAgent:
    """Tests for BaseWerewolfAgent base functionality."""

    def test_add_known_info(self, mock_llm_client):
        """Test adding known information."""
        agent = WerewolfAgent(
            player_id="p1",
            player_name="TestPlayer",
            seat_number=1,
            llm_client=mock_llm_client,
        )

        agent.add_known_info({
            "type": "check_result",
            "content": "3号是好人",
        })

        assert len(agent.known_info) == 1
        assert agent.known_info[0]["type"] == "check_result"

    def test_add_memory(self, mock_llm_client):
        """Test adding memory events."""
        agent = WerewolfAgent(
            player_id="p1",
            player_name="TestPlayer",
            seat_number=1,
            llm_client=mock_llm_client,
        )

        agent.add_memory({
            "type": "speech",
            "day": 1,
            "content": "我是好人",
        })

        assert len(agent.memory) == 1
        assert agent.memory[0]["type"] == "speech"

    def test_format_known_info_empty(self, mock_llm_client):
        """Test formatting empty known info."""
        agent = WerewolfAgent(
            player_id="p1",
            player_name="TestPlayer",
            seat_number=1,
            llm_client=mock_llm_client,
        )

        result = agent.format_known_info()
        assert result == "暂无已知信息"

    def test_format_known_info_with_content(self, mock_llm_client):
        """Test formatting known info with content."""
        agent = WerewolfAgent(
            player_id="p1",
            player_name="TestPlayer",
            seat_number=1,
            llm_client=mock_llm_client,
        )

        agent.add_known_info({"type": "check", "content": "3号是狼人"})

        result = agent.format_known_info()
        assert "3号是狼人" in result
        assert "[check]" in result

    def test_format_game_state(self, mock_llm_client, sample_game_state):
        """Test formatting game state."""
        agent = WerewolfAgent(
            player_id="p1",
            player_name="TestPlayer",
            seat_number=1,
            llm_client=mock_llm_client,
        )

        formatted = agent.format_game_state(sample_game_state)

        assert formatted["day_number"] == "1"
        assert "1号Player_1" in formatted["alive_players"]
        assert formatted["dead_players"] == "无"

    def test_set_dead(self, mock_llm_client):
        """Test marking agent as dead."""
        agent = WerewolfAgent(
            player_id="p1",
            player_name="TestPlayer",
            seat_number=1,
            llm_client=mock_llm_client,
        )

        assert agent.is_alive is True
        agent.set_dead()
        assert agent.is_alive is False

    def test_parse_json_response_valid(self, mock_llm_client):
        """Test parsing valid JSON response."""
        agent = WerewolfAgent(
            player_id="p1",
            player_name="TestPlayer",
            seat_number=1,
            llm_client=mock_llm_client,
        )

        response = '{"action": "kill", "target": 3}'
        result = agent._parse_json_response(response)

        assert result["action"] == "kill"
        assert result["target"] == 3

    def test_parse_json_response_with_code_blocks(self, mock_llm_client):
        """Test parsing JSON response with markdown code blocks."""
        agent = WerewolfAgent(
            player_id="p1",
            player_name="TestPlayer",
            seat_number=1,
            llm_client=mock_llm_client,
        )

        response = '```json\n{"action": "kill", "target": 3}\n```'
        result = agent._parse_json_response(response)

        assert result["action"] == "kill"
        assert result["target"] == 3

    def test_parse_json_response_invalid(self, mock_llm_client):
        """Test parsing invalid JSON response."""
        agent = WerewolfAgent(
            player_id="p1",
            player_name="TestPlayer",
            seat_number=1,
            llm_client=mock_llm_client,
        )

        response = "not json"
        result = agent._parse_json_response(response)

        assert result == {}


class TestWerewolfAgent:
    """Tests for WerewolfAgent."""

    def test_role_properties(self, mock_llm_client):
        """Test werewolf role properties."""
        agent = WerewolfAgent(
            player_id="p1",
            player_name="TestWolf",
            seat_number=1,
            llm_client=mock_llm_client,
        )

        assert agent.role_type == "werewolf"
        assert agent.team == "werewolf"
        assert agent.role_name == "狼人"
        assert agent.team_name == "狼人阵营"

    def test_set_teammates(self, mock_llm_client):
        """Test setting werewolf teammates."""
        agent = WerewolfAgent(
            player_id="p1",
            player_name="TestWolf",
            seat_number=1,
            llm_client=mock_llm_client,
        )

        teammates = [
            {"seat_number": 3, "name": "Wolf_2", "is_alive": True},
            {"seat_number": 5, "name": "Wolf_3", "is_alive": True},
        ]
        agent.set_teammates(teammates)

        assert len(agent.teammates) == 2
        # Should add to known info
        assert len(agent.known_info) == 2

    def test_get_system_prompt(self, mock_llm_client, sample_game_state):
        """Test getting system prompt."""
        agent = WerewolfAgent(
            player_id="p1",
            player_name="TestWolf",
            seat_number=1,
            teammates=[{"seat_number": 3, "name": "Wolf_2", "is_alive": True}],
            llm_client=mock_llm_client,
        )

        prompt = agent.get_system_prompt(sample_game_state)

        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert "狼人" in prompt

    @pytest.mark.asyncio
    async def test_decide_night_action(
        self, mock_llm_client, sample_game_state, sample_available_targets
    ):
        """Test werewolf night action decision."""
        mock_llm_client.generate = AsyncMock(
            return_value='{"action": "kill", "target": 5, "reasoning": "选择击杀"}'
        )

        agent = WerewolfAgent(
            player_id="p1",
            player_name="TestWolf",
            seat_number=1,
            teammates=[{"seat_number": 3, "name": "Wolf_2", "is_alive": True}],
            llm_client=mock_llm_client,
        )

        decision = await agent.decide_night_action(
            sample_game_state, sample_available_targets
        )

        assert "action" in decision
        assert "target" in decision
        assert "reasoning" in decision


class TestSeerAgent:
    """Tests for SeerAgent."""

    def test_role_properties(self, mock_llm_client):
        """Test seer role properties."""
        agent = SeerAgent(
            player_id="p1",
            player_name="TestSeer",
            seat_number=1,
            llm_client=mock_llm_client,
        )

        assert agent.role_type == "seer"
        assert agent.team == "villager"
        assert agent.role_name == "预言家"
        assert agent.team_name == "好人阵营"

    def test_add_check_result(self, mock_llm_client):
        """Test adding check result."""
        agent = SeerAgent(
            player_id="p1",
            player_name="TestSeer",
            seat_number=1,
            llm_client=mock_llm_client,
        )

        agent.add_check_result(
            seat_number=3,
            player_name="Player_3",
            is_werewolf=True,
            day=1,
        )

        assert len(agent.check_history) == 1
        assert agent.check_history[0]["is_werewolf"] is True
        assert len(agent.known_info) == 1

    def test_format_check_history_empty(self, mock_llm_client):
        """Test formatting empty check history."""
        agent = SeerAgent(
            player_id="p1",
            player_name="TestSeer",
            seat_number=1,
            llm_client=mock_llm_client,
        )

        result = agent.format_check_history()
        assert result == "暂无查验记录"

    def test_format_check_history_with_results(self, mock_llm_client):
        """Test formatting check history with results."""
        agent = SeerAgent(
            player_id="p1",
            player_name="TestSeer",
            seat_number=1,
            llm_client=mock_llm_client,
        )

        agent.add_check_result(3, "Player_3", True, 1)
        agent.add_check_result(5, "Player_5", False, 2)

        result = agent.format_check_history()

        assert "第1夜" in result
        assert "第2夜" in result
        assert "狼人" in result
        assert "好人" in result

    @pytest.mark.asyncio
    async def test_decide_night_action(
        self, mock_llm_client, sample_game_state, sample_available_targets
    ):
        """Test seer night action decision."""
        mock_llm_client.generate = AsyncMock(
            return_value='{"action": "check", "target": 3, "reasoning": "选择查验"}'
        )

        agent = SeerAgent(
            player_id="p1",
            player_name="TestSeer",
            seat_number=1,
            llm_client=mock_llm_client,
        )

        decision = await agent.decide_night_action(
            sample_game_state, sample_available_targets
        )

        assert "action" in decision
        assert "target" in decision
        assert "reasoning" in decision


class TestWitchAgent:
    """Tests for WitchAgent."""

    def test_role_properties(self, mock_llm_client):
        """Test witch role properties."""
        agent = WitchAgent(
            player_id="p1",
            player_name="TestWitch",
            seat_number=1,
            llm_client=mock_llm_client,
        )

        assert agent.role_type == "witch"
        assert agent.team == "villager"
        assert agent.role_name == "女巫"

    def test_initial_potion_status(self, mock_llm_client):
        """Test initial potion status."""
        agent = WitchAgent(
            player_id="p1",
            player_name="TestWitch",
            seat_number=1,
            llm_client=mock_llm_client,
        )

        assert agent.has_antidote is True
        assert agent.has_poison is True

    def test_use_antidote(self, mock_llm_client):
        """Test using antidote."""
        agent = WitchAgent(
            player_id="p1",
            player_name="TestWitch",
            seat_number=1,
            llm_client=mock_llm_client,
        )

        result = agent.use_antidote()
        assert result is True
        assert agent.has_antidote is False

        # Second use should fail
        result = agent.use_antidote()
        assert result is False

    def test_use_poison(self, mock_llm_client):
        """Test using poison."""
        agent = WitchAgent(
            player_id="p1",
            player_name="TestWitch",
            seat_number=1,
            llm_client=mock_llm_client,
        )

        result = agent.use_poison()
        assert result is True
        assert agent.has_poison is False

        # Second use should fail
        result = agent.use_poison()
        assert result is False

    def test_get_potion_status(self, mock_llm_client):
        """Test getting potion status."""
        agent = WitchAgent(
            player_id="p1",
            player_name="TestWitch",
            seat_number=1,
            llm_client=mock_llm_client,
        )

        status = agent.get_potion_status()
        assert status["antidote"] == "有"
        assert status["poison"] == "有"

        agent.use_antidote()
        status = agent.get_potion_status()
        assert status["antidote"] == "已使用"
        assert status["poison"] == "有"

    @pytest.mark.asyncio
    async def test_decide_night_action(
        self, mock_llm_client, sample_game_state, sample_available_targets
    ):
        """Test witch night action decision."""
        mock_llm_client.generate = AsyncMock(
            return_value='{"action": "save", "target": null, "reasoning": "救人"}'
        )

        agent = WitchAgent(
            player_id="p1",
            player_name="TestWitch",
            seat_number=1,
            llm_client=mock_llm_client,
        )

        killed_player = {"seat_number": 3, "name": "Player_3"}

        decision = await agent.decide_night_action(
            sample_game_state,
            sample_available_targets,
            killed_player=killed_player,
        )

        assert "action" in decision
        assert "reasoning" in decision


class TestHunterAgent:
    """Tests for HunterAgent."""

    def test_role_properties(self, mock_llm_client):
        """Test hunter role properties."""
        agent = HunterAgent(
            player_id="p1",
            player_name="TestHunter",
            seat_number=1,
            llm_client=mock_llm_client,
        )

        assert agent.role_type == "hunter"
        assert agent.team == "villager"
        assert agent.role_name == "猎人"

    def test_initial_can_shoot(self, mock_llm_client):
        """Test initial shooting ability."""
        agent = HunterAgent(
            player_id="p1",
            player_name="TestHunter",
            seat_number=1,
            llm_client=mock_llm_client,
        )

        assert agent.can_shoot is True

    def test_disable_shoot(self, mock_llm_client):
        """Test disabling shooting ability."""
        agent = HunterAgent(
            player_id="p1",
            player_name="TestHunter",
            seat_number=1,
            llm_client=mock_llm_client,
        )

        agent.disable_shoot()
        assert agent.can_shoot is False

    @pytest.mark.asyncio
    async def test_decide_night_action_pass(
        self, mock_llm_client, sample_game_state, sample_available_targets
    ):
        """Test hunter has no night action."""
        agent = HunterAgent(
            player_id="p1",
            player_name="TestHunter",
            seat_number=1,
            llm_client=mock_llm_client,
        )

        decision = await agent.decide_night_action(
            sample_game_state, sample_available_targets
        )

        assert decision["action"] == "pass"
        assert decision["target"] is None

    @pytest.mark.asyncio
    async def test_decide_shoot_when_poisoned(
        self, mock_llm_client, sample_game_state, sample_available_targets
    ):
        """Test hunter cannot shoot when poisoned."""
        agent = HunterAgent(
            player_id="p1",
            player_name="TestHunter",
            seat_number=1,
            llm_client=mock_llm_client,
        )

        decision = await agent.decide_shoot(
            sample_game_state,
            death_reason="poisoned",
            available_targets=sample_available_targets,
        )

        assert decision["action"] == "no_shoot"
        assert "毒" in decision["reasoning"]

    @pytest.mark.asyncio
    async def test_decide_shoot_when_killed(
        self, mock_llm_client, sample_game_state, sample_available_targets
    ):
        """Test hunter can shoot when killed."""
        mock_llm_client.generate = AsyncMock(
            return_value='{"action": "shoot", "target": 3, "reasoning": "开枪带走"}'
        )

        agent = HunterAgent(
            player_id="p1",
            player_name="TestHunter",
            seat_number=1,
            llm_client=mock_llm_client,
        )

        decision = await agent.decide_shoot(
            sample_game_state,
            death_reason="killed",
            available_targets=sample_available_targets,
        )

        assert decision["action"] == "shoot"
        assert decision["target"] is not None


class TestVillagerAgent:
    """Tests for VillagerAgent."""

    def test_role_properties(self, mock_llm_client):
        """Test villager role properties."""
        agent = VillagerAgent(
            player_id="p1",
            player_name="TestVillager",
            seat_number=1,
            llm_client=mock_llm_client,
        )

        assert agent.role_type == "villager"
        assert agent.team == "villager"
        assert agent.role_name == "村民"

    @pytest.mark.asyncio
    async def test_decide_night_action_pass(
        self, mock_llm_client, sample_game_state, sample_available_targets
    ):
        """Test villager has no night action."""
        agent = VillagerAgent(
            player_id="p1",
            player_name="TestVillager",
            seat_number=1,
            llm_client=mock_llm_client,
        )

        decision = await agent.decide_night_action(
            sample_game_state, sample_available_targets
        )

        assert decision["action"] == "pass"
        assert decision["target"] is None


class TestSpeechGeneration:
    """Tests for speech generation."""

    @pytest.mark.asyncio
    async def test_generate_speech_fallback(
        self, mock_llm_client, sample_game_state
    ):
        """Test speech generation fallback on error."""
        mock_llm_client.generate = AsyncMock(side_effect=Exception("API Error"))

        agent = VillagerAgent(
            player_id="p1",
            player_name="TestVillager",
            seat_number=1,
            llm_client=mock_llm_client,
        )

        speech = await agent.generate_speech(sample_game_state, [])

        # Should return fallback message
        assert "1号" in speech

    @pytest.mark.asyncio
    async def test_generate_speech_success(
        self, mock_llm_client, sample_game_state
    ):
        """Test successful speech generation."""
        mock_llm_client.generate = AsyncMock(
            return_value="大家好，我是村民，我觉得3号很可疑。"
        )

        agent = VillagerAgent(
            player_id="p1",
            player_name="TestVillager",
            seat_number=1,
            llm_client=mock_llm_client,
        )

        speech = await agent.generate_speech(sample_game_state, [])

        assert speech == "大家好，我是村民，我觉得3号很可疑。"
        # Should add to memory
        assert len(agent.memory) == 1


class TestVoteDecision:
    """Tests for vote decision."""

    @pytest.mark.asyncio
    async def test_decide_vote_success(
        self, mock_llm_client, sample_game_state, sample_available_targets
    ):
        """Test vote decision success."""
        mock_llm_client.generate = AsyncMock(
            return_value='{"action": "vote", "target": 3, "reasoning": "3号发言很可疑"}'
        )

        agent = VillagerAgent(
            player_id="p1",
            player_name="TestVillager",
            seat_number=1,
            llm_client=mock_llm_client,
        )

        decision = await agent.decide_vote(
            sample_game_state,
            speech_summary="各位玩家发言完毕",
            voteable_players=sample_available_targets,
        )

        assert decision["action"] == "vote"
        assert decision["target"] == 3
        assert len(agent.memory) == 1  # Vote added to memory

    @pytest.mark.asyncio
    async def test_decide_vote_abstain(
        self, mock_llm_client, sample_game_state, sample_available_targets
    ):
        """Test vote abstain decision."""
        mock_llm_client.generate = AsyncMock(
            return_value='{"action": "abstain", "target": null, "reasoning": "信息不足"}'
        )

        agent = VillagerAgent(
            player_id="p1",
            player_name="TestVillager",
            seat_number=1,
            llm_client=mock_llm_client,
        )

        decision = await agent.decide_vote(
            sample_game_state,
            speech_summary="各位玩家发言完毕",
            voteable_players=sample_available_targets,
        )

        assert decision["action"] == "abstain"
        assert decision["target"] is None

    @pytest.mark.asyncio
    async def test_decide_vote_fallback_on_error(
        self, mock_llm_client, sample_game_state, sample_available_targets
    ):
        """Test vote fallback on error."""
        mock_llm_client.generate = AsyncMock(side_effect=Exception("API Error"))

        agent = VillagerAgent(
            player_id="p1",
            player_name="TestVillager",
            seat_number=1,
            llm_client=mock_llm_client,
        )

        decision = await agent.decide_vote(
            sample_game_state,
            speech_summary="各位玩家发言完毕",
            voteable_players=sample_available_targets,
        )

        # Should abstain on error
        assert decision["action"] == "abstain"


class TestAgentCreation:
    """Tests for creating agents from different roles."""

    def test_create_all_agent_types(self, mock_llm_client):
        """Test creating all agent types."""
        agents = [
            WerewolfAgent("p1", "Wolf", 1, llm_client=mock_llm_client),
            SeerAgent("p2", "Seer", 2, llm_client=mock_llm_client),
            WitchAgent("p3", "Witch", 3, llm_client=mock_llm_client),
            HunterAgent("p4", "Hunter", 4, llm_client=mock_llm_client),
            VillagerAgent("p5", "Villager", 5, llm_client=mock_llm_client),
        ]

        # All should be instances of BaseWerewolfAgent
        for agent in agents:
            assert isinstance(agent, BaseWerewolfAgent)
            assert agent.is_alive is True
            assert agent.known_info == []
            assert agent.memory == []

    def test_agents_have_correct_teams(self, mock_llm_client):
        """Test that agents belong to correct teams."""
        werewolf = WerewolfAgent("p1", "Wolf", 1, llm_client=mock_llm_client)
        seer = SeerAgent("p2", "Seer", 2, llm_client=mock_llm_client)
        witch = WitchAgent("p3", "Witch", 3, llm_client=mock_llm_client)
        hunter = HunterAgent("p4", "Hunter", 4, llm_client=mock_llm_client)
        villager = VillagerAgent("p5", "Villager", 5, llm_client=mock_llm_client)

        assert werewolf.team == "werewolf"
        assert seer.team == "villager"
        assert witch.team == "villager"
        assert hunter.team == "villager"
        assert villager.team == "villager"
