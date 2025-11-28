"""Pydantic schemas for API request/response models."""
from datetime import datetime

from pydantic import BaseModel, Field


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

    class Config:
        from_attributes = True


# Player schemas
class PlayerBase(BaseModel):
    username: str
    is_guest: bool


class PlayerResponse(PlayerBase):
    id: str
    created_at: datetime
    last_active: datetime
    expires_at: datetime | None = None

    class Config:
        from_attributes = True


# Participant schemas
class ParticipantResponse(BaseModel):
    id: str
    player: PlayerResponse | None = None
    is_ai_agent: bool
    ai_personality: str | None = None
    joined_at: datetime
    left_at: datetime | None = None
    replaced_by_ai: bool

    class Config:
        from_attributes = True


# Room schemas
class CreateRoomRequest(BaseModel):
    game_type_slug: str
    max_players: int = Field(ge=2, le=8)
    min_players: int = Field(ge=2, le=8)
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

    class Config:
        from_attributes = True


class GameRoomDetailedResponse(GameRoomResponse):
    participants: list[ParticipantResponse] = []

    class Config:
        from_attributes = True


# Room list response
class RoomListResponse(BaseModel):
    rooms: list[GameRoomResponse]
    total: int


# 单人模式下移除了 JoinRoomResponse（无需加入房间功能）


# AI Agent response
class AIAgentResponse(BaseModel):
    ai_agent: PlayerResponse
    room_code: str

    class Config:
        from_attributes = True


# Role schemas (单人模式角色选择)
class RoleResponse(BaseModel):
    """角色信息响应模型"""
    id: str
    name: str
    description: str
    is_playable: bool = True  # 是否可由用户扮演

    class Config:
        from_attributes = True


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
