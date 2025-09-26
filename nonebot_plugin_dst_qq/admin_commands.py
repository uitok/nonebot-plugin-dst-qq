"""
管理员命令模块
整合缓存、压缩、配置等管理功能
"""

from typing import List

from nonebot.adapters import Bot, Event
from nonebot_plugin_alconna import on_alconna
from arclet.alconna import Alconna
from nonebot import logger

from .cluster_manager import get_cluster_manager
from .message_utils import send_message, handle_command_errors
from .server_browser import dst_browser
from .simple_cache import get_cache
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

# 缓存刷新命令
cache_refresh_cmd = on_alconna(
    Alconna("刷新缓存"),
    aliases={"cache_refresh", "刷新数据缓存"},
    priority=1,
    block=True
)

@cache_refresh_cmd.handle()
@require_admin
@handle_command_errors("刷新缓存")
async def handle_cache_refresh(bot: Bot, event: Event):
    """清空并预热关键缓存"""
    try:
        cache = get_cache()
        await cache.clear()

        warmed_items: List[str] = []

        # 预热服务器列表缓存
        try:
            response = await dst_browser.get_server_list()
            if response and response.success:
                data = response.data or {}
                server_count = len(data.get('GET', [])) if isinstance(data, dict) else 0
                warmed_items.append(f"服务器列表 {server_count} 条")
        except Exception as warm_error:
            logger.debug(f"预热服务器列表失败: {warm_error}")

        # 预热集群信息
        try:
            cluster_manager = get_cluster_manager()
            if cluster_manager:
                clusters = await cluster_manager.get_available_clusters(force_refresh=True)
                warmed_items.append(f"集群信息 {len(clusters)} 项")
        except Exception as warm_error:
            logger.debug(f"预热集群信息失败: {warm_error}")

        summary_lines = ["✅ 缓存刷新完成"]
        if warmed_items:
            summary_lines.append("🔥 已预热: " + "、".join(warmed_items))
        else:
            summary_lines.append("ℹ️ 无可预热的数据源")

        await send_message(bot, event, "\n".join(summary_lines))
    except Exception as e:
        await send_message(bot, event, f"❌ 刷新缓存失败: {e}")

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
    menu_text = """🔧 管理员缓存工具

┌────────────────────────┐
│        📦 缓存维护       │
├────────────────────────┤
│ /缓存状态   查看缓存统计 │
│ /清理缓存   清空所有缓存 │
│ /刷新缓存   清空并预热缓存 │
└────────────────────────┘

ℹ️ 数据压缩、归档以及定期维护任务已由系统自动执行。"""

    await send_message(bot, event, menu_text)
