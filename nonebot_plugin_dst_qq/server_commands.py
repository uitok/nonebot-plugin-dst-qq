"""
DST服务器查房命令模块
提供饥荒联机版服务器查询功能
"""

from nonebot.adapters import Bot, Event
from nonebot_plugin_alconna import on_alconna, Match
from arclet.alconna import Alconna, Args, Option
from nonebot import logger
from nonebot_plugin_waiter import waiter

from .server_browser import dst_browser
from .message_utils import send_message, handle_command_errors
from .utils import require_admin

# 查房命令
server_list_cmd = on_alconna(
    Alconna("查房", Args["keyword?", str]),
    aliases={"服务器列表", "server_list", "查服务器"},
    priority=2,
    block=True
)

@server_list_cmd.handle()
@handle_command_errors("查房")
async def handle_server_list(bot: Bot, event: Event, keyword: Match[str]):
    """处理查房命令"""
    search_keyword = keyword.result if keyword.available else ""
    user_id = str(event.get_user_id())
    
    # 发送查询提示
    await send_message(bot, event, "🔍 正在查询DST服务器列表...")
    
    try:
        # 搜索服务器
        result = await dst_browser.search_servers(
            keyword=search_keyword,
            region="ap-east-1",  # 默认亚太区
            platform="steam",   # 默认Steam平台
            max_results=15      # 增加结果数量用于选择
        )
        
        if result.success and result.data:
            servers = result.data
            
            # 如果只有1个服务器，直接显示详细信息
            if len(servers) == 1:
                formatted_text = dst_browser.format_server_info(servers[0])
                formatted_text = f"🏠 找到1个服务器{f' (搜索: {search_keyword})' if search_keyword else ''}\\n\\n" + formatted_text
                await send_message(bot, event, formatted_text)
                return
            
            # 多个服务器时显示选择列表
            list_text = f"🔍 找到 {len(servers)} 个服务器" + (f" (搜索: {search_keyword})" if search_keyword else "") + "\\n\\n"
            
            for i, server in enumerate(servers, 1):
                name = server.get("name", "未知服务器")
                connected = server.get("connected", 0)
                max_conn = server.get("max_connections", 0)
                password = "🔒" if server.get("password", False) else "🔓"
                list_text += f"{i}. {name} ({connected}/{max_conn}) {password}\\n"
            
            list_text += "\\n💡 回复序号查看详细信息 (如: 1)"
            await send_message(bot, event, list_text)
            
            # 等待用户选择
            @waiter(waits=["message"], keep_session=True)
            async def wait_for_choice(waiter_event: Event):
                if str(waiter_event.get_user_id()) != user_id:
                    return False
                
                message_text = str(waiter_event.get_message()).strip()
                if message_text.isdigit():
                    choice = int(message_text)
                    if 1 <= choice <= len(servers):
                        return choice
                return False
            
            try:
                choice = await wait_for_choice.wait(timeout=30)
                if choice:
                    selected_server = servers[choice - 1]
                    detailed_info = dst_browser.format_server_info(selected_server)
                    detailed_info = f"🏠 服务器详情 #{choice}\\n\\n" + detailed_info
                    
                    # 添加连接信息
                    host = selected_server.get("host", "")
                    port = selected_server.get("port", 0)
                    if host and port:
                        detailed_info += f"\\n\\n🌐 连接地址: {host}:{port}"
                    
                    await send_message(bot, event, detailed_info)
                else:
                    await send_message(bot, event, "⏰ 选择超时，请重新查询")
            except Exception as e:
                logger.error(f"等待用户选择时出错: {e}")
                await send_message(bot, event, "⏰ 选择超时，请重新查询")
                
        else:
            error_msg = result.message if result.message else "查询失败"
            await send_message(bot, event, f"❌ {error_msg}")
            
    except Exception as e:
        logger.error(f"查房命令执行失败: {e}")
        await send_message(bot, event, f"❌ 查房失败: {str(e)}")

# 区域服务器列表命令
region_servers_cmd = on_alconna(
    Alconna("区域服务器", Args["region?", str]),
    aliases={"region_servers", "查询区域"},
    priority=2,
    block=True
)

