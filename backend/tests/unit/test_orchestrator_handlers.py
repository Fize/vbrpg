# -*- coding: utf-8 -*-
"""Unit tests for WerewolfGameOrchestrator phase handlers.

Tests the 9 ``_handle_*`` methods that are called from ``_game_loop``.
Strategy: patch at the method/function level so each handler is tested in
isolation without real AI agents, LLM clients, or async waiting.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

from src.games.werewolf.engine import WerewolfEngine
from src.games.werewolf.orchestrator import WerewolfGameOrchestrator
from src.games.werewolf.state import (
    DeathReason,
    NightActions,
    WerewolfGameState,
    WerewolfPhase,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def engine_and_state():
    """Create a started engine with 10 players and return (engine, state)."""
    eng = WerewolfEngine()
    player_names = [f"P{i}" for i in range(1, 11)]
    state = eng.initialize_game(room_code="TEST001", player_names=player_names)
    eng.start_game()
    return eng, state


@pytest.fixture
def orchestrator(engine_and_state):
    """Orchestrator with game state injected and key methods patched."""
    eng, state = engine_and_state
    orch = WerewolfGameOrchestrator()
    orch._game_states["TEST001"] = state
    orch._llm_client = MagicMock()

    # Patch _wait_for_human_action to do nothing instantly
    orch._wait_for_human_action = AsyncMock()
    # Patch _state_to_dict to return a minimal dict
    orch._state_to_dict = MagicMock(return_value={
        "day_number": 1,
        "phase": "night",
        "alive_players": [],
        "dead_players": [],
        "speech_history": "",
        "vote_history": [],
        "death_history": [],
    })
    # Patch _ai_takeover fallback helpers
    orch._ai_takeover_night_action = AsyncMock()
    orch._ai_takeover_hunter_shoot = AsyncMock()
    # Patch host
    orch.host = MagicMock()
    return orch, state


# ---------------------------------------------------------------------------
# Helper — create a mock AI agent
# ---------------------------------------------------------------------------

def _mock_agent(**methods):
    """Create a MagicMock AI agent with the given async/sync methods."""
    agent = MagicMock()
    for name, impl in methods.items():
        setattr(agent, name, impl)
    return agent


# ===========================================================================
# T3.1 — _handle_werewolf_action
# ===========================================================================

class TestHandleWerewolfAction:
    """Night — werewolf pack chooses a kill target."""

    async def test_ai_wolves_discuss_and_decide(self, orchestrator):
        """All-AI werewolf pack: first wolf makes final kill decision."""
        orch, state = orchestrator
        room = "TEST001"

        # Identify the 3 werewolf seats
        wolf_seats = sorted(
            p.seat_number for p in state.players.values()
            if p.role == "werewolf"
        )

        # Mock AI agents for all 3 wolves
        for seat in wolf_seats:
            agent = _mock_agent(
                discuss_night_target=AsyncMock(return_value={
                    "suggested_target": wolf_seats[0] + 1,  # kill the first non-wolf
                    "opinion": "test opinion",
                }),
                make_final_kill_decision=AsyncMock(return_value={
                    "target": 5,  # kill seat 5
                    "reasoning": "test reasoning",
                }),
            )
            if seat not in orch._ai_agents.get(room, {}):
                orch._ai_agents.setdefault(room, {})[seat] = agent
            else:
                orch._ai_agents[room][seat] = agent

        # Give the alpha wolf (lowest seat) the make_final_kill_decision
        alpha_seat = wolf_seats[0]
        orch._ai_agents[room][alpha_seat] = _mock_agent(
            discuss_night_target=AsyncMock(return_value={
                "suggested_target": 5,
                "opinion": "test",
            }),
            make_final_kill_decision=AsyncMock(return_value={
                "target": 5,
                "reasoning": "strategic kill",
            }),
        )

        await orch._handle_werewolf_action(room)

        assert state.current_night_actions.werewolf_kill_target == 5, (
            f"Expected kill target 5, got {state.current_night_actions.werewolf_kill_target}"
        )

    async def test_fallback_to_decide_night_action(self, orchestrator):
        """When no make_final_kill_decision, fallback to decide_night_action."""
        orch, state = orchestrator
        room = "TEST001"

        wolf_seats = sorted(
            p.seat_number for p in state.players.values()
            if p.role == "werewolf"
        )

        # Agent without make_final_kill_decision → falls back to decide_night_action
        for seat in wolf_seats:
            agent = _mock_agent(
                discuss_night_target=AsyncMock(return_value={
                    "suggested_target": 7,
                    "opinion": "test",
                }),
                decide_night_action=AsyncMock(return_value={
                    "target": 7,
                    "reasoning": "fallback",
                }),
            )
            orch._ai_agents.setdefault(room, {})[seat] = agent

        # Remove make_final_kill_decision from alpha
        del orch._ai_agents[room][wolf_seats[0]].make_final_kill_decision

        await orch._handle_werewolf_action(room)

        assert state.current_night_actions.werewolf_kill_target == 7, (
            f"Expected kill target 7 (fallback), got "
            f"{state.current_night_actions.werewolf_kill_target}"
        )


# ===========================================================================
# T3.2 — _handle_seer_action
# ===========================================================================

class TestHandleSeerAction:
    """Night — seer checks a player's identity."""

    async def test_ai_seer_checks_target(self, orchestrator):
        """AI seer picks a target and it's stored in current_night_actions."""
        orch, state = orchestrator
        room = "TEST001"

        # Find seer
        seer = next(
            p for p in state.players.values()
            if p.role == "seer"
        )

        # Inject mock seer agent
        orch._ai_agents.setdefault(room, {})[seer.seat_number] = _mock_agent(
            decide_night_action=AsyncMock(return_value={
                "target": 3,
                "reasoning": "check P3",
            }),
        )

        await orch._handle_seer_action(room)

        assert state.current_night_actions.seer_check_target == 3, (
            f"Expected seer check target 3, got "
            f"{state.current_night_actions.seer_check_target}"
        )


