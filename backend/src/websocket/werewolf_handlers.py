"""WebSocket event handlers for Werewolf game."""
import asyncio
import logging
from typing import Any, AsyncGenerator

from src.websocket.server import sio
from src.websocket.sessions import user_sessions

logger = logging.getLogger(__name__)


# ============================================================================
# 通用广播方法
# ============================================================================

async def broadcast_to_room(
    room_code: str,
    event: str,
    data: dict,
):
    """
    向房间广播通用事件。

    Args:
        room_code: 房间代码
        event: 事件名称
        data: 事件数据
    """
    await sio.emit(event, data, room=room_code)
    logger.debug(f"Broadcast event '{event}' to room {room_code}")


# ============================================================================
# B30: 主持人公告广播事件
# ============================================================================

async def broadcast_host_announcement(
    room_code: str,
    announcement_type: str,
    content: str,
    metadata: dict | None = None
):
    """
    广播主持人公告到房间所有玩家。
    
    Args:
        room_code: 房间代码
        announcement_type: 公告类型 (game_start, night_start, dawn, death, etc.)
        content: 公告内容
        metadata: 额外元数据 (如死亡玩家信息等)
    """
    event_data = {
        "type": announcement_type,
        "content": content,
        "metadata": metadata or {}
    }
    
    await sio.emit(
        "werewolf:host_announcement",
        event_data,
        room=room_code
    )
    logger.info(f"Host announcement broadcast to room {room_code}: {announcement_type}")


async def stream_host_announcement(
    room_code: str,
    announcement_type: str,
    content_stream: AsyncGenerator[str, None],
    metadata: dict | None = None
):
    """
    流式广播主持人公告（打字机效果）。
    
    Args:
        room_code: 房间代码
        announcement_type: 公告类型
        content_stream: 内容流生成器
        metadata: 额外元数据
    """
    # 发送开始事件
    await sio.emit(
        "werewolf:host_announcement_start",
        {
            "type": announcement_type,
            "metadata": metadata or {}
        },
        room=room_code
    )
    
    full_content = ""
    try:
        async for chunk in content_stream:
            full_content += chunk
            await sio.emit(
                "werewolf:host_announcement_chunk",
                {
                    "type": announcement_type,
                    "chunk": chunk
                },
                room=room_code
            )
            # 控制流速，实现打字机效果
            await asyncio.sleep(0.05)
    finally:
        # 发送完成事件
        await sio.emit(
            "werewolf:host_announcement_end",
            {
                "type": announcement_type,
                "content": full_content,
                "metadata": metadata or {}
            },
            room=room_code
        )
    
    logger.info(f"Host announcement stream completed for room {room_code}: {announcement_type}")


# ============================================================================
# B31: 狼人杀游戏状态更新事件
# ============================================================================

async def broadcast_game_state_update(
    room_code: str,
    phase: str,
    day_number: int,
    alive_players: list[dict],
    dead_players: list[dict],
    current_speaker: dict | None = None
):
    """
    广播游戏状态更新。
    
    Args:
        room_code: 房间代码
        phase: 当前阶段
        day_number: 当前天数
        alive_players: 存活玩家列表 (seat_number, display_name)
        dead_players: 死亡玩家列表 (seat_number, display_name, death_reason, death_day)
        current_speaker: 当前发言者信息
    """
    await sio.emit(
        "werewolf:game_state",
        {
            "phase": phase,
            "day_number": day_number,
            "alive_players": alive_players,
            "dead_players": dead_players,
            "current_speaker": current_speaker
        },
        room=room_code
    )
    logger.debug(f"Game state update broadcast to room {room_code}: {phase}")


async def broadcast_phase_change(
    room_code: str,
    from_phase: str,
    to_phase: str,
    day_number: int
):
    """
    广播阶段切换事件。
    
    Args:
        room_code: 房间代码
        from_phase: 前一阶段
        to_phase: 当前阶段
        day_number: 当前天数
    """
    await sio.emit(
        "werewolf:phase_change",
        {
            "from_phase": from_phase,
            "to_phase": to_phase,
            "day_number": day_number
        },
        room=room_code
    )
    logger.info(f"Phase change broadcast to room {room_code}: {from_phase} -> {to_phase}")


# ============================================================================
# B32: 狼人夜间行动相关事件
# ============================================================================

