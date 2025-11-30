"""Pydantic schemas for API request/response models."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


# Game Type schemas
class GameTypeBase(BaseModel):
    name: str
    slug: str
    description: str
    rules_summary: str
    min_players: int
    max_players: int
    avg_duration_minutes: int
    is_available: bool


class GameTypeResponse(GameTypeBase):
    id: str

    model_config = ConfigDict(from_attributes=True)


# Player schemas
class PlayerBase(BaseModel):
    username: str
    is_guest: bool


class PlayerResponse(PlayerBase):
    id: str
    created_at: datetime
    last_active: datetime
    expires_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


# Participant schemas
class ParticipantResponse(BaseModel):
    id: str
    player: PlayerResponse | None = None
    is_ai_agent: bool
    ai_personality: str | None = None
    joined_at: datetime
    left_at: datetime | None = None
    replaced_by_ai: bool

    model_config = ConfigDict(from_attributes=True)


# Room schemas
class CreateRoomRequest(BaseModel):
    game_type_slug: str
    max_players: int = Field(ge=2, le=12)
    min_players: int = Field(ge=2, le=12)
    user_role: str = Field(default="spectator")  # 'spectator' or role ID
    is_spectator_mode: bool = Field(default=True)


class GameRoomBase(BaseModel):
    code: str
    status: str
    max_players: int
    min_players: int
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None


class GameRoomResponse(GameRoomBase):
    id: str
    game_type: GameTypeResponse
    current_player_count: int

    model_config = ConfigDict(from_attributes=True)


class GameRoomDetailedResponse(GameRoomResponse):
    participants: list[ParticipantResponse] = []
    user_role: Optional[str] = None
    is_spectator_mode: Optional[bool] = None

    model_config = ConfigDict(from_attributes=True)


# Room list response
class RoomListResponse(BaseModel):
    rooms: list[GameRoomResponse]
    total: int


# 单人模式下移除了 JoinRoomResponse（无需加入房间功能）


# AI Agent response
class AIAgentResponse(BaseModel):
    ai_agent: PlayerResponse
    room_code: str

    model_config = ConfigDict(from_attributes=True)


# Role schemas (单人模式角色选择)
class RoleResponse(BaseModel):
    """角色信息响应模型"""
    id: str
    name: str
    description: str
    is_playable: bool = True  # 是否可由用户扮演
    task: str | None = None  # 角色给 AI 或玩家的任务/指令描述

    model_config = ConfigDict(from_attributes=True)


class RoleListResponse(BaseModel):
    """角色列表响应"""
    roles: list[RoleResponse]
    supports_spectating: bool = True  # 是否支持旁观模式


class SelectRoleRequest(BaseModel):
    """角色选择请求"""
    role_id: str | None = None  # None 表示旁观者
    is_spectator: bool = True


class GameControlResponse(BaseModel):
    """游戏控制响应"""
    room_code: str
    status: str
    message: str


# =============================================================================
# Werewolf Game Schemas (狼人杀专用)
# =============================================================================

class WerewolfQuickStartRequest(BaseModel):
    """狼人杀快速开始请求"""
    player_id: str  # 用户的玩家ID
    preferred_role: str | None = None  # 可选的首选角色


class WerewolfPlayerInfo(BaseModel):
    """狼人杀玩家信息"""
    seat_number: int
    display_name: str
    is_alive: bool
    role: str | None = None  # 仅对自己或游戏结束后可见
    team: str | None = None
    death_reason: str | None = None
    death_day: int | None = None


class WerewolfGameStateResponse(BaseModel):
    """狼人杀游戏状态响应"""
    room_code: str
    phase: str
    day_number: int
    players: list[WerewolfPlayerInfo]
    winner: str | None = None
    your_seat: int | None = None
    your_role: str | None = None


class WerewolfActionRequest(BaseModel):
    """狼人杀玩家行动请求"""
    player_id: str
    action_type: str  # kill, check, save, poison, shoot, vote
    target_seat: int | None = None  # None 表示跳过/弃票


class WerewolfActionResponse(BaseModel):
    """狼人杀行动响应"""
    success: bool
    message: str
    result: dict | None = None  # 如预言家查验结果

