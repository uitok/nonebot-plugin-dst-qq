"""
调试命令模块
用于调试消息发送问题
"""

from nonebot.adapters import Bot, Event
from nonebot_plugin_alconna import on_alconna
from arclet.alconna import Alconna
from nonebot.adapters.onebot.v11 import MessageSegment
from nonebot import logger

# 测试图片发送命令
test_image_cmd = on_alconna(
    Alconna("测试图片"),
    aliases={"test_image", "图片测试"},
    priority=1,
    block=True
)

@test_image_cmd.handle()
async def handle_test_image(bot: Bot, event: Event):
    """处理测试图片发送命令"""
    user_id = str(event.get_user_id())
    print(f"🧪 开始测试图片发送给用户: {user_id}")
    
    try:
        # 方法1: 尝试发送一个简单的文字图片
        from .text_to_image import convert_text_to_image_async
        test_text = "🧪 这是一个测试图片\n测试文字转图片功能"
        
        print(f"📸 生成测试图片...")
        image_result = await convert_text_to_image_async(test_text)
        print(f"🔍 图片生成结果: {type(image_result)}, 前缀: {str(image_result)[:50]}")
        
        if isinstance(image_result, str) and (image_result.startswith("base64://") or image_result.startswith("file://")):
            # 尝试发送图片
            image_msg = MessageSegment.image(image_result)
            print(f"📤 发送测试图片消息...")
            result = await bot.send(event, image_msg)
            print(f"✅ 测试图片发送结果: {result}")
            
            # 清理临时文件
            if image_result.startswith("file://"):
                import os
                temp_path = image_result.replace("file://", "")
                try:
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)
                        print(f"🗑️ 已清理测试临时文件")
                except:
                    pass
                    
        else:
            # 发送文字说明图片生成失败
            await bot.send(event, f"❌ 图片生成失败，结果: {image_result}")
    
    except Exception as e:
        print(f"❌ 测试图片发送失败: {e}")
        import traceback
        traceback.print_exc()
        await bot.send(event, f"❌ 测试失败: {str(e)}")

# 测试普通消息发送命令
test_text_cmd = on_alconna(
    Alconna("测试文字"),
    aliases={"test_text", "文字测试"},
    priority=1,
    block=True
)

@test_text_cmd.handle()
async def handle_test_text(bot: Bot, event: Event):
    """处理测试普通消息发送命令"""
    user_id = str(event.get_user_id())
    print(f"🧪 开始测试文字发送给用户: {user_id}")
    
    try:
        test_message = "🧪 这是一个测试消息\n用于验证普通文字消息发送功能"
        print(f"📝 发送测试文字消息...")
        result = await bot.send(event, test_message)
        print(f"✅ 测试文字发送结果: {result}")
        
    except Exception as e:
        print(f"❌ 测试文字发送失败: {e}")
        import traceback
        traceback.print_exc()

# 调试信息命令
debug_info_cmd = on_alconna(
    Alconna("调试信息"),
    aliases={"debug_info", "debug"},
    priority=1,
    block=True
)

@debug_info_cmd.handle()
async def handle_debug_info(bot: Bot, event: Event):
    """显示调试信息"""
    user_id = str(event.get_user_id())
    
    # 获取图片模式状态
    from .message_dedup import _user_image_modes
    is_image_mode = user_id in _user_image_modes
    
    debug_msg = f"""🔍 调试信息

👤 用户ID: {user_id}
📱 事件类型: {type(event).__name__}
🖼️ 图片模式: {'✅ 启用' if is_image_mode else '❌ 禁用'}
🤖 Bot类型: {type(bot).__name__}

🧪 测试命令:
• 测试图片 - 测试图片发送
• 测试文字 - 测试文字发送
• 调试信息 - 显示此信息

📊 图片模式用户: {len(_user_image_modes)} 个"""
    
    await bot.send(event, debug_msg)