async def notify_werewolf_turn(
    room_code: str,
    werewolf_player_ids: list[str],
    alive_targets: list[dict]
):
    """
    通知狼人玩家开始行动。
    
    Args:
        room_code: 房间代码
        werewolf_player_ids: 狼人玩家ID列表
        alive_targets: 可选目标列表 (seat_number, display_name)
    """
    for player_id in werewolf_player_ids:
        # 找到该玩家的 sid
        sid = _get_sid_by_player_id(player_id)
        if sid:
            await sio.emit(
                "werewolf:your_turn",
                {
                    "role": "werewolf",
                    "action": "kill",
                    "targets": alive_targets,
                    "message": "请选择今晚要击杀的目标（可以空刀或自刀）"
                },
                room=sid
            )


async def notify_seer_turn(
    room_code: str,
    seer_player_id: str,
    alive_targets: list[dict]
):
    """
    通知预言家开始行动。
    
    Args:
        room_code: 房间代码
        seer_player_id: 预言家玩家ID
        alive_targets: 可选查验目标列表
    """
    sid = _get_sid_by_player_id(seer_player_id)
    if sid:
        await sio.emit(
            "werewolf:your_turn",
            {
                "role": "seer",
                "action": "check",
                "targets": alive_targets,
                "message": "请选择要查验的玩家"
            },
            room=sid
        )


async def notify_seer_result(
    room_code: str,
    seer_player_id: str,
    target_seat: int,
    target_name: str,
    is_werewolf: bool
):
    """
    通知预言家查验结果。
    
    Args:
        room_code: 房间代码
        seer_player_id: 预言家玩家ID
        target_seat: 被查验玩家座位号
        target_name: 被查验玩家名称
        is_werewolf: 是否为狼人
    """
    sid = _get_sid_by_player_id(seer_player_id)
    if sid:
        result = "狼人" if is_werewolf else "好人"
        await sio.emit(
            "werewolf:seer_result",
            {
                "target_seat": target_seat,
                "target_name": target_name,
                "is_werewolf": is_werewolf,
                "message": f"{target_seat}号玩家 {target_name} 的身份是：{result}"
            },
            room=sid
        )


async def notify_witch_turn(
    room_code: str,
    witch_player_id: str,
    killed_player: dict | None,
    has_antidote: bool,
    has_poison: bool,
    can_self_save: bool,
    alive_targets: list[dict]
):
    """
    通知女巫开始行动。
    
    Args:
        room_code: 房间代码
        witch_player_id: 女巫玩家ID
        killed_player: 今晚被杀的玩家信息 (seat_number, display_name) 或 None
        has_antidote: 是否有解药
        has_poison: 是否有毒药
        can_self_save: 是否可以自救（第一晚自救规则）
        alive_targets: 可毒杀的目标列表
    """
    sid = _get_sid_by_player_id(witch_player_id)
    if sid:
        await sio.emit(
            "werewolf:your_turn",
            {
                "role": "witch",
                "action": "use_potion",
                "killed_player": killed_player,
                "has_antidote": has_antidote,
                "has_poison": has_poison,
                "can_self_save": can_self_save,
                "targets": alive_targets,
                "message": _build_witch_message(killed_player, has_antidote, has_poison)
            },
            room=sid
        )


async def notify_hunter_shoot(
    room_code: str,
    hunter_player_id: str,
    alive_targets: list[dict]
):
    """
    通知猎人可以开枪。
    
    Args:
        room_code: 房间代码
        hunter_player_id: 猎人玩家ID
        alive_targets: 可射杀的目标列表
    """
    sid = _get_sid_by_player_id(hunter_player_id)
    if sid:
        await sio.emit(
            "werewolf:hunter_shoot",
            {
                "role": "hunter",
                "action": "shoot",
                "targets": alive_targets,
                "message": "你已死亡，是否开枪带走一名玩家？"
            },
            room=sid
        )


# ============================================================================
# B33: AI发言流式输出事件
# ============================================================================

