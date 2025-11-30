# -*- coding: utf-8 -*-
"""Host-specific prompt templates (re-export from main prompts module)."""

# Re-export from main prompts module for convenience
from src.services.ai_agents.prompts.host_prompts import (
    HOST_ANNOUNCEMENT_PROMPTS,
    HOST_SYSTEM_PROMPT,
)

__all__ = [
    "HOST_SYSTEM_PROMPT",
    "HOST_ANNOUNCEMENT_PROMPTS",
]
