"""Werewolf game API endpoints.

狼人杀游戏专用 API 端点，支持：
- 快速开始单人模式游戏
- 玩家行动处理
- 游戏状态查询
"""
import logging
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import (
    WerewolfQuickStartRequest,
    WerewolfGameStateResponse,
    WerewolfActionRequest,
    WerewolfActionResponse,
    WerewolfPlayerInfo,
    GameLogEntryResponse,
    GameLogListResponse,
    GameControlRequest,
    GameControlResponse,
)
from src.database import get_db
from src.services.werewolf_game_service import WerewolfGameService
from src.utils.errors import APIError, BadRequestError, NotFoundError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/werewolf", tags=["werewolf"])

# Store for active game services (in production, use Redis or similar)
_game_services: dict[str, WerewolfGameService] = {}


def get_or_create_service(db: AsyncSession, room_code: str) -> WerewolfGameService:
    """Get or create a WerewolfGameService instance."""
    if room_code not in _game_services:
        _game_services[room_code] = WerewolfGameService(db)
    return _game_services[room_code]


# =============================================================================
# B39: 快速开始端点
# =============================================================================

@router.post("/quick-start", response_model=WerewolfGameStateResponse)
async def quick_start_game(
    request: WerewolfQuickStartRequest,
    db: AsyncSession = Depends(get_db)
):
    """快速开始一局狼人杀游戏（单人模式）。
    
    创建一个新的游戏房间，分配角色，并开始游戏。
    - 10名玩家（1名人类玩家 + 9名AI）
    - 配置：3狼人 + 1预言家 + 1女巫 + 1猎人 + 4村民
    
    Args:
        request: 包含玩家ID和可选首选角色
        
    Returns:
        初始游戏状态
    """
    from src.models.game import GameRoom, GameRoomParticipant
    from src.models.user import Player
    
    try:
        # Generate a unique room code
        room_code = f"WW-{str(uuid4())[:8].upper()}"
        
        # 创建数据库房间记录
        room = GameRoom(
            code=room_code,
            game_type_id="werewolf",
            status="Waiting",
            max_players=10,
            min_players=10,
            user_role="spectator" if request.preferred_role is None else "player",
            is_spectator_mode=request.preferred_role is None,
        )
        db.add(room)
        await db.flush()
        
        # 创建人类玩家记录
        human_player = Player(
            id=request.player_id,
            username=f"玩家_{request.player_id[:8]}",
            is_guest=True,
        )
        db.add(human_player)
        await db.flush()
        
        # 创建人类参与者记录
        human_participant = GameRoomParticipant(
            game_room_id=room.id,
            player_id=human_player.id,
            is_ai_agent=False,
            is_owner=True,  # 单人模式下，唯一的人类玩家就是房主
        )
        db.add(human_participant)
        
        # 创建 9 个 AI 参与者记录
        for i in range(9):
            ai_player = Player(
                username=f"AI玩家{i + 1}",
                is_guest=True,
            )
            db.add(ai_player)
            await db.flush()
            
            ai_participant = GameRoomParticipant(
                game_room_id=room.id,
                player_id=ai_player.id,
                is_ai_agent=True,
                ai_personality="balanced",
            )
            db.add(ai_participant)
        
        room.current_participant_count = 10
        await db.commit()
        await db.refresh(room, ["participants"])
        
        # Create service and start game
        service = WerewolfGameService(db)
        _game_services[room_code] = service
        
        game_state = await service.start_game(
            room_code=room_code,
            human_player_id=request.player_id,
            human_role=request.preferred_role
        )
        
        # Get visible state for the human player
        visible_state = service.get_visible_state(room_code, request.player_id)
        
        if not visible_state:
            raise HTTPException(status_code=500, detail="Failed to get game state")
        
        # Convert to response
        players = [
            WerewolfPlayerInfo(
                seat_number=p["seat_number"],
                display_name=p["display_name"],
                is_alive=p["is_alive"],
                role=p.get("role"),
                team=p.get("team"),
                death_reason=p.get("death_reason"),
                death_day=p.get("death_day")
            )
            for p in visible_state["players"]
        ]
        
        return WerewolfGameStateResponse(
            room_code=room_code,
            phase=visible_state["phase"],
            day_number=visible_state["day_number"],
            players=players,
            winner=visible_state.get("winner"),
            your_seat=visible_state.get("your_seat"),
            your_role=visible_state.get("your_role")
        )
        
    except APIError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Error starting werewolf game: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# B40: 玩家行动端点
