"""
消息去重模块
防止因网络问题导致的消息重复发送
"""

import hashlib
import time
from functools import wraps
from typing import Dict

from nonebot import logger

class MessageDedup:
    """消息去重器"""
    
    def __init__(self, window_seconds: int = 10):
        """初始化去重器"""
        self.window_seconds = window_seconds
        self.sent_messages: Dict[str, float] = {}  # 消息哈希 -> 发送时间
    
    def _get_message_hash(self, user_id: str, content: str) -> str:
        """生成消息哈希"""
        message_key = f"{user_id}:{content}"
        return hashlib.md5(message_key.encode()).hexdigest()
    
    def _cleanup_old_messages(self):
        """清理过期的消息记录"""
        current_time = time.time()
        expired_keys = [
            key for key, timestamp in self.sent_messages.items()
            if current_time - timestamp > self.window_seconds
        ]
        for key in expired_keys:
            del self.sent_messages[key]
    
    def should_send(self, user_id: str, content: str) -> bool:
        """检查是否应该发送消息（去重检查）"""
        self._cleanup_old_messages()
        
        message_hash = self._get_message_hash(user_id, content)
        current_time = time.time()
        
        # 检查是否在去重窗口内发送过相同消息
        if message_hash in self.sent_messages:
            time_diff = current_time - self.sent_messages[message_hash]
            if time_diff < self.window_seconds:
                return False  # 重复消息，不发送
        
        # 记录消息发送时间
        self.sent_messages[message_hash] = current_time
        return True

# 全局去重器实例
_dedup_instance = MessageDedup(window_seconds=10)

# 用户图片模式设置 - 存储启用图片模式的用户ID
_user_image_modes = set()

def add_user_image_mode(user_id: str):
    """为用户启用图片模式"""
    _user_image_modes.add(str(user_id))
    logger.info(f"用户 {user_id} 已启用图片模式")

def remove_user_image_mode(user_id: str):
    """为用户禁用图片模式"""
    _user_image_modes.discard(str(user_id))
    logger.info(f"用户 {user_id} 已禁用图片模式")

def is_user_image_mode(user_id: str) -> bool:
    """检查用户是否启用了图片模式"""
    return str(user_id) in _user_image_modes

def get_image_mode_users() -> set:
    """获取所有启用图片模式的用户"""
    return _user_image_modes.copy()

def dedup_message(func):
    """消息去重装饰器"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # 尝试从参数中提取 bot, event, message
        bot = None
        event = None
        message = None
        
        # 从位置参数中提取
        if len(args) >= 2:
            bot = args[0]
            event = args[1]
        if len(args) >= 3:
            message = args[2]
        
        # 从关键字参数中提取
        if not bot:
            bot = kwargs.get('bot')
        if not event:
            event = kwargs.get('event')
        if not message:
            message = kwargs.get('message')
        
        # 如果无法提取必要参数，直接执行原函数
        if not bot or not event or not message:
            return await func(*args, **kwargs)
        
        # 获取用户ID
        user_id = getattr(event, 'user_id', str(getattr(event, 'get_user_id', lambda: 'unknown')()))
        
        # 检查是否应该发送
        if _dedup_instance.should_send(user_id, str(message)):
            return await func(*args, **kwargs)
        else:
            # 重复消息，跳过发送
            logger.debug(f"消息去重: 跳过重复消息发送给用户 {user_id}")
            return
    
    return wrapper

async def send_with_dedup(bot, event, message):
    """带去重功能的消息发送函数"""
    # 统一获取用户ID的方式
    try:
        user_id = str(event.get_user_id())
    except:
        user_id = str(getattr(event, 'user_id', 'unknown'))
    
    # 检查去重
    if not _dedup_instance.should_send(user_id, str(message)):
        logger.debug(f"消息去重: 跳过重复消息发送给用户 {user_id}")
        return
    
    # 发送消息
    try:
        result = await bot.send(event, message)
        logger.success(f"消息发送成功: {result}")
    except Exception as send_error:
        logger.error(f"消息发送失败: {send_error}")
        raise
