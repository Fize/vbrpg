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