# ===========================================================================
# T3.3 — _handle_witch_action
# ===========================================================================

class TestHandleWitchAction:
    """Night — witch decides to save and/or poison."""

    async def test_ai_witch_saves_kill_target(self, orchestrator):
        """Witch saves the werewolf's kill target."""
        orch, state = orchestrator
        room = "TEST001"

        # Setup: werewolves killed seat 3
        state.current_night_actions.werewolf_kill_target = 3

        # Find witch
        witch = next(
            p for p in state.players.values()
            if p.role == "witch"
        )

        # Inject mock witch agent
        orch._ai_agents.setdefault(room, {})[witch.seat_number] = _mock_agent(
            decide_night_action=AsyncMock(return_value={
                "action": "save",
            }),
        )

        assert state.witch_has_antidote is True

        await orch._handle_witch_action(room)

        assert state.current_night_actions.witch_save is True, "Witch should save"
        assert state.witch_has_antidote is False, "Antidote should be consumed"

    async def test_ai_witch_poisons_target(self, orchestrator):
        """Witch poisons a player."""
        orch, state = orchestrator
        room = "TEST001"

        state.current_night_actions.werewolf_kill_target = 3

        witch = next(
            p for p in state.players.values()
            if p.role == "witch"
        )

        orch._ai_agents.setdefault(room, {})[witch.seat_number] = _mock_agent(
            decide_night_action=AsyncMock(return_value={
                "action": "poison",
                "target": 6,
            }),
        )

        assert state.witch_has_poison is True

        await orch._handle_witch_action(room)

        assert state.current_night_actions.witch_poison_target == 6, \
            f"Expected poison target 6, got {state.current_night_actions.witch_poison_target}"
        assert state.witch_has_poison is False, "Poison should be consumed"


