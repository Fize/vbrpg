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
    # 辅助方法
    # =========================================================================
    
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
