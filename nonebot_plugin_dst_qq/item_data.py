"""
饥荒物品名对照数据
Don't Starve Together Item Name Mapping Data

版本: v5.0 (内置数据版本)
更新: 2024.9.14
此模块包含饥荒物品中英文对照数据，无需外部文件依赖
"""

# 物品名对照字典
ITEM_NAME_MAPPING = {    'abigail': '阿比盖尔',
    'acorn': '桦栗果',
    'amulet': '重生护符',
    'anchor': '锚',
    'antlionhat': '刮地皮头盔',
    'armorgrass': '草甲',
    'armormarble': '大理石甲',
    'armorruins': '铥矿甲',
    'armorwood': '木甲',
    'ash': '灰烬',
    'asparagus': '芦笋',
    'axe': '斧头',
    'axe_pickaxe': '十字镐',
    'backpack': '背包',
    'bandage': '蜂蜜药膏',
    'beefalowool': '牛毛',
    'berries': '浆果',
    'bird_egg': '鸟蛋',
    'boomerang': '回旋镖',
    'bugnet': '捕虫网',
    'butterfly': '蝴蝶',
    'campfire': '营火',
    'carrot': '胡萝卜',
    'chester_eyebone': '切斯特眼骨',
    'cutgrass': '草',
    'cutreeds': '芦苇',
    'cutstone': '石块',
    'deerclops_eyeball': '独眼巨鹿眼球',
    'dragonfly_fire': '龙蝇炎',
    'dragonfruit': '火龙果',
    'earmuffs': '保暖耳罩',
    'fireflies': '萤火虫',
    'fishingrod': '钓竿',
    'flint': '燧石',
    'flower': '花',
    'fruitfly': '果蝇',
    'gears': '齿轮',
    'goldnugget': '金块',
    'hambat': '火腿球棒',
    'hammer': '锤子',
    'healingsalve': '治疗药膏',
    'honey': '蜂蜜',
    'ice': '冰',
    'icebox': '冰箱',
    'krampus_sack': '坎普斯背包',
    'log': '木头',
    'mandrake': '曼德拉草',
    'marble': '大理石',
    'meat': '肉',
    'monstermeat': '怪物肉',
    'nightmarefuel': '噩梦燃料',
    'papyrus': '纸莎草',
    'pickaxe': '镐',
    'piggyback': '猪皮背包',
    'poop': '粪便',
    'rabbit': '兔子',
    'rocks': '石头',
    'rope': '绳子',
    'seeds': '种子',
    'shovel': '铲子',
    'silk': '蜘蛛丝',
    'spear': '长矛',
    'spider_gland': '蜘蛛腺体',
    'stinger': '蜜蜂刺',
    'tentaclespike': '触手尖刺',
    'torch': '火把',
    'twigs': '树枝',
    'umbrella': '雨伞',
    'walkingcane': '步行手杖',
    'winterhat': '冬帽'
}

def get_chinese_name(english_name: str) -> str:
    """
    根据英文名获取中文名
    
    Args:
        english_name: 英文物品名
        
    Returns:
        中文物品名，如果找不到则返回原英文名
    """
    return ITEM_NAME_MAPPING.get(english_name, english_name)

def search_items(keyword: str) -> list:
    """
    搜索物品
    
    Args:
        keyword: 搜索关键词（支持中英文）
        
    Returns:
        匹配的物品列表 [(英文名, 中文名), ...]
    """
    keyword = keyword.lower().strip()
    if not keyword:
        return []
    
    results = []
    
    # 搜索英文名和中文名
    for english_name, chinese_name in ITEM_NAME_MAPPING.items():
        if (keyword in english_name.lower() or 
            keyword in chinese_name.lower()):
            results.append((english_name, chinese_name))
    
    return results[:50]  # 限制返回结果数量

def get_total_count() -> int:
    """获取物品总数"""
    return len(ITEM_NAME_MAPPING)

# 模块信息
__version__ = "5.0"
__count__ = len(ITEM_NAME_MAPPING)
