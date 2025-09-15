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

# 旧版查房功能已完全迁移至 server_browser_commands.py
# 移除旧代码以简化项目结构

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

# 热门服务器功能已合并至 server_browser_commands.py

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