# =============================================================================

@router.post("/rooms/{room_code}/action", response_model=WerewolfActionResponse)
async def submit_action(
    room_code: str,
    request: WerewolfActionRequest,
    db: AsyncSession = Depends(get_db)
):
    """提交玩家行动。
    
    处理各种游戏行动：
    - kill: 狼人击杀
    - check: 预言家查验
    - save: 女巫救人
    - poison: 女巫毒人
    - shoot: 猎人开枪
    - vote: 投票
    
    Args:
        room_code: 房间代码
        request: 行动请求
        
    Returns:
        行动结果
    """
    try:
        service = _game_services.get(room_code)
        if not service:
            raise NotFoundError(f"Game not found for room {room_code}")
        
        await service.process_human_action(
            room_code=room_code,
            player_id=request.player_id,
            action_type=request.action_type,
            target_seat=request.target_seat
        )
        
        # Build result based on action type
        result = None
        if request.action_type == "check":
            # Get seer result from game state
            game_state = service.get_game_state(room_code)
            if game_state and game_state.seer_result:
                result = {
                    "target_seat": request.target_seat,
                    "is_werewolf": game_state.seer_result.get("is_werewolf", False)
                }
        
        return WerewolfActionResponse(
            success=True,
            message=f"行动 {request.action_type} 已处理",
            result=result
        )
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BadRequestError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except APIError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Error processing werewolf action: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rooms/{room_code}/state", response_model=WerewolfGameStateResponse)
async def get_game_state(
    room_code: str,
    player_id: str,
    db: AsyncSession = Depends(get_db)
):
    """获取当前游戏状态。
    
    返回指定玩家可见的游戏状态。
    
    Args:
        room_code: 房间代码
        player_id: 请求玩家ID
        
    Returns:
        玩家可见的游戏状态
    """
    try:
        service = _game_services.get(room_code)
        if not service:
            raise NotFoundError(f"Game not found for room {room_code}")
        
        visible_state = service.get_visible_state(room_code, player_id)
        if not visible_state:
            raise NotFoundError(f"Game state not found for room {room_code}")
        
        players = [
            WerewolfPlayerInfo(
                seat_number=p["seat_number"],
                display_name=p["display_name"],
                is_alive=p["is_alive"],
                role=p.get("role"),
                team=p.get("team"),
                death_reason=p.get("death_reason"),
                death_day=p.get("death_day")
            )
            for p in visible_state["players"]
        ]
        
        return WerewolfGameStateResponse(
            room_code=room_code,
            phase=visible_state["phase"],
            day_number=visible_state["day_number"],
            players=players,
            winner=visible_state.get("winner"),
            your_seat=visible_state.get("your_seat"),
            your_role=visible_state.get("your_role")
        )
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting werewolf game state: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rooms/{room_code}/role", response_model=dict)
async def get_player_role(
    room_code: str,
    player_id: str,
    db: AsyncSession = Depends(get_db)
):
    """获取玩家自己的角色信息。
    
    Args:
        room_code: 房间代码
        player_id: 玩家ID
        
    Returns:
        玩家角色信息
    """
    try:
        service = _game_services.get(room_code)
        if not service:
            raise NotFoundError(f"Game not found for room {room_code}")
        
        role = service.get_player_role(room_code, player_id)
        if not role:
            raise NotFoundError(f"Player not found in game")
        
        # Get role display info
        role_names = {
            "werewolf": "狼人",
            "seer": "预言家",
            "witch": "女巫",
            "hunter": "猎人",
            "villager": "村民"
        }
        
        role_descriptions = {
            "werewolf": "你是狼人，每晚可以选择击杀一名玩家。你需要隐藏身份，消灭好人阵营。",
            "seer": "你是预言家，每晚可以查验一名玩家的身份。利用你的信息引导好人找出狼人。",
            "witch": "你是女巫，拥有一瓶解药和一瓶毒药。解药可救人，毒药可杀人，各限用一次。",
            "hunter": "你是猎人，当你死亡时可以开枪带走一名玩家。",
            "villager": "你是普通村民，通过分析发言找出狼人，用投票消灭他们。"
        }
        
        return {
            "role": role,
            "role_name": role_names.get(role, role),
            "description": role_descriptions.get(role, ""),
            "team": "werewolf" if role == "werewolf" else "villager"
        }
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting player role: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# B24: 游戏日志 API
# =============================================================================

