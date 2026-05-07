"""每日运势 — 运势签生成"""

import random
from datetime import date

# 运势等级、对应 emoji 和签文池
_FORTUNES = [
    ("大吉", "🌟", ["万事如意", "好运连连", "心想事成", "贵人相助",
                     "今天运气爆棚！", "适合表白或尝试新事物"]),
    ("吉", "👍", ["诸事顺利", "小有收获", "今天状态不错",
                   "适合推进重要事项", "平平淡淡才是真"]),
    ("中吉", "✨", ["今天运气还行", "会有小惊喜", "适合开始新计划",
                     "稍加努力就能达成目标"]),
    ("小吉", "🍀", ["稍微有点好运", "一切都在掌握中",
                     "今天适合低调行事", "稳扎稳打就好"]),
    ("末吉", "🌿", ["不好不坏的一天", "保持平常心",
                     "宜摸鱼，忌焦虑", "顺其自然吧"]),
    ("凶", "😰", ["今天要小心行事", "避免冲动决策",
                   "凡事三思而后行", "适合独处充电"]),
    ("大凶", "💀", ["诸事不宜，宜摸鱼", "今天适合宅在家里",
                     "不宜出门，不宜社交", "吃点好的安慰自己"]),
]

# 特殊签（低概率）
_SPECIAL = [
    ("神签", "🎊", ["天选之人！今天做什么都顺利",
                     "幸运 MAX！去买张彩票吧"]),
    ("恋签", "💕", ["桃花运旺盛~", "今天可能会遇见重要的人"]),
]


def get_daily_fortune() -> str:
    """获取今日运势，基于日期种子确保每天相同"""
    today = date.today()
    rng = random.Random(today.toordinal())
    if rng.random() < 0.05:
        rank, emoji, messages = _SPECIAL[0] if rng.random() < 0.5 else _SPECIAL[1]
    else:
        rank, emoji, messages = rng.choice(_FORTUNES)
    message = rng.choice(messages)
    return f"📜 今日运势 — {emoji} {rank}\n{message}"


def get_random_fortune() -> str:
    """随机抽一签（每次结果不同）"""
    pool = _FORTUNES + _SPECIAL
    rank, emoji, messages = random.choice(pool)
    message = random.choice(messages)
    return f"🎲 抽签 — {emoji} {rank}\n{message}"
