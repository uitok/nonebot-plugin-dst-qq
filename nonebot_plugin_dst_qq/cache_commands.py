"""
缓存管理命令模块

提供缓存的查看、清理等管理功能
"""

from nonebot import on_command
from nonebot.rule import to_me
from nonebot.adapters import Event
from nonebot.adapters.onebot.v11 import MessageSegment
from nonebot.permission import SUPERUSER
from nonebot.log import logger
from .cache_manager import cache_manager

# 缓存状态查看
cache_status = on_command(
    "缓存状态", 
    rule=to_me(), 
    permission=SUPERUSER,
    priority=1,
    block=True
)

@cache_status.handle()
async def handle_cache_status():
    """显示缓存统计信息"""
    try:
        stats = cache_manager.get_stats()
        
        message = f"""🗄️ 缓存系统状态

📊 统计信息:
• 总请求数: {stats['total_requests']}
• 内存命中: {stats['memory_hits']} ({stats['memory_hit_rate']:.1%})
• 文件命中: {stats['file_hits']} ({stats['file_hit_rate']:.1%})
• 未命中: {stats['misses']}
• 总命中率: {stats['hit_rate']:.1%}

🧠 内存缓存:
• 当前大小: {stats['memory_cache_size']} 项
• 活跃键数: {len(stats['memory_cache_keys'])}

💡 使用命令:
• @我 清空缓存 - 清空所有缓存
• @我 清空API缓存 - 只清空API缓存
• @我 清空数据缓存 - 只清空数据库缓存"""

        await cache_status.finish(message)
        
    except Exception as e:
        logger.error(f"获取缓存状态失败: {e}")
        await cache_status.finish("❌ 获取缓存状态失败，请查看日志")


# 清空所有缓存
clear_all_cache = on_command(
    "清空缓存", 
    rule=to_me(), 
    permission=SUPERUSER,
    priority=1,
    block=True
)

@clear_all_cache.handle()
async def handle_clear_all_cache():
    """清空所有缓存"""
    try:
        await cache_manager.clear()
        await clear_all_cache.finish("✅ 所有缓存已清空")
        
    except Exception as e:
        logger.error(f"清空缓存失败: {e}")
        await clear_all_cache.finish("❌ 清空缓存失败，请查看日志")


# 清空API缓存
clear_api_cache = on_command(
    "清空API缓存", 
    rule=to_me(), 
    permission=SUPERUSER,
    priority=1,
    block=True
)

@clear_api_cache.handle()
async def handle_clear_api_cache():
    """清空API缓存"""
    try:
        await cache_manager.clear("api")
        await clear_api_cache.finish("✅ API缓存已清空")
        
    except Exception as e:
        logger.error(f"清空API缓存失败: {e}")
        await clear_api_cache.finish("❌ 清空API缓存失败，请查看日志")


# 清空数据缓存
clear_db_cache = on_command(
    "清空数据缓存", 
    rule=to_me(), 
    permission=SUPERUSER,
    priority=1,
    block=True
)

@clear_db_cache.handle()
async def handle_clear_db_cache():
    """清空数据库缓存"""
    try:
        await cache_manager.clear("db")
        await clear_db_cache.finish("✅ 数据库缓存已清空")
        
    except Exception as e:
        logger.error(f"清空数据库缓存失败: {e}")
        await clear_db_cache.finish("❌ 清空数据库缓存失败，请查看日志")


# 清空配置缓存
clear_config_cache = on_command(
    "清空配置缓存", 
    rule=to_me(), 
    permission=SUPERUSER,
    priority=1,
    block=True
)

@clear_config_cache.handle()
async def handle_clear_config_cache():
    """清空配置缓存"""
    try:
        await cache_manager.clear("config")
        await clear_config_cache.finish("✅ 配置缓存已清空")
        
    except Exception as e:
        logger.error(f"清空配置缓存失败: {e}")
        await clear_config_cache.finish("❌ 清空配置缓存失败，请查看日志")