@router.get("/rooms/{room_code}/logs", response_model=GameLogListResponse)
async def get_game_logs(
    room_code: str,
    level: str = "basic",
    db: AsyncSession = Depends(get_db)
):
    """获取游戏日志。
    
    返回游戏过程中的所有日志条目，支持按级别过滤。
    
    Args:
        room_code: 房间代码
        level: 日志级别 (basic | detailed)
            - basic: 仅返回公开日志（发言、主持人公告、死亡）
            - detailed: 返回所有日志（包括系统日志和私密信息）
        
    Returns:
        日志列表
    """
    try:
        service = _game_services.get(room_code)
        if not service:
            raise NotFoundError(f"Game not found for room {room_code}")
        
        game_state = service.get_game_state(room_code)
        if not game_state:
            raise NotFoundError(f"Game state not found for room {room_code}")
        
        # 获取日志
        all_logs = game_state.game_logs if hasattr(game_state, "game_logs") else []
        
        # 根据级别过滤
        if level == "basic":
            # 仅返回公开日志
            filtered_logs = [log for log in all_logs if log.is_public]
        else:
            # 返回所有日志
            filtered_logs = all_logs
        
        # 转换为响应格式
        log_entries = [
            GameLogEntryResponse(
                id=log.id,
                type=log.type,
                content=log.content,
                day=log.day,
                phase=log.phase,
                time=log.time,
                player_id=log.player_id,
                player_name=log.player_name,
                seat_number=log.seat_number,
                metadata=log.metadata,
                is_public=log.is_public,
            )
            for log in filtered_logs
        ]
        
        return GameLogListResponse(
            room_code=room_code,
            day_number=game_state.day_number,
            phase=game_state.phase.value if game_state.phase else "unknown",
            logs=log_entries,
            total=len(log_entries),
            level=level,
        )
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting game logs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rooms/{room_code}/control", response_model=GameControlResponse)
async def control_game(
    room_code: str,
    request: GameControlRequest,
    db: AsyncSession = Depends(get_db)
):
    """游戏控制（开始/暂停/继续）。
    
    Args:
        room_code: 房间代码
        request: 控制请求
            - action: start | pause | resume
            - player_id: 操作玩家ID（可选）
        
    Returns:
        控制结果
    """
    try:
        service = _game_services.get(room_code)
        if not service:
            raise NotFoundError(f"Game not found for room {room_code}")
        
        action = request.action.lower()
        
        if action == "start":
            await service.start_game_manual(room_code)
            message = "游戏已开始"
        elif action == "pause":
            await service.pause_game(room_code)
            message = "游戏已暂停"
        elif action == "resume":
            await service.resume_game(room_code)
            message = "游戏已继续"
        else:
            raise BadRequestError(f"未知的操作: {action}")
        
        game_state = service.get_game_state(room_code)
        status = "paused" if (game_state and game_state.is_paused) else "running"
        
        return GameControlResponse(
            room_code=room_code,
            status=status,
            message=message,
        )
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BadRequestError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error controlling game: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
