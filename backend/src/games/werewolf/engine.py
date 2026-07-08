"""Werewolf game engine using LangGraph StateGraph."""

import logging
import random
from typing import Any, Dict, List, Literal, Optional, TypedDict

from langgraph.graph import StateGraph, START, END

from src.games.base.engine import BaseGameEngine
from src.games.base.state import BaseGameState
from src.games.werewolf.state import (
    WerewolfGameState,
    WerewolfPhase,
    NightSubPhase,
    DeathReason,
    PlayerState,
    NightActions,
    WEREWOLF_10P_CONFIG,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# LangGraph state wrapper — TypedDict is required by StateGraph
# ---------------------------------------------------------------------------

class GraphState(TypedDict):
    """Thin wrapper around WerewolfGameState for LangGraph compatibility."""
    game_state: WerewolfGameState


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class WerewolfEngine(BaseGameEngine):
    """Werewolf game engine with LangGraph-based game flow.

    Design principles
    -----------------
    * Graph nodes are PURE functions — they transform state in-place and return
      the updated GraphState.  No asyncio.sleep, no WebSocket calls, no human
      interaction.
    * Human (and AI) interaction happens OUTSIDE the graph.  The Orchestrator
      calls the graph via ``.invoke(state)``, pauses when it encounters a node
      that requires external input, and resumes after receiving that input.
    * Each node updates ``game_state.phase`` and related fields to reflect the
      current game sub-phase.
    """

    def __init__(self) -> None:
        self._compiled_graph: Any = None

    # ------------------------------------------------------------------
    # Public interface (BaseGameEngine overrides)
    # ------------------------------------------------------------------

    def initialize_game(self, room_code: str, **kwargs: Any) -> WerewolfGameState:
        """Initialize a new werewolf game state.

        Accepts the same keyword arguments as the old
        ``initialize_game_with_human_player``:

        * ``player_names`` (list[str]) — exactly 10 player names.
        * ``human_player_id`` (str, optional) — the human player's user ID.
        * ``human_role`` (str, optional) — desired role for the human.
        """
        player_names: List[str] = kwargs.get("player_names", [])
        human_player_id: Optional[str] = kwargs.get("human_player_id")
        human_role: Optional[str] = kwargs.get("human_role")

        if len(player_names) != 10:
            raise ValueError(
                f"Werewolf 10P requires exactly 10 players, got {len(player_names)}"
            )

        state = WerewolfGameState(room_code=room_code, is_spectator_mode=False)

        # 1. Build role list from config and shuffle
        roles: List[str] = []
        for role_name, count in WEREWOLF_10P_CONFIG.items():
            roles.extend([role_name] * count)
        random.shuffle(roles)

        # 2. Assign a random seat for the human player (if any)
        human_seat: Optional[int] = None
        if human_player_id:
            human_seat = random.randint(1, 10)
            state.human_player_seat = human_seat
            state.user_seat_number = human_seat

        # 3. If the human requested a specific role, swap it into their seat
        if human_role and human_role in roles and human_seat is not None:
            role_idx = roles.index(human_role)
            seat_idx = human_seat - 1
            roles[role_idx], roles[seat_idx] = roles[seat_idx], roles[role_idx]

        # 4. Create player states
        for i, (name, role_name) in enumerate(zip(player_names, roles), start=1):
            team = "werewolf" if role_name == "werewolf" else "villager"
            is_human = (i == human_seat) if human_seat is not None else False

            state.players[i] = PlayerState(
                player_id=human_player_id if is_human else f"ai_player_{i}",
                player_name=name,
                seat_number=i,
                role=role_name,
                team=team,
                is_ai=not is_human,
                is_human=is_human,
            )

        logger.info(
            "Game initialized: room=%s, human_seat=%s, human_role=%s",
            room_code,
            human_seat,
            state.players[human_seat].role if human_seat else "N/A",
        )
        self.state = state
        return state

    def check_winner(self, state: BaseGameState) -> Optional[str]:
        """Check win condition.  Returns winner team or None."""
        return _check_win_condition(state)

    # ------------------------------------------------------------------
    # Graph construction
    # ------------------------------------------------------------------

    def build_graph(self) -> StateGraph:
        """Build the werewolf game flow StateGraph (nodes + edges)."""
        g = StateGraph(GraphState)

        # ---- register nodes ----
        g.add_node("night_werewolf", self._node_night_werewolf)
        g.add_node("night_seer", self._node_night_seer)
        g.add_node("night_witch", self._node_night_witch)
        g.add_node("day_announcement", self._node_day_announcement)
        g.add_node("day_discussion", self._node_day_discussion)
        g.add_node("day_vote", self._node_day_vote)
        g.add_node("last_words", self._node_last_words)
        g.add_node("hunter_shoot", self._node_hunter_shoot)
        g.add_node("check_winner", self._node_check_winner)

        # ---- unconditional edges ----
        g.add_edge(START, "night_werewolf")
        g.add_edge("night_werewolf", "night_seer")
        g.add_edge("night_seer", "night_witch")
        g.add_edge("night_witch", "day_announcement")
        g.add_edge("day_announcement", "day_discussion")
        g.add_edge("day_discussion", "day_vote")
        g.add_conditional_edges(
            "day_vote",
            _route_after_vote,
            {"last_words": "last_words", "check_winner": "check_winner"},
        )
        g.add_conditional_edges(
            "last_words",
            _route_after_last_words,
            {"hunter_shoot": "hunter_shoot", "check_winner": "check_winner"},
        )
        g.add_edge("hunter_shoot", "check_winner")
        g.add_conditional_edges(
            "check_winner",
            _route_after_winner_check,
            {"night_werewolf": "night_werewolf", END: END},
        )

        return g

    def compile_graph(self) -> Any:
        """Build and compile the graph (cached)."""
        if self._compiled_graph is None:
            graph = self.build_graph()
            self._compiled_graph = graph.compile()
        return self._compiled_graph

    # ------------------------------------------------------------------
    # Backward-compatible API  (old WerewolfEngine methods)
    # ------------------------------------------------------------------

    def start_game(self) -> None:
        """Start the game — backward compat with old API. Sets day=1, phase=NIGHT."""
        state = self.state if hasattr(self, 'state') else None
        if state:
            state.day_number = 1
            state.phase = "night"
            state.is_started = True

    def get_alive_players(self) -> list:
        """Get alive players from self.state."""
        if not hasattr(self, 'state') or not self.state:
            return []
        return [p for p in self.state.players.values() if p.is_alive]

    def get_player_by_seat(self, seat: int):
        """Get player by seat number."""
        if not hasattr(self, 'state') or not self.state:
            return None
        return self.state.players.get(seat)

    def get_alive_player_by_seat(self, seat: int):
        """Get alive player by seat."""
        if not hasattr(self, 'state') or not self.state:
            return None
        player = self.state.players.get(seat)
        if player and player.is_alive:
            return player
        return None

    def get_werewolf_teammates(self, seat: int) -> list:
        """Get werewolf teammates."""
        if not hasattr(self, 'state') or not self.state:
            return []
        player = self.state.players.get(seat)
        if not player or player.role != "werewolf":
            return []
        return [p for p in self.state.players.values() 
                if p.role == "werewolf" and p.seat_number != seat]

    def count_teams(self) -> tuple:
        """Count alive teams. Returns (werewolf_count, good_count)."""
        if not hasattr(self, 'state') or not self.state:
            return (0, 0)
        werewolves = sum(1 for p in self.state.players.values() 
                        if p.is_alive and p.team == "werewolf")
        good = sum(1 for p in self.state.players.values() 
                   if p.is_alive and p.team == "villager")
        return (werewolves, good)

    def set_werewolf_kill(self, target_seat: int | None) -> None:
        """Set werewolf kill target."""
        if not hasattr(self, 'state') or not self.state:
            return
        self.state.current_night_actions.werewolf_kill_target = target_seat

    def set_seer_check(self, target_seat: int) -> bool:
        """Set seer check target. Returns True if target is werewolf."""
        if not hasattr(self, 'state') or not self.state:
            return False
        self.state.current_night_actions.seer_check_target = target_seat
        player = self.state.players.get(target_seat)
        return player.role == "werewolf" if player else False

    def set_witch_action(self, save: bool = False, poison_target: int | None = None) -> None:
        """Set witch save/poison action."""
        if not hasattr(self, 'state') or not self.state:
            return
        if save and self.state.witch_has_antidote:
            self.state.current_night_actions.witch_save = True
            self.state.witch_has_antidote = False
        if poison_target and self.state.witch_has_poison:
            self.state.current_night_actions.witch_poison_target = poison_target
            self.state.witch_has_poison = False

    def process_night(self) -> list:
        """Process night actions, return deaths list."""
        if not hasattr(self, 'state') or not self.state:
            return []
        deaths = []
        actions = self.state.current_night_actions
        if actions.werewolf_kill_target and not actions.witch_save:
            target = self.state.players.get(actions.werewolf_kill_target)
            if target and target.is_alive:
                target.is_alive = False
                target.death_reason = DeathReason.KILLED
                target.death_day = self.state.day_number
                deaths.append({"seat_number": target.seat_number, "player_name": target.player_name, "reason": DeathReason.KILLED.value})
        if actions.witch_poison_target:
            target = self.state.players.get(actions.witch_poison_target)
            if target and target.is_alive:
                target.is_alive = False
                target.death_reason = DeathReason.POISONED
                target.death_day = self.state.day_number
                deaths.append({"seat_number": target.seat_number, "player_name": target.player_name, "reason": DeathReason.POISONED.value})
        self.state.death_history.extend([{**d, "day": self.state.day_number, "phase": "night"} for d in deaths])
        self.state.current_night_actions = NightActions()
        return deaths

    def start_day(self) -> None:
        """Transition to day phase."""
        if self.state: self.state.phase = WerewolfPhase.DAY.value

    def start_discussion(self, speaking_order=None) -> list:
        """Start discussion. Returns speaking order."""
        if not self.state: return []
        self.state.phase = WerewolfPhase.DISCUSSION.value if hasattr(WerewolfPhase, 'DISCUSSION') else "day_discussion"
        if speaking_order: return speaking_order
        return [p.seat_number for p in self.get_alive_players()]

    def add_speech(self, seat: int, content: str) -> None:
        """Record a speech."""
        if not self.state: return
        player = self.state.players.get(seat)
        if player:
            self.state.speech_history.append({"day": self.state.day_number, "seat_number": seat, "player_name": player.player_name, "content": content})

    def start_vote(self) -> None:
        """Start voting."""
        if self.state: 
            self.state.phase = WerewolfPhase.VOTE.value if hasattr(WerewolfPhase, 'VOTE') else "day_vote"
            self.state.current_votes = {}

    def cast_vote(self, voter_seat: int, target_seat: int | None) -> None:
        """Cast a vote."""
        if self.state and target_seat is not None:
            self.state.current_votes[voter_seat] = target_seat

    def tally_votes(self) -> tuple:
        """Tally votes. Returns (vote_counts, eliminated_seat, is_tie)."""
        if not self.state: return ({}, None, False)
        vote_counts = {}
        for target in self.state.current_votes.values():
            vote_counts[target] = vote_counts.get(target, 0) + 1
        if not vote_counts: return ({}, None, True)
        max_votes = max(vote_counts.values())
        top = [s for s, c in vote_counts.items() if c == max_votes]
        if len(top) > 1: return (vote_counts, None, True)
        return (vote_counts, top[0], False)

    def execute_vote_result(self, eliminated_seat: int | None) -> dict | None:
        """Execute vote elimination."""
        if not self.state or not eliminated_seat: return None
        target = self.state.players.get(eliminated_seat)
        if not target or not target.is_alive: return None
        target.is_alive = False
        target.death_reason = DeathReason.VOTED
        target.death_day = self.state.day_number
        result = {"seat_number": eliminated_seat, "player_name": target.player_name, "role": target.role, "reason": DeathReason.VOTED.value}
        self.state.death_history.append({**result, "day": self.state.day_number, "phase": "vote"})
        self.state.vote_history.append({"day": self.state.day_number, "votes": dict(self.state.current_votes), "eliminated": eliminated_seat})
        return result

    def can_hunter_shoot(self, seat: int, death_reason) -> bool:
        """Check if hunter can shoot."""
        if not self.state: return False
        player = self.state.players.get(seat)
        if not player or player.role != "hunter": return False
        reason = death_reason if isinstance(death_reason, DeathReason) else DeathReason(death_reason) if hasattr(DeathReason, '__call__') else death_reason
        return reason != DeathReason.POISONED

    def hunter_shoot(self, hunter_seat: int, target_seat: int) -> dict | None:
        """Execute hunter shoot."""
        if not self.state: return None
        target = self.state.players.get(target_seat)
        if not target or not target.is_alive: return None
        target.is_alive = False
        target.death_reason = DeathReason.SHOT
        target.death_day = self.state.day_number
        return {"seat_number": target_seat, "player_name": target.player_name, "role": target.role, "reason": DeathReason.SHOT.value, "hunter_seat": hunter_seat}

    def advance_night_sub_phase(self) -> str | None:
        """Advance night sub-phase, return next or None."""
        if not self.state: return None
        current = self.state.sub_phase
        sub = NightSubPhase
        if hasattr(sub, 'WEREWOLF_ACTION'):
            if current == sub.WEREWOLF_ACTION.value: self.state.sub_phase = sub.SEER_ACTION.value; return self.state.sub_phase
            elif current == sub.SEER_ACTION.value: self.state.sub_phase = sub.WITCH_ACTION.value; return self.state.sub_phase
            elif current == sub.WITCH_ACTION.value: return None
        return None

    def transition_to_next_night(self) -> None:
        """Transition to next night."""
        if not self.state: return
        self.state.day_number += 1
        self.state.phase = "night"
        self.state.current_night_actions = NightActions()
        self.state.current_votes = {}

    def get_public_state(self) -> dict:
        """Get public game state."""
        if not self.state: return {}
        alive = [{"seat_number": p.seat_number, "player_name": p.player_name, "is_alive": p.is_alive, "is_ai": p.is_ai} for p in self.state.players.values() if p.is_alive]
        dead = [{"seat_number": p.seat_number, "player_name": p.player_name, "role": p.role if self.state.winner else None, "death_reason": p.death_reason.value if p.death_reason else None, "death_day": p.death_day} for p in self.state.players.values() if not p.is_alive]
        return {"room_code": self.state.room_code, "day_number": self.state.day_number, "phase": self.state.phase, "alive_players": alive, "dead_players": dead, "winner": self.state.winner}

    def get_player_state(self, seat: int) -> dict | None:
        """Get state for a specific player."""
        if not self.state: return None
        p = self.state.players.get(seat)
        if not p: return None
        result = {"seat_number": p.seat_number, "player_name": p.player_name, "role": p.role, "team": p.team, "is_alive": p.is_alive}
        if p.role == "werewolf":
            result["teammates"] = [{"seat_number": t.seat_number, "player_name": t.player_name, "is_alive": t.is_alive} for t in self.get_werewolf_teammates(seat)]
        return result

    def add_game_log(self, log_type: str, content: str, player_id=None, player_name=None, seat_number=None, metadata=None, is_public=True):
        """Add a game log entry."""
        if not self.state: return None
        from src.games.werewolf.state import GameLogEntry
        entry = GameLogEntry.create(log_type=log_type, content=content, day=self.state.day_number, phase=self.state.phase, player_id=player_id, player_name=player_name, seat_number=seat_number, metadata=metadata, is_public=is_public)
        self.state.game_logs.append(entry)
        return entry

    def get_game_logs(self, log_type=None, player_id=None, day=None, limit=None) -> list:
        """Get filtered game logs."""
        if not self.state: return []
        logs = list(self.state.game_logs)
        if log_type: logs = [l for l in logs if l.type == log_type]
        if player_id: logs = [l for l in logs if l.player_id == player_id]
        if day: logs = [l for l in logs if l.day == day]
        if limit: logs = logs[-limit:]
        return logs

    # ------------------------------------------------------------------
    # Node implementations  (all pure — transform state in place)
    # ------------------------------------------------------------------

    # -- Night: werewolf action -------------------------------------------

    @staticmethod
    def _node_night_werewolf(state: GraphState) -> GraphState:
        """Night sub-phase: werewolves choose a kill target.

        Sets phase to ``NIGHT_WEREWOLF`` and updates
        ``current_night_actions.werewolf_kill_target``.

        The actual target is set by the Orchestrator via
        ``game_state.current_night_actions.werewolf_kill_target = seat``
        **before** calling into this node.
        """
        gs = state["game_state"]
        if not gs.is_started:
            gs.day_number = 1
            gs.is_started = True
        gs.phase = WerewolfPhase.NIGHT_WEREWOLF.value
        gs.sub_phase = NightSubPhase.WEREWOLF_ACTION.value
        # NOTE: current_night_actions is NOT reset here.
        # The Orchestrator sets kill/check/poison targets before invoke().
        # Resetting would wipe out those pre-set values.
        # night_witch resets after processing.
        logger.debug("Night — werewolf action (target: %s)", gs.current_night_actions.werewolf_kill_target)
        return {"game_state": gs}

    # -- Night: seer action ------------------------------------------------

    @staticmethod
    def _node_night_seer(state: GraphState) -> GraphState:
        """Night sub-phase: seer checks a target.

        Sets phase and awaits ``seer_check_target``.
        """
        gs = state["game_state"]
        gs.phase = WerewolfPhase.NIGHT_SEER.value
        gs.sub_phase = NightSubPhase.SEER_ACTION.value
        logger.debug("Night — seer action (target: %s)", gs.current_night_actions.seer_check_target)
        return {"game_state": gs}

    # -- Night: witch action ----------------------------------------------

    @staticmethod
    def _node_night_witch(state: GraphState) -> GraphState:
        """Night sub-phase: witch decides to save / poison.

        Sets phase and awaits ``witch_save`` / ``witch_poison_target``.

        **Night deaths are processed here** — after the witch action has been
        recorded, this node applies night kills before transitioning to day.
        """
        gs = state["game_state"]
        gs.phase = WerewolfPhase.NIGHT_WITCH.value
        gs.sub_phase = NightSubPhase.WITCH_ACTION.value

        # Process night deaths
        deaths: List[Dict[str, Any]] = []
        actions = gs.current_night_actions

        # Werewolf kill (unless witch saved)
        if actions.werewolf_kill_target and not actions.witch_save:
            target = gs.players.get(actions.werewolf_kill_target)
            if target and target.is_alive:
                target.is_alive = False
                target.death_reason = DeathReason.KILLED
                target.death_day = gs.day_number
                deaths.append({
                    "seat_number": target.seat_number,
                    "player_name": target.player_name,
                    "reason": DeathReason.KILLED.value,
                })
                logger.info("Player %s (seat %d) killed by werewolf", target.player_name, target.seat_number)

        # Witch poison
        if actions.witch_poison_target:
            target = gs.players.get(actions.witch_poison_target)
            if target and target.is_alive:
                target.is_alive = False
                target.death_reason = DeathReason.POISONED
                target.death_day = gs.day_number
                deaths.append({
                    "seat_number": target.seat_number,
                    "player_name": target.player_name,
                    "reason": DeathReason.POISONED.value,
                })
                logger.info("Player %s (seat %d) poisoned by witch", target.player_name, target.seat_number)

        if deaths:
            gs.death_history.extend([
                {**d, "day": gs.day_number, "phase": "night"} for d in deaths
            ])

        # Reset night actions for the next night
        gs.current_night_actions = NightActions()

        # Advance day
        gs.day_number += 1
        logger.debug("Night %d processed (%d deaths)", gs.day_number - 1, len(deaths))
        return {"game_state": gs}

    # -- Day: announcement ------------------------------------------------

    @staticmethod
    def _node_day_announcement(state: GraphState) -> GraphState:
        """Day phase start: announcement of night results.

        Sets phase to ``DAY_ANNOUNCEMENT``.  The Orchestrator reads
        ``death_history`` and broadcasts the public announcement.
        """
        gs = state["game_state"]
        gs.phase = WerewolfPhase.DAY_ANNOUNCEMENT.value
        # Note: current_votes is NOT cleared here.
        # The Orchestrator sets votes during discussion, and day_vote
        # clears them after tallying.
        logger.debug("Day %d — announcement", gs.day_number)
        return {"game_state": gs}

    # -- Day: discussion --------------------------------------------------

    @staticmethod
    def _node_day_discussion(state: GraphState) -> GraphState:
        """Day phase: discussion.

        Sets phase to ``DAY_DISCUSSION`` and resets speech tracking.
        """
        gs = state["game_state"]
        gs.phase = WerewolfPhase.DAY_DISCUSSION.value
        gs.current_speaker_seat = None
        logger.debug("Day %d — discussion", gs.day_number)
        return {"game_state": gs}

    # -- Day: vote --------------------------------------------------------

    @staticmethod
    def _node_day_vote(state: GraphState) -> GraphState:
        """Day phase: voting and tally.

        Tally the votes stored in ``current_votes``, eliminate the player with
        the most votes (skip on tie), and record the result in
        ``vote_history`` / ``death_history``.
        """
        gs = state["game_state"]
        gs.phase = WerewolfPhase.DAY_VOTE.value

        # ---- tally ----
        vote_counts: Dict[int, int] = {}
        for target in gs.current_votes.values():
            if target is not None:
                vote_counts[target] = vote_counts.get(target, 0) + 1

        eliminated_seat: Optional[int] = None
        is_tie = False

        if vote_counts:
            max_votes = max(vote_counts.values())
            top_candidates = [s for s, c in vote_counts.items() if c == max_votes]
            if len(top_candidates) > 1:
                is_tie = True
            else:
                eliminated_seat = top_candidates[0]
                target = gs.players.get(eliminated_seat)
                if target and target.is_alive:
                    target.is_alive = False
                    target.death_reason = DeathReason.VOTED
                    target.death_day = gs.day_number
                    logger.info("Player %s (seat %d) voted out", target.player_name, target.seat_number)

        # Record vote history
        vote_record: Dict[str, Any] = {
            "day": gs.day_number,
            "votes": dict(gs.current_votes),
            "eliminated": eliminated_seat,
            "is_tie": is_tie,
        }
        gs.vote_history.append(vote_record)

        if eliminated_seat is not None:
            target = gs.players.get(eliminated_seat)
            gs.death_history.append({
                "seat_number": eliminated_seat,
                "player_name": target.player_name if target else "?",
                "role": target.role if target else "?",
                "reason": DeathReason.VOTED.value,
                "day": gs.day_number,
                "phase": "vote",
            })

        # Mark in state so downstream nodes can find the eliminated player
        gs.last_words_seat = eliminated_seat
        gs.last_words_reason = DeathReason.VOTED.value if not is_tie else None

        gs.current_votes = {}
        logger.debug("Day %d — vote result: seat=%s tie=%s", gs.day_number, eliminated_seat, is_tie)
        return {"game_state": gs}

    # -- Last words -------------------------------------------------------

    @staticmethod
    def _node_last_words(state: GraphState) -> GraphState:
        """Last words for the eliminated player."""
        gs = state["game_state"]
        gs.phase = WerewolfPhase.LAST_WORDS.value
        logger.debug("Last words — seat=%s", gs.last_words_seat)
        return {"game_state": gs}

    # -- Hunter shoot -----------------------------------------------------

    @staticmethod
    def _node_hunter_shoot(state: GraphState) -> GraphState:
        """Hunter retaliates if eliminated and eligible.

        The Orchestrator sets ``player_to_shoot`` on the game state
        **before** entering this node.  If the hunter chooses not to shoot
        (or is ineligible), the node is a no-op.
        """
        gs = state["game_state"]
        gs.phase = WerewolfPhase.HUNTER_SHOOT.value

        hunter_seat = gs.last_words_seat
        if hunter_seat is None:
            logger.debug("Hunter shoot — no eliminated player, skip")
            return {"game_state": gs}

        player = gs.players.get(hunter_seat)
        if not player or player.role != "hunter":
            logger.debug("Hunter shoot — eliminated player is not hunter, skip")
            return {"game_state": gs}

        if player.death_reason == DeathReason.POISONED:
            logger.debug("Hunter shoot — hunter was poisoned, cannot shoot")
            return {"game_state": gs}

        # The Orchestrator fills ``player_to_shoot`` (seat number) before
        # calling this node.  If absent, the hunter chose not to shoot.
        target_seat = getattr(gs, "player_to_shoot", None)
        if target_seat is None:
            logger.debug("Hunter shoot — hunter chose not to shoot")
            return {"game_state": gs}

        target = gs.players.get(target_seat)
        if target and target.is_alive:
            target.is_alive = False
            target.death_reason = DeathReason.SHOT
            target.death_day = gs.day_number
            gs.death_history.append({
                "seat_number": target_seat,
                "player_name": target.player_name,
                "role": target.role,
                "reason": DeathReason.SHOT.value,
                "hunter_seat": hunter_seat,
                "day": gs.day_number,
                "phase": "hunter_shoot",
            })
            logger.info("Hunter %d shot %d", hunter_seat, target_seat)

        return {"game_state": gs}

    # -- Check winner -----------------------------------------------------

    @staticmethod
    def _node_check_winner(state: GraphState) -> GraphState:
        """Check win/loss condition after night or vote.

        Updates ``game_state.winner`` and ``game_state.phase`` when the
        game ends.
        """
        gs = state["game_state"]
        winner = _check_win_condition(gs)
        if winner:
            gs.winner = winner
            gs.phase = WerewolfPhase.GAME_OVER.value
            logger.info("Game over — %s wins", winner)
        else:
            gs.phase = WerewolfPhase.NIGHT.value
        return {"game_state": gs}


# =========================================================================
# Routing functions  (used by add_conditional_edges)
# =========================================================================


def _route_after_vote(state: GraphState) -> Literal["last_words", "check_winner"]:
    """After voting: route to last_words (someone eliminated) or winner check."""
    gs = state["game_state"]
    # If there was a tie, no elimination → go directly to winner check
    if gs.last_words_seat is None:
        return "check_winner"
    return "last_words"


def _route_after_last_words(state: GraphState) -> Literal["hunter_shoot", "check_winner"]:
    """After last words: route to hunter_shoot if eligible, else check winner."""
    gs = state["game_state"]
    hunter_seat = gs.last_words_seat
    if hunter_seat is not None:
        player = gs.players.get(hunter_seat)
        if player and player.role == "hunter" and player.death_reason != DeathReason.POISONED:
            return "hunter_shoot"
    return "check_winner"


def _route_after_winner_check(state: GraphState) -> Literal["night_werewolf", "__end__"]:
    """After winner check: loop back to night or end the game."""
    gs = state["game_state"]
    if gs.winner is not None:
        return END  # type: ignore[return-value]  # END resolves to "__end__"
    return "night_werewolf"


# =========================================================================
# Helpers
# =========================================================================


def _check_win_condition(state: BaseGameState) -> Optional[str]:
    """Check win condition.  Returns 'werewolf', 'villager', or None."""
    alive_wolves = 0
    alive_villagers = 0

    for player in state.players.values():
        if player.is_alive:
            if player.team == "werewolf":
                alive_wolves += 1
            else:
                alive_villagers += 1

    if alive_wolves == 0:
        logger.info("Win check — villagers win")
        return "villager"
    if alive_wolves >= alive_villagers:
        logger.info("Win check — werewolves win")
        return "werewolf"
    return None
