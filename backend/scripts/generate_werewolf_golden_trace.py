#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate deterministic golden traces from the legacy werewolf engine.

The traces intentionally exclude UUIDs, names and wall-clock timestamps. They
record rule state only, so another runtime can compare behavior without
depending on Python implementation details.
"""

import copy
import importlib.util
import json
import random
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


ENGINE_PATH = Path(__file__).resolve().parents[1] / "src/services/games/werewolf_engine.py"


def load_engine_module():
    """Load the legacy engine without importing database-backed service packages."""
    spec = importlib.util.spec_from_file_location("legacy_werewolf_engine", ENGINE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load legacy engine: {ENGINE_PATH}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def snapshot(state: Any) -> Dict[str, Any]:
    """Return stable rule state suitable for a cross-runtime fixture."""
    vote_history = copy.deepcopy(state.vote_history)
    for entry in vote_history:
        entry["votes"] = {str(k): v for k, v in sorted(entry["votes"].items())}

    return {
        "day_number": state.day_number,
        "phase": state.phase.value,
        "sub_phase": state.sub_phase,
        "roles": {str(seat): player.role for seat, player in sorted(state.players.items())},
        "alive_seats": [
            seat for seat, player in sorted(state.players.items()) if player.is_alive
        ],
        "dead_players": {
            str(seat): {
                "role": player.role,
                "death_reason": player.death_reason.value if player.death_reason else None,
                "death_day": player.death_day,
            }
            for seat, player in sorted(state.players.items())
            if not player.is_alive
        },
        "night_actions": {
            "werewolf_kill_target": state.current_night_actions.werewolf_kill_target,
            "seer_check_target": state.current_night_actions.seer_check_target,
            "witch_save": state.current_night_actions.witch_save,
            "witch_poison_target": state.current_night_actions.witch_poison_target,
        },
        "witch_has_antidote": state.witch_has_antidote,
        "witch_has_poison": state.witch_has_poison,
        "current_votes": {str(k): v for k, v in sorted(state.current_votes.items())},
        "death_history": copy.deepcopy(state.death_history),
        "vote_history": vote_history,
        "winner": state.winner,
    }


def new_game(engine_module: Any, seed: int):
    """Create a deterministic ten-player game with a seer at seat one."""
    random.seed(seed)
    engine = engine_module.WerewolfEngine()
    player_names = [f"Player_{seat}" for seat in range(1, 11)]
    state = engine.initialize_game(
        room_code=f"GOLDEN{seed}",
        player_names=player_names,
        user_role="seer",
    )
    return engine, state


def alive_seat(state: Any, predicate: Optional[Callable[[Any], bool]] = None) -> int:
    """Return the first alive seat matching an optional predicate."""
    for seat, player in sorted(state.players.items()):
        if player.is_alive and (predicate is None or predicate(player)):
            return seat
    raise AssertionError("No matching alive player")


def record_step(
    trace: List[Dict[str, Any]],
    state: Any,
    operation: str,
    args: Dict[str, Any],
    result: Any = None,
) -> None:
    """Append one operation and its stable post-operation state."""
    entry: Dict[str, Any] = {
        "operation": operation,
        "args": args,
        "state": snapshot(state),
    }
    if result is not None:
        entry["result"] = result
    trace.append(entry)


def start_game(engine: Any, state: Any, trace: List[Dict[str, Any]]) -> None:
    """Record common initialization and start operations."""
    record_step(trace, state, "initialize_game", {"player_count": 10, "user_role": "seer"})
    engine.start_game()
    record_step(trace, state, "start_game", {})


def cast_all_votes(engine: Any, state: Any, target_seat: Optional[int]) -> int:
    """Cast one target or abstention for every alive participant."""
    voters = [seat for seat, player in sorted(state.players.items()) if player.is_alive]
    for voter_seat in voters:
        engine.cast_vote(voter_seat, target_seat)
    return len(voters)


def scenario_night_kill(engine_module: Any, seed: int) -> Dict[str, Any]:
    engine, state = new_game(engine_module, seed)
    trace: List[Dict[str, Any]] = []
    start_game(engine, state, trace)
    target = alive_seat(state, lambda player: player.role != "werewolf")
    engine.set_werewolf_kill(target)
    record_step(trace, state, "set_werewolf_kill", {"target_seat": target})
    deaths = engine.process_night()
    record_step(trace, state, "process_night", {}, {"deaths": deaths})
    engine.start_day()
    record_step(trace, state, "start_day", {})
    return {"name": "normal_night_kill", "seed": seed, "trace": trace}


def scenario_witch_save(engine_module: Any, seed: int) -> Dict[str, Any]:
    engine, state = new_game(engine_module, seed)
    trace: List[Dict[str, Any]] = []
    start_game(engine, state, trace)
    target = alive_seat(state, lambda player: player.role != "werewolf")
    engine.set_werewolf_kill(target)
    record_step(trace, state, "set_werewolf_kill", {"target_seat": target})
    engine.set_witch_action(save=True)
    record_step(trace, state, "set_witch_action", {"save": True})
    deaths = engine.process_night()
    record_step(trace, state, "process_night", {}, {"deaths": deaths})
    return {"name": "witch_save", "seed": seed, "trace": trace}


def scenario_witch_poison(engine_module: Any, seed: int) -> Dict[str, Any]:
    engine, state = new_game(engine_module, seed)
    trace: List[Dict[str, Any]] = []
    start_game(engine, state, trace)
    target = alive_seat(state, lambda player: player.role != "witch")
    engine.set_witch_action(poison_target=target)
    record_step(trace, state, "set_witch_action", {"poison_target": target})
    deaths = engine.process_night()
    record_step(trace, state, "process_night", {}, {"deaths": deaths})
    return {"name": "witch_poison", "seed": seed, "trace": trace}


def scenario_seer_check(engine_module: Any, seed: int, check_werewolf: bool) -> Dict[str, Any]:
    engine, state = new_game(engine_module, seed)
    trace: List[Dict[str, Any]] = []
    start_game(engine, state, trace)
    target = alive_seat(
        state,
        (lambda player: player.role == "werewolf")
        if check_werewolf
        else (lambda player: player.role != "werewolf"),
    )
    result = engine.set_seer_check(target)
    record_step(
        trace,
        state,
        "set_seer_check",
        {"target_seat": target},
        {"is_werewolf": result},
    )
    return {
        "name": "seer_true" if check_werewolf else "seer_false",
        "seed": seed,
        "trace": trace,
    }


def scenario_vote_tie(engine_module: Any, seed: int) -> Dict[str, Any]:
    engine, state = new_game(engine_module, seed)
    trace: List[Dict[str, Any]] = []
    start_game(engine, state, trace)
    engine.start_vote()
    record_step(trace, state, "start_vote", {})
    alive = [seat for seat, player in sorted(state.players.items()) if player.is_alive]
    first_target, second_target = alive[-2:]
    for index, voter in enumerate(alive):
        engine.cast_vote(voter, first_target if index % 2 == 0 else second_target)
    record_step(
        trace,
        state,
        "cast_votes",
        {"target_seats": [first_target, second_target], "voter_count": len(alive)},
    )
    counts, eliminated, is_tie = engine.tally_votes()
    record_step(
        trace,
        state,
        "tally_votes",
        {},
        {
            "vote_counts": {str(k): v for k, v in sorted(counts.items())},
            "eliminated_seat": eliminated,
            "is_tie": is_tie,
        },
    )
    return {"name": "vote_tie", "seed": seed, "trace": trace}


def scenario_vote_abstain(engine_module: Any, seed: int) -> Dict[str, Any]:
    engine, state = new_game(engine_module, seed)
    trace: List[Dict[str, Any]] = []
    start_game(engine, state, trace)
    engine.start_vote()
    record_step(trace, state, "start_vote", {})
    voter_count = cast_all_votes(engine, state, None)
    record_step(trace, state, "cast_votes", {"target_seat": None, "voter_count": voter_count})
    counts, eliminated, is_tie = engine.tally_votes()
    record_step(
        trace,
        state,
        "tally_votes",
        {},
        {"vote_counts": counts, "eliminated_seat": eliminated, "is_tie": is_tie},
    )
    return {"name": "vote_all_abstain", "seed": seed, "trace": trace}


def scenario_hunter_shoot(engine_module: Any, seed: int) -> Dict[str, Any]:
    engine, state = new_game(engine_module, seed)
    trace: List[Dict[str, Any]] = []
    start_game(engine, state, trace)
    hunter = alive_seat(state, lambda player: player.role == "hunter")
    target = alive_seat(state, lambda player: player.seat_number != hunter)
    result = engine.hunter_shoot(hunter, target)
    record_step(
        trace,
        state,
        "hunter_shoot",
        {"hunter_seat": hunter, "target_seat": target},
        result,
    )
    return {"name": "hunter_shoot", "seed": seed, "trace": trace}


def scenario_win(engine_module: Any, seed: int, winning_team: str) -> Dict[str, Any]:
    engine, state = new_game(engine_module, seed)
    trace: List[Dict[str, Any]] = []
    start_game(engine, state, trace)
    engine.start_vote()
    record_step(trace, state, "start_vote", {})

    if winning_team == "villager":
        targets = [
            seat for seat, player in sorted(state.players.items()) if player.role == "werewolf"
        ]
    else:
        targets = [
            seat for seat, player in sorted(state.players.items()) if player.role != "werewolf"
        ][:4]

    for target in targets:
        voter_count = cast_all_votes(engine, state, target)
        counts, eliminated, is_tie = engine.tally_votes()
        record_step(
            trace,
            state,
            "tally_votes",
            {"target_seat": target, "voter_count": voter_count},
            {
                "vote_counts": {str(k): v for k, v in sorted(counts.items())},
                "eliminated_seat": eliminated,
                "is_tie": is_tie,
            },
        )
        result = engine.execute_vote_result(eliminated)
        record_step(trace, state, "execute_vote_result", {"eliminated_seat": eliminated}, result)
        winner = engine.check_win_condition()
        record_step(trace, state, "check_win_condition", {}, {"winner": winner})
        if winner is not None:
            break
        engine.start_vote()
        record_step(trace, state, "start_vote", {})

    return {"name": f"{winning_team}_win", "seed": seed, "trace": trace}


def build_trace_suite() -> Dict[str, Any]:
    """Build ten deterministic traces covering legacy rule branches."""
    engine_module = load_engine_module()
    traces = [
        scenario_night_kill(engine_module, 20260823),
        scenario_witch_save(engine_module, 20260824),
        scenario_witch_poison(engine_module, 20260825),
        scenario_seer_check(engine_module, 20260826, True),
        scenario_seer_check(engine_module, 20260827, False),
        scenario_vote_tie(engine_module, 20260828),
        scenario_vote_abstain(engine_module, 20260829),
        scenario_hunter_shoot(engine_module, 20260830),
        scenario_win(engine_module, 20260831, "villager"),
        scenario_win(engine_module, 20260832, "werewolf"),
    ]
    return {
        "schema_version": "legacy-werewolf-trace.v2",
        "source": "backend/src/services/games/werewolf_engine.py",
        "trace_count": len(traces),
        "traces": traces,
    }


if __name__ == "__main__":
    print(json.dumps(build_trace_suite(), ensure_ascii=False, separators=(",", ":")))
