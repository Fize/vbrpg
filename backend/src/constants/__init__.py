"""Constants module for static game data."""

from src.constants.game_types import GAME_TYPES, get_game_type_by_slug
from src.constants.roles import ROLES_BY_GAME, get_roles_by_game_slug

__all__ = [
    "GAME_TYPES",
    "get_game_type_by_slug",
    "ROLES_BY_GAME",
    "get_roles_by_game_slug",
]
