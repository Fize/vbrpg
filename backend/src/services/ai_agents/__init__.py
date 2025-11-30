# -*- coding: utf-8 -*-
"""AI Agents module for game AI functionality.

This module provides AI agents for various game roles, including:
- Role-specific agents (Werewolf, Seer, Witch, Hunter, Villager)
- Host agent for game narration
- Base classes and common utilities
"""

from src.services.ai_agents.base import BaseWerewolfAgent
from src.services.ai_agents.host import WerewolfHost
from src.services.ai_agents.hunter_agent import HunterAgent
from src.services.ai_agents.seer_agent import SeerAgent
from src.services.ai_agents.villager_agent import VillagerAgent
from src.services.ai_agents.werewolf_agent import WerewolfAgent
from src.services.ai_agents.witch_agent import WitchAgent

__all__ = [
    "BaseWerewolfAgent",
    "WerewolfHost",
    "WerewolfAgent",
    "SeerAgent",
    "WitchAgent",
    "HunterAgent",
    "VillagerAgent",
]
