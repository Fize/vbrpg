# -*- coding: utf-8 -*-
"""Unit tests for werewolf AI agents."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.games.base.agent import BaseGameAgent
from src.games.werewolf.agents import (
    WerewolfAgent,
    SeerAgent,
    WitchAgent,
    HunterAgent,
    VillagerAgent,
)


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


class TestBaseGameAgent:
    """Tests for BaseGameAgent base functionality (via WerewolfAgent)."""

    def test_initial_state(self):
        """Test initial agent state."""
        agent = WerewolfAgent(
            player_id="p1",
            player_name="TestPlayer",
            seat_number=1,
        )

        assert agent.player_id == "p1"
        assert agent.player_name == "TestPlayer"
        assert agent.seat_number == 1
        assert agent.is_alive is True
        assert agent.memory == []

    def test_add_memory(self):
        """Test adding memory events."""
        agent = WerewolfAgent(
            player_id="p1",
            player_name="TestPlayer",
            seat_number=1,
        )

        agent.add_memory({
            "type": "speech",
            "day": 1,
            "content": "我是好人",
        })

        assert len(agent.memory) == 1
        assert agent.memory[0]["type"] == "speech"

    def test_get_system_prompt(self, sample_game_state):
        """Test getting system prompt."""
        agent = WerewolfAgent(
            player_id="p1",
            player_name="TestPlayer",
            seat_number=1,
        )

        prompt = agent.get_system_prompt(sample_game_state)
        assert isinstance(prompt, str)
        assert len(prompt) > 0


class TestWerewolfAgent:
    """Tests for WerewolfAgent."""

    def test_role_properties(self):
        """Test werewolf role properties."""
        agent = WerewolfAgent(
            player_id="p1",
            player_name="TestWolf",
            seat_number=1,
        )

        assert agent.role_type == "werewolf"
        assert agent.team == "werewolf"

    def test_set_teammates(self):
        """Test setting werewolf teammates."""
        agent = WerewolfAgent(
            player_id="p1",
            player_name="TestWolf",
            seat_number=1,
        )

        teammates = [
            {"seat_number": 3, "name": "Wolf_2", "is_alive": True},
            {"seat_number": 5, "name": "Wolf_3", "is_alive": True},
        ]
        agent.set_teammates(teammates)

        assert len(agent.teammates) == 2
        # Should add to known info
        assert len(agent.known_info) == 2

    def test_get_system_prompt(self, sample_game_state):
        """Test getting system prompt."""
        agent = WerewolfAgent(
            player_id="p1",
            player_name="TestWolf",
            seat_number=1,
            teammates=[{"seat_number": 3, "name": "Wolf_2", "is_alive": True}],
        )

        prompt = agent.get_system_prompt(sample_game_state)

        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert "狼人" in prompt

    def test_format_known_info_empty(self):
        """Test formatting empty known info."""
        agent = WerewolfAgent(
            player_id="p1",
            player_name="TestPlayer",
            seat_number=1,
        )

        result = agent.format_known_info()
        assert result == "暂无已知信息"

    def test_format_known_info_with_content(self):
        """Test formatting known info with content."""
        agent = WerewolfAgent(
            player_id="p1",
            player_name="TestPlayer",
            seat_number=1,
        )

        agent.set_teammates([
            {"seat_number": 3, "name": "Wolf_2", "is_alive": True},
        ])

        result = agent.format_known_info()
        assert "3号" in result

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
        )

        decision = await agent.decide_night_action(
            sample_game_state, sample_available_targets, llm_client=mock_llm_client
        )

        assert "action" in decision
        assert "target" in decision
        assert "reasoning" in decision

    @pytest.mark.asyncio
    async def test_discuss_night_target(self, mock_llm_client, sample_game_state, sample_available_targets):
        """Test werewolf night discussion."""
        mock_llm_client.generate = AsyncMock(
            return_value='{"suggested_target": 5, "opinion": "建议击杀5号"}'
        )

        agent = WerewolfAgent(
            player_id="p1",
            player_name="TestWolf",
            seat_number=1,
            teammates=[{"seat_number": 3, "name": "Wolf_2", "is_alive": True}],
        )

        result = await agent.discuss_night_target(
            sample_game_state, sample_available_targets, llm_client=mock_llm_client
        )

        assert "suggested_target" in result
        assert result["seat_number"] == 1
        assert result["name"] == "TestWolf"

    @pytest.mark.asyncio
    async def test_make_final_kill_decision(self, mock_llm_client, sample_game_state, sample_available_targets):
        """Test werewolf final kill decision."""
        mock_llm_client.generate = AsyncMock(
            return_value='{"action": "kill", "target": 5, "reasoning": "最终决定击杀5号"}'
        )

        agent = WerewolfAgent(
            player_id="p1",
            player_name="TestWolf",
            seat_number=1,
            teammates=[{"seat_number": 3, "name": "Wolf_2", "is_alive": True}],
        )

        teammate_opinions = [
            {"seat_number": 3, "name": "Wolf_2", "suggested_target": 5, "opinion": "5号像女巫"},
            {"seat_number": 1, "name": "TestWolf", "suggested_target": 3, "opinion": "3号像预言家"},
        ]

        result = await agent.make_final_kill_decision(
            sample_game_state, sample_available_targets, teammate_opinions, llm_client=mock_llm_client
        )

        assert "target" in result
        assert result["action"] == "kill"

    def test_parse_json_response_valid(self):
        """Test parsing valid JSON response."""
        agent = WerewolfAgent(
            player_id="p1",
            player_name="TestPlayer",
            seat_number=1,
        )

        response = '{"action": "kill", "target": 3}'
        result = agent._parse_json_response(response)

        assert result["action"] == "kill"
        assert result["target"] == 3

    def test_parse_json_response_with_code_blocks(self):
        """Test parsing JSON response with markdown code blocks."""
        agent = WerewolfAgent(
            player_id="p1",
            player_name="TestPlayer",
            seat_number=1,
        )

        response = '```json\n{"action": "kill", "target": 3}\n```'
        result = agent._parse_json_response(response)

        assert result["action"] == "kill"
        assert result["target"] == 3

    def test_parse_json_response_invalid(self):
        """Test parsing invalid JSON response."""
        agent = WerewolfAgent(
            player_id="p1",
            player_name="TestPlayer",
            seat_number=1,
        )

        response = "not json"
        result = agent._parse_json_response(response)

        assert result == {}


class TestSeerAgent:
    """Tests for SeerAgent."""

    def test_role_properties(self):
        """Test seer role properties."""
        agent = SeerAgent(
            player_id="p1",
            player_name="TestSeer",
            seat_number=1,
        )

        assert agent.role_type == "seer"
        assert agent.team == "villager"

    def test_add_check_result(self):
        """Test adding check result."""
        agent = SeerAgent(
            player_id="p1",
            player_name="TestSeer",
            seat_number=1,
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

    def test_format_check_history_empty(self):
        """Test formatting empty check history."""
        agent = SeerAgent(
            player_id="p1",
            player_name="TestSeer",
            seat_number=1,
        )

        result = agent.format_check_history()
        assert result == "暂无查验记录"

    def test_format_check_history_with_results(self):
        """Test formatting check history with results."""
        agent = SeerAgent(
            player_id="p1",
            player_name="TestSeer",
            seat_number=1,
        )

        agent.add_check_result(3, "Player_3", True, 1)
        agent.add_check_result(5, "Player_5", False, 2)

        result = agent.format_check_history()

        assert "第1夜" in result
        assert "第2夜" in result
        assert "狼人" in result
        assert "好人" in result

    def test_get_confirmed_werewolves(self):
        """Test getting confirmed werewolves."""
        agent = SeerAgent(
            player_id="p1",
            player_name="TestSeer",
            seat_number=1,
        )

        agent.add_check_result(3, "Player_3", True, 1)
        agent.add_check_result(5, "Player_5", False, 2)

        werewolves = agent.get_confirmed_werewolves()
        assert werewolves == [3]

    def test_get_confirmed_good(self):
        """Test getting confirmed good players."""
        agent = SeerAgent(
            player_id="p1",
            player_name="TestSeer",
            seat_number=1,
        )

        agent.add_check_result(3, "Player_3", True, 1)
        agent.add_check_result(5, "Player_5", False, 2)

        good = agent.get_confirmed_good()
        assert good == [5]

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
        )

        decision = await agent.decide_night_action(
            sample_game_state, sample_available_targets, llm_client=mock_llm_client
        )

        assert "action" in decision
        assert "target" in decision
        assert "reasoning" in decision


class TestWitchAgent:
    """Tests for WitchAgent."""

    def test_role_properties(self):
        """Test witch role properties."""
        agent = WitchAgent(
            player_id="p1",
            player_name="TestWitch",
            seat_number=1,
        )

        assert agent.role_type == "witch"
        assert agent.team == "villager"

    def test_initial_potion_status(self):
        """Test initial potion status."""
        agent = WitchAgent(
            player_id="p1",
            player_name="TestWitch",
            seat_number=1,
        )

        assert agent.has_antidote is True
        assert agent.has_poison is True

    def test_use_antidote(self):
        """Test using antidote."""
        agent = WitchAgent(
            player_id="p1",
            player_name="TestWitch",
            seat_number=1,
        )

        result = agent.use_antidote()
        assert result is True
        assert agent.has_antidote is False

        # Second use should fail
        result = agent.use_antidote()
        assert result is False

    def test_use_poison(self):
        """Test using poison."""
        agent = WitchAgent(
            player_id="p1",
            player_name="TestWitch",
            seat_number=1,
        )

        result = agent.use_poison()
        assert result is True
        assert agent.has_poison is False

        # Second use should fail
        result = agent.use_poison()
        assert result is False

    def test_get_potion_status(self):
        """Test getting potion status."""
        agent = WitchAgent(
            player_id="p1",
            player_name="TestWitch",
            seat_number=1,
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
        )

        killed_player = {"seat_number": 3, "name": "Player_3"}

        decision = await agent.decide_night_action(
            sample_game_state,
            sample_available_targets,
            killed_player=killed_player,
            llm_client=mock_llm_client,
        )

        assert "action" in decision
        assert "reasoning" in decision

    @pytest.mark.asyncio
    async def test_decide_self_save(self):
        """Test witch self-save decision on first night."""
        agent = WitchAgent(
            player_id="p1",
            player_name="TestWitch",
            seat_number=1,
        )

        game_state = {"day_number": 1}
        decision = await agent.decide_self_save(game_state)

        assert decision is True

    @pytest.mark.asyncio
    async def test_decide_self_save_not_first_night(self):
        """Test witch self-save decision after first night."""
        agent = WitchAgent(
            player_id="p1",
            player_name="TestWitch",
            seat_number=1,
        )

        game_state = {"day_number": 2}
        decision = await agent.decide_self_save(game_state)

        assert decision is False


class TestHunterAgent:
    """Tests for HunterAgent."""

    def test_role_properties(self):
        """Test hunter role properties."""
        agent = HunterAgent(
            player_id="p1",
            player_name="TestHunter",
            seat_number=1,
        )

        assert agent.role_type == "hunter"
        assert agent.team == "villager"

    def test_initial_can_shoot(self):
        """Test initial shooting ability."""
        agent = HunterAgent(
            player_id="p1",
            player_name="TestHunter",
            seat_number=1,
        )

        assert agent.can_shoot is True

    def test_disable_shoot(self):
        """Test disabling shooting ability."""
        agent = HunterAgent(
            player_id="p1",
            player_name="TestHunter",
            seat_number=1,
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
        )

        decision = await agent.decide_night_action(
            sample_game_state, sample_available_targets, llm_client=mock_llm_client
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
        )

        decision = await agent.decide_shoot(
            sample_game_state,
            death_reason="poisoned",
            available_targets=sample_available_targets,
            llm_client=mock_llm_client,
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
        )

        decision = await agent.decide_shoot(
            sample_game_state,
            death_reason="killed",
            available_targets=sample_available_targets,
            llm_client=mock_llm_client,
        )

        assert decision["action"] == "shoot"
        assert decision["target"] is not None


class TestVillagerAgent:
    """Tests for VillagerAgent."""

    def test_role_properties(self):
        """Test villager role properties."""
        agent = VillagerAgent(
            player_id="p1",
            player_name="TestVillager",
            seat_number=1,
        )

        assert agent.role_type == "villager"
        assert agent.team == "villager"

    @pytest.mark.asyncio
    async def test_decide_night_action_pass(
        self, mock_llm_client, sample_game_state, sample_available_targets
    ):
        """Test villager has no night action."""
        agent = VillagerAgent(
            player_id="p1",
            player_name="TestVillager",
            seat_number=1,
        )

        decision = await agent.decide_night_action(
            sample_game_state, sample_available_targets, llm_client=mock_llm_client
        )

        assert decision["action"] == "pass"
        assert decision["target"] is None


class TestAgentCreation:
    """Tests for creating agents from different roles."""

    def test_create_all_agent_types(self):
        """Test creating all agent types."""
        agents = [
            WerewolfAgent("p1", "Wolf", 1),
            SeerAgent("p2", "Seer", 2),
            WitchAgent("p3", "Witch", 3),
            HunterAgent("p4", "Hunter", 4),
            VillagerAgent("p5", "Villager", 5),
        ]

        for agent in agents:
            assert isinstance(agent, BaseGameAgent)
            assert agent.is_alive is True
            assert agent.memory == []

    def test_agents_have_correct_teams(self):
        """Test that agents belong to correct teams."""
        werewolf = WerewolfAgent("p1", "Wolf", 1)
        seer = SeerAgent("p2", "Seer", 2)
        witch = WitchAgent("p3", "Witch", 3)
        hunter = HunterAgent("p4", "Hunter", 4)
        villager = VillagerAgent("p5", "Villager", 5)

        assert werewolf.team == "werewolf"
        assert seer.team == "villager"
        assert witch.team == "villager"
        assert hunter.team == "villager"
        assert villager.team == "villager"


class TestGenerateSpeech:
    """Tests for BaseGameAgent.generate_speech."""

    @pytest.fixture
    def mock_llm_speech(self):
        """Create a mock LLM client that returns plain text speech."""
        client = MagicMock()
        client.generate = AsyncMock(return_value="我是好人")
        return client

    @pytest.mark.asyncio
    async def test_generate_speech_returns_string(self, mock_llm_speech, sample_game_state):
        """Test generate_speech returns the LLM response as a string."""
        agent = VillagerAgent(
            seat_number=5,
            player_name="P5",
            player_id="p5",
        )

        response = await agent.generate_speech(
            game_state=sample_game_state,
            llm_client=mock_llm_speech,
        )

        assert response == "我是好人"

    @pytest.mark.asyncio
    async def test_generate_speech_prompt_format(self, mock_llm_speech, sample_game_state):
        """Test generate_speech builds the correct prompt structure."""
        agent = VillagerAgent(
            seat_number=5,
            player_name="P5",
            player_id="p5",
        )

        await agent.generate_speech(
            game_state=sample_game_state,
            llm_client=mock_llm_speech,
        )

        # Verify the mock was called with the right message format
        call_kwargs = mock_llm_speech.generate.call_args.kwargs
        messages = call_kwargs["messages"]
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert "P5" in messages[1]["content"]
        assert "第1天" in messages[1]["content"]
        assert "白天讨论" in messages[1]["content"]


class TestDecideVote:
    """Tests for BaseGameAgent.decide_vote."""

    @pytest.mark.asyncio
    async def test_decide_vote_returns_target(self, sample_game_state):
        """Test decide_vote returns the target from LLM response."""
        agent = VillagerAgent(
            seat_number=5,
            player_name="P5",
            player_id="p5",
        )

        mock_client = MagicMock()
        mock_client.generate = AsyncMock(
            return_value='{"target": 3, "reasoning": "test"}'
        )

        available_targets = [
            {"seat_number": i, "name": f"P{i}"}
            for i in range(1, 11)
            if i != 5
        ]

        result = await agent.decide_vote(
            game_state=sample_game_state,
            available_targets=available_targets,
            llm_client=mock_client,
        )

        assert result["target"] == 3
        assert result["reasoning"] == "test"

    @pytest.mark.asyncio
    async def test_decide_vote_fallback_on_parse_failure(self, sample_game_state):
        """Test decide_vote falls back to first available target on JSON parse failure."""
        agent = VillagerAgent(
            seat_number=5,
            player_name="P5",
            player_id="p5",
        )

        mock_client = MagicMock()
        mock_client.generate = AsyncMock(return_value="not json")

        available_targets = [
            {"seat_number": i, "name": f"P{i}"}
            for i in range(1, 11)
            if i != 5
        ]

        result = await agent.decide_vote(
            game_state=sample_game_state,
            available_targets=available_targets,
            llm_client=mock_client,
        )

        assert result["target"] == 1  # first available seat_number
        assert "解析失败" in result["reasoning"]
