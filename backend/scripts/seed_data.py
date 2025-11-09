"""Seed initial data for the database."""
import asyncio
import os
import sys
from pathlib import Path

# Ensure we're running from backend directory
backend_dir = Path(__file__).parent.parent
os.chdir(backend_dir)

# Add backend directory to path
sys.path.insert(0, str(backend_dir))

from sqlalchemy import select

from src.database import AsyncSessionLocal
from src.models.game_type import GameType


async def seed_game_types():
    """Seed game types table with Crime Scene game and placeholder games."""
    async with AsyncSessionLocal() as session:
        # Define all games
        games_data = [
            {
                "name": "犯罪现场",
                "slug": "crime-scene",
                "description": "一款推理解谜游戏，玩家通过收集线索、推理分析来找出真凶。每个玩家扮演不同的角色，通过互动和讨论来揭开谜团。",
                "rules_summary": """
游戏分为几个阶段：
1. 角色分配：每个玩家获得一个角色卡，包含背景故事和秘密信息
2. 线索收集：玩家轮流探索场景，收集证据和线索
3. 讨论推理：玩家可以自由讨论，分享信息或保留秘密
4. 指认凶手：根据收集的信息，投票指认凶手
5. 真相揭晓：揭示最终答案

游戏目标：找出真凶，或者隐藏真相（如果你是凶手）
""",
                "min_players": 4,
                "max_players": 8,
                "avg_duration_minutes": 60,
                "is_available": True
            },
            {
                "name": "狼人杀",
                "slug": "werewolf",
                "description": "经典的社交推理游戏，村民和狼人展开智慧与心理的较量。白天投票，夜晚行动，谁能笑到最后？",
                "rules_summary": "狼人杀规则：村民需要找出所有狼人，狼人需要消灭所有村民。",
                "min_players": 6,
                "max_players": 12,
                "avg_duration_minutes": 45,
                "is_available": False
            },
            {
                "name": "阿瓦隆",
                "slug": "avalon",
                "description": "亚瑟王的传说背景下的团队游戏，正义与邪恶阵营暗中较量，身份隐藏，信任与背叛交织。",
                "rules_summary": "阿瓦隆规则：好人阵营完成任务，坏人阵营破坏任务。",
                "min_players": 5,
                "max_players": 10,
                "avg_duration_minutes": 30,
                "is_available": False
            },
            {
                "name": "谁是卧底",
                "slug": "undercover",
                "description": "简单有趣的语言游戏，通过描述词语找出混入队伍的卧底。考验语言表达和观察能力。",
                "rules_summary": "谁是卧底规则：平民找出卧底，卧底隐藏身份。",
                "min_players": 4,
                "max_players": 10,
                "avg_duration_minutes": 20,
                "is_available": False
            },
            {
                "name": "德州扑克",
                "slug": "texas-holdem",
                "description": "世界上最流行的扑克游戏，策略、运气和心理战的完美结合。",
                "rules_summary": "德州扑克规则：通过下注和比牌获胜。",
                "min_players": 2,
                "max_players": 9,
                "avg_duration_minutes": 40,
                "is_available": False
            }
        ]

        # Insert each game if not exists
        for game_data in games_data:
            result = await session.execute(
                select(GameType).where(GameType.slug == game_data["slug"])
            )
            existing = result.scalar_one_or_none()

            if existing:
                print(f"✓ {game_data['name']} already exists, skipping...")
                continue

            game = GameType(**game_data)
            session.add(game)
            status = "可游玩" if game_data["is_available"] else "即将推出"
            print(f"✓ {game_data['name']} ({status}) seeded successfully")

        await session.commit()


async def main():
    """Run all seed functions."""
    print("Starting database seeding...")
    await seed_game_types()
    print("Database seeding completed!")


if __name__ == "__main__":
    asyncio.run(main())
