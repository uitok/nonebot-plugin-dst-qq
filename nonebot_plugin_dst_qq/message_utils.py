"""
通用消息发送工具模块
提供统一的消息发送、错误处理等功能
"""

from typing import Optional, Any
from nonebot.adapters import Bot, Event
from nonebot import logger
import traceback
from functools import wraps

async def send_message(bot: Bot, event: Event, text: str):
    """统一的消息发送方法"""
    await bot.send(event, text)

async def send_error_message(bot: Bot, event: Event, error: Exception, operation: str):
    """统一的错误消息发送"""
    logger.error(f"{operation}失败: {error}")
    logger.debug(f"错误详情: {traceback.format_exc()}")
    error_msg = f"❌ {operation}失败: {str(error)}"
    await send_message(bot, event, error_msg)

async def send_success_message(bot: Bot, event: Event, message: str, operation: str = None):
    """统一的成功消息发送"""
    if operation:
        logger.info(f"✅ {operation}成功")
    success_msg = f"✅ {message}"
    await send_message(bot, event, success_msg)

async def send_warning_message(bot: Bot, event: Event, message: str, operation: str = None):
    """统一的警告消息发送"""
    if operation:
        logger.warning(f"⚠️ {operation}: {message}")
    warning_msg = f"⚠️ {message}"
    await send_message(bot, event, warning_msg)

def handle_command_errors(operation_name: str):
    """命令错误处理装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(bot: Bot, event: Event, *args, **kwargs):
            try:
                return await func(bot, event, *args, **kwargs)
            except Exception as e:
                await send_error_message(bot, event, e, operation_name)
                logger.error(f"命令处理异常 - {operation_name}: {traceback.format_exc()}")
        return wrapper
    return decorator

async def safe_api_call(bot: Bot, event: Event, api_func, error_message: str, *args, **kwargs) -> Optional[Any]:
    """安全的API调用封装"""
    try:
        result = await api_func(*args, **kwargs)
        if hasattr(result, 'success') and result.success:
            return result
        elif hasattr(result, 'success'):
            await send_error_message(bot, event, Exception(result.message or "未知错误"), error_message)
            return None
        else:
            return result
    except Exception as e:
        await send_error_message(bot, event, e, error_message)
        return None

async def ensure_cluster_available(bot: Bot, event: Event, dmp_api) -> Optional[str]:
    """确保集群可用的通用函数"""
    try:
        cluster_name = await dmp_api.get_current_cluster()
        if not cluster_name:
            await send_error_message(bot, event, Exception("无法获取可用集群列表，请检查DMP服务器连接"), "获取集群")
            return None
        return cluster_name
    except Exception as e:
        await send_error_message(bot, event, e, "获取集群")
        return None

async def validate_response_data(bot: Bot, event: Event, response, operation: str) -> bool:
    """验证API响应数据的通用函数"""
    if not response:
        await send_error_message(bot, event, Exception("响应为空"), operation)
        return False
    
    if hasattr(response, 'success'):
        if not response.success:
            await send_error_message(bot, event, Exception(response.message or "API调用失败"), operation)
            return False
        
        if not response.data:
            await send_warning_message(bot, event, f"{operation}返回空数据", operation)
            return False
    
    return True