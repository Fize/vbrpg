"""Guest username generator.

Generates usernames in the format: Guest_形容词_动物
Example: Guest_快乐_熊猫, Guest_勇敢_狮子
"""

import random

# 形容词列表 (Adjectives)
ADJECTIVES = [
    "快乐", "勇敢", "聪明", "可爱", "活泼",
    "温柔", "友善", "机智", "灵巧", "优雅",
    "沉稳", "热情", "冷静", "幽默", "神秘",
    "闪亮", "迅速", "强大", "温暖", "清新",
    "善良", "坚强", "睿智", "敏捷", "淘气",
    "温和", "活跃", "稳重", "开朗", "细心",
]

# 动物列表 (Animals)
ANIMALS = [
    "熊猫", "狮子", "老虎", "大象", "长颈鹿",
    "企鹅", "考拉", "袋鼠", "海豚", "鲸鱼",
    "猎豹", "狐狸", "狼", "熊", "兔子",
    "松鼠", "猴子", "猩猩", "河马", "犀牛",
    "斑马", "羚羊", "鹿", "驼鹿", "骆驼",
    "鹰", "猫头鹰", "鹦鹉", "孔雀", "天鹅",
    "海豹", "海獭", "水獭", "浣熊", "刺猬",
    "仓鼠", "龙猫", "雪貂", "獾", "鼬",
]


def generate_guest_username() -> str:
    """Generate a random guest username.
    
    Format: Guest_形容词_动物
    Example: Guest_快乐_熊猫
    
    Returns:
        A randomly generated guest username
    """
    adjective = random.choice(ADJECTIVES)
    animal = random.choice(ANIMALS)
    return f"Guest_{adjective}_{animal}"


def generate_unique_guest_username(existing_usernames: set[str], max_attempts: int = 100) -> str:
    """Generate a unique guest username that doesn't exist in the set.
    
    Args:
        existing_usernames: Set of existing usernames to avoid
        max_attempts: Maximum number of generation attempts
        
    Returns:
        A unique guest username
        
    Raises:
        ValueError: If unable to generate unique username after max_attempts
    """
    for _ in range(max_attempts):
        username = generate_guest_username()
        if username not in existing_usernames:
            return username

    # Fallback: append random number
    return f"{generate_guest_username()}_{random.randint(1000, 9999)}"


def is_guest_username(username: str) -> bool:
    """Check if a username is a guest username.
    
    Args:
        username: Username to check
        
    Returns:
        True if username follows guest format, False otherwise
    """
    return username.startswith("Guest_")
