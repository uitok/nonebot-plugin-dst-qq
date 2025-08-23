"""
通用工具函数模块

提供插件中常用的工具函数，包括权限检查、数据处理等功能。
"""

from typing import Union
from nonebot.adapters import Bot, Event
from nonebot.adapters.onebot.v11 import Bot as OneBotV11, PrivateMessageEvent, GroupMessageEvent

from .config import get_config


async def is_superuser(bot: Bot, event: Event) -> bool:
    """
    检查用户是否为超级用户
    
    Args:
        bot: Bot实例
        event: 事件对象
        
    Returns:
        bool: 是否为超级用户
    """
    try:
        # 获取配置
        config = get_config()
        
        # 获取用户ID
        user_id = str(event.get_user_id())
        
        # 检查是否在超级用户列表中
        return user_id in config.bot.superusers
        
    except Exception:
        # 如果出现任何错误，返回False以确保安全
        return False


async def is_admin_group(event: Event) -> bool:
    """
    检查群组是否为管理员群组
    
    Args:
        event: 事件对象
        
    Returns:
        bool: 是否为管理员群组
    """
    try:
        # 只对群消息事件有效
        if not isinstance(event, GroupMessageEvent):
            return False
            
        config = get_config()
        group_id = str(event.group_id)
        
        # 如果没有设置管理员群组，则所有群组都不是管理员群组
        if not config.bot.admin_groups:
            return False
            
        return group_id in config.bot.admin_groups
        
    except Exception:
        return False


async def is_allowed_group(event: Event) -> bool:
    """
    检查群组是否被允许使用
    
    Args:
        event: 事件对象
        
    Returns:
        bool: 是否允许使用
    """
    try:
        # 私聊消息总是允许（如果启用了私聊功能）
        if isinstance(event, PrivateMessageEvent):
            config = get_config()
            return config.bot.enable_private_chat
            
        # 群消息检查
        if isinstance(event, GroupMessageEvent):
            config = get_config()
            
            # 如果禁用了群聊功能，直接返回False
            if not config.bot.enable_group_chat:
                return False
                
            # 如果没有设置允许的群组列表，则所有群组都允许
            if not config.bot.allowed_groups:
                return True
                
            group_id = str(event.group_id)
            return group_id in config.bot.allowed_groups
            
        return False
        
    except Exception:
        return False


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
