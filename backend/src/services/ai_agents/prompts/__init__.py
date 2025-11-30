# -*- coding: utf-8 -*-
"""Prompt templates for AI agents.

This module contains all prompt templates used by AI agents, including:
- Game rules and context
- Role-specific prompts (werewolf, seer, witch, hunter, villager)
- Host announcement prompts
- Common speech and voting prompts
"""

from src.services.ai_agents.prompts.game_rules import WEREWOLF_GAME_RULES
from src.services.ai_agents.prompts.werewolf_prompts import (
    WEREWOLF_NIGHT_PROMPT,
    WEREWOLF_SYSTEM_PROMPT,
)
from src.services.ai_agents.prompts.seer_prompts import (
    SEER_NIGHT_PROMPT,
    SEER_SYSTEM_PROMPT,
)
from src.services.ai_agents.prompts.witch_prompts import (
    WITCH_NIGHT_PROMPT,
    WITCH_SYSTEM_PROMPT,
)
from src.services.ai_agents.prompts.hunter_prompts import (
    HUNTER_SHOOT_PROMPT,
    HUNTER_SYSTEM_PROMPT,
)
from src.services.ai_agents.prompts.villager_prompts import (
    VILLAGER_SYSTEM_PROMPT,
)
from src.services.ai_agents.prompts.common_prompts import (
    SPEECH_PROMPT,
    VOTE_PROMPT,
)
from src.services.ai_agents.prompts.host_prompts import (
    HOST_SYSTEM_PROMPT,
    HOST_ANNOUNCEMENT_PROMPTS,
)

__all__ = [
    # Game rules
    "WEREWOLF_GAME_RULES",
    # Role prompts
    "WEREWOLF_SYSTEM_PROMPT",
    "WEREWOLF_NIGHT_PROMPT",
    "SEER_SYSTEM_PROMPT",
    "SEER_NIGHT_PROMPT",
    "WITCH_SYSTEM_PROMPT",
    "WITCH_NIGHT_PROMPT",
    "HUNTER_SYSTEM_PROMPT",
    "HUNTER_SHOOT_PROMPT",
    "VILLAGER_SYSTEM_PROMPT",
    # Common prompts
    "SPEECH_PROMPT",
    "VOTE_PROMPT",
    # Host prompts
    "HOST_SYSTEM_PROMPT",
    "HOST_ANNOUNCEMENT_PROMPTS",
]
