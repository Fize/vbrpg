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
from datetime import datetime

from src.models.game import GameType, GameRole


async def seed_game_types():
    """Seed game types table with Crime Scene game and placeholder games."""
    async with AsyncSessionLocal() as session:
        # Define all games (with stable ids so roles/references can be linked)
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
                "is_available": True
            }
        ]

        # Define per-game roles to seed (keyed by game slug)
        roles_by_game = {
            "werewolf": [
                {
                    "slug": "villager",
                    "name": "村民",
                    "description": "普通村民，无特殊能力，白天参与讨论与投票。",
                    "task": "在白天参与讨论并投票找出狼人；没有夜间能力。",
                    "is_playable": True,
                },
                {
                    "slug": "werewolf",
                    "name": "狼人",
                    "description": "夜间行动的隐秘阵营，目标是消灭村民并隐瞒身份。",
                    "task": "每晚选择一个玩家作为击杀目标；在白天混淆视听避免被投票判定。",
                    "is_playable": True,
                },
                {
                    "slug": "seer",
                    "name": "预言家",
                    "description": "每晚可以查看一名玩家的真实身份（好人阵营/狼人阵营）。",
                    "task": "每晚选择一名玩家查验其身份，获得该玩家是狼人还是好人的信息，并在白天合理引导村民投票。",
                    "is_playable": True,
                },
                {
                    "slug": "witch",
                    "name": "女巫",
                    "description": "拥有解药和毒药各一瓶，解药可以救活当晚被狼人杀死的玩家，毒药可以毒死任意一名玩家。",
                    "task": "每晚得知被狼人击杀的目标后决定是否使用解药救人；可以在任意夜晚使用毒药毒死一名玩家。每种药只能使用一次。",
                    "is_playable": True,
                },
                {
                    "slug": "hunter",
                    "name": "猎人",
                    "description": "当猎人被淘汰（无论是被狼人杀死还是被投票出局）时，可以立即开枪带走一名玩家。",
                    "task": "被淘汰时开枪选择一名玩家作为报复目标。注意：如果被女巫毒死则不能开枪。",
                    "is_playable": True,
                },
            ],
        }

        # Insert/update each game if not exists
        for game_data in games_data:
            result = await session.execute(
                select(GameType).where(GameType.slug == game_data["slug"])
            )
            existing = result.scalar_one_or_none()

            if existing:
                # Update updatable fields from seed if they differ
                updated = False
                for key in ("name", "description", "rules_summary", "min_players", "max_players", "avg_duration_minutes", "is_available"):
                    if getattr(existing, key) != game_data[key]:
                        setattr(existing, key, game_data[key])
                        updated = True

                if updated:
                    session.add(existing)
                    print(f"✓ {game_data['name']} exists — updated from seed data")
                else:
                    print(f"✓ {game_data['name']} already exists, no changes needed")
                # Ensure roles are seeded/updated for this game (if roles provided)
                if game_data["slug"] in roles_by_game:
                    game_roles = roles_by_game[game_data["slug"]]
                    for role_data in game_roles:
                        # Try to find existing role by slug + game id
                        role_query = await session.execute(
                            select(GameRole).where(
                                GameRole.slug == role_data["slug"],
                                GameRole.game_type_id == existing.id
                            )
                        )
                        existing_role = role_query.scalar_one_or_none()
                        if existing_role:
                            # update fields
                            updated_role = False
                            for k in ("name", "description", "task", "is_playable"):
                                if getattr(existing_role, k) != role_data[k]:
                                    setattr(existing_role, k, role_data[k])
                                    updated_role = True
                            if updated_role:
                                session.add(existing_role)
                                print(f"  - updated role {existing_role.slug} for {existing.slug}")
                        else:
                            new_role = GameRole(
                                game_type_id=existing.id,
                                slug=role_data["slug"],
                                name=role_data["name"],
                                description=role_data["description"],
                                task=role_data["task"],
                                is_playable=role_data.get("is_playable", True),
                                created_at=datetime.utcnow(),
                            )
                            session.add(new_role)
                            print(f"  - inserted role {role_data['slug']} for {existing.slug}")
                continue

            # set id if present in seed data to keep it stable
            if "id" in game_data:
                game = GameType(id=game_data["id"], **{k: v for k, v in game_data.items() if k != "id"})
            else:
                game = GameType(**game_data)
            session.add(game)
            status = "可游玩" if game_data["is_available"] else "即将推出"
            print(f"✓ {game_data['name']} ({status}) seeded successfully")

        await session.commit()

        # After committing game types, ensure roles for newly inserted games are created
        # (in case we just inserted a brand new GameType)
        for game_data in games_data:
            slug = game_data["slug"]
            if slug not in roles_by_game:
                continue

            # find game (fresh from DB)
            result = await session.execute(select(GameType).where(GameType.slug == slug))
            game_obj = result.scalar_one_or_none()
            if not game_obj:
                continue

            for role_data in roles_by_game[slug]:
                role_query = await session.execute(
                    select(GameRole).where(GameRole.slug == role_data["slug"], GameRole.game_type_id == game_obj.id)
                )
                existing_role = role_query.scalar_one_or_none()
                if not existing_role:
                    new_role = GameRole(
                        game_type_id=game_obj.id,
                        slug=role_data["slug"],
                        name=role_data["name"],
                        description=role_data["description"],
                        task=role_data["task"],
                        is_playable=role_data.get("is_playable", True),
                        created_at=datetime.utcnow(),
                    )
                    session.add(new_role)
                    print(f"✓ seeded role {role_data['slug']} for {slug}")

        await session.commit()


async def main():
    """Run all seed functions."""
    print("Starting database seeding...")
    await seed_game_types()
    print("Database seeding completed!")


if __name__ == "__main__":
    asyncio.run(main())
