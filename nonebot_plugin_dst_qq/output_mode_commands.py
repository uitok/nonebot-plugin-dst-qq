"""
消息输出模式切换命令
提供切换文字/图片输出模式的命令
"""

from nonebot.adapters import Bot, Event
from nonebot_plugin_alconna import on_alconna, AlconnaQuery, Query
from arclet.alconna import Alconna, Args

from .output_mode_manager import get_output_mode_manager, OutputMode
from .message_dedup import send_with_dedup, set_user_image_mode
from nonebot import logger

# 获取输出模式管理器
output_mode_manager = get_output_mode_manager()

# 切换模式命令
switch_mode_cmd = on_alconna(
    Alconna("切换模式", Args["mode", str]),
    aliases={"切换输出模式", "输出模式", "switch_mode"},
    priority=5,
    block=True
)

@switch_mode_cmd.handle()
async def handle_switch_mode(bot: Bot, event: Event, mode: Query[str] = AlconnaQuery("mode", "")):
    """处理切换输出模式命令"""
    user_id = str(event.get_user_id())
    
    # 标准化模式参数
    mode = mode.result.lower().strip() if mode.result else ""
    
    # 模式映射
    mode_mapping = {
        "图片": OutputMode.IMAGE,
        "图像": OutputMode.IMAGE, 
        "image": OutputMode.IMAGE,
        "img": OutputMode.IMAGE,
        "pic": OutputMode.IMAGE,
        "文字": OutputMode.TEXT,
        "文本": OutputMode.TEXT,
        "text": OutputMode.TEXT,
        "txt": OutputMode.TEXT,
    }
    
    if mode not in mode_mapping:
        available_modes = "、".join(["图片", "文字"])
        await send_with_dedup(bot, event, f"❌ 不支持的输出模式: {mode}\n\n可用模式: {available_modes}")
        return
    
    target_mode = mode_mapping[mode]
    
    # 使用简化的模式设置
    if target_mode == OutputMode.IMAGE:
        set_user_image_mode(user_id, True)
        success_msg = "🖼️ 输出模式已切换为图片模式\n\n现在所有消息将以图片形式发送"
        print(f"✅ 用户 {user_id} 图片模式已设置")
    else:
        set_user_image_mode(user_id, False)
        success_msg = "📝 输出模式已切换为文字模式\n\n现在所有消息将以文字形式发送"
        print(f"✅ 用户 {user_id} 文字模式已设置")
    
    await send_with_dedup(bot, event, success_msg)

# 查看当前模式命令
mode_status_cmd = on_alconna(
    Alconna("模式状态"),
    aliases={"输出模式状态", "当前模式", "mode_status"},
    priority=5,
    block=True
)

@mode_status_cmd.handle()
async def handle_mode_status(bot: Bot, event: Event):
    """处理查看模式状态命令"""
    user_id = str(event.get_user_id())
    
    # 检查用户当前模式
    is_image_mode = hasattr(send_with_dedup, '_user_image_modes') and user_id in send_with_dedup._user_image_modes
    
    if is_image_mode:
        status_msg = "🖼️ 当前输出模式: 图片\n\n💡 使用 '切换模式 文字' 来切换为文字模式"
    else:
        status_msg = "📝 当前输出模式: 文字\n\n💡 使用 '切换模式 图片' 来切换为图片模式"
    
    await send_with_dedup(bot, event, status_msg)

# 重置模式命令  
reset_mode_cmd = on_alconna(
    Alconna("重置模式"),
    aliases={"重置输出模式", "reset_mode"},
    priority=5,
    block=True
)

@reset_mode_cmd.handle()
async def handle_reset_mode(bot: Bot, event: Event):
    """处理重置输出模式命令"""
    user_id = str(event.get_user_id())
    
    set_user_image_mode(user_id, False)
    await send_with_dedup(bot, event, "✅ 输出模式已重置为默认文字模式")

# 模式帮助命令
mode_help_cmd = on_alconna(
    Alconna("模式帮助"),
    aliases={"输出模式帮助", "mode_help"},
    priority=5,
    block=True
)

@mode_help_cmd.handle()
async def handle_mode_help(bot: Bot, event: Event):
    """处理模式帮助命令"""
    help_msg = """📋 输出模式帮助

🔧 可用命令：
• 切换模式 图片 - 切换到图片输出模式
• 切换模式 文字 - 切换到文字输出模式  
• 模式状态 - 查看当前输出模式
• 重置模式 - 重置为默认文字模式
• 模式帮助 - 显示此帮助信息

📝 模式说明：
• 文字模式：消息以普通文字形式发送
• 图片模式：消息转换为图片形式发送

💡 使用技巧：
• 图片模式适合查看大量文字信息
• 文字模式便于复制和搜索内容
• 可以随时切换模式，设置会保持有效

🎯 示例：
切换模式 图片
切换模式 文字
模式状态"""
    
    await send_with_dedup(bot, event, help_msg)