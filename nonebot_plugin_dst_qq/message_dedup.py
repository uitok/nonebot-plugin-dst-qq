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
    print(f"🔧 设置用户 {user_id} 图片模式: {enabled}")
    print(f"🔧 设置前图片模式用户列表: {_user_image_modes}")
    
    if enabled:
        _user_image_modes.add(user_id)
        print(f"✅ 用户 {user_id} 启用图片模式")
    else:
        _user_image_modes.discard(user_id)
        print(f"✅ 用户 {user_id} 禁用图片模式")
    
    print(f"🔧 设置后图片模式用户列表: {_user_image_modes}")

async def send_with_dedup(bot, event, message):
    """
    带去重功能的消息发送函数，支持图片模式输出
    
    Args:
        bot: Bot实例
        event: 事件对象
        message: 消息内容
    """
    # 统一获取用户ID的方式
    try:
        user_id = str(event.get_user_id())
    except:
        user_id = str(getattr(event, 'user_id', 'unknown'))
    
    print(f"🔍 检查用户 {user_id} 的图片模式设置...")
    
    if _dedup_instance.should_send(user_id, str(message)):
        # 简化的图片模式检查 - 使用全局字典
        try:
            # 检查用户是否设置了图片模式
            print(f"🔍 当前图片模式用户列表: {_user_image_modes}")
            if user_id in _user_image_modes:
                print(f"🔍 用户 {user_id} 图片模式已激活")
                
                # 检查是否需要转换为图片 - 排除已经是图片消息的情况
                is_already_image = False
                if hasattr(message, 'type') and message.type == 'image':
                    is_already_image = True
                elif isinstance(message, str) and (message.startswith("base64://") or message.startswith("[CQ:image")):
                    is_already_image = True
                
                if isinstance(message, str) and not is_already_image:
                    try:
                        from .text_to_image import convert_text_to_image_async
                        print(f"📸 转换文字为图片: {message[:50]}...")
                        image_message = await convert_text_to_image_async(message)
                        
                        # 检查转换结果 - 如果返回的是原文本或非base64，说明转换失败或图片太大
                        if image_message == message or not (isinstance(image_message, str) and image_message.startswith("base64://")):
                            print(f"🔄 图片转换未成功，直接发送文本消息")
                            try:
                                result = await bot.send(event, message)
                                print(f"✅ 文本消息发送成功: {result}")
                            except Exception as text_error:
                                print(f"❌ 文本消息发送失败: {text_error}")
                            return
                        
                        print(f"✅ 图片转换成功，发送图片消息")
                        try:
                            # 创建图片消息段
                            from nonebot.adapters.onebot.v11 import MessageSegment
                            image_msg = MessageSegment.image(image_message)
                            print(f"📤 发送MessageSegment图片消息")
                            result = await bot.send(event, image_msg)
                            print(f"✅ 图片消息发送成功: {result}")
                            return
                        except Exception as send_error:
                            print(f"❌ 图片消息发送失败: {send_error}")
                            print(f"🔍 图片消息类型: {type(image_message)}")
                            print(f"🔍 图片消息内容前缀: {str(image_message)[:100]}...")
                            # 尝试发送原文本作为备选方案
                            print(f"🔄 尝试发送原文本...")
                            try:
                                result = await bot.send(event, message)
                                print(f"✅ 原文本发送成功: {result}")
                            except Exception as text_error:
                                print(f"❌ 原文本发送也失败: {text_error}")
                            return
                    except Exception as e:
                        print(f"⚠️ 文字转图片失败，使用原文本发送: {e}")
                        await bot.send(event, message)
                        return
            else:
                print(f"🔍 用户 {user_id} 文字模式")
            
            # 文字模式或转换失败，直接发送
            try:
                result = await bot.send(event, message)
                print(f"✅ 文字消息发送成功: {result}")
            except Exception as send_error:
                print(f"❌ 文字消息发送失败: {send_error}")
                raise
            
        except Exception as e:
            print(f"⚠️ 处理输出模式时出错: {e}")
            await bot.send(event, message)
    else:
        print(f"🔇 消息去重: 跳过重复消息发送给用户 {user_id}")