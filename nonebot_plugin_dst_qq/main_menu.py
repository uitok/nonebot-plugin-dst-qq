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

━━━━━━━━━━━━ 🏠 服务器查房 ━━━━━━━━━━━━
• /查房 <关键词> —— 智能搜索服务器
• /热门房间 —— 速览当前活跃房间
• /无密码房间 —— 过滤开放服务器
• /新手房间 —— 获取友好入门房
• /快速查房 —— 随机推荐一键加入
• /区域概况 —— 各区域在线统计

━━━━━━━━━━━━ 🎯 服务器工具 ━━━━━━━━━━━━
• /房间 —— 查看当前服务器全貌
• /直连 —— 获取直连代码与端口
• /集群状态 —— 监看集群运行状况
• /消息互通 —— 开启/关闭 QQ ↔ 游戏

━━━━━━━━━━━━ 📖 物品与百科 ━━━━━━━━━━━━
• /物品 <名称> —— 查询 Wiki 详情
• /搜索物品 <关键词> —— 模糊检索
• /物品统计 —— 浏览热门物品数据

━━━━━━━━━━━━ ⚙️ 管理入口 ━━━━━━━━━━━━
• /管理命令 —— 管理员功能面板
• /缓存状态 —— 查看缓存命中情况
• /刷新缓存 —— 清空并预热缓存

⚡ 核心特性
  🚀 多级缓存与自动归档
  🎯 智能集群管理与监控
  💬 实时消息桥接 QQ / 游戏
  📖 内置 2800+ 物品百科

🔐 权限速览
  • 基础功能：所有用户
  • 管理工具：超级用户

💡 提示：使用「/帮助 <命令>」获取详细说明"""

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
    
    help_text = """❓ DMP 机器人使用指南

🎯 快速上手
• /菜单 —— 查看完整功能索引
• /房间 —— 获取服务器综合信息
• /查房 关键词 —— 搜索目标房间

🏠 查房小贴士
• 支持中英文、模糊匹配
• 默认自动分页（输入序号查看详情）
• 导航指令：上一页 / 下一页 / 退出

💬 消息互通
• /消息互通 —— 建立 QQ ↔ 游戏通道
• /关闭互通 —— 立即停止同步
• /切换模式 图片 —— 切换为图片回复

📖 物品百科
• /物品 名称 —— 获取 Wiki 详情页
• /搜索物品 关键词 —— 列出关联物品

⚙️ 管理入口
• 仅超级用户可执行
• /管理命令 —— 浏览管理功能面板

🔄 常见问题
• 命令大小写不敏感
• 支持多数命令别名
• 关键数据每 5 分钟自动刷新

📞 反馈 & Issue
https://github.com/uitok/nonebot-plugin-dst-qq"""

    await send_message(bot, event, help_text)
