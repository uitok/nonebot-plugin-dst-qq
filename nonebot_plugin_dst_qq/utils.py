"""
通用工具函数模块
简化版权限检查和数据处理工具
"""

from typing import Union
from functools import wraps
from nonebot import get_driver
from nonebot.adapters import Bot, Event
from nonebot.adapters.onebot.v11 import GroupMessageEvent, PrivateMessageEvent
from .config import get_config

async def is_admin(bot: Bot, event: Event) -> bool:
    """检查用户是否为管理员（超级用户或群管理员）"""
    try:
        user_id = str(event.get_user_id())
        
        # 检查超级用户
        driver = get_driver()
        if user_id in driver.config.superusers:
            return True
        
        # 检查群管理员
        if isinstance(event, GroupMessageEvent):
            try:
                config = get_config()
                group_id = str(event.group_id)
                if config.bot.admin_groups and group_id in config.bot.admin_groups:
                    return True
            except:
                pass
        
        return False
    except:
        return False

def require_admin(func):
    """管理员权限装饰器"""
    @wraps(func)
    async def wrapper(bot: Bot, event: Event, *args, **kwargs):
        if await is_admin(bot, event):
            return await func(bot, event, *args, **kwargs)
        else:
            await bot.send(event, "❌ 权限不足，仅管理员可使用此命令")
    return wrapper


def format_file_size(size_bytes: int) -> str:
    """
    格式化文件大小显示
    
    Args:
        size_bytes: 字节数
        
    Returns:
        str: 格式化后的大小字符串
    """
    if size_bytes == 0:
        return "0 B"
        
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
        
    return f"{size_bytes:.2f} {size_names[i]}"


def truncate_string(text: str, max_length: int = 100) -> str:
    """
    截断字符串到指定长度
    
    Args:
        text: 原始字符串
        max_length: 最大长度
        
    Returns:
        str: 截断后的字符串
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def safe_int(value: Union[str, int], default: int = 0) -> int:
    """
    安全地转换为整数
    
    Args:
        value: 要转换的值
        default: 默认值
        
    Returns:
        int: 转换后的整数
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_float(value: Union[str, float], default: float = 0.0) -> float:
    """
    安全地转换为浮点数
    
    Args:
        value: 要转换的值
        default: 默认值
        
    Returns:
        float: 转换后的浮点数
    """
    try:
        return float(value)
    except (ValueError, TypeError):
        return default
