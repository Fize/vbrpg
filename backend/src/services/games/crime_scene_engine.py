"""Crime Scene game engine implementation.

Handles game logic for the Crime Scene (犯罪现场) tabletop game:
- Phase management (Setup, Investigation, Accusation, Resolution)
- Action validation
- Win condition checking
- Game state transitions
"""

import logging
from typing import Any, Optional
from enum import Enum
import random

logger = logging.getLogger(__name__)


class GamePhase(str, Enum):
    """Crime Scene game phases."""
    SETUP = "Setup"
    INVESTIGATION = "Investigation"
    ACCUSATION = "Accusation"
    RESOLUTION = "Resolution"


class ActionType(str, Enum):
    """Valid action types in Crime Scene."""
    DRAW_CARD = "draw_card"
    INVESTIGATE_LOCATION = "investigate_location"
    REVEAL_CLUE = "reveal_clue"
    MAKE_ACCUSATION = "make_accusation"
    PASS_TURN = "pass_turn"


class CrimeSceneEngine:
    """Game engine for Crime Scene tabletop game.
    
    Crime Scene is a deduction game where players:
    1. Draw cards representing evidence
    2. Investigate locations for clues
    3. Deduce the murderer, weapon, and location
    4. Make accusations to win the game
    """
    
    def __init__(self):
        """Initialize game engine."""
        self.min_players = 4
        self.max_players = 8
        self.cards_per_player = 5
        
    def initialize_game(
        self,
        players: list[str],
        game_data: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        """Initialize a new Crime Scene game.
        
        Args:
            players: List of player IDs (human + AI)
            game_data: Optional existing game data
            
        Returns:
            Initial game state
        """
        if len(players) < self.min_players or len(players) > self.max_players:
            raise ValueError(f"Crime Scene requires {self.min_players}-{self.max_players} players")
        
        # Setup murder scenario
        suspects = ["厨师", "管家", "医生", "园丁", "秘书", "司机"]
        weapons = ["刀", "枪", "毒药", "绳子", "烛台", "扳手"]
        locations = ["书房", "厨房", "卧室", "餐厅", "花园", "车库"]
        
        # Randomly select solution
        solution = {
            "murderer": random.choice(suspects),
            "weapon": random.choice(weapons),
            "location": random.choice(locations)
        }
        
        # Create evidence deck (all cards except solution)
        evidence_deck = []
        for suspect in suspects:
            if suspect != solution["murderer"]:
                evidence_deck.append({"type": "suspect", "name": suspect})
        for weapon in weapons:
            if weapon != solution["weapon"]:
                evidence_deck.append({"type": "weapon", "name": weapon})
        for location in locations:
            if location != solution["location"]:
                evidence_deck.append({"type": "location", "name": location})
        
        # Shuffle deck
        random.shuffle(evidence_deck)
        
        # Deal cards to players
        player_hands = {}
        for i, player_id in enumerate(players):
            start_idx = i * self.cards_per_player
            end_idx = start_idx + self.cards_per_player
            player_hands[player_id] = evidence_deck[start_idx:end_idx]
        
        # Initialize game state
        game_state = {
            "phase": GamePhase.INVESTIGATION,
            "current_turn_index": 0,
            "turn_number": 1,
            "players": players,
            "solution": solution,  # Hidden from players
            "player_hands": player_hands,
            "revealed_clues": [],
            "accusations": [],
            "locations": locations,
            "winner": None
        }
        
        logger.info(f"Crime Scene game initialized with {len(players)} players")
        return game_state
    
    def get_valid_actions(
        self,
        game_state: dict[str, Any],
        player_id: str
    ) -> list[dict[str, Any]]:
        """Get valid actions for current player.
        
        Args:
            game_state: Current game state
            player_id: Player taking action
            
        Returns:
            List of valid actions with metadata
        """
        phase = game_state["phase"]
        actions = []
        
        if phase == GamePhase.INVESTIGATION:
            # Can investigate locations not yet revealed
            for location in game_state["locations"]:
                if location not in [c.get("location") for c in game_state.get("revealed_clues", [])]:
                    actions.append({
                        "type": ActionType.INVESTIGATE_LOCATION,
                        "description": f"调查 {location}",
                        "parameters": {"location": location}
                    })
            
            # Can reveal clue from hand
            player_hand = game_state["player_hands"].get(player_id, [])
            if player_hand:
                actions.append({
                    "type": ActionType.REVEAL_CLUE,
                    "description": "展示手牌中的线索",
                    "parameters": {"card_index": 0}  # Simplified: reveal first card
                })
            
            # Can make accusation
            actions.append({
                "type": ActionType.MAKE_ACCUSATION,
                "description": "指控凶手",
                "parameters": {}
            })
            
        elif phase == GamePhase.ACCUSATION:
            # Must make accusation or pass
            actions.append({
                "type": ActionType.MAKE_ACCUSATION,
                "description": "指控凶手",
                "parameters": {}
            })
            actions.append({
                "type": ActionType.PASS_TURN,
                "description": "跳过回合",
                "parameters": {}
            })
        
        return actions
    
    def apply_action(
        self,
        game_state: dict[str, Any],
        player_id: str,
        action: dict[str, Any]
    ) -> dict[str, Any]:
        """Apply player action to game state.
        
        Args:
            game_state: Current game state
            player_id: Player taking action
            action: Action to apply
            
        Returns:
            Updated game state
        """
        action_type = action.get("action_type") or action.get("type")
        parameters = action.get("parameters", {})
        
        if action_type == ActionType.INVESTIGATE_LOCATION:
            location = parameters.get("location")
            if location:
                game_state["revealed_clues"].append({
                    "type": "investigation",
                    "location": location,
                    "player_id": player_id
                })
                logger.info(f"Player {player_id} investigated {location}")
        
        elif action_type == ActionType.REVEAL_CLUE:
            card_index = parameters.get("card_index", 0)
            player_hand = game_state["player_hands"].get(player_id, [])
            if player_hand and card_index < len(player_hand):
                revealed_card = player_hand.pop(card_index)
                game_state["revealed_clues"].append({
                    "type": "card",
                    "card": revealed_card,
                    "player_id": player_id
                })
                logger.info(f"Player {player_id} revealed clue: {revealed_card}")
        
        elif action_type == ActionType.MAKE_ACCUSATION:
            # Extract accusation from parameters or action
            accusation = parameters.get("accusation", {})
            if not accusation:
                # Default accusation (AI will provide proper one)
                accusation = {
                    "murderer": "未知",
                    "weapon": "未知",
                    "location": "未知"
                }
            
            game_state["accusations"].append({
                "player_id": player_id,
                "accusation": accusation
            })
            logger.info(f"Player {player_id} made accusation: {accusation}")
            
            # Check if correct
            if self._check_accusation(game_state, accusation):
                game_state["winner"] = player_id
                game_state["phase"] = GamePhase.RESOLUTION
                logger.info(f"Player {player_id} won with correct accusation!")
        
        # Advance turn
        game_state["current_turn_index"] = (game_state["current_turn_index"] + 1) % len(game_state["players"])
        if game_state["current_turn_index"] == 0:
            game_state["turn_number"] += 1
        
        return game_state
    
    def check_win_condition(self, game_state: dict[str, Any]) -> Optional[str]:
        """Check if game has been won.
        
        Args:
            game_state: Current game state
            
        Returns:
            Winner player_id if game won, None otherwise
        """
        return game_state.get("winner")
    
    def _check_accusation(self, game_state: dict[str, Any], accusation: dict[str, Any]) -> bool:
        """Check if accusation matches solution."""
        solution = game_state["solution"]
        return (
            accusation.get("murderer") == solution["murderer"] and
            accusation.get("weapon") == solution["weapon"] and
            accusation.get("location") == solution["location"]
        )
    
    def get_current_player(self, game_state: dict[str, Any]) -> str:
        """Get current turn player ID."""
        players = game_state["players"]
        index = game_state["current_turn_index"]
        return players[index]
    
    def validate_game_state(self, game_state: dict[str, Any]) -> bool:
        """Validate game state structure.
        
        Args:
            game_state: Game state to validate
            
        Returns:
            True if valid, False otherwise
        """
        required_keys = ["phase", "current_turn_index", "turn_number", "players", "solution"]
        return all(key in game_state for key in required_keys)
