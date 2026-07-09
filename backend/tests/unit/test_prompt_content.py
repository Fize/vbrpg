# -*- coding: utf-8 -*-
"""Tests for prompt content — verifies speech history is included and private info is not leaked."""

import pytest

from src.games.werewolf.agents import (
    WerewolfAgent,
    SeerAgent,
    WitchAgent,
    HunterAgent,
    VillagerAgent,
)


@pytest.fixture
def sample_game_state():
    """Create sample game state with speech history, no role info in player dicts."""
    return {
        "day_number": 2,
        "phase": "night",
        "alive_players": [
            {"seat_number": i, "name": f"Player_{i}", "player_id": f"p{i}"}
            for i in range(1, 11)
            if i != 2  # Player_2 is dead
        ],
        "dead_players": [
            {"seat_number": 2, "name": "Player_2", "player_id": "p2"},
        ],
        "speech_history": (
            "1号Player_1: 我觉得今天应该先听大家发言\n"
            "3号Player_3: 我认为2号很可疑\n"
            "4号Player_4: 我同意3号的观点\n"
        ),
        "vote_history": [],
        "death_history": [],
    }


class TestPromptContent:
    """Verify all agent prompts contain public speech history and don't leak private info."""

    # ── T1.1: Villager ──────────────────────────────────────────────

    def test_villager_prompt_has_speech_history(self, sample_game_state):
        """Villager prompt should include speech history section with player names."""
        agent = VillagerAgent(player_id="p5", player_name="Player_5", seat_number=5)
        prompt = agent.get_system_prompt(sample_game_state)

        assert "白天发言记录" in prompt
        assert "1号Player_1" in prompt
        assert "Player_1" in prompt
        assert "5号Player_5" in prompt

    # ── T1.2: Witch ─────────────────────────────────────────────────

    def test_witch_prompt_has_speech_history(self, sample_game_state):
        """Witch prompt should include speech history section."""
        agent = WitchAgent(player_id="p3", player_name="Player_3", seat_number=3)
        prompt = agent.get_system_prompt(sample_game_state)

        assert "白天发言记录" in prompt

    # ── T1.3: Werewolf ──────────────────────────────────────────────

    def test_werewolf_prompt_has_speech_history(self, sample_game_state):
        """Werewolf prompt should include speech history section."""
        agent = WerewolfAgent(player_id="p1", player_name="Player_1", seat_number=1)
        agent.set_teammates([{"seat_number": 6, "name": "Player_6", "player_id": "p6"}])
        prompt = agent.get_system_prompt(sample_game_state)

        assert "白天发言记录" in prompt

    # ── T1.4: Seer ──────────────────────────────────────────────────

    def test_seer_prompt_has_speech_history(self, sample_game_state):
        """Seer prompt should include speech history section."""
        agent = SeerAgent(player_id="p7", player_name="Player_7", seat_number=7)
        prompt = agent.get_system_prompt(sample_game_state)

        assert "白天发言记录" in prompt

    # ── T1.5: Hunter ────────────────────────────────────────────────

    def test_hunter_prompt_has_speech_history(self, sample_game_state):
        """Hunter prompt should include speech history section."""
        agent = HunterAgent(player_id="p4", player_name="Player_4", seat_number=4)
        prompt = agent.get_system_prompt(sample_game_state)

        assert "白天发言记录" in prompt

    # ── T1.6: No role leakage ───────────────────────────────────────

    def test_all_prompts_no_role_leakage(self, sample_game_state):
        """No agent prompt should contain the literal word 'role' in the rendered text."""
        agents = [
            ("villager", VillagerAgent(player_id="p5", player_name="Player_5", seat_number=5)),
            ("witch", WitchAgent(player_id="p3", player_name="Player_3", seat_number=3)),
            ("seer", SeerAgent(player_id="p7", player_name="Player_7", seat_number=7)),
            ("hunter", HunterAgent(player_id="p4", player_name="Player_4", seat_number=4)),
        ]
        # Werewolf needs a teammate to avoid an ambiguous assertion; set one here too.
        ww = WerewolfAgent(player_id="p1", player_name="Player_1", seat_number=1)
        ww.set_teammates([{"seat_number": 6, "name": "Player_6", "player_id": "p6"}])
        agents.append(("werewolf", ww))

        for name, agent in agents:
            prompt = agent.get_system_prompt(sample_game_state)
            assert "'role'" not in prompt, (
                f"{name} prompt leaked 'role': {prompt[:200]}"
            )

    # ── T1.7: Alive / dead players in villager prompt ───────────────

    def test_villager_prompt_has_alive_dead_players(self, sample_game_state):
        """Villager prompt should list alive and dead players."""
        agent = VillagerAgent(player_id="p5", player_name="Player_5", seat_number=5)
        prompt = agent.get_system_prompt(sample_game_state)

        assert "存活玩家" in prompt
        assert "已死亡玩家" in prompt
        assert "Player_1" in prompt  # alive
        assert "Player_2" in prompt  # dead

    # ── T1.8: Speech history empty on day 1 ─────────────────────────

    def test_speech_history_empty_on_day_1(self):
        """Prompt should handle day 1 with no speech history gracefully."""
        game_state = {
            "day_number": 1,
            "phase": "night",
            "alive_players": [
                {"seat_number": i, "name": f"Player_{i}", "player_id": f"p{i}"}
                for i in range(1, 11)
            ],
            "dead_players": [],
            "speech_history": "",
            "vote_history": [],
            "death_history": [],
        }

        agent = VillagerAgent(player_id="p5", player_name="Player_5", seat_number=5)
        prompt = agent.get_system_prompt(game_state)

        assert isinstance(prompt, str)
        assert len(prompt) > 0