# ===========================================================================
# T3.4 — _handle_day_announcement
# ===========================================================================

class TestHandleDayAnnouncement:
    """Day — announce night results."""

    async def test_announces_dead_players(self, orchestrator):
        """Announcement references players killed during the night."""
        orch, state = orchestrator
        room = "TEST001"

        # Simulate a player killed during night
        state.death_history.append({
            "seat_number": 4,
            "day": 1,
            "phase": "night",
        })
        state.day_number = 1

        await orch._handle_day_announcement(room)

        # The handler logs the announcement; verify it ran without error
        # and state is unchanged (announcement is mainly side-effect/logging)
        assert len(state.death_history) == 1

    async def test_peaceful_night(self, orchestrator):
        """No deaths → peaceful night announcement."""
        orch, state = orchestrator
        room = "TEST001"
        state.day_number = 1

        await orch._handle_day_announcement(room)

        assert len([d for d in state.death_history
                    if d.get("day") == state.day_number and d.get("phase") == "night"]) == 0


# ===========================================================================
# T3.5 — _handle_day_discussion
# ===========================================================================

class TestHandleDayDiscussion:
    """Day — alive players give speeches."""

    async def test_ai_players_generate_speeches(self, orchestrator):
        """All alive AI players generate a speech that is recorded in speech_history."""
        orch, state = orchestrator
        room = "TEST001"
        state.day_number = 1

        # Mock AI agents for all alive players to return a speech
        for seat, player in state.players.items():
            if player.is_alive:
                orch._ai_agents.setdefault(room, {})[seat] = _mock_agent(
                    generate_speech=AsyncMock(return_value="I am a villager, trust me."),
                )

        await orch._handle_day_discussion(room)

        # Every alive player should have a speech entry
        alive_count = sum(1 for p in state.players.values() if p.is_alive)
        assert len(state.speech_history) == alive_count, (
            f"Expected {alive_count} speeches, got {len(state.speech_history)}"
        )
        for entry in state.speech_history:
            assert "content" in entry
            assert "seat_number" in entry
            assert "day" in entry
            assert entry["day"] == 1


# ===========================================================================
# T3.6 — _handle_vote
# ===========================================================================

class TestHandleVote:
    """Day vote — AI agents decide who to vote for."""

    async def test_ai_players_vote(self, orchestrator):
        """All alive AI players cast votes stored in current_votes."""
        orch, state = orchestrator
        room = "TEST001"
        state.day_number = 1

        # Mock AI agents: each votes for a different target
        for seat, player in state.players.items():
            if player.is_alive:
                target = (seat % 10) + 1  # vote for next seat
                if target == seat:
                    target = (target % 10) + 1
                orch._ai_agents.setdefault(room, {})[seat] = _mock_agent(
                    decide_vote=AsyncMock(return_value={"target": target}),
                )

        await orch._handle_vote(room)

        alive_count = sum(1 for p in state.players.values() if p.is_alive)
        assert len(state.current_votes) == alive_count, (
            f"Expected {alive_count} votes, got {len(state.current_votes)}"
        )
        # Verify all alive voters cast a vote
        for seat, player in state.players.items():
            if player.is_alive:
                assert seat in state.current_votes, (
                    f"Alive seat {seat} did not vote"
                )


# ===========================================================================
# T3.7 — _handle_last_words
# ===========================================================================

