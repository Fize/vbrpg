"""AI Personality Generator - generates random personalities for game agents."""
import random
from typing import Dict, List

class PersonalityGenerator:
    """Generates random AI personalities at game start."""
    
    TRAITS = {
        "analytical": "善于逻辑分析，注重证据和推理",
        "aggressive": "强势果断，喜欢主动出击",
        "cautious": "谨慎保守，偏好安全策略",
        "chaotic": "行为难以预测，喜欢出人意料",
        "cooperative": "注重团队协作，乐于分享信息",
        "deceptive": "善于伪装和误导，精于心理博弈",
        "emotional": "情绪化，容易被场上气氛带动",
        "quiet": "沉默寡言，发言简洁但有分量",
        "suspicious": "疑心重，对所有人都保持警惕",
        "confident": "自信满满，发言有说服力",
    }
    
    SPEAKING_STYLES = ["简洁直接", "长篇大论", "喜欢反问", "引用他人发言", "用数据说话"]
    
    @classmethod
    def generate(cls) -> Dict[str, str]:
        """Generate a random personality."""
        trait_name = random.choice(list(cls.TRAITS.keys()))
        trait_desc = cls.TRAITS[trait_name]
        style = random.choice(cls.SPEAKING_STYLES)
        
        return {
            "trait": trait_name,
            "trait_desc": trait_desc,
            "speaking_style": style,
            "description": f"性格{trait_desc}，说话风格{style}",
        }
    
    @classmethod
    def generate_all(cls, count: int) -> List[Dict[str, str]]:
        """Generate unique personalities for multiple agents."""
        used_traits = set()
        personalities = []
        for _ in range(count):
            available = [t for t in cls.TRAITS if t not in used_traits]
            if not available:
                available = list(cls.TRAITS.keys())
            trait_name = random.choice(available)
            used_traits.add(trait_name)
            style = random.choice(cls.SPEAKING_STYLES)
            personalities.append({
                "trait": trait_name,
                "trait_desc": cls.TRAITS[trait_name],
                "speaking_style": style,
                "description": f"性格{cls.TRAITS[trait_name]}，说话风格{style}",
            })
        return personalities