async def stream_ai_speech(
    room_code: str,
    speaker_seat: int,
    speaker_name: str,
    speech_stream: AsyncGenerator[str, None]
):
    """
    流式广播AI玩家发言（打字机效果）。
    
    Args:
        room_code: 房间代码
        speaker_seat: 发言者座位号
        speaker_name: 发言者名称
        speech_stream: 发言内容流生成器
    """
    # 发送开始事件
    await sio.emit(
        "werewolf:speech_start",
        {
            "speaker_seat": speaker_seat,
            "speaker_name": speaker_name
        },
        room=room_code
    )
    
    full_speech = ""
    try:
        async for chunk in speech_stream:
            full_speech += chunk
            await sio.emit(
                "werewolf:speech_chunk",
                {
                    "speaker_seat": speaker_seat,
                    "chunk": chunk
                },
                room=room_code
            )
            # 控制流速，实现打字机效果
            await asyncio.sleep(0.03)
    finally:
        # 发送完成事件
        await sio.emit(
            "werewolf:speech_end",
            {
                "speaker_seat": speaker_seat,
                "speaker_name": speaker_name,
                "content": full_speech
            },
            room=room_code
        )
    
    logger.info(f"AI speech stream completed for seat {speaker_seat} in room {room_code}")
    return full_speech


async def broadcast_vote_update(
    room_code: str,
    voter_seat: int,
    voter_name: str,
    target_seat: int | None,
    target_name: str | None
):
    """
    广播投票更新。
    
    Args:
        room_code: 房间代码
        voter_seat: 投票者座位号
        voter_name: 投票者名称
        target_seat: 被投票者座位号（None表示弃票）
        target_name: 被投票者名称
    """
    await sio.emit(
        "werewolf:vote_update",
        {
            "voter_seat": voter_seat,
            "voter_name": voter_name,
            "target_seat": target_seat,
            "target_name": target_name,
            "is_abstain": target_seat is None
        },
        room=room_code
    )


async def broadcast_vote_result(
    room_code: str,
    vote_counts: dict[int, int],
    eliminated_seat: int | None,
    eliminated_name: str | None,
    is_tie: bool = False
):
    """
    广播投票结果。
    
    Args:
        room_code: 房间代码
        vote_counts: 得票数 {seat_number: count}
        eliminated_seat: 被淘汰者座位号（None表示平票无人出局）
        eliminated_name: 被淘汰者名称
        is_tie: 是否平票
    """
    await sio.emit(
        "werewolf:vote_result",
        {
            "vote_counts": vote_counts,
            "eliminated_seat": eliminated_seat,
            "eliminated_name": eliminated_name,
            "is_tie": is_tie
        },
        room=room_code
    )


async def broadcast_game_over(
    room_code: str,
    winner: str,
    winning_players: list[dict],
    all_players: list[dict]
):
    """
    广播游戏结束。
    
    Args:
        room_code: 房间代码
        winner: 获胜方 (werewolf, villager)
        winning_players: 获胜玩家列表
        all_players: 所有玩家列表（包含真实身份）
    """
    await sio.emit(
        "werewolf:game_over",
        {
            "winner": winner,
            "winner_name": "狼人阵营" if winner == "werewolf" else "好人阵营",
            "winning_players": winning_players,
            "all_players": all_players
        },
        room=room_code
    )
    logger.info(f"Game over broadcast to room {room_code}: {winner} wins")


async def broadcast_role_assignment(
    room_code: str,
    players: list[dict]
):
    """
    广播角色分配信息（观战模式下可见所有角色）。
    
    Args:
        room_code: 房间代码
        players: 玩家列表，包含 seat_number, player_name, role, team
    """
    await sio.emit(
        "werewolf:role_assignment",
        {
            "players": players
        },
        room=room_code
    )
    logger.info(f"Role assignment broadcast to room {room_code}: {len(players)} players")


# ============================================================================
# 用户操作事件处理器
# ============================================================================

@sio.event
async def werewolf_action(sid: str, data: dict):
    """
    处理狼人杀玩家行动。
    
    Args:
        sid: Socket session ID
        data: {
            "room_code": str,
            "player_id": str,
            "action_type": str,  # kill, check, save, poison, shoot, vote
            "target_seat": int | None
        }
    """
    try:
        room_code = data.get("room_code")
        player_id = data.get("player_id")
        action_type = data.get("action_type")
        target_seat = data.get("target_seat")
        
        if not room_code or not player_id or not action_type:
            await sio.emit(
                "werewolf:error",
                {"message": "缺少必要参数"},
                room=sid
            )
            return
        
        logger.info(
            f"Werewolf action received: player={player_id}, "
            f"action={action_type}, target={target_seat}"
        )
        
        # 发送确认
        await sio.emit(
            "werewolf:action_received",
            {
                "action_type": action_type,
                "target_seat": target_seat,
                "message": "行动已收到，等待处理..."
            },
            room=sid
        )
        
        # 实际处理将由 WerewolfGameService 完成
        # 这里只负责接收和转发事件
        
    except Exception as e:
        logger.error(f"Error handling werewolf action: {e}")
        await sio.emit(
            "werewolf:error",
            {"message": f"处理行动失败: {str(e)}"},
            room=sid
        )


