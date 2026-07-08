# -*- coding: utf-8 -*-
"""Werewolf game orchestrator — connects LangGraph engine, AI agents, WebSocket.

This is the SERVICE layer that replaces the old 4746-line werewolf_game_service.py.
It handles:
  - Game initialization with AI agent creation
  - The game LOOP outside the LangGraph engine (calling engine.compile_graph().invoke())
  - AI agent LLM calls between graph nodes (night actions, speeches, votes)
  - WebSocket broadcasts and host announcements
  - Human player input waiting (async while loop)
  - AI takeover on timeout
"""

import asyncio
import logging
from typing import Any, AsyncIterator, Dict, List, Optional

from src.llm import LLMClient
from src.games.base.personality import PersonalityGenerator
from src.games.werewolf.engine import WerewolfEngine
from src.games.werewolf.state import (
    WerewolfGameState,
    WerewolfPhase,
    NightActions,
    PlayerState,
)

logger = logging.getLogger(__name__)


class WerewolfGameOrchestrator:
    """Orchestrates a werewolf game session.

    Design
    ------
    * The orchestrator owns the game LOOP — it advances the LangGraph, pauses
      for AI / human input between nodes, and resumes.
    * Each call to ``engine.compile_graph().invoke()`` advances ONE graph node.
      Between nodes the orchestrator handles I/O (LLM calls, WebSockets, human
      waiting).
    * ``_game_states`` and ``_ai_agents`` are keyed by room_code so a single
      orchestrator instance can manage multiple concurrent games.
    """

    def __init__(self) -> None:
        self.engine = WerewolfEngine()
        self.host: Optional["WerewolfHost"] = None        # type: ignore[name-defined]
        self._game_states: Dict[str, WerewolfGameState] = {}
        self._ai_agents: Dict[str, Dict[int, Any]] = {}   # room_code -> {seat: agent}
        self._llm_client = LLMClient()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def start_game(
        self,
        room_code: str,
        human_player_id: str,
        human_role: Optional[str] = None,
    ) -> WerewolfGameState:
        """Initialize game, create AI agents with personalities, start the game loop.

        Returns the initial game state.  The game loop runs as a background task.
        """
        # 1. Initialize game state with 10 default player names
        player_names = [f"玩家{i}" for i in range(1, 11)]
        state = self.engine.initialize_game(
            room_code=room_code,
            player_names=player_names,
            human_player_id=human_player_id,
            human_role=human_role,
        )
        self._game_states[room_code] = state

        # 2. Create AI agents with random personalities
        ai_players = [p for p in state.players.values() if p.is_ai]
        personalities = PersonalityGenerator.generate_all(len(ai_players))
        agents: Dict[int, Any] = {}
        for player, personality in zip(ai_players, personalities):
            agent = self._create_agent(player.role, player, personality)
            if agent is not None:
                agents[player.seat_number] = agent

        # Link werewolf teammates
        werewolf_agents = {
            seat: ag for seat, ag in agents.items()
            if hasattr(ag, "set_teammates")
        }
        for seat, agent in werewolf_agents.items():
            teammates = [
                {"seat_number": s, "name": state.players[s].player_name, "player_id": state.players[s].player_id, "is_alive": True}
                for s in werewolf_agents
                if s != seat
            ]
            agent.set_teammates(teammates)

        self._ai_agents[room_code] = agents

        # 3. Mark as started (the graph node will pick this up)
        state.is_started = True

        # 4. Import host lazily to avoid circular imports
        from src.games.werewolf.host import WerewolfHost
        self.host = WerewolfHost(llm_client=self._llm_client)

        # 5. Run game loop in background
        asyncio.create_task(self._game_loop(room_code))
        return state

    async def process_human_action(
        self,
        room_code: str,
        action_type: str,
        action_data: Dict[str, Any],
    ) -> None:
        """Receive a human player's action and store it on the game state.

        Called by the WebSocket handler when a human player submits an action.
        The game loop awaits on ``waiting_for_human_action`` and picks up the
        action the next time it polls.
        """
        state = self._game_states.get(room_code)
        if state is None:
            logger.warning("process_human_action: no state for room %s", room_code)
            return

        # Store action data on state so the game loop can read it
        state.pending_human_action = {"type": action_type, "data": action_data}
        state.waiting_for_human_action = False
        logger.info(
            "Human action received: room=%s type=%s data=%s",
            room_code, action_type, action_data,
        )

    def get_game_state(self, room_code: str) -> WerewolfGameState | None:
        """Get the raw game state for a room. Returns None if no game exists."""
        return self._game_states.get(room_code)

    def get_visible_state(self, room_code: str, player_id: str) -> dict | None:
        """Get the public/visible game state for a specific player.

        Returns a dict compatible with the frontend's WerewolfGameStateResponse.
        Includes: room_code, day_number, phase, sub_phase, alive_players list with
        seat_number+player_name+is_alive+is_ai, dead_players list, winner if game over,
        human_player_seat, waiting_for_human_action, human_action_type.
        For the human player, also includes their role and team.
        """
        state = self._game_states.get(room_code)
        if not state:
            return None

        result = {
            "room_code": state.room_code,
            "game_id": state.game_id,
            "day_number": state.day_number,
            "phase": state.phase,
            "sub_phase": getattr(state, 'sub_phase', None),
            "alive_players": [
                {
                    "seat_number": p.seat_number,
                    "player_name": p.player_name,
                    "is_alive": p.is_alive,
                    "is_ai": p.is_ai,
                }
                for p in state.players.values() if p.is_alive
            ],
            "dead_players": [
                {
                    "seat_number": p.seat_number,
                    "player_name": p.player_name,
                    "role": p.role if state.winner else None,
                    "death_reason": p.death_reason.value if p.death_reason else None,
                    "death_day": p.death_day,
                }
                for p in state.players.values() if not p.is_alive
            ],
            "winner": state.winner,
            "human_player_seat": state.human_player_seat,
            "waiting_for_human_action": state.waiting_for_human_action,
            "human_action_type": state.human_action_type,
            "current_speaker_seat": getattr(state, 'current_speaker_seat', None),
            "spectator_mode": getattr(state, 'is_spectator_mode', False),
        }
        # Add role info if player is in the game
        for seat, p in state.players.items():
            if p.player_id == player_id:
                result["player_role"] = p.role
                result["player_team"] = p.team
                result["player_seat"] = seat
                break
        return result

    def get_player_role(self, room_code: str, player_id: str) -> str | None:
        """Get a player's role. Returns None if player not found."""
        state = self._game_states.get(room_code)
        if not state:
            return None
        for p in state.players.values():
            if p.player_id == player_id:
                return p.role
        return None

    def pause_game(self, room_code: str) -> None:
        """Pause the game."""
        state = self._game_states.get(room_code)
        if state:
            state.is_paused = True

    def resume_game(self, room_code: str) -> None:
        """Resume the game."""
        state = self._game_states.get(room_code)
        if state:
            state.is_paused = False

    def stop_game(self, room_code: str) -> None:
        """Stop the game."""
        state = self._game_states.get(room_code)
        if state:
            state.is_stopped = True

    async def process_player_speech(self, room_code: str, player_id: str, content: str) -> dict:
        """Process a human player's speech input. Alias for process_human_action."""
        await self.process_human_action(room_code, "speech", {"player_id": player_id, "content": content})
        return {"success": True}

    async def process_human_vote(self, room_code: str, player_id: str, target_seat: int | None) -> dict:
        """Process a human player's vote."""
        await self.process_human_action(room_code, "vote", {"player_id": player_id, "target_seat": target_seat})
        return {"success": True}

    async def process_human_night_action(
        self,
        room_code: str,
        player_id: str,
        action_type: str,
        target_seat: int | None = None,
        witch_action: str | None = None,
    ) -> dict:
        """Process a human player's night action (werewolf_kill, seer_check, witch_action, hunter_shoot)."""
        data: dict = {"target_seat": target_seat}
        if witch_action:
            data["witch_action"] = witch_action
        await self.process_human_action(room_code, action_type, {"player_id": player_id, **data})
        return {"success": True}

    async def process_human_speech(self, room_code: str, player_id: str, content: str) -> dict:
        """Process human speech. Same as process_player_speech."""
        await self.process_human_action(room_code, "speech", {"player_id": player_id, "content": content})
        return {"success": True}

    async def process_werewolf_chat(self, room_code: str, player_id: str, content: str) -> dict:
        """Process werewolf private chat message."""
        state = self._game_states.get(room_code)
        if not state:
            return {"success": False, "error": "Game not found"}
        # Find sender
        sender_seat = None
        sender_name = None
        for s, p in state.players.items():
            if p.player_id == player_id:
                sender_seat = s
                sender_name = p.player_name
                break
        if sender_seat is None:
            return {"success": False, "error": "Player not found"}
        # Record chat
        entry = {
            "night_number": state.day_number,
            "seat_number": sender_seat,
            "player_name": sender_name,
            "content": content,
            "is_human": True,
        }
        state.werewolf_private_chat.append(entry)
        return {"success": True, "chat_entry": entry}

    async def process_human_last_words(self, room_code: str, player_id: str, content: str) -> dict:
        """Process a human player's last words."""
        await self.process_human_action(room_code, "last_words", {"player_id": player_id, "content": content})
        return {"success": True}

    # ------------------------------------------------------------------
    # Game loop
    # ------------------------------------------------------------------

    async def _game_loop(self, room_code: str) -> None:
        """Main game loop — runs LangGraph, handles AI/Human interactions between nodes."""
        state = self._game_states.get(room_code)
        if state is None:
            return

        graph = self.engine.compile_graph()

        while state and not state.is_stopped and state.winner is None:
            phase = state.phase

            # ----- Phase-specific handling (before graph invoke) -----
            try:
                if phase == WerewolfPhase.NIGHT_WEREWOLF.value:
                    await self._handle_werewolf_action(room_code)
                elif phase == WerewolfPhase.NIGHT_SEER.value:
                    await self._handle_seer_action(room_code)
                elif phase == WerewolfPhase.NIGHT_WITCH.value:
                    await self._handle_witch_action(room_code)
                elif phase == WerewolfPhase.DAY_ANNOUNCEMENT.value:
                    await self._handle_day_announcement(room_code)
                elif phase == WerewolfPhase.DAY_DISCUSSION.value:
                    await self._handle_day_discussion(room_code)
                elif phase == WerewolfPhase.DAY_VOTE.value:
                    await self._handle_vote(room_code)
                elif phase == WerewolfPhase.LAST_WORDS.value:
                    await self._handle_last_words(room_code)
                elif phase == WerewolfPhase.HUNTER_SHOOT.value:
                    await self._handle_hunter_shoot(room_code)
                elif phase == WerewolfPhase.GAME_OVER.value:
                    await self._handle_game_over(room_code)
                    break
            except Exception:
                logger.exception("Error in phase handler for %s (phase=%s)", room_code, phase)
                break

            # ----- Advance graph one node -----
            try:
                # Wrap state in GraphState typed-dict
                gs_wrapper = {"game_state": state}
                result = graph.invoke(gs_wrapper, {"recursion_limit": 5})
                state = result["game_state"]
                self._game_states[room_code] = state
            except Exception:
                logger.exception("Graph invoke failed for room %s", room_code)
                break

        # Game ended
        if state and state.winner:
            await self._handle_game_over(room_code)

        logger.info("Game loop ended: room=%s winner=%s", room_code, state.winner if state else "N/A")

    # ------------------------------------------------------------------
    # Phase handlers  (input-setting methods called BEFORE graph invoke)
    # ------------------------------------------------------------------

    async def _handle_werewolf_action(self, room_code: str) -> None:
        """Night — werewolf chooses a kill target.

        If the werewolf player is AI, calls ``WerewolfAgent.decide_night_action``.
        If human, waits for input (with AI takeover on timeout).
        Sets ``state.current_night_actions.werewolf_kill_target``.
        """
        state = self._game_states.get(room_code)
        if state is None:
            return

        # Find the decision-maker (only one werewolf makes the call)
        alive_wolves = [
            p for p in state.players.values()
            if p.is_alive and p.role == "werewolf"
        ]
        if not alive_wolves:
            return

        # For now, pick the first alive werewolf as decider
        decider = alive_wolves[0]
        available_targets = [
            {"seat_number": p.seat_number, "name": p.player_name, "player_id": p.player_id}
            for p in state.players.values()
            if p.is_alive and p.team != "werewolf"
        ]

        if decider.is_ai:
            agent = self._ai_agents.get(room_code, {}).get(decider.seat_number)
            if agent is not None and hasattr(agent, "decide_night_action"):
                gs_dict = self._state_to_dict(state)
                decision = await agent.decide_night_action(
                    game_state=gs_dict,
                    available_targets=available_targets,
                    llm_client=self._llm_client,
                )
                target = decision.get("target")
                if target is not None:
                    state.current_night_actions.werewolf_kill_target = target
                    logger.info(
                        "AI werewolf %s decided to kill seat %d",
                        decider.player_name, target,
                    )
        else:
            # Human — wait for input with AI takeover on timeout
            await self._wait_for_human_action(room_code, "kill", timeout=30)
            action = getattr(state, "pending_human_action", None)
            if action and action["type"] == "kill":
                state.current_night_actions.werewolf_kill_target = action["data"].get("target")
            else:
                # AI takeover
                await self._ai_takeover_night_action(room_code, "werewolf")

    async def _handle_seer_action(self, room_code: str) -> None:
        """Night — seer chooses a target to check."""
        state = self._game_states.get(room_code)
        if state is None:
            return

        seer = next(
            (p for p in state.players.values() if p.is_alive and p.role == "seer"),
            None,
        )
        if seer is None:
            return

        available_targets = [
            {"seat_number": p.seat_number, "name": p.player_name}
            for p in state.players.values()
            if p.is_alive and p.seat_number != seer.seat_number
        ]

        if seer.is_ai:
            agent = self._ai_agents.get(room_code, {}).get(seer.seat_number)
            if agent is not None and hasattr(agent, "decide_night_action"):
                gs_dict = self._state_to_dict(state)
                decision = await agent.decide_night_action(
                    game_state=gs_dict,
                    available_targets=available_targets,
                    llm_client=self._llm_client,
                )
                target = decision.get("target")
                if target is not None:
                    state.current_night_actions.seer_check_target = target
                    logger.info("AI seer %s checked seat %d", seer.player_name, target)
        else:
            await self._wait_for_human_action(room_code, "check", timeout=30)
            action = getattr(state, "pending_human_action", None)
            if action and action["type"] == "check":
                state.current_night_actions.seer_check_target = action["data"].get("target")
            else:
                await self._ai_takeover_night_action(room_code, "seer")

    async def _handle_witch_action(self, room_code: str) -> None:
        """Night — witch decides to save and/or poison."""
        state = self._game_states.get(room_code)
        if state is None:
            return

        witch = next(
            (p for p in state.players.values() if p.is_alive and p.role == "witch"),
            None,
        )
        if witch is None:
            return

        kill_target = state.current_night_actions.werewolf_kill_target
        killed_player = (
            {"seat_number": state.players[kill_target].seat_number, "name": state.players[kill_target].player_name}
            if kill_target and kill_target in state.players
            else None
        )

        available_targets = [
            {"seat_number": p.seat_number, "name": p.player_name}
            for p in state.players.values()
            if p.is_alive and p.seat_number != witch.seat_number
        ]

        if witch.is_ai:
            agent = self._ai_agents.get(room_code, {}).get(witch.seat_number)
            if agent is not None and hasattr(agent, "decide_night_action"):
                gs_dict = self._state_to_dict(state)
                decision = await agent.decide_night_action(
                    game_state=gs_dict,
                    available_targets=available_targets,
                    killed_player=killed_player,
                    llm_client=self._llm_client,
                )
                action = decision.get("action", "pass")
                if action == "save":
                    state.current_night_actions.witch_save = True
                    # Mark antidote as used on the state
                    state.witch_has_antidote = False
                    logger.info("AI witch %s saved seat %d", witch.player_name, kill_target)
                if action == "poison":
                    poison_target = decision.get("target")
                    if poison_target is not None:
                        state.current_night_actions.witch_poison_target = poison_target
                        state.witch_has_poison = False
                        logger.info("AI witch %s poisoned seat %d", witch.player_name, poison_target)
        else:
            await self._wait_for_human_action(room_code, "witch", timeout=30)
            action = getattr(state, "pending_human_action", None)
            if action and action["type"] == "witch":
                data = action["data"]
                if data.get("save"):
                    state.current_night_actions.witch_save = True
                    state.witch_has_antidote = False
                if data.get("poison_target"):
                    state.current_night_actions.witch_poison_target = data["poison_target"]
                    state.witch_has_poison = False
            else:
                await self._ai_takeover_night_action(room_code, "witch")

    async def _handle_day_announcement(self, room_code: str) -> None:
        """Day — announce night results via host."""
        state = self._game_states.get(room_code)
        if state is None or self.host is None:
            return

        dead_players = [
            d for d in state.death_history
            if d.get("day") == state.day_number and d.get("phase") == "night"
        ]

        # Broadcast dawn announcement via host
        dead_player_objs = []
        death_reasons = []
        for d in dead_players:
            seat = d.get("seat_number")
            player = state.players.get(seat) if seat else None
            if player:
                dead_player_objs.append({"seat_number": seat, "name": player.player_name})
                death_reasons.append(d.get("reason", "unknown"))

        # In practice the host announce_stream would broadcast via WebSocket
        # For now, log it
        if dead_player_objs:
            logger.info(
                "Day %d dawn: dead=%s reasons=%s",
                state.day_number,
                [p["name"] for p in dead_player_objs],
                death_reasons,
            )
        else:
            logger.info("Day %d dawn: peaceful night", state.day_number)

    async def _handle_day_discussion(self, room_code: str) -> None:
        """Day — iterate alive players and generate AI speeches."""
        state = self._game_states.get(room_code)
        if state is None:
            return

        # Order: ascending seat number, starting from 1
        alive_players = sorted(
            [p for p in state.players.values() if p.is_alive],
            key=lambda p: p.seat_number,
        )

        for player in alive_players:
            if player.is_ai:
                agent = self._ai_agents.get(room_code, {}).get(player.seat_number)
                if agent is not None and hasattr(agent, "generate_speech"):
                    gs_dict = self._state_to_dict(state)
                    try:
                        speech = await agent.generate_speech(
                            game_state=gs_dict,
                            llm_client=self._llm_client,
                        )
                        speech_text = ""
                        if hasattr(speech, "__aiter__"):
                            async for chunk in speech:
                                speech_text += chunk
                        elif isinstance(speech, str):
                            speech_text = speech
                        else:
                            speech_text = str(speech)

                        state.speech_history.append({
                            "seat_number": player.seat_number,
                            "player_name": player.player_name,
                            "content": speech_text,
                            "day": state.day_number,
                        })
                        logger.info(
                            "AI speech: seat %d %s — %s",
                            player.seat_number, player.player_name, speech_text[:50],
                        )
                    except Exception:
                        logger.exception(
                            "Speech generation failed for %s (seat %d)",
                            player.player_name, player.seat_number,
                        )
            # Human speech — would wait for WebSocket input in real implementation

    async def _handle_vote(self, room_code: str) -> None:
        """Day vote — AI agents decide who to vote for."""
        state = self._game_states.get(room_code)
        if state is None:
            return

        alive_players = [
            p for p in state.players.values() if p.is_alive
        ]

        for voter in alive_players:
            available_targets = [
                {"seat_number": p.seat_number, "name": p.player_name}
                for p in alive_players
                if p.seat_number != voter.seat_number
            ]

            if voter.is_ai:
                agent = self._ai_agents.get(room_code, {}).get(voter.seat_number)
                if agent is not None and hasattr(agent, "decide_vote"):
                    gs_dict = self._state_to_dict(state)
                    try:
                        decision = await agent.decide_vote(
                            game_state=gs_dict,
                            available_targets=available_targets,
                            llm_client=self._llm_client,
                        )
                        target = decision.get("target")
                        if target is not None:
                            state.current_votes[voter.seat_number] = target
                            logger.info(
                                "AI vote: seat %d votes for seat %d",
                                voter.seat_number, target,
                            )
                    except Exception:
                        logger.exception(
                            "Vote decision failed for %s (seat %d)",
                            voter.player_name, voter.seat_number,
                        )
            else:
                # Human — wait for input (async while loop)
                await self._wait_for_human_action(room_code, "vote", timeout=30)
                action = getattr(state, "pending_human_action", None)
                if action and action["type"] == "vote":
                    state.current_votes[voter.seat_number] = action["data"].get("target")
                else:
                    # AI takeover: random vote
                    import random
                    fallback = random.choice(available_targets)
                    state.current_votes[voter.seat_number] = fallback["seat_number"]

    async def _handle_last_words(self, room_code: str) -> None:
        """Last words for the eliminated player."""
        state = self._game_states.get(room_code)
        if state is None or state.last_words_seat is None:
            return

        eliminated = state.players.get(state.last_words_seat)
        if eliminated is None:
            return

        # Human eliminated player could speak; AI gets no last words for now
        if eliminated.is_human:
            await self._wait_for_human_action(room_code, "last_words", timeout=15)
            action = getattr(state, "pending_human_action", None)
            if action and action["type"] == "last_words":
                state.last_words_content = action["data"].get("content", "")
                logger.info(
                    "Last words from human %s: %s",
                    eliminated.player_name, state.last_words_content[:50],
                )

    async def _handle_hunter_shoot(self, room_code: str) -> None:
        """Hunter decides to shoot (if eliminated and eligible)."""
        state = self._game_states.get(room_code)
        if state is None or state.last_words_seat is None:
            return

        hunter = state.players.get(state.last_words_seat)
        if hunter is None or hunter.role != "hunter":
            return

        # If poisoned, hunter cannot shoot
        if hunter.death_reason and hunter.death_reason.value == "poisoned":
            logger.info("Hunter %s was poisoned, cannot shoot", hunter.player_name)
            return

        available_targets = [
            {"seat_number": p.seat_number, "name": p.player_name}
            for p in state.players.values()
            if p.is_alive and p.seat_number != hunter.seat_number
        ]

        if not available_targets:
            return

        if hunter.is_ai:
            agent = self._ai_agents.get(room_code, {}).get(hunter.seat_number)
            if agent is not None and hasattr(agent, "decide_shoot"):
                gs_dict = self._state_to_dict(state)
                try:
                    death_reason = hunter.death_reason.value if hunter.death_reason else "voted"
                    decision = await agent.decide_shoot(
                        game_state=gs_dict,
                        death_reason=death_reason,
                        available_targets=available_targets,
                        llm_client=self._llm_client,
                    )
                    action = decision.get("action", "no_shoot")
                    if action == "shoot":
                        target = decision.get("target")
                        if target is not None:
                            state.player_to_shoot = target
                            logger.info(
                                "AI hunter %s shoots seat %d",
                                hunter.player_name, target,
                            )
                except Exception:
                    logger.exception("Hunter shoot decision failed for %s", hunter.player_name)
        else:
            await self._wait_for_human_action(room_code, "shoot", timeout=30)
            action = getattr(state, "pending_human_action", None)
            if action and action["type"] == "shoot":
                target = action["data"].get("target")
                if target is not None:
                    state.player_to_shoot = target
            else:
                # AI takeover
                await self._ai_takeover_hunter_shoot(room_code, hunter)

    async def _handle_game_over(self, room_code: str) -> None:
        """Handle game end."""
        state = self._game_states.get(room_code)
        if state is None or self.host is None:
            return

        logger.info(
            "Game over: room=%s winner=%s day=%d",
            room_code, state.winner, state.day_number,
        )
        # Cleanup
        self._game_states.pop(room_code, None)
        self._ai_agents.pop(room_code, None)

    # ------------------------------------------------------------------
    # AI helpers
    # ------------------------------------------------------------------

    async def _ai_takeover_night_action(self, room_code: str, role: str) -> None:
        """AI takeover when human player times out on a night action."""
        state = self._game_states.get(room_code)
        if state is None:
            return

        # Fall back to AI agent decision
        player = next(
            (p for p in state.players.values() if p.is_human and p.role == role and p.is_alive),
            None,
        )
        if player is None:
            return

        agent = self._ai_agents.get(room_code, {}).get(player.seat_number)
        if agent is None:
            return

        available_targets = [
            {"seat_number": p.seat_number, "name": p.player_name}
            for p in state.players.values()
            if p.is_alive
        ]

        gs_dict = self._state_to_dict(state)
        try:
            decision = await agent.decide_night_action(
                game_state=gs_dict,
                available_targets=available_targets,
                llm_client=self._llm_client,
            )
            logger.info("AI takeover for human %s: %s", role, decision)
        except Exception:
            logger.exception("AI takeover failed for human %s", role)

    async def _ai_takeover_hunter_shoot(self, room_code: str, hunter: PlayerState) -> None:
        """AI takeover when human hunter times out."""
        agent = self._ai_agents.get(room_code, {}).get(hunter.seat_number)
        if agent is None:
            return

        available_targets = [
            {"seat_number": p.seat_number, "name": p.player_name}
            for p in self._game_states[room_code].players.values()
            if p.is_alive and p.seat_number != hunter.seat_number
        ]

        gs_dict = self._state_to_dict(self._game_states[room_code])
        try:
            death_reason = hunter.death_reason.value if hunter.death_reason else "voted"
            decision = await agent.decide_shoot(
                game_state=gs_dict,
                death_reason=death_reason,
                available_targets=available_targets,
                llm_client=self._llm_client,
            )
            if decision.get("action") == "shoot":
                self._game_states[room_code].player_to_shoot = decision.get("target")
                logger.info("AI takeover hunter shoot: %s", decision)
        except Exception:
            logger.exception("AI takeover hunter shoot failed")

    # ------------------------------------------------------------------
    # Human input waiting
    # ------------------------------------------------------------------

    async def _wait_for_human_action(
        self,
        room_code: str,
        action_type: str,
        timeout: int = 30,
        interval: float = 0.1,
    ) -> None:
        """Wait for a human player's action with timeout.

        Sets ``state.waiting_for_human_action = True`` and polls every
        ``interval`` seconds.  If the human doesn't respond within
        ``timeout`` seconds, proceeds (the caller should have an AI takeover
        fallback).
        """
        state = self._game_states.get(room_code)
        if state is None:
            return

        state.waiting_for_human_action = True
        state.human_action_type = action_type
        state.pending_human_action = None

        elapsed = 0.0
        while state.waiting_for_human_action and elapsed < timeout:
            await asyncio.sleep(interval)
            elapsed += interval
            # Check if the human submitted an action (set by process_human_action)
            if state.pending_human_action is not None:
                break

        state.waiting_for_human_action = False
        if state.pending_human_action is None:
            logger.info("Human action timeout: room=%s type=%s", room_code, action_type)

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def _state_to_dict(self, state: WerewolfGameState) -> Dict[str, Any]:
        """Convert game state to a flat dict for AI agent consumption."""
        alive_players = [
            {"seat_number": p.seat_number, "name": p.player_name, "role": p.role}
            for p in state.players.values()
            if p.is_alive
        ]
        dead_players = [
            {"seat_number": p.seat_number, "name": p.player_name, "role": p.role}
            for p in state.players.values()
            if not p.is_alive
        ]
        return {
            "day_number": state.day_number,
            "phase": state.phase,
            "alive_players": alive_players,
            "dead_players": dead_players,
            "speech_history": "\n".join(
                f"{s['seat_number']}号{s['player_name']}: {s['content']}"
                for s in state.speech_history[-20:]
            ),
            "vote_history": state.vote_history,
            "death_history": state.death_history,
        }

    def _create_agent(self, role: str, player: PlayerState, personality: Dict[str, Any]) -> Any:
        """Create an AI agent for a player's role."""
        from src.games.werewolf.agents import (
            WerewolfAgent,
            SeerAgent,
            WitchAgent,
            HunterAgent,
            VillagerAgent,
        )
        mapping = {
            "werewolf": WerewolfAgent,
            "seer": SeerAgent,
            "witch": WitchAgent,
            "hunter": HunterAgent,
            "villager": VillagerAgent,
        }
        cls = mapping.get(role)
        if cls is None:
            logger.warning("No agent class for role: %s", role)
            return None
        return cls(
            player.player_id,
            player.player_name,
            player.seat_number,
            personality=personality,
        )
