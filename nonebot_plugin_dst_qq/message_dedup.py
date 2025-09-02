"""
消息去重模块
防止因网络问题导致的消息重复发送
"""

import time
from functools import wraps
from typing import Dict, Tuple
import hashlib


class MessageDedup:
    """消息去重器"""
    
    def __init__(self, window_seconds: int = 10):
        """
        初始化去重器
        
        Args:
            window_seconds: 去重窗口时间（秒）
        """
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
        """
        检查是否应该发送消息（去重检查）
        
        Args:
            user_id: 用户ID
            content: 消息内容
            
        Returns:
            True if should send, False if duplicate
        """
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


def dedup_message(func):
    """
    消息去重装饰器
    
    防止在短时间内发送相同的消息给同一用户
    """
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
            print(f"🔇 消息去重: 跳过重复消息发送给用户 {user_id}")
            return
    
    return wrapper


# 全局用户图片模式状态
_user_image_modes = set()

def set_user_image_mode(user_id: str, enabled: bool):
    """设置用户图片模式"""
    global _user_image_modes
    if enabled:
        _user_image_modes.add(user_id)
        print(f"✅ 用户 {user_id} 启用图片模式")
    else:
        _user_image_modes.discard(user_id)
        print(f"✅ 用户 {user_id} 禁用图片模式")

async def send_with_dedup(bot, event, message):
    """
    带去重功能的消息发送函数，支持图片模式输出
    
    Args:
        bot: Bot实例
        event: 事件对象
        message: 消息内容
    """
    user_id = getattr(event, 'user_id', str(getattr(event, 'get_user_id', lambda: 'unknown')()))
    
    if _dedup_instance.should_send(user_id, str(message)):
        # 简化的图片模式检查 - 使用全局字典
        try:
            # 检查用户是否设置了图片模式
            if user_id in _user_image_modes:
                print(f"🔍 用户 {user_id} 图片模式已激活")
                
                # 如果消息是纯文本，转换为图片
                if isinstance(message, str) and not message.startswith("base64://") and not message.startswith("[CQ:image"):
                    try:
                        from .text_to_image import convert_text_to_image
                        print(f"📸 转换文字为图片: {message[:50]}...")
                        image_message = convert_text_to_image(message)
                        print(f"✅ 图片转换成功，发送图片消息")
                        await bot.send(event, image_message)
                        return
                    except Exception as e:
                        print(f"⚠️ 文字转图片失败，使用原文本发送: {e}")
                        await bot.send(event, message)
                        return
            else:
                print(f"🔍 用户 {user_id} 文字模式")
            
            # 文字模式或转换失败，直接发送
            await bot.send(event, message)
            
        except Exception as e:
            print(f"⚠️ 处理输出模式时出错: {e}")
            await bot.send(event, message)
    else:
        print(f"🔇 消息去重: 跳过重复消息发送给用户 {user_id}")