@sio.event
async def werewolf_ready(sid: str, data: dict):
    """
    处理玩家准备开始游戏。
    
    Args:
        sid: Socket session ID
        data: {"room_code": str, "player_id": str}
    """
    try:
        room_code = data.get("room_code")
        player_id = data.get("player_id")
        
        if not room_code or not player_id:
            await sio.emit(
                "werewolf:error",
                {"message": "缺少必要参数"},
                room=sid
            )
            return
        
        logger.info(f"Player {player_id} ready in room {room_code}")
        
        # 广播玩家准备状态
        await sio.emit(
            "werewolf:player_ready",
            {
                "player_id": player_id,
                "message": "玩家已准备"
            },
            room=room_code
        )
        
    except Exception as e:
        logger.error(f"Error handling werewolf ready: {e}")
        await sio.emit(
            "werewolf:error",
            {"message": f"处理失败: {str(e)}"},
            room=sid
        )


# ============================================================================
# B19-B22: 游戏控制事件处理器
# ============================================================================

@sio.event
async def werewolf_start_game(sid: str, data: dict):
    """
    B19: 处理开始游戏事件。
    
    Args:
        sid: Socket session ID
        data: {"room_code": str, "player_id": str}
    """
    from src.api.werewolf_routes import _game_services, WerewolfGameService
    from src.database import get_db
    from src.models.game import GameRoom
    from sqlalchemy import select
    
    try:
        room_code = data.get("room_code")
        player_id = data.get("player_id")
        
        print(f"[DEBUG] werewolf_start_game called with room_code={room_code}, player_id={player_id}")
        print(f"[DEBUG] Available game services: {list(_game_services.keys())}")
        
        if not room_code:
            await sio.emit(
                "werewolf:error",
                {"message": "缺少房间代码"},
                room=sid
            )
            return
        
        logger.info(f"Start game request received for room {room_code} from player {player_id}")
        
        # 获取游戏服务
        service = _game_services.get(room_code)
        
        # 如果服务不存在（可能因为服务器重启），尝试重建
        if not service:
            print(f"[DEBUG] Game service not found for room {room_code}, attempting to recreate...")
            
            async for db in get_db():
                # 检查房间是否存在
                result = await db.execute(
                    select(GameRoom).where(GameRoom.code == room_code)
                )
                room = result.scalar_one_or_none()
                
                if not room:
                    await sio.emit(
                        "werewolf:error",
                        {"message": f"房间不存在: {room_code}"},
                        room=sid
                    )
                    return
                
                # 显式加载关联数据以避免懒加载问题
                await db.refresh(room, ["participants"])
                
                # 获取人类玩家ID（优先查找 is_owner=True，否则查找 is_ai_agent=False）
                human_participant = None
                for p in room.participants:
                    print(f"[DEBUG] Participant: player_id={p.player_id}, is_ai_agent={p.is_ai_agent}, is_owner={p.is_owner}")
                    if p.is_owner:
                        human_participant = p
                        break
                    if not p.is_ai_agent and human_participant is None:
                        human_participant = p
                
                # 如果是纯观战模式（没有人类玩家），使用第一个参与者作为"观察者视角"
                if not human_participant and room.participants:
                    human_participant = room.participants[0]
                    print(f"[DEBUG] No human player found, using first participant as observer: {human_participant.player_id}")
                
                if not human_participant:
                    await sio.emit(
                        "werewolf:error",
                        {"message": "房间没有参与者"},
                        room=sid
                    )
                    return
                
                # 重新创建服务并初始化游戏
                service = WerewolfGameService(db)
                _game_services[room_code] = service
                
                # 对于观战模式，human_player_id 可以是任意一个玩家ID
                await service.start_game(
                    room_code=room_code,
                    human_player_id=str(human_participant.player_id),
                    human_role=None  # 观战模式不指定角色
                )
                
                print(f"[DEBUG] Game service recreated for room {room_code}")
                break
        
        if not service:
            await sio.emit(
                "werewolf:error",
                {"message": f"无法创建游戏服务: {room_code}"},
                room=sid
            )
            return
        
        # 广播游戏即将开始事件
        await sio.emit(
            "werewolf:game_starting",
            {
                "room_code": room_code,
                "message": "游戏即将开始...",
            },
            room=room_code
        )
        
        # 运行游戏流程（异步执行）
        asyncio.create_task(service.run_game(room_code))
        
    except Exception as e:
        logger.error(f"Error handling werewolf start game: {e}", exc_info=True)
        await sio.emit(
            "werewolf:error",
            {"message": f"开始游戏失败: {str(e)}"},
            room=sid
        )


