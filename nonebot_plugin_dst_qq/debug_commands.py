"""
调试命令模块
用于调试消息发送问题
"""

from nonebot.adapters import Bot, Event
from nonebot_plugin_alconna import on_alconna
from arclet.alconna import Alconna
from nonebot.adapters.onebot.v11 import MessageSegment
from nonebot import logger
from .message_utils import send_message, handle_command_errors

# 测试图片发送命令
test_image_cmd = on_alconna(
    Alconna("测试图片"),
    aliases={"test_image", "图片测试"},
    priority=1,
    block=True
)

@test_image_cmd.handle()
@handle_command_errors("测试图片")
async def handle_test_image(bot: Bot, event: Event):
    """处理测试图片发送命令"""
    user_id = str(event.get_user_id())
    print(f"🧪 开始测试图片发送给用户: {user_id}")
    
    # 图片功能已禁用
    await bot.send(event, "🧪 图片功能已禁用，直接发送测试消息")
    return
    
    # 以下代码已禁用
    if False:
        print(f"📊 图片字节大小: {len(image_bytes)} bytes")
        
        # 尝试多种发送方式
        success = False
        
        # 方式1: 字节数据
        try:
            print(f"📤 测试方式1: 字节数据发送...")
            image_msg = MessageSegment.image(image_bytes)
            result = await bot.send(event, image_msg)
            print(f"✅ 字节数据发送成功: {result}")
            success = True
        except Exception as e:
            print(f"❌ 字节数据发送失败: {e}")
        
        # 方式2: BytesIO
        if not success:
            try:
                from io import BytesIO
                print(f"📤 测试方式2: BytesIO发送...")
                bio = BytesIO(image_bytes)
                image_msg = MessageSegment.image(bio)
                result = await bot.send(event, image_msg)
                print(f"✅ BytesIO发送成功: {result}")
                success = True
            except Exception as e:
                print(f"❌ BytesIO发送失败: {e}")
        
        # 方式3: Base64
        if not success:
            try:
                import base64
                print(f"📤 测试方式3: Base64发送...")
                base64_str = base64.b64encode(image_bytes).decode('utf-8')
                image_msg = MessageSegment.image(f"base64://{base64_str}")
                result = await bot.send(event, image_msg)
                print(f"✅ Base64发送成功: {result}")
                success = True
            except Exception as e:
                print(f"❌ Base64发送失败: {e}")
        
        if not success:
            # 图片功能已禁用
            pass
    else:
        # 图片功能已禁用
        pass

# 测试普通消息发送命令
test_text_cmd = on_alconna(
    Alconna("测试文字"),
    aliases={"test_text", "文字测试"},
    priority=1,
    block=True
)

@test_text_cmd.handle()
@handle_command_errors("测试文字")
async def handle_test_text(bot: Bot, event: Event):
    """处理测试普通消息发送命令"""
    user_id = str(event.get_user_id())
    print(f"🧪 开始测试文字发送给用户: {user_id}")
    
    test_message = "🧪 这是一个测试消息\n用于验证普通文字消息发送功能"
    print(f"📝 发送测试文字消息...")
    result = await bot.send(event, test_message)
    print(f"✅ 测试文字发送结果: {result}")

# 调试信息命令
debug_info_cmd = on_alconna(
    Alconna("调试信息"),
    aliases={"debug_info", "debug"},
    priority=1,
    block=True
)

@debug_info_cmd.handle()
@handle_command_errors("调试信息")
async def handle_debug_info(bot: Bot, event: Event):
    """显示调试信息"""
    user_id = str(event.get_user_id())
    
    debug_msg = f"""🔍 调试信息

👤 用户ID: {user_id}
📱 事件类型: {type(event).__name__}
🤖 Bot类型: {type(bot).__name__}

🧪 测试命令:
• 测试文字 - 测试文字发送
• 调试信息 - 显示此信息

📝 当前模式: 文字模式（图片功能已禁用）"""
    
    await send_message(bot, event, debug_msg)