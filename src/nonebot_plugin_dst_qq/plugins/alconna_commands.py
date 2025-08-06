"""
使用 Alconna 的命令处理器
提供更强大的命令解析功能
"""

from typing import Optional
from arclet.alconna import Alconna, Args, Field, Option, Subcommand
from arclet.alconna.typing import CommandMeta
from nonebot import require
from nonebot.plugin import on_alconna
from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import Depends
from nonebot.permission import SUPERUSER

from ..config import get_config
from .dmp_api import DMPAPI
from .dmp_advanced import DMPAdvanced
from .message_exchange import MessageExchange

# 获取配置
config = get_config()
dmp_api = DMPAPI()
dmp_advanced = DMPAdvanced()
message_exchange = MessageExchange()

# 基础查询命令
world_cmd = on_alconna(
    Alconna(
        "世界",
        Args["world_name?", str] = Field("Master", description="世界名称"),
        meta=CommandMeta(
            description="获取世界信息",
            usage="世界 [世界名称]",
            example="世界 Master"
        )
    ),
    aliases={"world", "worldinfo"},
    priority=5
)

room_cmd = on_alconna(
    Alconna(
        "房间",
        Args["world_name?", str] = Field("Master", description="世界名称"),
        meta=CommandMeta(
            description="获取房间信息",
            usage="房间 [世界名称]",
            example="房间 Master"
        )
    ),
    aliases={"room", "roominfo"},
    priority=5
)

system_cmd = on_alconna(
    Alconna(
        "系统",
        meta=CommandMeta(
            description="获取系统信息",
            usage="系统",
            example="系统"
        )
    ),
    aliases={"sys", "system"},
    priority=5
)

players_cmd = on_alconna(
    Alconna(
        "玩家",
        Args["world_name?", str] = Field("Master", description="世界名称"),
        meta=CommandMeta(
            description="获取在线玩家列表",
            usage="玩家 [世界名称]",
            example="玩家 Master"
        )
    ),
    aliases={"players", "playerlist"},
    priority=5
)

connection_cmd = on_alconna(
    Alconna(
        "直连",
        meta=CommandMeta(
            description="获取服务器直连信息",
            usage="直连",
            example="直连"
        )
    ),
    aliases={"connection", "connect"},
    priority=5
)

help_cmd = on_alconna(
    Alconna(
        "菜单",
        meta=CommandMeta(
            description="显示帮助信息",
            usage="菜单",
            example="菜单"
        )
    ),
    aliases={"help", "帮助"},
    priority=5
)

# 管理员命令
admin_cmd = on_alconna(
    Alconna(
        "管理命令",
        meta=CommandMeta(
            description="显示管理员功能菜单",
            usage="管理命令",
            example="管理命令"
        )
    ),
    aliases={"admin", "管理"},
    permission=SUPERUSER,
    priority=5
)

backup_cmd = on_alconna(
    Alconna(
        "查看备份",
        meta=CommandMeta(
            description="获取备份文件列表",
            usage="查看备份",
            example="查看备份"
        )
    ),
    aliases={"backup", "备份列表"},
    permission=SUPERUSER,
    priority=5
)

create_backup_cmd = on_alconna(
    Alconna(
        "创建备份",
        meta=CommandMeta(
            description="手动创建备份",
            usage="创建备份",
            example="创建备份"
        )
    ),
    aliases={"createbackup", "新建备份"},
    permission=SUPERUSER,
    priority=5
)

execute_cmd = on_alconna(
    Alconna(
        "执行",
        Args["world_name", str] = Field(..., description="世界名称"),
        Args["command", str] = Field(..., description="要执行的命令"),
        meta=CommandMeta(
            description="执行游戏命令",
            usage="执行 <世界名称> <命令>",
            example="执行 Master c_listallplayers()"
        )
    ),
    aliases={"execute", "cmd"},
    permission=SUPERUSER,
    priority=5
)

rollback_cmd = on_alconna(
    Alconna(
        "回档",
        Args["days", int] = Field(..., description="回档天数", ge=1, le=5),
        meta=CommandMeta(
            description="回档指定天数 (1-5天)",
            usage="回档 <天数>",
            example="回档 2"
        )
    ),
    aliases={"rollback", "回退"},
    permission=SUPERUSER,
    priority=5
)

reset_world_cmd = on_alconna(
    Alconna(
        "重置世界",
        Args["world_name?", str] = Field("Master", description="世界名称"),
        meta=CommandMeta(
            description="重置世界 (默认Master)",
            usage="重置世界 [世界名称]",
            example="重置世界 Master"
        )
    ),
    aliases={"resetworld", "重置"},
    permission=SUPERUSER,
    priority=5
)