@sio.event
async def werewolf_pause_game(sid: str, data: dict):
    """
    B20: 处理暂停游戏事件。
    
    Args:
        sid: Socket session ID
        data: {"room_code": str, "player_id": str}
    """
    from src.api.werewolf_routes import _game_services
    
    try:
        room_code = data.get("room_code")
        player_id = data.get("player_id")
        
        if not room_code:
            await sio.emit(
                "werewolf:error",
                {"message": "缺少房间代码"},
                room=sid
            )
            return
        
        logger.info(f"Pause game request received for room {room_code} from player {player_id}")
        
        # 获取游戏服务并暂停游戏
        service = _game_services.get(room_code)
        if service:
            try:
                await service.pause_game(room_code)
                # 广播游戏暂停事件
                await sio.emit(
                    "werewolf:game_paused",
                    {
                        "room_code": room_code,
                        "message": "游戏已暂停",
                        "paused_by": player_id,
                    },
                    room=room_code
                )
            except Exception as pause_err:
                await sio.emit(
                    "werewolf:error",
                    {"message": str(pause_err)},
                    room=sid
                )
        else:
            await sio.emit(
                "werewolf:error",
                {"message": f"游戏服务不存在: {room_code}"},
                room=sid
            )
        
    except Exception as e:
        logger.error(f"Error handling werewolf pause game: {e}")
        await sio.emit(
            "werewolf:error",
            {"message": f"暂停游戏失败: {str(e)}"},
            room=sid
        )


@sio.event
async def werewolf_resume_game(sid: str, data: dict):
    """
    B21: 处理继续游戏事件。
    
    Args:
        sid: Socket session ID
        data: {"room_code": str, "player_id": str}
    """
    from src.api.werewolf_routes import _game_services
    
    try:
        room_code = data.get("room_code")
        player_id = data.get("player_id")
        
        if not room_code:
            await sio.emit(
                "werewolf:error",
                {"message": "缺少房间代码"},
                room=sid
            )
            return
        
        logger.info(f"Resume game request received for room {room_code} from player {player_id}")
        
        # 获取游戏服务并继续游戏
        service = _game_services.get(room_code)
        if service:
            try:
                await service.resume_game(room_code)
                # 广播游戏继续事件
                await sio.emit(
                    "werewolf:game_resumed",
                    {
                        "room_code": room_code,
                        "message": "游戏继续",
                        "resumed_by": player_id,
                    },
                    room=room_code
                )
            except Exception as resume_err:
                await sio.emit(
                    "werewolf:error",
                    {"message": str(resume_err)},
                    room=sid
                )
        else:
            await sio.emit(
                "werewolf:error",
                {"message": f"游戏服务不存在: {room_code}"},
                room=sid
            )
        
    except Exception as e:
        logger.error(f"Error handling werewolf resume game: {e}")
        await sio.emit(
            "werewolf:error",
            {"message": f"继续游戏失败: {str(e)}"},
            room=sid
        )


