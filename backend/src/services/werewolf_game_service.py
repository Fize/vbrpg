"""Werewolf game service for managing single-player werewolf games."""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.game import GameRoom, GameRoomParticipant, GameSession, GameState
from src.services.games.werewolf_engine import (
    WerewolfEngine,
    WerewolfPhase,
    WerewolfGameState,
    PlayerState,
    GameLogEntry,
)
from src.services.ai_agents import (
    WerewolfAgent,
    SeerAgent,
    WitchAgent,
    HunterAgent,
    VillagerAgent,
)
from src.services.ai_agents.host import WerewolfHost
from src.websocket import (
    broadcast_host_announcement,
    stream_host_announcement,
    broadcast_game_state_update,
    broadcast_phase_change,
    notify_werewolf_turn,
    notify_seer_turn,
    notify_seer_result,
    notify_witch_turn,
    notify_hunter_shoot,
    stream_ai_speech,
    broadcast_vote_update,
    broadcast_vote_result,
    broadcast_game_over,
)
from src.utils.errors import BadRequestError, NotFoundError

logger = logging.getLogger(__name__)


class WerewolfGameService:
    """Service for managing werewolf game sessions.
    
    This service handles:
    - Game initialization with AI players
    - Night phase execution (werewolf/seer/witch actions)
    - Day phase execution (AI speeches and voting)
    - Human player action processing
    - Win condition checking
    """
    
    def __init__(self, db: AsyncSession):
        """Initialize service.
        
        Args:
            db: Database session
        """
        self.db = db
        self.engine = WerewolfEngine()
        self.host = WerewolfHost()
        self._ai_agents: dict[int, Any] = {}  # seat_number -> agent
        self._game_states: dict[str, WerewolfGameState] = {}  # room_code -> state
    
    # =========================================================================
    # B34: 游戏启动流程
    # =========================================================================
    
    async def start_game(
        self,
        room_code: str,
        human_player_id: str,
        human_role: str | None = None
    ) -> WerewolfGameState:
        """Start a new werewolf game.
        
        Args:
            room_code: Room code for the game
            human_player_id: The human player's ID
            human_role: Optional role for human player (for testing)
            
        Returns:
            Initialized game state
        """
        logger.info(f"Starting werewolf game in room {room_code}")
        
        # Initialize game state
        game_state = self.engine.initialize_game(
            room_code=room_code,
            user_player_id=human_player_id,
            user_preferred_role=human_role
        )
        
        # Store state
        self._game_states[room_code] = game_state
        
        # Create AI agents for all non-human players
        await self._create_ai_agents(game_state, human_player_id)
        
        # Broadcast game start announcement
        await self._announce_game_start(room_code, game_state)
        
        # Start the first night
        await self._start_night_phase(room_code)
        
        return game_state
    
    async def _create_ai_agents(
        self,
        game_state: WerewolfGameState,
        human_player_id: str
    ):
        """Create AI agents for non-human players."""
        for player in game_state.players.values():
            if player.player_id == human_player_id:
                continue
            
            # Create agent based on role
            agent = self._create_agent_for_role(
                role=player.role,
                seat_number=player.seat_number,
                player_name=f"玩家{player.seat_number}"
            )
            
            if agent:
                self._ai_agents[player.seat_number] = agent
                
                # Set teammates for werewolves
                if player.role == "werewolf":
                    teammates = [
                        (p.seat_number, f"玩家{p.seat_number}")
                        for p in game_state.players.values()
                        if p.role == "werewolf" and p.seat_number != player.seat_number
                    ]
                    agent.set_teammates(teammates)
        
        logger.info(f"Created {len(self._ai_agents)} AI agents")
    
    def _create_agent_for_role(
        self,
        role: str,
        seat_number: int,
        player_name: str
    ):
        """Create an AI agent for a specific role."""
        if role == "werewolf":
            return WerewolfAgent(
                seat_number=seat_number,
                player_name=player_name
            )
        elif role == "seer":
            return SeerAgent(
                seat_number=seat_number,
                player_name=player_name
            )
        elif role == "witch":
            return WitchAgent(
                seat_number=seat_number,
                player_name=player_name,
                can_self_save=True
            )
        elif role == "hunter":
            return HunterAgent(
                seat_number=seat_number,
                player_name=player_name
            )
        elif role == "villager":
            return VillagerAgent(
                seat_number=seat_number,
                player_name=player_name
            )
        return None
    
    async def _announce_game_start(
        self,
        room_code: str,
        game_state: WerewolfGameState
    ):
        """Announce game start with role assignment."""
        # Stream host announcement
        announcement_stream = self.host.announce_game_start_stream(
            player_count=len(game_state.players),
            werewolf_count=3,
            special_roles=["预言家", "女巫", "猎人"]
        )
        
        await stream_host_announcement(
            room_code=room_code,
            announcement_type="game_start",
            content_stream=announcement_stream,
            metadata={
                "player_count": len(game_state.players),
                "werewolf_count": 3
            }
        )
    
    # =========================================================================
    # B35: 夜晚执行流程
    # =========================================================================
    
    async def _start_night_phase(self, room_code: str):
        """Start the night phase."""
        game_state = self._game_states.get(room_code)
        if not game_state:
            return
        
        # Announce night start
        announcement_stream = self.host.announce_night_start_stream(
            day_number=game_state.day_number
        )
        await stream_host_announcement(
            room_code=room_code,
            announcement_type="night_start",
            content_stream=announcement_stream,
            metadata={"day_number": game_state.day_number}
        )
        
        # Update phase
        old_phase = game_state.phase
        game_state.phase = WerewolfPhase.NIGHT_WEREWOLF
        await broadcast_phase_change(
            room_code=room_code,
            from_phase=old_phase.value,
            to_phase=game_state.phase.value,
            day_number=game_state.day_number
        )
        
        # Start werewolf action
        await self._execute_werewolf_action(room_code)
    
    async def _execute_werewolf_action(self, room_code: str):
        """Execute werewolf kill action (AI only, human waits)."""
        game_state = self._game_states.get(room_code)
        if not game_state:
            return
        
        # Get alive werewolves and targets
        werewolves = [
            p for p in game_state.players.values()
            if p.role == "werewolf" and p.is_alive
        ]
        targets = [
            {"seat_number": p.seat_number, "display_name": f"玩家{p.seat_number}"}
            for p in game_state.players.values()
            if p.is_alive
        ]
        
        # Check if human is werewolf
        human_werewolf = None
        ai_werewolves = []
        for wolf in werewolves:
            if wolf.seat_number in self._ai_agents:
                ai_werewolves.append(wolf)
            else:
                human_werewolf = wolf
        
        if human_werewolf:
            # Notify human to make decision
            await notify_werewolf_turn(
                room_code=room_code,
                werewolf_player_ids=[human_werewolf.player_id],
                alive_targets=targets
            )
            # Wait for human input via werewolf_action event
            return
        
        # All werewolves are AI - let them decide
        if ai_werewolves:
            # Use first werewolf's agent to make decision
            wolf_agent = self._ai_agents.get(ai_werewolves[0].seat_number)
            if wolf_agent:
                game_history = game_state.game_log
                alive_seats = [p.seat_number for p in game_state.players.values() if p.is_alive]
                
                target_seat = await wolf_agent.decide_night_action(
                    game_history=game_history,
                    alive_players=alive_seats
                )
                
                # Process the kill
                self.engine.process_werewolf_action(game_state, target_seat)
                game_state.game_log.append(f"夜晚：狼人选择击杀{target_seat}号玩家" if target_seat else "夜晚：狼人选择空刀")
        
        # Move to seer phase
        await self._execute_seer_action(room_code)
    
    async def _execute_seer_action(self, room_code: str):
        """Execute seer check action."""
        game_state = self._game_states.get(room_code)
        if not game_state:
            return
        
        game_state.phase = WerewolfPhase.NIGHT_SEER
        
        # Find alive seer
        seer = next(
            (p for p in game_state.players.values() if p.role == "seer" and p.is_alive),
            None
        )
        
        if not seer:
            # Seer is dead, skip to witch
            await self._execute_witch_action(room_code)
            return
        
        targets = [
            {"seat_number": p.seat_number, "display_name": f"玩家{p.seat_number}"}
            for p in game_state.players.values()
            if p.is_alive and p.seat_number != seer.seat_number
        ]
        
        if seer.seat_number in self._ai_agents:
            # AI seer
            seer_agent = self._ai_agents[seer.seat_number]
            game_history = game_state.game_log
            alive_seats = [p.seat_number for p in game_state.players.values() if p.is_alive]
            
            target_seat = await seer_agent.decide_night_action(
                game_history=game_history,
                alive_players=alive_seats
            )
            
            if target_seat:
                is_werewolf = self.engine.process_seer_action(game_state, target_seat)
                seer_agent.record_check_result(target_seat, is_werewolf)
                game_state.game_log.append(f"夜晚：预言家查验了{target_seat}号玩家，结果是{'狼人' if is_werewolf else '好人'}")
            
            # Move to witch
            await self._execute_witch_action(room_code)
        else:
            # Human seer
            await notify_seer_turn(
                room_code=room_code,
                seer_player_id=seer.player_id,
                alive_targets=targets
            )
            # Wait for human input
    
    async def _execute_witch_action(self, room_code: str):
        """Execute witch save/poison action."""
        game_state = self._game_states.get(room_code)
        if not game_state:
            return
        
        game_state.phase = WerewolfPhase.NIGHT_WITCH
        
        # Find alive witch
        witch = next(
            (p for p in game_state.players.values() if p.role == "witch" and p.is_alive),
            None
        )
        
        if not witch:
            # Witch is dead, process night and go to day
            await self._end_night_phase(room_code)
            return
        
        # Get killed player info
        killed_seat = game_state.werewolf_target
        killed_player = None
        if killed_seat:
            killed_p = game_state.players.get(killed_seat)
            if killed_p:
                killed_player = {
                    "seat_number": killed_seat,
                    "display_name": f"玩家{killed_seat}"
                }
        
        # Check witch potions
        has_antidote = game_state.witch_actions.get("has_antidote", True)
        has_poison = game_state.witch_actions.get("has_poison", True)
        can_self_save = game_state.day_number == 1  # First night can self-save
        
        targets = [
            {"seat_number": p.seat_number, "display_name": f"玩家{p.seat_number}"}
            for p in game_state.players.values()
            if p.is_alive and p.seat_number != witch.seat_number
        ]
        
        if witch.seat_number in self._ai_agents:
            # AI witch
            witch_agent = self._ai_agents[witch.seat_number]
            
            save_target, poison_target = await witch_agent.decide_night_action(
                game_history=game_state.game_log,
                alive_players=[p.seat_number for p in game_state.players.values() if p.is_alive],
                killed_player=killed_seat,
                can_save=has_antidote and (killed_seat is not None),
                can_poison=has_poison
            )
            
            self.engine.process_witch_action(
                game_state,
                save_target=save_target,
                poison_target=poison_target
            )
            
            if save_target:
                game_state.game_log.append(f"夜晚：女巫救了{save_target}号玩家")
            if poison_target:
                game_state.game_log.append(f"夜晚：女巫毒了{poison_target}号玩家")
            
            # End night
            await self._end_night_phase(room_code)
        else:
            # Human witch
            await notify_witch_turn(
                room_code=room_code,
                witch_player_id=witch.player_id,
                killed_player=killed_player,
                has_antidote=has_antidote,
                has_poison=has_poison,
                can_self_save=can_self_save,
                alive_targets=targets
            )
            # Wait for human input
    
    async def _end_night_phase(self, room_code: str):
        """End night phase and transition to day."""
        game_state = self._game_states.get(room_code)
        if not game_state:
            return
        
        # Process night deaths
        deaths = self.engine.advance_to_day(game_state)
        
        # Announce dawn
        dead_info = [
            {"seat_number": d, "display_name": f"玩家{d}"}
            for d in deaths
        ] if deaths else None
        
        announcement_stream = self.host.announce_dawn_stream(
            day_number=game_state.day_number,
            dead_players=dead_info
        )
        await stream_host_announcement(
            room_code=room_code,
            announcement_type="dawn",
            content_stream=announcement_stream,
            metadata={"dead_players": dead_info}
        )
        
        # Check win condition
        winner = self.engine.check_winner(game_state)
        if winner:
            await self._end_game(room_code, winner)
            return
        
        # Handle hunter shoot if applicable
        for death_seat in deaths:
            player = game_state.players.get(death_seat)
            if player and player.role == "hunter":
                await self._handle_hunter_shoot(room_code, death_seat)
                return
        
        # Start day discussion
        await self._start_day_discussion(room_code)
    
    # =========================================================================
    # B36: 白天执行流程
    # =========================================================================
    
    async def _start_day_discussion(self, room_code: str):
        """Start day discussion phase."""
        game_state = self._game_states.get(room_code)
        if not game_state:
            return
        
        game_state.phase = WerewolfPhase.DAY_DISCUSSION
        
        # Announce discussion start
        await broadcast_host_announcement(
            room_code=room_code,
            announcement_type="discussion_start",
            content=f"第{game_state.day_number}天，请各位玩家依次发言，从1号开始。"
        )
        
        # Execute speeches in order
        await self._execute_speeches(room_code)
    
    async def _execute_speeches(self, room_code: str):
        """Execute all player speeches in seat order."""
        game_state = self._game_states.get(room_code)
        if not game_state:
            return
        
        # Get alive players in seat order
        alive_players = sorted(
            [p for p in game_state.players.values() if p.is_alive],
            key=lambda p: p.seat_number
        )
        
        for player in alive_players:
            if player.seat_number in self._ai_agents:
                # AI speech with streaming
                agent = self._ai_agents[player.seat_number]
                
                speech_stream = agent.generate_speech_stream(
                    game_history=game_state.game_log,
                    alive_players=[p.seat_number for p in alive_players],
                    day_number=game_state.day_number
                )
                
                speech_content = await stream_ai_speech(
                    room_code=room_code,
                    speaker_seat=player.seat_number,
                    speaker_name=f"玩家{player.seat_number}",
                    speech_stream=speech_stream
                )
                
                game_state.game_log.append(f"第{game_state.day_number}天 - {player.seat_number}号发言: {speech_content}")
                
                # Small delay between speeches
                await asyncio.sleep(0.5)
            else:
                # Human player - in single player mode, human can choose to skip or just listen
                # For simplicity, we'll broadcast that it's human's turn
                await broadcast_host_announcement(
                    room_code=room_code,
                    announcement_type="your_turn_speech",
                    content=f"轮到你发言了（{player.seat_number}号）",
                    metadata={"seat_number": player.seat_number}
                )
                # In auto mode, we skip human speech after a brief pause
                await asyncio.sleep(2)
        
        # Start voting
        await self._start_voting(room_code)
    
    async def _start_voting(self, room_code: str):
        """Start voting phase."""
        game_state = self._game_states.get(room_code)
        if not game_state:
            return
        
        game_state.phase = WerewolfPhase.DAY_VOTE
        game_state.vote_results = {}
        
        # Announce voting
        await broadcast_host_announcement(
            room_code=room_code,
            announcement_type="vote_start",
            content="发言结束，请投票选出今天要放逐的玩家。"
        )
        
        # Execute votes
        await self._execute_votes(room_code)
    
    async def _execute_votes(self, room_code: str):
        """Execute all player votes."""
        game_state = self._game_states.get(room_code)
        if not game_state:
            return
        
        alive_players = [p for p in game_state.players.values() if p.is_alive]
        alive_seats = [p.seat_number for p in alive_players]
        
        for player in alive_players:
            if player.seat_number in self._ai_agents:
                # AI vote
                agent = self._ai_agents[player.seat_number]
                
                vote_target = await agent.decide_vote(
                    game_history=game_state.game_log,
                    alive_players=alive_seats
                )
                
                self.engine.process_vote(game_state, player.seat_number, vote_target)
                
                # Broadcast vote
                target_name = f"玩家{vote_target}" if vote_target else None
                await broadcast_vote_update(
                    room_code=room_code,
                    voter_seat=player.seat_number,
                    voter_name=f"玩家{player.seat_number}",
                    target_seat=vote_target,
                    target_name=target_name
                )
                
                game_state.game_log.append(
                    f"投票: {player.seat_number}号投给{vote_target}号" if vote_target 
                    else f"投票: {player.seat_number}号弃票"
                )
                
                await asyncio.sleep(0.3)
            else:
                # Human player - wait for input or auto-abstain
                # For simplicity in auto mode, human abstains
                self.engine.process_vote(game_state, player.seat_number, None)
                await broadcast_vote_update(
                    room_code=room_code,
                    voter_seat=player.seat_number,
                    voter_name=f"玩家{player.seat_number}",
                    target_seat=None,
                    target_name=None
                )
        
        # Process vote result
        await self._process_vote_result(room_code)
    
    async def _process_vote_result(self, room_code: str):
        """Process voting result and eliminate player if applicable."""
        game_state = self._game_states.get(room_code)
        if not game_state:
            return
        
        eliminated, is_tie, vote_counts = self.engine.process_vote_result(game_state)
        
        # Broadcast result
        eliminated_name = f"玩家{eliminated}" if eliminated else None
        await broadcast_vote_result(
            room_code=room_code,
            vote_counts=vote_counts,
            eliminated_seat=eliminated,
            eliminated_name=eliminated_name,
            is_tie=is_tie
        )
        
        if eliminated:
            game_state.game_log.append(f"投票结果: {eliminated}号玩家被放逐")
            
            # Announce death
            player = game_state.players.get(eliminated)
            if player:
                announcement_stream = self.host.announce_death_stream(
                    seat_number=eliminated,
                    player_name=f"玩家{eliminated}",
                    death_reason="vote"
                )
                await stream_host_announcement(
                    room_code=room_code,
                    announcement_type="death",
                    content_stream=announcement_stream
                )
                
                # Check for hunter
                if player.role == "hunter":
                    await self._handle_hunter_shoot(room_code, eliminated)
                    return
        else:
            game_state.game_log.append("投票结果: 平票，无人出局")
        
        # Check win condition
        winner = self.engine.check_winner(game_state)
        if winner:
            await self._end_game(room_code, winner)
            return
        
        # Start next night
        game_state.day_number += 1
        await self._start_night_phase(room_code)
    
    # =========================================================================
    # B37: 用户行动处理
    # =========================================================================
    
    async def process_human_action(
        self,
        room_code: str,
        player_id: str,
        action_type: str,
        target_seat: int | None
    ):
        """Process action from human player.
        
        Args:
            room_code: Room code
            player_id: Human player ID
            action_type: Type of action (kill, check, save, poison, shoot, vote)
            target_seat: Target seat number (None for skip/abstain)
        """
        game_state = self._game_states.get(room_code)
        if not game_state:
            raise NotFoundError(f"Game not found for room {room_code}")
        
        # Find human player
        human_player = next(
            (p for p in game_state.players.values() if p.player_id == player_id),
            None
        )
        if not human_player:
            raise BadRequestError("Player not in game")
        
        if action_type == "kill":
            await self._handle_human_kill(room_code, human_player, target_seat)
        elif action_type == "check":
            await self._handle_human_check(room_code, human_player, target_seat)
        elif action_type == "save":
            await self._handle_human_save(room_code, human_player, target_seat)
        elif action_type == "poison":
            await self._handle_human_poison(room_code, human_player, target_seat)
        elif action_type == "shoot":
            await self._handle_human_shoot(room_code, human_player, target_seat)
        elif action_type == "vote":
            await self._handle_human_vote(room_code, human_player, target_seat)
        else:
            raise BadRequestError(f"Unknown action type: {action_type}")
    
    async def _handle_human_kill(
        self,
        room_code: str,
        player: PlayerState,
        target_seat: int | None
    ):
        """Handle human werewolf kill action."""
        game_state = self._game_states[room_code]
        
        if player.role != "werewolf":
            raise BadRequestError("Only werewolf can kill")
        if game_state.phase != WerewolfPhase.NIGHT_WEREWOLF:
            raise BadRequestError("Not werewolf action phase")
        
        self.engine.process_werewolf_action(game_state, target_seat)
        game_state.game_log.append(
            f"夜晚：狼人选择击杀{target_seat}号玩家" if target_seat else "夜晚：狼人选择空刀"
        )
        
        # Continue to seer phase
        await self._execute_seer_action(room_code)
    
    async def _handle_human_check(
        self,
        room_code: str,
        player: PlayerState,
        target_seat: int | None
    ):
        """Handle human seer check action."""
        game_state = self._game_states[room_code]
        
        if player.role != "seer":
            raise BadRequestError("Only seer can check")
        if game_state.phase != WerewolfPhase.NIGHT_SEER:
            raise BadRequestError("Not seer action phase")
        
        if target_seat:
            is_werewolf = self.engine.process_seer_action(game_state, target_seat)
            game_state.game_log.append(
                f"夜晚：预言家查验了{target_seat}号玩家，结果是{'狼人' if is_werewolf else '好人'}"
            )
            
            # Notify human of result
            target_player = game_state.players.get(target_seat)
            await notify_seer_result(
                room_code=room_code,
                seer_player_id=player.player_id,
                target_seat=target_seat,
                target_name=f"玩家{target_seat}",
                is_werewolf=is_werewolf
            )
        
        # Continue to witch phase
        await self._execute_witch_action(room_code)
    
    async def _handle_human_save(
        self,
        room_code: str,
        player: PlayerState,
        target_seat: int | None
    ):
        """Handle human witch save action."""
        game_state = self._game_states[room_code]
        
        if player.role != "witch":
            raise BadRequestError("Only witch can save")
        if game_state.phase != WerewolfPhase.NIGHT_WITCH:
            raise BadRequestError("Not witch action phase")
        
        self.engine.process_witch_action(game_state, save_target=target_seat)
        if target_seat:
            game_state.game_log.append(f"夜晚：女巫救了{target_seat}号玩家")
    
    async def _handle_human_poison(
        self,
        room_code: str,
        player: PlayerState,
        target_seat: int | None
    ):
        """Handle human witch poison action."""
        game_state = self._game_states[room_code]
        
        if player.role != "witch":
            raise BadRequestError("Only witch can poison")
        if game_state.phase != WerewolfPhase.NIGHT_WITCH:
            raise BadRequestError("Not witch action phase")
        
        self.engine.process_witch_action(game_state, poison_target=target_seat)
        if target_seat:
            game_state.game_log.append(f"夜晚：女巫毒了{target_seat}号玩家")
        
        # End night phase
        await self._end_night_phase(room_code)
    
    async def _handle_human_shoot(
        self,
        room_code: str,
        player: PlayerState,
        target_seat: int | None
    ):
        """Handle human hunter shoot action."""
        game_state = self._game_states[room_code]
        
        if player.role != "hunter":
            raise BadRequestError("Only hunter can shoot")
        
        if target_seat:
            self.engine.process_hunter_shoot(game_state, target_seat)
            game_state.game_log.append(f"猎人开枪带走了{target_seat}号玩家")
            
            # Announce hunter shoot
            await broadcast_host_announcement(
                room_code=room_code,
                announcement_type="hunter_shoot",
                content=f"猎人发动技能，带走了{target_seat}号玩家！",
                metadata={"target_seat": target_seat}
            )
        
        # Check win and continue
        winner = self.engine.check_winner(game_state)
        if winner:
            await self._end_game(room_code, winner)
        elif game_state.phase == WerewolfPhase.DAY_ANNOUNCEMENT:
            await self._start_day_discussion(room_code)
        else:
            game_state.day_number += 1
            await self._start_night_phase(room_code)
    
    async def _handle_human_vote(
        self,
        room_code: str,
        player: PlayerState,
        target_seat: int | None
    ):
        """Handle human vote action."""
        game_state = self._game_states[room_code]
        
        if game_state.phase != WerewolfPhase.DAY_VOTE:
            raise BadRequestError("Not voting phase")
        
        self.engine.process_vote(game_state, player.seat_number, target_seat)
        game_state.game_log.append(
            f"投票: {player.seat_number}号投给{target_seat}号" if target_seat 
            else f"投票: {player.seat_number}号弃票"
        )
    
    # =========================================================================
    # B38: 猎人技能和游戏结束
    # =========================================================================
    
    async def _handle_hunter_shoot(self, room_code: str, hunter_seat: int):
        """Handle hunter death and shooting."""
        game_state = self._game_states.get(room_code)
        if not game_state:
            return
        
        game_state.phase = WerewolfPhase.HUNTER_SHOOT
        
        hunter = game_state.players.get(hunter_seat)
        if not hunter:
            return
        
        # Get alive targets
        targets = [
            {"seat_number": p.seat_number, "display_name": f"玩家{p.seat_number}"}
            for p in game_state.players.values()
            if p.is_alive and p.seat_number != hunter_seat
        ]
        
        if hunter_seat in self._ai_agents:
            # AI hunter
            hunter_agent = self._ai_agents[hunter_seat]
            
            shoot_target = await hunter_agent.decide_shoot(
                game_history=game_state.game_log,
                alive_players=[p.seat_number for p in game_state.players.values() if p.is_alive]
            )
            
            if shoot_target:
                self.engine.process_hunter_shoot(game_state, shoot_target)
                game_state.game_log.append(f"猎人开枪带走了{shoot_target}号玩家")
                
                await broadcast_host_announcement(
                    room_code=room_code,
                    announcement_type="hunter_shoot",
                    content=f"猎人发动技能，带走了{shoot_target}号玩家！",
                    metadata={"target_seat": shoot_target}
                )
            
            # Check win and continue
            winner = self.engine.check_winner(game_state)
            if winner:
                await self._end_game(room_code, winner)
            elif game_state.phase == WerewolfPhase.DAY_ANNOUNCEMENT:
                await self._start_day_discussion(room_code)
            else:
                game_state.day_number += 1
                await self._start_night_phase(room_code)
        else:
            # Human hunter - notify and wait
            await notify_hunter_shoot(
                room_code=room_code,
                hunter_player_id=hunter.player_id,
                alive_targets=targets
            )
    
    async def _end_game(self, room_code: str, winner: str):
        """End the game and announce winner."""
        game_state = self._game_states.get(room_code)
        if not game_state:
            return
        
        game_state.phase = WerewolfPhase.GAME_OVER
        game_state.winner = winner
        
        # Prepare player info for reveal
        all_players = [
            {
                "seat_number": p.seat_number,
                "display_name": f"玩家{p.seat_number}",
                "role": p.role,
                "team": p.team,
                "is_alive": p.is_alive
            }
            for p in game_state.players.values()
        ]
        
        winning_team = "werewolf" if winner == "werewolf" else "villager"
        winning_players = [p for p in all_players if p["team"] == winning_team]
        
        # Announce game over
        announcement_stream = self.host.announce_game_over_stream(
            winner=winner,
            day_number=game_state.day_number
        )
        await stream_host_announcement(
            room_code=room_code,
            announcement_type="game_over",
            content_stream=announcement_stream,
            metadata={"winner": winner}
        )
        
        # Broadcast detailed results
        await broadcast_game_over(
            room_code=room_code,
            winner=winner,
            winning_players=winning_players,
            all_players=all_players
        )
        
        game_state.game_log.append(f"游戏结束，{'狼人阵营' if winner == 'werewolf' else '好人阵营'}获胜！")
        
        logger.info(f"Game ended in room {room_code}: {winner} wins")
        
        # Clean up
        self._cleanup_game(room_code)
    
    def _cleanup_game(self, room_code: str):
        """Clean up game resources."""
        if room_code in self._game_states:
            del self._game_states[room_code]
        
        # Clear AI agents for this game
        # Note: In production, agents should be scoped per game
        self._ai_agents.clear()

    # =========================================================================
    # 游戏控制方法 (Phase 3: B6, B7, B8, B9)
    # =========================================================================

    async def start_game_manual(self, room_code: str) -> bool:
        """手动开始游戏（由用户触发）。

        Args:
            room_code: 房间代码

        Returns:
            是否成功开始游戏

        Raises:
            NotFoundError: 游戏状态不存在
            BadRequestError: 游戏已开始
        """
        game_state = self._game_states.get(room_code)
        if not game_state:
            raise NotFoundError(f"游戏状态不存在: {room_code}")

        if game_state.is_started:
            raise BadRequestError("游戏已经开始")

        # 设置游戏已开始
        game_state.is_started = True
        game_state.is_paused = False

        logger.info(f"Game manually started in room {room_code}")

        # 记录日志
        self._add_game_log(
            room_code=room_code,
            log_type="system",
            content="游戏开始",
            metadata={"triggered_by": "manual"},
        )

        return True

    async def pause_game(self, room_code: str) -> bool:
        """暂停游戏，等待当前行动完成后生效。

        Args:
            room_code: 房间代码

        Returns:
            是否成功暂停

        Raises:
            NotFoundError: 游戏状态不存在
            BadRequestError: 游戏未开始或已暂停
        """
        game_state = self._game_states.get(room_code)
        if not game_state:
            raise NotFoundError(f"游戏状态不存在: {room_code}")

        if not game_state.is_started:
            raise BadRequestError("游戏尚未开始")

        if game_state.is_paused:
            raise BadRequestError("游戏已经暂停")

        # 标记暂停（当前行动完成后生效）
        game_state.is_paused = True

        logger.info(f"Game paused in room {room_code}")

        # 记录日志
        self._add_game_log(
            room_code=room_code,
            log_type="system",
            content="游戏暂停",
        )

        return True

    async def resume_game(self, room_code: str) -> bool:
        """继续游戏。

        Args:
            room_code: 房间代码

        Returns:
            是否成功继续

        Raises:
            NotFoundError: 游戏状态不存在
            BadRequestError: 游戏未暂停
        """
        game_state = self._game_states.get(room_code)
        if not game_state:
            raise NotFoundError(f"游戏状态不存在: {room_code}")

        if not game_state.is_paused:
            raise BadRequestError("游戏未暂停")

        # 取消暂停
        game_state.is_paused = False

        logger.info(f"Game resumed in room {room_code}")

        # 记录日志
        self._add_game_log(
            room_code=room_code,
            log_type="system",
            content="游戏继续",
        )

        return True

    async def _check_paused_before_next_action(self, room_code: str) -> bool:
        """在执行下一个行动前检查是否暂停。

        如果游戏暂停，此方法会阻塞直到游戏继续。

        Args:
            room_code: 房间代码

        Returns:
            True 表示可以继续执行，False 表示游戏状态不存在
        """
        game_state = self._game_states.get(room_code)
        if not game_state:
            return False

        # 如果暂停，等待继续
        while game_state.is_paused:
            await asyncio.sleep(0.5)
            # 重新获取状态，以防游戏被清理
            game_state = self._game_states.get(room_code)
            if not game_state:
                return False

        return True

    # =========================================================================
    # 主持人公告广播 (Phase 4: B10)
    # =========================================================================

    async def _broadcast_host_announcement(
        self,
        room_code: str,
        announcement_type: str,
        metadata: dict | None = None,
    ) -> str:
        """广播主持人公告（流式）。

        流程：
        1. 调用 WerewolfHost 生成公告
        2. 发送 announcement_start 事件
        3. 循环发送 announcement_chunk 事件
        4. 发送 announcement_end 事件
        5. 记录到游戏日志

        Args:
            room_code: 房间代码
            announcement_type: 公告类型
            metadata: 额外元数据

        Returns:
            完整的公告内容
        """
        game_state = self._game_states.get(room_code)
        if not game_state:
            logger.warning(f"Cannot broadcast announcement: game state not found for {room_code}")
            return ""

        # 构建公告上下文
        context = self._build_announcement_context(game_state, announcement_type, metadata)

        # 使用流式输出广播公告
        content_stream = self.host.announce_stream(announcement_type, context)

        full_content = await stream_host_announcement(
            room_code=room_code,
            announcement_type=announcement_type,
            content_stream=content_stream,
            metadata=metadata,
        )

        # 记录到游戏日志
        self._add_game_log(
            room_code=room_code,
            log_type="host_announcement",
            content=full_content,
            metadata={
                "announcement_type": announcement_type,
                **(metadata or {}),
            },
            is_public=True,
        )

        return full_content

    def _build_announcement_context(
        self,
        game_state: WerewolfGameState,
        announcement_type: str,
        metadata: dict | None = None,
    ) -> dict:
        """为主持人公告构建上下文。

        Args:
            game_state: 游戏状态
            announcement_type: 公告类型
            metadata: 额外元数据

        Returns:
            上下文字典
        """
        base_context = {
            "day_number": game_state.day_number,
            "alive_count": len([p for p in game_state.players.values() if p.is_alive]),
        }

        # 根据公告类型添加特定上下文
        if announcement_type == "game_start":
            werewolf_count = len([
                p for p in game_state.players.values() if p.role == "werewolf"
            ])
            base_context.update({
                "player_count": len(game_state.players),
                "role_config": f"3狼人、1预言家、1女巫、1猎人、4村民",
            })

        elif announcement_type == "night_start":
            pass  # 基础上下文已足够

        elif announcement_type == "dawn":
            # 从 metadata 获取死亡信息
            dead_players = metadata.get("dead_players", []) if metadata else []
            dead_text = ", ".join([
                f"{p['seat_number']}号"
                for p in dead_players
            ]) if dead_players else "无"

            base_context.update({
                "dead_players": dead_text,
                "death_reasons": metadata.get("death_reasons", "无") if metadata else "无",
            })

        elif announcement_type == "discussion_start":
            alive_players = [
                p for p in game_state.players.values() if p.is_alive
            ]
            base_context.update({
                "alive_players": ", ".join([f"{p.seat_number}号" for p in alive_players]),
                "speaking_order": ", ".join([str(p.seat_number) for p in sorted(alive_players, key=lambda x: x.seat_number)]),
            })

        elif announcement_type == "vote_start":
            alive_players = [
                p for p in game_state.players.values() if p.is_alive
            ]
            base_context.update({
                "voters": ", ".join([f"{p.seat_number}号" for p in alive_players]),
                "candidates": ", ".join([f"{p.seat_number}号" for p in alive_players]),
            })

        elif announcement_type == "vote_result":
            if metadata:
                vote_counts = metadata.get("vote_counts", {})
                base_context.update({
                    "vote_counts": ", ".join([f"{k}号: {v}票" for k, v in vote_counts.items()]),
                    "highest_vote_player": metadata.get("eliminated_name", "无"),
                    "is_tie": metadata.get("is_tie", False),
                })

        elif announcement_type == "request_speech":
            if metadata:
                base_context.update({
                    "seat_number": metadata.get("seat_number"),
                    "player_name": metadata.get("player_name", ""),
                    "is_human": metadata.get("is_human", False),
                })

        elif announcement_type == "game_end":
            if metadata:
                base_context.update({
                    "winner_team": "狼人阵营" if metadata.get("winner") == "werewolf" else "好人阵营",
                    "werewolf_players": metadata.get("werewolf_players", ""),
                    "good_players": metadata.get("good_players", ""),
                    "total_days": game_state.day_number,
                })

        return base_context
    
    # =========================================================================
    # 讨论流程实现 (Phase 5: B11, B12, B13, B14)
    # =========================================================================

    async def _execute_discussion_phase(self, room_code: str) -> None:
        """执行讨论阶段主流程（主持人主导）。

        流程：
        1. 广播讨论开始公告
        2. 获取存活玩家列表（按座位号排序）
        3. 依次调用 _request_player_speech
        4. 广播发言结束公告

        Args:
            room_code: 房间代码
        """
        game_state = self._game_states.get(room_code)
        if not game_state:
            logger.warning(f"Cannot execute discussion: game state not found for {room_code}")
            return

        # 更新阶段
        old_phase = game_state.phase
        game_state.phase = WerewolfPhase.DAY_DISCUSSION

        await broadcast_phase_change(
            room_code=room_code,
            from_phase=old_phase.value if old_phase else "unknown",
            to_phase=game_state.phase.value,
            day_number=game_state.day_number,
        )

        # 1. 广播讨论开始公告
        await self._broadcast_host_announcement(
            room_code=room_code,
            announcement_type="discussion_start",
            metadata={"day_number": game_state.day_number},
        )

        # 2. 获取存活玩家列表（按座位号排序）
        alive_players = sorted(
            [p for p in game_state.players.values() if p.is_alive],
            key=lambda p: p.seat_number,
        )

        # 3. 依次调用 _request_player_speech
        for player in alive_players:
            # 检查暂停状态
            if not await self._check_paused_before_next_action(room_code):
                return

            # 点名发言
            await self._request_player_speech(room_code, player)

        # 4. 广播发言结束公告
        await self._broadcast_host_announcement(
            room_code=room_code,
            announcement_type="discussion_end",
            metadata={"day_number": game_state.day_number},
        )

        logger.info(f"Discussion phase completed in room {room_code}")

    async def _request_player_speech(
        self,
        room_code: str,
        player: PlayerState,
    ) -> None:
        """主持人点名玩家发言。

        流程：
        1. 广播点名公告（使用 AI Host）
        2. 发送 werewolf:request_speech 事件
        3. 设置 current_speaker_seat
        4. 根据是否人类玩家选择等待或触发 AI 发言

        Args:
            room_code: 房间代码
            player: 玩家状态
        """
        game_state = self._game_states.get(room_code)
        if not game_state:
            return

        is_human = player.seat_number not in self._ai_agents
        player_name = f"玩家{player.seat_number}"

        # 1. 广播点名公告
        announcement_content = await self.host.announce_request_speech(
            seat_number=player.seat_number,
            player_name=player_name,
            is_human=is_human,
            stream=False,
        )

        # 2. 发送 request_speech 事件（通过 WebSocket 广播）
        from src.websocket import broadcast_to_room

        await broadcast_to_room(
            room_code=room_code,
            event="werewolf:request_speech",
            data={
                "seat_number": player.seat_number,
                "player_name": player_name,
                "is_human": is_human,
                "announcement": announcement_content,
            },
        )

        # 3. 设置 current_speaker_seat
        game_state.current_speaker_seat = player.seat_number

        # 记录日志
        self._add_game_log(
            room_code=room_code,
            log_type="host_announcement",
            content=announcement_content,
            metadata={
                "announcement_type": "request_speech",
                "seat_number": player.seat_number,
                "is_human": is_human,
            },
            is_public=True,
        )

        # 4. 根据是否人类玩家选择处理方式
        if is_human:
            # 人类玩家：等待发言
            speech_content = await self._wait_for_human_speech(room_code, player)

            if speech_content:
                # 记录人类发言
                self._add_game_log(
                    room_code=room_code,
                    log_type="speech",
                    content=speech_content,
                    player_id=player.player_id,
                    player_name=player_name,
                    seat_number=player.seat_number,
                    is_public=True,
                )
        else:
            # AI 玩家：触发 AI 发言
            await self._execute_ai_speech(room_code, player)

        # 发言结束处理
        await self._handle_speech_end(room_code, player)

    async def _wait_for_human_speech(
        self,
        room_code: str,
        player: PlayerState,
    ) -> str | None:
        """等待人类玩家发言（无超时，无限等待）。

        流程：
        1. 设置 waiting_for_player_input = True
        2. 启动提醒任务（每30秒）
        3. 使用 asyncio.Event 等待发言
        4. 返回发言内容

        Args:
            room_code: 房间代码
            player: 玩家状态

        Returns:
            发言内容，如果超时或取消则返回 None
        """
        game_state = self._game_states.get(room_code)
        if not game_state:
            return None

        # 1. 设置等待状态
        game_state.waiting_for_player_input = True
        game_state.speech_reminder_count = 0

        # 创建等待事件
        speech_event = asyncio.Event()
        speech_content: list[str] = []  # 使用列表来存储发言内容

        # 存储事件引用，供 process_player_speech 使用
        if not hasattr(game_state, "_speech_events"):
            game_state._speech_events = {}
        game_state._speech_events[player.seat_number] = {
            "event": speech_event,
            "content": speech_content,
        }

        # 2. 启动提醒任务
        reminder_task = asyncio.create_task(
            self._speech_reminder_loop(room_code, player)
        )

        try:
            # 3. 等待发言
            await speech_event.wait()

            # 4. 返回发言内容
            return speech_content[0] if speech_content else None

        finally:
            # 清理
            reminder_task.cancel()
            try:
                await reminder_task
            except asyncio.CancelledError:
                pass

            game_state.waiting_for_player_input = False
            if hasattr(game_state, "_speech_events"):
                game_state._speech_events.pop(player.seat_number, None)

    async def _speech_reminder_loop(
        self,
        room_code: str,
        player: PlayerState,
    ) -> None:
        """发言提醒循环（每30秒提醒一次）。

        Args:
            room_code: 房间代码
            player: 玩家状态
        """
        while True:
            await asyncio.sleep(30)  # 每30秒提醒一次
            await self._send_speech_reminder(room_code, player)

    async def _send_speech_reminder(
        self,
        room_code: str,
        player: PlayerState,
    ) -> None:
        """发送发言提醒（每30秒）。

        流程：
        1. 递增 speech_reminder_count
        2. 发送 werewolf:speech_reminder 事件

        Args:
            room_code: 房间代码
            player: 玩家状态
        """
        game_state = self._game_states.get(room_code)
        if not game_state:
            return

        # 1. 递增提醒计数
        game_state.speech_reminder_count += 1

        # 2. 发送提醒事件
        from src.websocket import broadcast_to_room

        await broadcast_to_room(
            room_code=room_code,
            event="werewolf:speech_reminder",
            data={
                "seat_number": player.seat_number,
                "player_name": f"玩家{player.seat_number}",
                "reminder_count": game_state.speech_reminder_count,
                "message": f"请{player.seat_number}号玩家尽快发言，已等待{game_state.speech_reminder_count * 30}秒",
            },
        )

        logger.info(
            f"Sent speech reminder #{game_state.speech_reminder_count} to room {room_code} for player {player.seat_number}"
        )

    async def _execute_ai_speech(
        self,
        room_code: str,
        player: PlayerState,
    ) -> None:
        """执行 AI 玩家发言。

        Args:
            room_code: 房间代码
            player: AI 玩家状态
        """
        game_state = self._game_states.get(room_code)
        if not game_state:
            return

        agent = self._ai_agents.get(player.seat_number)
        if not agent:
            logger.warning(f"No AI agent found for seat {player.seat_number}")
            return

        alive_players = [p for p in game_state.players.values() if p.is_alive]

        # B16/B18: 构建 AI 上下文
        ai_context = self._build_ai_context(room_code, current_seat=player.seat_number)

        # 更新 Agent 上下文
        agent.update_context(
            speeches=ai_context.get("current_round_speeches", []),
            host_context=ai_context.get("host_context"),
            game_state=ai_context,
        )

        # B18: 生成流式发言（使用增强的参数）
        speech_stream = agent.generate_speech_stream(
            game_state=ai_context,
            previous_speeches=ai_context.get("today_speeches", []),
            current_round_speeches=ai_context.get("current_round_speeches", []),
            host_context=ai_context.get("host_context"),
        )

        # 流式广播发言
        speech_content = await stream_ai_speech(
            room_code=room_code,
            speaker_seat=player.seat_number,
            speaker_name=f"玩家{player.seat_number}",
            speech_stream=speech_stream,
        )

        # 记录发言日志
        self._add_game_log(
            room_code=room_code,
            log_type="speech",
            content=speech_content,
            player_name=f"玩家{player.seat_number}",
            seat_number=player.seat_number,
            is_public=True,
        )

        logger.debug(f"AI player {player.seat_number} speech completed in room {room_code}")

    async def _handle_speech_end(
        self,
        room_code: str,
        player: PlayerState,
    ) -> None:
        """处理发言结束（发送过渡公告）。

        Args:
            room_code: 房间代码
            player: 刚完成发言的玩家
        """
        game_state = self._game_states.get(room_code)
        if not game_state:
            return

        player_name = f"玩家{player.seat_number}"

        # 使用 AI Host 生成发言结束过渡公告
        transition_content = await self.host.announce_player_speech_end(
            seat_number=player.seat_number,
            player_name=player_name,
            stream=False,
        )

        # 广播发言结束事件
        from src.websocket import broadcast_to_room

        await broadcast_to_room(
            room_code=room_code,
            event="werewolf:speech_end",
            data={
                "seat_number": player.seat_number,
                "player_name": player_name,
                "announcement": transition_content,
            },
        )

        # 清除当前发言者
        game_state.current_speaker_seat = None

        logger.debug(f"Speech end handled for player {player.seat_number} in room {room_code}")

    # =========================================================================
    # 玩家发言与上下文 (Phase 6: B15, B16)
    # =========================================================================

    async def process_player_speech(
        self,
        room_code: str,
        player_id: str,
        seat_number: int,
        content: str,
    ) -> bool:
        """处理玩家发言。

        流程：
        1. 验证是否轮到该玩家发言
        2. 创建 GameLogEntry 记录发言
        3. 广播 werewolf:player_speech 事件
        4. 设置 waiting_for_player_input = False
        5. 触发发言等待的 Event

        Args:
            room_code: 房间代码
            player_id: 玩家ID
            seat_number: 玩家座位号
            content: 发言内容

        Returns:
            是否成功处理发言

        Raises:
            NotFoundError: 游戏状态不存在
            BadRequestError: 未轮到该玩家发言
        """
        game_state = self._game_states.get(room_code)
        if not game_state:
            raise NotFoundError(f"游戏状态不存在: {room_code}")

        # 1. 验证是否轮到该玩家发言
        if game_state.current_speaker_seat != seat_number:
            raise BadRequestError(
                f"当前不是{seat_number}号玩家的发言时间，当前发言者: {game_state.current_speaker_seat}"
            )

        if not game_state.waiting_for_player_input:
            raise BadRequestError("系统未处于等待玩家发言状态")

        # 2. 创建 GameLogEntry 记录发言
        player_name = f"玩家{seat_number}"
        self._add_game_log(
            room_code=room_code,
            log_type="speech",
            content=content,
            player_id=player_id,
            player_name=player_name,
            seat_number=seat_number,
            is_public=True,
        )

        # 3. 广播 werewolf:player_speech 事件
        from src.websocket import broadcast_to_room

        await broadcast_to_room(
            room_code=room_code,
            event="werewolf:player_speech",
            data={
                "seat_number": seat_number,
                "player_name": player_name,
                "content": content,
            },
        )

        # 4. 设置 waiting_for_player_input = False
        game_state.waiting_for_player_input = False

        # 5. 触发发言等待的 Event
        if hasattr(game_state, "_speech_events"):
            speech_event_data = game_state._speech_events.get(seat_number)
            if speech_event_data:
                # 存储发言内容
                speech_event_data["content"].append(content)
                # 触发事件
                speech_event_data["event"].set()

        logger.info(f"Processed speech from player {seat_number} in room {room_code}")

        return True

    def _build_ai_context(
        self,
        room_code: str,
        current_seat: int | None = None,
    ) -> dict:
        """为 AI Agent 构建上下文。

        内容包括：
        - 游戏历史日志
        - 当天所有公开发言
        - 主持人公告摘要
        - 存活玩家信息
        - 本轮已有发言

        Args:
            room_code: 房间代码
            current_seat: 当前请求上下文的玩家座位号（可选）

        Returns:
            结构化的上下文字典
        """
        game_state = self._game_states.get(room_code)
        if not game_state:
            return {}

        # 获取当天的公开发言
        today_speeches = []
        for log in game_state.game_logs:
            if log.day == game_state.day_number and log.type == "speech" and log.is_public:
                today_speeches.append({
                    "seat_number": log.seat_number,
                    "player_name": log.player_name or f"玩家{log.seat_number}",
                    "content": log.content,
                })

        # 获取主持人公告摘要
        host_announcements = []
        for log in game_state.game_logs:
            if log.type == "host_announcement" and log.is_public:
                announcement_type = log.metadata.get("announcement_type", "") if log.metadata else ""
                host_announcements.append({
                    "type": announcement_type,
                    "content": log.content[:100] + "..." if len(log.content) > 100 else log.content,
                    "day": log.day,
                })

        # 获取存活玩家信息
        alive_players = [
            {
                "seat_number": p.seat_number,
                "player_name": f"玩家{p.seat_number}",
            }
            for p in game_state.players.values()
            if p.is_alive
        ]

        # 获取死亡玩家信息
        dead_players = [
            {
                "seat_number": p.seat_number,
                "player_name": f"玩家{p.seat_number}",
                "death_day": p.death_day,
                "death_reason": p.death_reason,
            }
            for p in game_state.players.values()
            if not p.is_alive
        ]

        # 获取本轮已有发言（当前座位号之前的）
        current_round_speeches = []
        if current_seat is not None:
            for speech in today_speeches:
                if speech["seat_number"] and speech["seat_number"] < current_seat:
                    current_round_speeches.append(speech)

        # 构建完整历史日志（用于AI决策）
        game_history = []
        for log in game_state.game_logs:
            if log.is_public:
                game_history.append({
                    "day": log.day,
                    "phase": log.phase,
                    "type": log.type,
                    "content": log.content,
                    "seat_number": log.seat_number,
                    "player_name": log.player_name,
                })

        return {
            "day_number": game_state.day_number,
            "phase": game_state.phase.value if game_state.phase else "unknown",
            "alive_count": len(alive_players),
            "alive_players": alive_players,
            "dead_players": dead_players,
            "today_speeches": today_speeches,
            "current_round_speeches": current_round_speeches,
            "host_announcements": host_announcements,
            "game_history": game_history,
            "host_context": self._build_host_context_summary(game_state),
        }

    def _build_host_context_summary(self, game_state: WerewolfGameState) -> str:
        """构建主持人上下文摘要。

        Args:
            game_state: 游戏状态

        Returns:
            主持人上下文摘要文本
        """
        summary_parts = [
            f"当前是第{game_state.day_number}天，{game_state.phase.value if game_state.phase else '未知'}阶段。",
        ]

        # 添加存活信息
        alive_count = len([p for p in game_state.players.values() if p.is_alive])
        summary_parts.append(f"场上还有{alive_count}名玩家存活。")

        # 添加死亡信息
        dead_players = [p for p in game_state.players.values() if not p.is_alive]
        if dead_players:
            dead_info = ", ".join([
                f"{p.seat_number}号({p.death_reason or '未知原因'})"
                for p in dead_players
            ])
            summary_parts.append(f"已出局玩家: {dead_info}。")

        return " ".join(summary_parts)

    # =========================================================================
    # 辅助方法
    # =========================================================================

    def _add_game_log(
        self,
        room_code: str,
        log_type: str,
        content: str,
        player_id: str | None = None,
        player_name: str | None = None,
        seat_number: int | None = None,
        metadata: dict | None = None,
        is_public: bool = True,
    ) -> GameLogEntry | None:
        """添加游戏日志条目。

        Args:
            room_code: 房间代码
            log_type: 日志类型 (speech, host_announcement, death, vote, skill)
            content: 日志内容
            player_id: 玩家ID（可选）
            player_name: 玩家名称（可选）
            seat_number: 座位号（可选）
            metadata: 额外元数据（可选）
            is_public: 是否公开（用于日志级别过滤）

        Returns:
            创建的日志条目，如果游戏状态不存在则返回 None
        """
        game_state = self._game_states.get(room_code)
        if not game_state:
            return None

        log_entry = GameLogEntry.create(
            log_type=log_type,
            content=content,
            day=game_state.day_number,
            phase=game_state.phase.value if game_state.phase else "unknown",
            player_id=player_id,
            player_name=player_name,
            seat_number=seat_number,
            metadata=metadata,
            is_public=is_public,
        )

        game_state.game_logs.append(log_entry)
        logger.debug(f"Added game log: [{log_type}] {content[:50]}...")

        return log_entry
    
    def get_game_state(self, room_code: str) -> WerewolfGameState | None:
        """Get current game state."""
        return self._game_states.get(room_code)
    
    def get_player_role(self, room_code: str, player_id: str) -> str | None:
        """Get a player's role (for their eyes only)."""
        game_state = self._game_states.get(room_code)
        if not game_state:
            return None
        
        for player in game_state.players.values():
            if player.player_id == player_id:
                return player.role
        return None
    
    def get_visible_state(
        self,
        room_code: str,
        player_id: str
    ) -> dict | None:
        """Get game state visible to a specific player."""
        game_state = self._game_states.get(room_code)
        if not game_state:
            return None
        
        # Find requesting player
        requesting_player = next(
            (p for p in game_state.players.values() if p.player_id == player_id),
            None
        )
        
        # Build visible state
        players_info = []
        for p in game_state.players.values():
            info = {
                "seat_number": p.seat_number,
                "display_name": f"玩家{p.seat_number}",
                "is_alive": p.is_alive
            }
            
            # Show role only for self or if game is over
            if p.player_id == player_id or game_state.phase == WerewolfPhase.GAME_OVER:
                info["role"] = p.role
                info["team"] = p.team
            
            # Show death info for dead players
            if not p.is_alive:
                info["death_reason"] = p.death_reason
                info["death_day"] = p.death_day
            
            players_info.append(info)
        
        return {
            "room_code": room_code,
            "phase": game_state.phase.value,
            "day_number": game_state.day_number,
            "players": players_info,
            "winner": game_state.winner,
            "your_seat": requesting_player.seat_number if requesting_player else None,
            "your_role": requesting_player.role if requesting_player else None
        }
