"""
调试命令模块
精简的调试功能，仅保留必要的测试命令
"""

from nonebot.adapters import Bot, Event
from nonebot_plugin_alconna import on_alconna
from arclet.alconna import Alconna
from nonebot import logger
from .message_utils import send_message, handle_command_errors
from .utils import require_admin

# 连接测试命令（管理员专用）
test_connection_cmd = on_alconna(
    Alconna("测试连接"),
    aliases={"test_connection", "连接测试"},
    priority=1,
    block=True
)

@test_connection_cmd.handle()
@require_admin
@handle_command_errors("测试连接")
async def handle_test_connection(bot: Bot, event: Event):
    """测试各服务连接状态（管理员专用）"""
    
    await send_message(bot, event, "🧪 开始测试系统连接...")
    
    results = []
    
    # 测试DMP连接
    try:
        from .config import get_config
        config = get_config()
        results.append(f"✅ 配置已加载: {config.dmp.base_url}")
    except Exception as e:
        results.append(f"❌ DMP连接测试异常: {e}")
    
    # 测试缓存系统
    try:
        from .simple_cache import get_cache
        cache = get_cache()
        await cache.get("test_key")
        results.append("✅ 缓存系统正常")
    except Exception as e:
        results.append(f"❌ 缓存系统异常: {e}")
    
    # 测试数据库
    try:
        from .database import chat_history_db
        await chat_history_db.get_recent_messages(1)
        results.append("✅ 数据库连接正常")
    except Exception as e:
        results.append(f"❌ 数据库连接异常: {e}")
    
    test_result = "🧪 系统连接测试结果:\n\n" + "\n".join(results)
    await send_message(bot, event, test_result)

# 简单调试信息命令（管理员专用）
debug_info_cmd = on_alconna(
    Alconna("调试信息"),
    aliases={"debug_info", "debug"},
    priority=1,
    block=True
)

@debug_info_cmd.handle()
@require_admin
@handle_command_errors("调试信息")
async def handle_debug_info(bot: Bot, event: Event):
    """显示调试信息（管理员专用）"""
    user_id = str(event.get_user_id())
    
    debug_msg = f"""🔍 系统调试信息

👤 用户ID: {user_id}
📱 事件类型: {type(event).__name__}
🤖 Bot类型: {type(bot).__name__}

🧪 调试命令:
• /测试连接 - 测试系统连接
• /调试信息 - 显示此信息

💡 其他调试功能请使用管理命令"""
    
    await send_message(bot, event, debug_msg)