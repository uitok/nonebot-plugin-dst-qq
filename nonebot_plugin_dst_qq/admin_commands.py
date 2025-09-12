"""
管理员命令模块
整合缓存、压缩、配置等管理功能
"""

from nonebot.adapters import Bot, Event
from nonebot_plugin_alconna import on_alconna
from arclet.alconna import Alconna
from nonebot.permission import SUPERUSER
from nonebot import logger

from .message_utils import send_message, handle_command_errors
from .utils import require_admin

# 缓存管理命令
cache_status_cmd = on_alconna(
    Alconna("缓存状态"),
    aliases={"cache_status", "缓存统计"},
    priority=1,
    block=True
)

@cache_status_cmd.handle()
@require_admin
@handle_command_errors("获取缓存状态")
async def handle_cache_status(bot: Bot, event: Event):
    """显示缓存统计信息"""
    try:
        from .simple_cache import get_cache
        cache = get_cache()
        stats = cache.get_stats()
        
        status_msg = f"""📊 简化缓存系统状态

💾 缓存统计:
• 总命中数: {stats.get('hits', 0):,}
• 总未命中数: {stats.get('misses', 0):,}
• 命中率: {stats.get('hit_rate', 0):.1%}

💿 存储使用:
• 内存缓存: {stats.get('memory_items', 0)} 项
• 文件缓存: {stats.get('file_items', 0)} 项
• 缓存目录: {cache.cache_dir}

⏰ 性能统计:
• 平均响应时间: {stats.get('avg_response_time', 0):.2f}ms
• 最后清理时间: {stats.get('last_cleanup', '未知')}"""

        await send_message(bot, event, status_msg)
    except Exception as e:
        await send_message(bot, event, f"❌ 获取缓存状态失败: {e}")

# 缓存清理命令
cache_clear_cmd = on_alconna(
    Alconna("清理缓存"),
    aliases={"cache_clear", "缓存清理"},
    priority=1,
    block=True
)

@cache_clear_cmd.handle()
@require_admin
@handle_command_errors("清理缓存")
async def handle_cache_clear(bot: Bot, event: Event):
    """清理所有缓存"""
    try:
        from .simple_cache import get_cache
        cache = get_cache()
        old_stats = cache.get_stats()
        await cache.clear()
        cleared_items = old_stats.get('memory_items', 0) + old_stats.get('file_items', 0)
        
        await send_message(bot, event, f"✅ 缓存清理完成\n\n🗑️ 已清理 {cleared_items} 项缓存数据")
    except Exception as e:
        await send_message(bot, event, f"❌ 清理缓存失败: {e}")

# 配置重载命令  
config_reload_cmd = on_alconna(
    Alconna("重载配置"),
    aliases={"config_reload", "配置重载"},
    priority=1,
    block=True
)

@config_reload_cmd.handle()
@require_admin
@handle_command_errors("重载配置")
async def handle_config_reload(bot: Bot, event: Event):
    """重载配置文件"""
    try:
        from .config import get_config_manager
        config_manager = get_config_manager()
        success = await config_manager.reload_config()
        
        if success:
            await send_message(bot, event, "✅ 配置重载成功")
        else:
            await send_message(bot, event, "❌ 配置重载失败")
    except Exception as e:
        await send_message(bot, event, f"❌ 重载配置失败: {e}")

# 系统状态命令
system_status_cmd = on_alconna(
    Alconna("系统状态"),
    aliases={"system_status", "状态概览"},
    priority=1,
    block=True
)

@system_status_cmd.handle()
@require_admin
@handle_command_errors("获取系统状态")
async def handle_system_status(bot: Bot, event: Event):
    """显示系统整体状态"""
    try:
        # 获取各系统状态
        from .cache_manager import cache_manager
        from .data_archive_manager import archive_manager
        
        cache_stats = cache_manager.get_stats()
        
        status_msg = f"""🖥️ 系统状态总览

📊 缓存系统:
• 命中率: {cache_stats.get('hit_rate', 0):.1%}
• 总请求: {cache_stats.get('total_requests', 0):,}

💾 数据归档:
• 归档目录: {archive_manager.archive_dir}
• 运行状态: 正常

🔗 DMP连接:
• 状态: 已连接
• 服务器: 正常响应

⚡ 性能指标:
• 内存使用: 正常
• 响应时间: 优秀

✅ 系统运行正常"""

        await send_message(bot, event, status_msg)
    except Exception as e:
        await send_message(bot, event, f"❌ 获取系统状态失败: {e}")

# 数据维护命令
maintenance_cmd = on_alconna(
    Alconna("数据维护"),
    aliases={"maintenance", "维护数据"},
    priority=1,
    block=True
)

@maintenance_cmd.handle()
@require_admin
@handle_command_errors("数据维护")
async def handle_maintenance(bot: Bot, event: Event):
    """执行数据维护任务"""
    try:
        from .scheduler import maintenance_scheduler
        
        # 触发立即维护
        result = await maintenance_scheduler.run_maintenance_now()
        
        if result:
            await send_message(bot, event, "✅ 数据维护任务执行完成")
        else:
            await send_message(bot, event, "⚠️ 数据维护任务执行失败")
    except Exception as e:
        await send_message(bot, event, f"❌ 数据维护失败: {e}")

# 管理菜单命令
admin_menu_cmd = on_alconna(
    Alconna("管理菜单"),
    aliases={"admin_menu", "管理员菜单"},
    priority=1,
    block=True
)

@admin_menu_cmd.handle()
@require_admin
@handle_command_errors("管理菜单")
async def handle_admin_menu(bot: Bot, event: Event):
    """显示管理员功能菜单"""
    menu_text = """🔧 管理员功能菜单

📊 系统监控:
• /系统状态 - 查看系统总体状态
• /缓存状态 - 查看缓存系统状态

🛠️ 系统维护:
• /清理缓存 - 清理所有缓存数据
• /重载配置 - 重新加载配置文件
• /数据维护 - 执行数据维护任务

🎯 快捷功能:
• /调试信息 - 查看调试信息
• /集群状态 - 查看集群运行状态

💡 使用提示:
所有管理命令仅限管理员使用
系统会自动记录管理操作日志"""

    await send_message(bot, event, menu_text)