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
from nonebot_plugin_waiter import waiter

from .database import item_wiki_manager
from .message_utils import send_message, handle_command_errors
from .wiki_screenshot import screenshot_wiki_item_separate

# ========================================
# 物品查询命令
# ========================================

item_query_cmd = on_alconna(
    Alconna("物品", Args["keyword", str]),
    aliases={"查物品", "item", "wiki", "查询物品", "查"},
    priority=5,
    block=True,
)

# 分离截图命令
item_separate_cmd = on_alconna(
    Alconna("物品分离", Args["keyword", str]),
    aliases={"分离物品", "物品详情", "详细物品"},
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
    
    # 使用快速搜索物品，获取更多结果用于分页
    all_items = item_wiki_manager.search_items_quick(search_keyword, limit=50)
    
    if not all_items:
        await send_message(bot, event, f"❌ 未找到相关物品: {search_keyword}")
        return
    
    # 如果只有一个结果，直接查询Wiki
    if len(all_items) == 1:
        item = all_items[0]
        await _send_wiki_result(bot, event, item)
    else:
        # 多个结果时，使用分页显示
        await _show_item_selection_with_pagination(bot, event, all_items, search_keyword)


async def _show_item_selection_with_pagination(bot: Bot, event: Event, all_items: list, search_keyword: str, page: int = 1, separate_mode: bool = False):
    """分页显示物品选择列表"""
    items_per_page = 10  # 每页显示10个物品
    total_items = len(all_items)
    total_pages = (total_items + items_per_page - 1) // items_per_page
    
    # 确保页码在有效范围内
    page = max(1, min(page, total_pages))
    
    # 计算当前页的物品范围
    start_idx = (page - 1) * items_per_page
    end_idx = min(start_idx + items_per_page, total_items)
    current_page_items = all_items[start_idx:end_idx]
    
    # 构建显示文本
    result_text = f"🔍 搜索结果: {search_keyword}\n"
    result_text += f"📊 找到 {total_items} 个相关物品 (第 {page}/{total_pages} 页)\n\n"
    
    # 显示当前页的物品
    for i, item in enumerate(current_page_items, 1):
        result_text += f"{i}. {item['chinese_name']} ({item['english_name']})\n"
    
    # 添加操作提示
    result_text += "\n🎯 操作选项:\n"
    if separate_mode:
        result_text += f"• 输入序号 1-{len(current_page_items)} 查看分离截图\n"
    else:
        result_text += f"• 输入序号 1-{len(current_page_items)} 查看物品Wiki\n"
    
    if page > 1:
        result_text += "• 输入 'p' 或 '上一页' 查看上一页\n"
    if page < total_pages:
        result_text += "• 输入 'n' 或 '下一页' 查看下一页\n"
    
    result_text += f"• 输入 'q' 或 '退出' 结束查询"
    
    await send_message(bot, event, result_text)
    
    # 等待用户输入
    @waiter(waits=["message"], keep_session=True)
    async def wait_for_pagination_input(waiter_event: Event):
        # 检查用户和会话
        if waiter_event.get_user_id() != event.get_user_id():
            return
        
        if hasattr(event, 'group_id') and hasattr(waiter_event, 'group_id'):
            if getattr(event, 'group_id', None) != getattr(waiter_event, 'group_id', None):
                return
        elif hasattr(event, 'group_id') != hasattr(waiter_event, 'group_id'):
            return
        
        message_text = str(waiter_event.get_message()).strip().lower()
        
        # 处理各种输入
        # 1. 查看上一页
        if message_text in ['p', '上一页', 'prev', 'previous'] and page > 1:
            return {'action': 'prev_page'}
        
        # 2. 查看下一页  
        elif message_text in ['n', '下一页', 'next'] and page < total_pages:
            return {'action': 'next_page'}
        
        # 3. 退出
        elif message_text in ['q', '退出', 'quit', 'exit']:
            return {'action': 'quit'}
        
        # 4. 数字选择
        else:
            try:
                selection = int(message_text)
                if 1 <= selection <= len(current_page_items):
                    return {'action': 'select', 'index': selection - 1}
                else:
                    await send_message(bot, waiter_event, f"❌ 请输入有效序号 (1-{len(current_page_items)})")
                    return None
            except ValueError:
                # 如果不是识别的命令，忽略
                return None
    
    try:
        # 等待用户输入，60秒超时
        user_input = await wait_for_pagination_input.wait(timeout=60)
        
        if user_input:
            action = user_input['action']
            
            if action == 'prev_page':
                # 上一页
                await _show_item_selection_with_pagination(bot, event, all_items, search_keyword, page - 1, separate_mode)
            
            elif action == 'next_page':
                # 下一页
                await _show_item_selection_with_pagination(bot, event, all_items, search_keyword, page + 1, separate_mode)
            
            elif action == 'quit':
                # 退出
                await send_message(bot, event, "👋 已退出物品查询")
            
            elif action == 'select':
                # 选择物品
                selected_item = current_page_items[user_input['index']]
                if separate_mode:
                    await _send_separate_wiki_result(bot, event, selected_item)
                else:
                    await _send_wiki_result(bot, event, selected_item)
        
        else:
            # 超时
            await send_message(bot, event, "⏰ 查询超时，已自动退出")
    
    except Exception as e:
        logger.error(f"分页处理时出错: {e}")
        await send_message(bot, event, "❌ 处理查询时出错，请重新查询")


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


@item_separate_cmd.handle()
@handle_command_errors("物品分离截图")
async def handle_item_separate_query(bot: Bot, event: Event, keyword: Match[str]):
    """处理物品分离截图命令"""
    if not keyword.available:
        await send_message(bot, event, "请输入要查询的物品名称\n例如: 物品分离 大理石")
        return
    
    search_keyword = keyword.result.strip()
    
    if not search_keyword:
        await send_message(bot, event, "请输入要查询的物品名称")
        return
    
    # 发送搜索提示
    await send_message(bot, event, f"🔍 正在搜索物品: {search_keyword}")
    
    # 快速搜索物品
    all_items = item_wiki_manager.search_items_quick(search_keyword, limit=50)
    
    if not all_items:
        await send_message(bot, event, f"❌ 未找到相关物品: {search_keyword}")
        return
    
    if len(all_items) == 1:
        # 如果只有一个结果，直接发送分离截图
        await _send_separate_wiki_result(bot, event, all_items[0])
    else:
        # 多个结果，显示分页选择（复用现有的分页功能）
        await _show_item_selection_with_pagination(bot, event, all_items, search_keyword, page=1, separate_mode=True)


async def _send_separate_wiki_result(bot: Bot, event: Event, item: dict):
    """发送分离的Wiki查询结果"""
    try:
        chinese_name = item['chinese_name']
        english_name = item['english_name']
        
        # 发送查询提示
        await send_message(bot, event, f"📖 正在获取 {chinese_name} 的详细Wiki信息...")
        
        # 获取分离截图
        logger.info(f"开始获取分离Wiki截图: {chinese_name} ({english_name})")
        screenshot_results = await screenshot_wiki_item_separate(chinese_name)
        
        # 发送信息栏截图
        if screenshot_results['infobox']:
            logger.info(f"发送信息栏截图: {len(screenshot_results['infobox'])} bytes")
            await bot.send(event, MessageSegment.text(f"📊 {chinese_name} - 信息栏"))
            await bot.send(event, MessageSegment.image(screenshot_results['infobox']))
        else:
            logger.warning("信息栏截图获取失败")
        
        # 发送正文内容截图
        if screenshot_results['content']:
            logger.info(f"发送正文截图: {len(screenshot_results['content'])} bytes")
            await bot.send(event, MessageSegment.text(f"📄 {chinese_name} - 正文内容"))
            await bot.send(event, MessageSegment.image(screenshot_results['content']))
        else:
            logger.warning("正文内容截图获取失败")
        
        # 如果都失败了，发送备用信息
        if not screenshot_results['infobox'] and not screenshot_results['content']:
            fallback_text = f"📖 {chinese_name} ({english_name})\n\n❌ Wiki截图获取失败\n" \
                          f"你可以访问: https://dontstarve.huijiwiki.com/wiki/{chinese_name}"
            await send_message(bot, event, fallback_text)
    
    except Exception as e:
        logger.error(f"发送分离Wiki结果失败: {e}")
        await send_message(bot, event, f"❌ 获取详细Wiki信息失败: {str(e)}")


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
    
    # 使用快速搜索物品（搜索命令显示更多结果）
    items = item_wiki_manager.search_items_quick(search_keyword, limit=50)
        
    if not items:
        await send_message(bot, event, f"❌ 未找到相关物品: {search_keyword}")
        return
    
    # 构建结果文本
    result_text = f"🔍 搜索结果 ({len(items)} 个):\n"
    for i, item in enumerate(items, 1):
        result_text += f"{i}. {item['chinese_name']} ({item['english_name']})\n"
    
    await send_message(bot, event, result_text)


# ========================================
# 处理数字选择功能已集成到上面的主查询命令中
# 使用 nonebot-plugin-waiter 实现会话状态管理
# ========================================


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