@sio.event
async def werewolf_leave_room(sid: str, data: dict):
    """
    处理玩家离开房间事件，停止游戏并清理资源。
    
    Args:
        sid: Socket session ID
        data: {"room_code": str, "player_id": str}
    """
    from src.api.werewolf_routes import _game_services
    
    try:
        room_code = data.get("room_code")
        player_id = data.get("player_id")
        
        if not room_code:
            logger.warning(f"Leave room request without room_code from sid {sid}")
            return
        
        logger.info(f"Leave room request received for room {room_code} from player {player_id}")
        
        # 离开 Socket.IO 房间
        sio.leave_room(sid, room_code)
        
        # 获取游戏服务并停止游戏
        service = _game_services.get(room_code)
        if service:
            try:
                await service.stop_game(room_code)
                logger.info(f"Game stopped for room {room_code} due to player {player_id} leaving")
                
                # 清理游戏服务
                _game_services.pop(room_code, None)
                
                # 广播游戏已停止事件
                await sio.emit(
                    "werewolf:game_stopped",
                    {
                        "room_code": room_code,
                        "message": "游戏已停止",
                        "reason": "player_left",
                    },
                    room=room_code
                )
            except Exception as stop_err:
                logger.error(f"Error stopping game for room {room_code}: {stop_err}")
        else:
            logger.info(f"No game service found for room {room_code}, nothing to stop")
        
    except Exception as e:
        logger.error(f"Error handling werewolf leave room: {e}")


@sio.event
async def werewolf_player_speech(sid: str, data: dict):
    """
    B22: 处理玩家发言事件。
    
    Args:
        sid: Socket session ID
        data: {
            "room_code": str,
            "player_id": str,
            "seat_number": int,
            "content": str
        }
    """
    try:
        room_code = data.get("room_code")
        player_id = data.get("player_id")
        seat_number = data.get("seat_number")
        content = data.get("content")
        
        if not room_code or not player_id or seat_number is None:
            await sio.emit(
                "werewolf:error",
                {"message": "缺少必要参数"},
                room=sid
            )
            return
        
        if not content or not content.strip():
            await sio.emit(
                "werewolf:error",
                {"message": "发言内容不能为空"},
                room=sid
            )
            return
        
        logger.info(
            f"Player speech received: room={room_code}, seat={seat_number}, "
            f"content length={len(content)}"
        )
        
        # 发送确认
        await sio.emit(
            "werewolf:speech_received",
            {
                "seat_number": seat_number,
                "message": "发言已收到",
            },
            room=sid
        )
        
        # 广播发言内容到房间
        await sio.emit(
            "werewolf:player_speech",
            {
                "seat_number": seat_number,
                "player_name": f"玩家{seat_number}",
                "content": content.strip(),
            },
            room=room_code
        )
        
        # 实际的发言处理将由 WerewolfGameService.process_player_speech() 处理
        
    except Exception as e:
        logger.error(f"Error handling werewolf player speech: {e}")
        await sio.emit(
            "werewolf:error",
            {"message": f"处理发言失败: {str(e)}"},
            room=sid
        )


# ============================================================================
# 辅助函数
# ============================================================================

def _get_sid_by_player_id(player_id: str) -> str | None:
    """根据玩家ID获取对应的socket session ID。"""
    for sid, pid in user_sessions.items():
        if pid == player_id:
            return sid
    return None


def _build_witch_message(
    killed_player: dict | None,
    has_antidote: bool,
    has_poison: bool
) -> str:
    """构建女巫提示消息。"""
    parts = []
    
    if killed_player:
        parts.append(f"今晚 {killed_player['seat_number']}号 {killed_player['display_name']} 被杀")
        if has_antidote:
            parts.append("你有解药，是否使用？")
    else:
        parts.append("今晚是平安夜，没有人被杀")
    
    if has_poison:
        parts.append("你有毒药，是否使用？")
    
    if not has_antidote and not has_poison:
        parts.append("你没有药水可用")
    
    return "。".join(parts) + "。"


# ============================================================================
# AI 行动广播
# ============================================================================

async def broadcast_ai_action(
    room_code: str,
    ai_player_id: str,
    action: dict[str, Any]
):
    """
    广播 AI 代理的行动详情（用于详细日志模式）。
    
    Args:
        room_code: 房间代码
        ai_player_id: AI 玩家 ID
        action: 行动数据，包含：
            - action_type: 行动类型 (werewolf_kill, seer_check, witch_save, witch_poison, vote, etc.)
            - seat_number: AI 玩家座位号
            - role: AI 玩家角色
            - target: 目标座位号（如果有）
            - reasoning: AI 决策理由
            - result: 行动结果（如预言家查验结果）
    """
    try:
        await sio.emit(
            "werewolf:ai_action",
            {
                "room_code": room_code,
                "ai_player_id": ai_player_id,
                "action": action,
            },
            room=room_code
        )
        logger.debug(f"Broadcasted ai_action for room {room_code}: {action.get('action_type')}")
    except Exception as e:
        logger.error(f"Error broadcasting ai_action: {e}")
