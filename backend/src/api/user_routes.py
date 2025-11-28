"""User-related API endpoints.

单人模式下无需用户认证，此模块保留为空。
所有玩家相关功能由 AI 代理系统处理。
"""
from fastapi import APIRouter

# Create empty router for compatibility
router = APIRouter(tags=["users"])

# 单人模式下无需任何用户端点
# - 无需 /api/v1/players/guest (游客创建)
# - 无需 /api/v1/players/me (获取当前玩家)
# - 无需 /api/v1/players/me/upgrade (升级账户)
# - 无需 /api/v1/players/me/stats (玩家统计)
# - 无需 /api/v1/sessions/* (会话管理)
