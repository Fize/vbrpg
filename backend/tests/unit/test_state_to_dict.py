# -*- coding: utf-8 -*-
"""Tests for WerewolfGameOrchestrator._state_to_dict."""

import pytest

from src.games.werewolf.engine import WerewolfEngine
from src.games.werewolf.orchestrator import WerewolfGameOrchestrator


@pytest.fixture
def engine():
    """Create a real WerewolfEngine with an initialized + started game state."""
    eng = WerewolfEngine()
    eng.initialize_game(
        room_code="TEST001",
        player_names=[f"P{i}" for i in range(1, 11)],
    )
    eng.start_game()
    return eng


@pytest.fixture
def orchestrator(engine):
    """Create an orchestrator and inject the engine's state."""
    orch = WerewolfGameOrchestrator()
    orch._game_states["TEST001"] = engine.state
    return orch


# ---------------------------------------------------------------------------
# T2.1 — All expected keys present
# ---------------------------------------------------------------------------


def test_state_to_dict_has_all_keys(orchestrator, engine):
    """_state_to_dict returns a dict with the expected keys."""
    result = orchestrator._state_to_dict(engine.state)

    expected_keys = {
        "day_number",
        "phase",
        "alive_players",
        "dead_players",
        "speech_history",
        "vote_history",
        "death_history",
    }
    assert set(result.keys()) == expected_keys, (
        f"Expected keys {expected_keys}, got {set(result.keys())}"
    )


# ---------------------------------------------------------------------------
# T2.2 — Alive players must NOT contain role
# ---------------------------------------------------------------------------


def test_alive_players_no_role(orchestrator, engine):
    """alive_players entries must not contain 'role'."""
    result = orchestrator._state_to_dict(engine.state)

    for player in result["alive_players"]:
        assert "role" not in player, (
            f"Alive player {player.get('name')} contains 'role' key: {player}"
        )


# ---------------------------------------------------------------------------
# T2.3 — Dead players must NOT contain role
# ---------------------------------------------------------------------------


def test_dead_players_no_role(orchestrator, engine):
    """dead_players entries must not contain 'role'."""
    result = orchestrator._state_to_dict(engine.state)

    for player in result["dead_players"]:
        assert "role" not in player, (
            f"Dead player {player.get('name')} contains 'role' key: {player}"
        )


# ---------------------------------------------------------------------------
# T2.4 — Speech history format
# ---------------------------------------------------------------------------


def test_speech_history_format(orchestrator, engine):
    """Speech history entries are formatted as 'seat_number号name: content'."""
    engine.state.speech_history.append(
        {"seat_number": 1, "player_name": "P1", "content": "我是好人", "day": 1}
    )

    result = orchestrator._state_to_dict(engine.state)

    assert "1号P1: 我是好人" in result["speech_history"], (
        f"Expected '1号P1: 我是好人' in speech_history, "
        f"got: {result['speech_history']!r}"
    )


# ---------------------------------------------------------------------------
# T2.5 — Speech history truncated at 20 entries
# ---------------------------------------------------------------------------


def test_speech_history_truncated_at_20(orchestrator, engine):
    """Only the last 20 speech entries appear in the output."""
    for i in range(25):
        engine.state.speech_history.append(
            {
                "seat_number": i % 10 + 1,
                "player_name": f"P{i % 10 + 1}",
                "content": f"Speech {i + 1}",
                "day": 1,
            }
        )

    result = orchestrator._state_to_dict(engine.state)

    lines = result["speech_history"].split("\n")
    assert len(lines) == 20, (
        f"Expected 20 lines in speech_history, got {len(lines)}"
    )