chat_history_cmd = on_alconna(
    Alconna(
        "聊天历史",
        Args["world_name?", str] = Field("Master", description="世界名称"),
        Args["lines?", int] = Field(50, description="行数", ge=1, le=100),
        meta=CommandMeta(
            description="获取聊天历史",
            usage="聊天历史 [世界名称] [行数]",
            example="聊天历史 Master 20"
        )
    ),
    aliases={"chathistory", "聊天记录"},
    permission=SUPERUSER,
    priority=5
)

chat_stats_cmd = on_alconna(
    Alconna(
        "聊天统计",
        meta=CommandMeta(
            description="获取聊天历史统计信息",
            usage="聊天统计",
            example="聊天统计"
        )
    ),
    aliases={"chatstats", "聊天数据"},
    permission=SUPERUSER,
    priority=5
)

# 消息互通命令
message_exchange_cmd = on_alconna(
    Alconna(
        "消息互通",
        meta=CommandMeta(
            description="开启游戏内消息与QQ消息互通",
            usage="消息互通",
            example="消息互通"
        )
    ),
    aliases={"开启互通", "互通开启"},
    priority=5
)

close_exchange_cmd = on_alconna(
    Alconna(
        "关闭互通",
        meta=CommandMeta(
            description="关闭消息互通功能",
            usage="关闭互通",
            example="关闭互通"
        )
    ),
    aliases={"互通关闭", "停止互通"},
    priority=5
)

exchange_status_cmd = on_alconna(
    Alconna(
        "互通状态",
        meta=CommandMeta(
            description="查看当前互通状态",
            usage="互通状态",
            example="互通状态"
        )
    ),
    aliases={"status", "状态"},
    priority=5
)

latest_messages_cmd = on_alconna(
    Alconna(
        "最新消息",
        Args["count?", int] = Field(10, description="消息数量", ge=1, le=50),
        meta=CommandMeta(
            description="获取游戏内最新消息",
            usage="最新消息 [数量]",
            example="最新消息 5"
        )
    ),
    aliases={"latest", "最新"},
    priority=5
)

# 命令处理器
@world_cmd.handle()
async def handle_world(world_name: str = "Master"):
    """处理世界信息查询"""
    try:
        result = await dmp_api.get_world_info(world_name)
        await world_cmd.finish(result)
    except Exception as e:
        await world_cmd.finish(f"获取世界信息失败: {str(e)}")

@room_cmd.handle()
async def handle_room(world_name: str = "Master"):
    """处理房间信息查询"""
    try:
        result = await dmp_api.get_room_info(world_name)
        await room_cmd.finish(result)
    except Exception as e:
        await room_cmd.finish(f"获取房间信息失败: {str(e)}")

@system_cmd.handle()
async def handle_system():
    """处理系统信息查询"""
    try:
        result = await dmp_api.get_system_info()
        await system_cmd.finish(result)
    except Exception as e:
        await system_cmd.finish(f"获取系统信息失败: {str(e)}")

@players_cmd.handle()
async def handle_players(world_name: str = "Master"):
    """处理玩家列表查询"""
    try:
        result = await dmp_api.get_players(world_name)
        await players_cmd.finish(result)
    except Exception as e:
        await players_cmd.finish(f"获取玩家列表失败: {str(e)}")

@connection_cmd.handle()
async def handle_connection():
    """处理直连信息查询"""
    try:
        result = await dmp_api.get_connection_info()
        await connection_cmd.finish(result)
    except Exception as e:
        await connection_cmd.finish(f"获取直连信息失败: {str(e)}")

@help_cmd.handle()
async def handle_help():
    """处理帮助信息"""
    help_text = """🎮 DMP 饥荒管理机器人 - 帮助菜单

📋 基础命令：
• /世界 [世界名] - 获取世界信息
• /房间 [世界名] - 获取房间信息  
• /系统 - 获取系统信息
• /玩家 [世界名] - 获取在线玩家列表
• /直连 - 获取服务器直连信息
• /菜单 - 显示此帮助信息

🔧 管理员命令：
• /管理命令 - 显示管理员功能菜单
• /查看备份 - 获取备份文件列表
• /创建备份 - 手动创建备份
• /执行 <世界> <命令> - 执行游戏命令
• /回档 <天数> - 回档指定天数 (1-5天)
• /重置世界 [世界名] - 重置世界
• /聊天历史 [世界名] [行数] - 获取聊天历史
• /聊天统计 - 获取聊天历史统计信息

💬 消息互通功能：
• 消息互通 - 开启游戏内消息与QQ消息互通
• 关闭互通 - 关闭消息互通功能
• 互通状态 - 查看当前互通状态
• 最新消息 [数量] - 获取游戏内最新消息

💡 提示：管理员命令需要超级用户权限"""
    await help_cmd.finish(help_text)