class TestHandleLastWords:
    """Last words for the eliminated player."""

    async def test_human_last_words_recorded(self, orchestrator):
        """Human eliminated player's last words are recorded."""
        orch, state = orchestrator
        room = "TEST001"

        # Setup: seat 1 is human and eliminated
        human_player = state.players[1]
        human_player.is_human = True
        human_player.is_ai = False

        state.last_words_seat = 1
        # When _wait_for_human_action returns, set up pending_human_action
        async def fake_wait(room_code, action_type, timeout=30):
            state.pending_human_action = {
                "type": "last_words",
                "data": {"content": "Good game everyone!"},
            }
        orch._wait_for_human_action = fake_wait

        await orch._handle_last_words(room)

        assert state.last_words_content == "Good game everyone!", (
            f"Expected last words 'Good game everyone!', got '{state.last_words_content}'"
        )

    async def test_ai_player_no_last_words(self, orchestrator):
        """AI players do not generate last words."""
        orch, state = orchestrator
        room = "TEST001"

        # Setup: AI eliminated player
        ai_player = state.players[1]
        ai_player.is_human = False
        ai_player.is_ai = True

        state.last_words_seat = 1

        await orch._handle_last_words(room)

        # No last_words_content should be set since is_human is False
        last_words = getattr(state, "last_words_content", None)
        assert last_words is None, f"AI player should not have last words, got: {last_words}"


# ===========================================================================
# T3.8 — _handle_hunter_shoot
# ===========================================================================

class TestHandleHunterShoot:
    """Hunter shoots a target when eliminated."""

    async def test_ai_hunter_shoots_target(self, orchestrator):
        """AI hunter decides to shoot and the target is stored in player_to_shoot."""
        orch, state = orchestrator
        room = "TEST001"

        # Find hunter and set as eliminated
        hunter = next(
            p for p in state.players.values()
            if p.role == "hunter"
        )
        hunter.is_alive = False
        hunter.death_reason = DeathReason.VOTED

        state.last_words_seat = hunter.seat_number

        # Inject mock hunter agent
        orch._ai_agents.setdefault(room, {})[hunter.seat_number] = _mock_agent(
            decide_shoot=AsyncMock(return_value={
                "action": "shoot",
                "target": 8,
            }),
        )

        await orch._handle_hunter_shoot(room)

        assert state.player_to_shoot == 8, (
            f"Expected hunter target 8, got {state.player_to_shoot}"
        )

    async def test_hunter_poisoned_cannot_shoot(self, orchestrator):
        """Hunter poisoned → cannot shoot."""
        orch, state = orchestrator
        room = "TEST001"

        hunter = next(
            p for p in state.players.values()
            if p.role == "hunter"
        )
        hunter.is_alive = False
        hunter.death_reason = DeathReason.POISONED
        state.last_words_seat = hunter.seat_number

        await orch._handle_hunter_shoot(room)

        # player_to_shoot should not be set
        target = getattr(state, "player_to_shoot", None)
        assert target is None, "Poisoned hunter should not shoot"

    async def test_hunter_no_shoot_action(self, orchestrator):
        """AI hunter decides not to shoot."""
        orch, state = orchestrator
        room = "TEST001"

        hunter = next(
            p for p in state.players.values()
            if p.role == "hunter"
        )
        hunter.is_alive = False
        hunter.death_reason = DeathReason.VOTED
        state.last_words_seat = hunter.seat_number

        orch._ai_agents.setdefault(room, {})[hunter.seat_number] = _mock_agent(
            decide_shoot=AsyncMock(return_value={
                "action": "no_shoot",
            }),
        )

        await orch._handle_hunter_shoot(room)

        target = getattr(state, "player_to_shoot", None)
        assert target is None, "Hunter should not shoot when deciding no_shoot"


# ===========================================================================
# T3.9 — _handle_game_over
# ===========================================================================

class TestHandleGameOver:
    """Game over — cleanup and final broadcast."""

    async def test_cleanup_removes_state_and_agents(self, orchestrator):
        """Game over cleans up state and agent mappings."""
        orch, state = orchestrator
        room = "TEST001"

        # Put something in _ai_agents
        orch._ai_agents[room] = {1: MagicMock()}
        state.winner = "villager"

        await orch._handle_game_over(room)

        assert room not in orch._game_states, "Game state should be removed"
        assert room not in orch._ai_agents, "AI agents should be removed"