@region_servers_cmd.handle()
@handle_command_errors("区域服务器查询")
async def handle_region_servers(bot: Bot, event: Event, region: Match[str]):
    """处理区域服务器查询命令"""
    
    # 区域映射
    region_map = {
        "美东": "us-east-1",
        "美国": "us-east-1", 
        "欧洲": "eu-central-1",
        "亚太": "ap-east-1",
        "新加坡": "ap-southeast-1",
        "中国": "cn-north-1",
        "国服": "cn-north-1"
    }
    
    if region.available:
        region_name = region.result
        region_code = region_map.get(region_name, region_name)
        
        await send_message(bot, event, f"🔍 正在查询 {region_name} 区域服务器...")
        
        try:
            result = await dst_browser.search_servers(
                region=region_code,
                max_results=10
            )
            
            if result.success and result.data:
                formatted_text = dst_browser.format_server_list(result.data)
                await send_message(bot, event, formatted_text)
            else:
                await send_message(bot, event, f"❌ 未找到 {region_name} 区域的服务器")
                
        except Exception as e:
            logger.error(f"区域服务器查询失败: {e}")
            await send_message(bot, event, f"❌ 查询失败: {str(e)}")
    else:
        # 显示区域概况
        await send_message(bot, event, "🌍 正在获取各区域服务器概况...")
        
        try:
            result = await dst_browser.get_region_summary()
            
            if result.success and result.data:
                summary_text = "🌍 各区域服务器概况\n\n"
                for region_name, info in result.data.items():
                    total = info.get('total', 0)
                    summary_text += f"📍 {region_name}: {total} 个服务器\n"
                
                summary_text += "\n💡 使用 /区域服务器 <区域名> 查看具体服务器"
                summary_text += "\n支持的区域: 美东、欧洲、亚太、新加坡、中国"
                
                await send_message(bot, event, summary_text)
            else:
                await send_message(bot, event, "❌ 获取区域概况失败")
                
        except Exception as e:
            logger.error(f"获取区域概况失败: {e}")
            await send_message(bot, event, f"❌ 获取失败: {str(e)}")

# 热门服务器命令
popular_servers_cmd = on_alconna(
    Alconna("热门服务器"),
    aliases={"popular_servers", "热门房间"},
    priority=2,
    block=True
)

@popular_servers_cmd.handle()
@handle_command_errors("热门服务器查询")
async def handle_popular_servers(bot: Bot, event: Event):
    """处理热门服务器查询命令"""
    
    await send_message(bot, event, "🔥 正在查询热门服务器...")
    
    try:
        # 获取亚太区服务器
        result = await dst_browser.search_servers(
            region="ap-east-1",
            max_results=20  # 获取更多服务器用于筛选
        )
        
        if result.success and result.data:
            # 按在线人数排序，取前8个
            servers = result.data
            popular_servers = sorted(
                servers,
                key=lambda x: x.get('connected', 0),
                reverse=True
            )[:8]
            
            if popular_servers:
                formatted_text = dst_browser.format_server_list(popular_servers)
                formatted_text = "🔥 " + formatted_text.replace("🔍 找到", "热门服务器", 1)
                await send_message(bot, event, formatted_text)
            else:
                await send_message(bot, event, "❌ 未找到热门服务器")
        else:
            await send_message(bot, event, "❌ 获取热门服务器失败")
            
    except Exception as e:
        logger.error(f"热门服务器查询失败: {e}")
        await send_message(bot, event, f"❌ 查询失败: {str(e)}")

# 服务器详情命令（管理员专用）
server_detail_cmd = on_alconna(
    Alconna("服务器详情", Args["server_id", str]),
    aliases={"server_detail", "房间详情"},
    priority=2,
    block=True
)

@server_detail_cmd.handle()
@require_admin
@handle_command_errors("服务器详情查询")
async def handle_server_detail(bot: Bot, event: Event, server_id: Match[str]):
    """处理服务器详情查询命令（管理员专用）"""
    
    if not server_id.available:
        await send_message(bot, event, "❌ 请指定服务器ID\n使用格式: /服务器详情 <服务器ID>")
        return
    
    rowid = server_id.result
    await send_message(bot, event, f"🔍 正在查询服务器详情: {rowid}")
    
    try:
        result = await dst_browser.get_server_details(rowid)
        
        if result.success:
            await send_message(bot, event, "✅ 服务器详情查询功能开发中...")
        else:
            await send_message(bot, event, f"❌ {result.message}")
            
    except Exception as e:
        logger.error(f"服务器详情查询失败: {e}")
        await send_message(bot, event, f"❌ 查询失败: {str(e)}")

# 查房帮助命令
server_help_cmd = on_alconna(
    Alconna("查房帮助"),
    aliases={"server_help", "服务器帮助"},
    priority=2,
    block=True
)

@server_help_cmd.handle()
@handle_command_errors("查房帮助")
async def handle_server_help(bot: Bot, event: Event):
    """处理查房帮助命令"""
    
    help_text = """🏠 DST服务器查房功能帮助

🔍 基础查询:
• /查房 - 查看所有服务器
• /查房 关键词 - 搜索包含关键词的服务器
• /热门服务器 - 查看人数最多的服务器

🌍 区域查询:
• /区域服务器 - 查看各区域概况
• /区域服务器 亚太 - 查看亚太区服务器
• /区域服务器 美东 - 查看美东区服务器
• /区域服务器 欧洲 - 查看欧洲区服务器

📊 服务器信息说明:
• 👥 在线人数/最大人数
• 🎮 游戏模式 (生存/无尽/荒野)
• 🔑 🔒=需密码 🔓=无密码
• 🛠️ 🔧=有MOD ⚡=原版
• ⚔️ ⚔️=PVP 🕊️=非PVP

💡 使用技巧:
• 搜索关键词可以是服务器名称或描述
• 支持中英文搜索
• 数据来源于Klei官方服务器列表

⚠️ 注意事项:
• 服务器信息每5分钟更新一次
• 部分私人服务器可能不会显示
• 连接服务器需要在游戏内操作"""

    await send_message(bot, event, help_text)