@admin_cmd.handle()
async def handle_admin():
    """处理管理员命令菜单"""
    admin_text = """🔧 管理员功能菜单

📋 备份管理：
• /查看备份 - 获取备份文件列表
• /创建备份 - 手动创建备份

🎮 游戏控制：
• /执行 <世界> <命令> - 执行游戏命令
• /回档 <天数> - 回档指定天数 (1-5天)
• /重置世界 [世界名] - 重置世界 (默认Master)

📊 日志查看：
• /聊天历史 [世界名] [行数] - 获取聊天历史 (默认50行)
• /聊天统计 - 获取聊天历史统计信息

⚠️ 注意：这些命令具有高风险，请谨慎使用！"""
    await admin_cmd.finish(admin_text)

@backup_cmd.handle()
async def handle_backup():
    """处理备份列表查询"""
    try:
        result = await dmp_advanced.get_backup_list()
        await backup_cmd.finish(result)
    except Exception as e:
        await backup_cmd.finish(f"获取备份列表失败: {str(e)}")

@create_backup_cmd.handle()
async def handle_create_backup():
    """处理创建备份"""
    try:
        result = await dmp_advanced.create_backup()
        await create_backup_cmd.finish(result)
    except Exception as e:
        await create_backup_cmd.finish(f"创建备份失败: {str(e)}")

@execute_cmd.handle()
async def handle_execute(world_name: str, command: str):
    """处理命令执行"""
    try:
        result = await dmp_advanced.execute_command(world_name, command)
        await execute_cmd.finish(result)
    except Exception as e:
        await execute_cmd.finish(f"执行命令失败: {str(e)}")

@rollback_cmd.handle()
async def handle_rollback(days: int):
    """处理世界回档"""
    try:
        result = await dmp_advanced.rollback_world(days)
        await rollback_cmd.finish(result)
    except Exception as e:
        await rollback_cmd.finish(f"回档失败: {str(e)}")

@reset_world_cmd.handle()
async def handle_reset_world(world_name: str = "Master"):
    """处理世界重置"""
    try:
        result = await dmp_advanced.reset_world(world_name)
        await reset_world_cmd.finish(result)
    except Exception as e:
        await reset_world_cmd.finish(f"重置世界失败: {str(e)}")

@chat_history_cmd.handle()
async def handle_chat_history(world_name: str = "Master", lines: int = 50):
    """处理聊天历史查询"""
    try:
        result = await dmp_advanced.get_chat_history(world_name, lines)
        await chat_history_cmd.finish(result)
    except Exception as e:
        await chat_history_cmd.finish(f"获取聊天历史失败: {str(e)}")

@chat_stats_cmd.handle()
async def handle_chat_stats():
    """处理聊天统计查询"""
    try:
        result = await dmp_advanced.get_chat_stats()
        await chat_stats_cmd.finish(result)
    except Exception as e:
        await chat_stats_cmd.finish(f"获取聊天统计失败: {str(e)}")

@message_exchange_cmd.handle()
async def handle_message_exchange():
    """处理开启消息互通"""
    try:
        result = await message_exchange.enable_exchange()
        await message_exchange_cmd.finish(result)
    except Exception as e:
        await message_exchange_cmd.finish(f"开启消息互通失败: {str(e)}")

@close_exchange_cmd.handle()
async def handle_close_exchange():
    """处理关闭消息互通"""
    try:
        result = await message_exchange.disable_exchange()
        await close_exchange_cmd.finish(result)
    except Exception as e:
        await close_exchange_cmd.finish(f"关闭消息互通失败: {str(e)}")

@exchange_status_cmd.handle()
async def handle_exchange_status():
    """处理互通状态查询"""
    try:
        result = await message_exchange.get_exchange_status()
        await exchange_status_cmd.finish(result)
    except Exception as e:
        await exchange_status_cmd.finish(f"获取互通状态失败: {str(e)}")

@latest_messages_cmd.handle()
async def handle_latest_messages(count: int = 10):
    """处理最新消息查询"""
    try:
        result = await message_exchange.get_latest_messages(count)
        await latest_messages_cmd.finish(result)
    except Exception as e:
        await latest_messages_cmd.finish(f"获取最新消息失败: {str(e)}") 