"""
主菜单模块
提供统一的机器人功能菜单
"""

from nonebot.adapters import Bot, Event
from nonebot_plugin_alconna import on_alconna
from arclet.alconna import Alconna

from .message_utils import send_message, handle_command_errors

# 主菜单命令
main_menu_cmd = on_alconna(
    Alconna("菜单"),
    aliases={"menu", "主菜单", "功能列表"},
    priority=1,
    block=True
)

@main_menu_cmd.handle()
@handle_command_errors("主菜单")
async def handle_main_menu(bot: Bot, event: Event):
    """显示主菜单"""
    
    menu_text = """🎮 DMP 饥荒管理平台机器人

┌─────────────────────────────┐
│        🏠 服务器查房          │  
├─────────────────────────────┤
│ /查房     搜索服务器房间     │
│ /热门房间 查看活跃服务器     │
│ /无密码房间 查看开放房间     │
│ /新手房间 新手友好房间       │
│ /快速查房 随机推荐房间       │
│ /区域概况 各区域统计         │
└─────────────────────────────┘

┌─────────────────────────────┐
│        🎯 服务器管理          │
├─────────────────────────────┤
│ /房间     服务器综合信息     │
│ /直连     获取直连信息       │
│ /集群状态 查看集群状态       │
│ /消息互通 开启消息互通       │
│ /关闭互通 关闭消息互通       │
└─────────────────────────────┘

┌─────────────────────────────┐
│        📖 物品查询           │
├─────────────────────────────┤
│ /物品     查询物品Wiki      │
│ /搜索物品 搜索物品列表      │
│ /物品统计 查看物品统计      │
└─────────────────────────────┘

┌─────────────────────────────┐
│        ⚙️ 管理功能           │
├─────────────────────────────┤
│ /管理命令 管理员功能菜单     │
│ /缓存状态 查看缓存状态       │
│ /配置查看 查看当前配置       │
└─────────────────────────────┘

⚡ 核心特性 (v0.4.5)：
• 🚀 多级缓存系统 - 性能提升10-50倍
• 🎯 智能集群管理 - 自动选择最优集群  
• 💬 实时消息互通 - QQ与游戏双向通信
• 📖 物品Wiki查询 - 支持2800+物品查询
• 🏠 服务器查房 - 亚太地区优化的查房功能

🔐 权限说明：
• 基础功能：所有用户
• 管理功能：仅超级用户

💡 使用 /帮助 <命令> 查看具体命令帮助"""

    await send_message(bot, event, menu_text)

# 帮助命令
help_cmd = on_alconna(
    Alconna("帮助"),
    aliases={"help", "使用帮助"},
    priority=1,
    block=True
)

@help_cmd.handle()
@handle_command_errors("帮助")
async def handle_help(bot: Bot, event: Event):
    """显示帮助信息"""
    
    help_text = """❓ DMP机器人使用帮助

🎯 基础操作：
• /菜单 - 显示所有功能
• /房间 - 查看服务器信息
• /查房 [关键词] - 搜索服务器

🏠 查房功能：
• 支持中英文搜索
• 自动分页显示 (10个/页)
• 输入序号查看详情
• 导航: 上一页/下一页/退出

💬 消息互通：
• /消息互通 - 开启QQ与游戏通信
• /关闭互通 - 关闭通信功能

📖 物品查询：
• /物品 [物品名] - 查询Wiki
• 支持中英文物品名
• 自动生成物品截图

⚙️ 管理功能：
• 仅超级用户可用
• /管理命令 查看管理菜单

💡 提示：
• 命令不区分大小写
• 支持简写和别名
• 数据每5分钟更新一次

📞 反馈问题：
https://github.com/uitok/nonebot-plugin-dst-qq"""

    await send_message(bot, event, help_text)