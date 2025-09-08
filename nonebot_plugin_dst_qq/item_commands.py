"""
物品查询命令
提供饥荒物品Wiki查询功能
"""

from nonebot import on_command, logger
from nonebot.adapters.onebot.v11 import Bot, Event, MessageSegment
from nonebot.params import CommandArg
from nonebot.typing import T_State
from arclet.alconna import Alconna, Args
from nonebot_plugin_alconna import on_alconna, Match

from .database import item_wiki_manager
from .message_utils import send_message, handle_command_errors

# ========================================
# 物品查询命令
# ========================================

item_query_cmd = on_alconna(
    Alconna("物品", Args["keyword", str]),
    aliases={"查物品", "item", "wiki", "查询物品"},
    priority=5,
    block=True,
)

@item_query_cmd.handle()
@handle_command_errors("物品查询")
async def handle_item_query(bot: Bot, event: Event, keyword: Match[str]):
    """处理物品查询命令"""
    if not keyword.available:
        await send_message(bot, event, "请输入要查询的物品名称\n例如: 物品 大理石")
        return
    
    search_keyword = keyword.result.strip()
    
    if not search_keyword:
        await send_message(bot, event, "请输入要查询的物品名称")
        return
    
    # 发送搜索提示
    await send_message(bot, event, f"🔍 正在搜索物品: {search_keyword}")
    
    # 使用快速搜索物品
    items = item_wiki_manager.search_items_quick(search_keyword, limit=5)
    
    if not items:
        await send_message(bot, event, f"❌ 未找到相关物品: {search_keyword}")
        return
    
    # 如果只有一个结果，直接查询Wiki
    if len(items) == 1:
        item = items[0]
        await _send_wiki_result(bot, event, item)
    else:
        # 多个结果时，显示选择列表
        result_text = f"找到 {len(items)} 个相关物品:\n"
        for i, item in enumerate(items, 1):
            result_text += f"{i}. {item['chinese_name']} ({item['english_name']})\n"
        result_text += "\n请输入序号选择，或使用更精确的关键词搜索"
        
        await send_message(bot, event, result_text)


async def _send_wiki_result(bot: Bot, event: Event, item: dict):
    """发送Wiki查询结果"""
    try:
        chinese_name = item['chinese_name']
        english_name = item['english_name']
        
        # 发送查询提示
        await send_message(bot, event, f"📖 正在获取 {chinese_name} 的Wiki信息...")
        
        # 获取Wiki图片，增加详细日志
        logger.info(f"开始获取Wiki图片: {chinese_name} ({english_name})")
        image_bytes = await item_wiki_manager.get_item_wiki_image(chinese_name)
        logger.info(f"Wiki图片获取结果: {len(image_bytes) if image_bytes else 0} bytes")
        
        if image_bytes:
            # 发送Wiki截图
            await bot.send(event, MessageSegment.image(image_bytes))
        else:
            # 如果截图失败，发送文本信息
            fallback_text = f"📖 {chinese_name} ({english_name})\n\n❌ Wiki截图获取失败\n" \
                          f"你可以访问: https://dontstarve.huijiwiki.com/wiki/{chinese_name}"
            
            await send_message(bot, event, fallback_text)
    
    except Exception as e:
        logger.error(f"发送Wiki结果失败: {e}")
        await send_message(bot, event, f"❌ 获取Wiki信息失败: {str(e)}")


# ========================================
# 物品搜索命令（仅搜索不查询Wiki）
# ========================================

item_search_cmd = on_alconna(
    Alconna("搜索物品", Args["keyword", str]),
    aliases={"search", "搜物品", "物品搜索"},
    priority=5,
    block=True,
)

@item_search_cmd.handle()
@handle_command_errors("物品搜索")
async def handle_item_search(bot: Bot, event: Event, keyword: Match[str]):
    """处理物品搜索命令（不查询Wiki）"""
    if not keyword.available:
        await send_message(bot, event, "请输入要搜索的物品名称\n例如: 搜索物品 石头")
        return
    
    search_keyword = keyword.result.strip()
    
    if not search_keyword:
        await send_message(bot, event, "请输入要搜索的物品名称")
        return
    
    # 使用快速搜索物品
    items = item_wiki_manager.search_items_quick(search_keyword, limit=20)
        
    if not items:
        await send_message(bot, event, f"❌ 未找到相关物品: {search_keyword}")
        return
    
    # 构建结果文本
    result_text = f"🔍 搜索结果 ({len(items)} 个):\n"
    for i, item in enumerate(items, 1):
        result_text += f"{i}. {item['chinese_name']} ({item['english_name']})\n"
    
    await send_message(bot, event, result_text)


# ========================================
# 处理数字选择（在物品列表中选择）
# ========================================

# 这里可以添加会话状态管理，但为了简单起见暂时省略
# 用户可以使用更精确的关键词来直接查询特定物品


# ========================================
# 物品数据管理命令（管理员专用）
# ========================================

from nonebot.permission import SUPERUSER

item_reload_cmd = on_alconna(
    Alconna("重载物品"),
    aliases={"reload_items", "刷新物品数据"},
    priority=5,
    block=True,
    permission=SUPERUSER,
)

@item_reload_cmd.handle()
@handle_command_errors("重载物品数据")
async def handle_item_reload(bot: Bot, event: Event):
    """处理物品数据重载命令（管理员专用）"""
    
    await send_message(bot, event, "🔄 正在重载物品数据...")
    
    success = await item_wiki_manager.reload_items_data()
    
    if success:
        await send_message(bot, event, "✅ 物品数据重载成功")
    else:
        await send_message(bot, event, "❌ 物品数据重载失败，请查看日志")


# ========================================
# 物品统计信息命令
# ========================================

item_stats_cmd = on_alconna(
    Alconna("物品统计"),
    aliases={"item_stats", "物品数量"},
    priority=5,
    block=True,
)

@item_stats_cmd.handle()
@handle_command_errors("物品统计")
async def handle_item_stats(bot: Bot, event: Event):
    """处理物品统计信息命令"""
    # 直接使用内置数据获取统计信息
    from .item_data import get_total_count, __version__
    total_items = get_total_count()
    
    result_text = f"📊 物品数据统计\n\n" \
                 f"• 总物品数量: {total_items}\n" \
                 f"• 数据版本: v{__version__}\n" \
                 f"• 数据来源: 内置物品数据库\n" \
                 f"• 支持中英文搜索\n" \
                 f"• 支持Wiki截图查询"
    
    await send_message(bot, event, result_text)