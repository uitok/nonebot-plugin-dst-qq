"""
配置管理命令
提供配置查看、更新、验证和热重载功能
"""

import json
from typing import Dict, Any
from nonebot import on_command
from nonebot.adapters import Event
from nonebot.adapters.onebot.v11 import Bot, Message
from nonebot.permission import SUPERUSER
from nonebot.rule import to_me

from .config import get_config_manager, ConfigValidationError
from nonebot import logger

# 配置查看命令
config_status = on_command("配置状态", rule=to_me(), permission=SUPERUSER, priority=1)
config_show = on_command("查看配置", rule=to_me(), permission=SUPERUSER, priority=1)
config_validate = on_command("验证配置", rule=to_me(), permission=SUPERUSER, priority=1)
config_test = on_command("测试连接", rule=to_me(), permission=SUPERUSER, priority=1)
config_reload = on_command("重载配置", rule=to_me(), permission=SUPERUSER, priority=1)
config_update = on_command("更新配置", rule=to_me(), permission=SUPERUSER, priority=1)
config_help = on_command("配置帮助", rule=to_me(), permission=SUPERUSER, priority=1)

@config_status.handle()
async def handle_config_status(bot: Bot, event: Event):
    """查看配置状态"""
    try:
        config_manager = get_config_manager()
        config = config_manager.get_config()
        
        response = "📋 当前配置状态:\n\n"
        
        # 基本信息
        response += f"🔧 配置版本: {config.version}\n"
        response += f"📅 最后更新: {config.last_updated}\n"
        response += f"📁 配置文件: {config_manager.config_file}\n\n"
        
        # DMP配置状态
        response += "🌐 DMP配置:\n"
        response += f"  📡 服务器: {config.dmp.base_url}\n"
        response += f"  🔑 令牌: {'已配置' if config.dmp.token and config.dmp.token != 'your_dmp_token_here' else '❌ 未配置'}\n"
        response += f"  🏢 默认集群: {config.dmp.default_cluster}\n"
        response += f"  ⏱️ 超时时间: {config.dmp.timeout}s\n\n"
        
        # 机器人配置状态
        response += "🤖 机器人配置:\n"
        response += f"  👑 超级用户: {len(config.bot.superusers)} 个\n"
        response += f"  💬 私聊: {'✅ 启用' if config.bot.enable_private_chat else '❌ 禁用'}\n"
        response += f"  👥 群聊: {'✅ 启用' if config.bot.enable_group_chat else '❌ 禁用'}\n\n"
        
        # 缓存配置状态
        response += "💾 缓存配置:\n"
        response += f"  🧠 内存缓存: {config.cache.memory_max_size} 条目, TTL {config.cache.memory_default_ttl}s\n"
        response += f"  📁 文件缓存: {config.cache.file_max_size} 条目, TTL {config.cache.file_default_ttl}s\n"
        response += f"  🧹 自动清理: {'✅ 启用' if config.cache.auto_cleanup else '❌ 禁用'}\n\n"
        
        # 消息配置状态
        response += "💬 消息互通配置:\n"
        response += f"  🔄 消息同步: {'✅ 启用' if config.message.enable_message_sync else '❌ 禁用'}\n"
        response += f"  ⏱️ 同步间隔: {config.message.sync_interval}s\n"
        response += f"  📏 最大长度: {config.message.max_message_length} 字符\n\n"
        
        # 日志配置状态
        response += "📝 日志配置:\n"
        response += f"  📊 日志级别: {config.logging.level}\n"
        response += f"  📄 日志格式: {config.logging.format}\n"
        response += f"  💾 记录到文件: {'✅ 启用' if config.logging.log_to_file else '❌ 禁用'}\n"
        
        await bot.send(event, response)
        
        logger.info(f"用户 {event.get_user_id()} 查看配置状态成功")
        
    except Exception as e:
        error_msg = f"查看配置状态失败: {e}"
        await bot.send(event, error_msg)
        logger.error(f"配置状态查看失败: {e}")

@config_show.handle()
async def handle_config_show(bot: Bot, event: Event):
    """查看完整配置（敏感信息会被隐藏）"""
    try:
        config_manager = get_config_manager()
        config = config_manager.get_config()
        
        # 创建安全的配置副本（隐藏敏感信息）
        safe_config = config.dict()
        
        # 隐藏敏感信息
        if 'dmp' in safe_config and 'token' in safe_config['dmp']:
            token = safe_config['dmp']['token']
            if len(token) > 10:
                safe_config['dmp']['token'] = token[:6] + "***" + token[-4:]
            else:
                safe_config['dmp']['token'] = "***"
        
        # 隐藏超级用户ID（部分）
        if 'bot' in safe_config and 'superusers' in safe_config['bot']:
            safe_config['bot']['superusers'] = [
                user_id[:3] + "***" + user_id[-2:] if len(user_id) > 5 else "***"
                for user_id in safe_config['bot']['superusers']
            ]
        
        # 格式化JSON输出
        config_json = json.dumps(safe_config, indent=2, ensure_ascii=False)
        
        response = f"📋 当前配置内容:\n\n```json\n{config_json}\n```\n\n"
        response += "⚠️ 敏感信息已隐藏\n"
        response += "💡 使用 '@机器人 更新配置' 命令修改配置"
        
        await bot.send(event, response)
        
        logger.info(f"用户 {event.get_user_id()} 查看配置内容成功")
        
    except Exception as e:
        error_msg = f"查看配置内容失败: {e}"
        await bot.send(event, error_msg)
        logger.error(f"配置内容查看失败: {e}")

@config_validate.handle()
async def handle_config_validate(bot: Bot, event: Event):
    """验证当前配置"""
    try:
        config_manager = get_config_manager()
        errors = config_manager.validate_config()
        
        if not errors:
            response = "✅ 配置验证通过！所有配置项都正确。"
        else:
            response = "❌ 配置验证失败，发现以下问题:\n\n"
            for section, section_errors in errors.items():
                response += f"📋 {section} 配置:\n"
                for error in section_errors:
                    response += f"  ❌ {error}\n"
                response += "\n"
            
            response += "💡 请使用 '@机器人 更新配置' 命令修复这些问题"
        
        await bot.send(event, response)
        
        validation_result = "通过" if not errors else "失败"
        logger.info(f"用户 {event.get_user_id()} 配置验证完成: {validation_result}")
        
    except Exception as e:
        error_msg = f"配置验证失败: {e}"
        await bot.send(event, error_msg)
        logger.error(f"配置验证失败: {e}")

@config_test.handle()
async def handle_config_test(bot: Bot, event: Event):
    """测试DMP服务器连接"""
    try:
        config_manager = get_config_manager()
        
        await bot.send(event, "🔄 正在测试DMP服务器连接...")
        
        is_connected = await config_manager.test_dmp_connection()
        
        if is_connected:
            response = "✅ DMP服务器连接测试成功！\n"
            response += "🌐 服务器响应正常\n"
            response += "🔑 API令牌验证通过"
        else:
            response = "❌ DMP服务器连接测试失败！\n"
            response += "请检查以下配置:\n"
            response += "  • 服务器地址是否正确\n"
            response += "  • API令牌是否有效\n"
            response += "  • 网络连接是否正常"
        
        await bot.send(event, response)
        
        test_result = "成功" if is_connected else "失败"
        logger.info(f"用户 {event.get_user_id()} DMP连接测试完成: {test_result}")
        
    except Exception as e:
        error_msg = f"连接测试失败: {e}"
        await bot.send(event, error_msg)
        logger.error(f"DMP连接测试失败: {e}")

@config_reload.handle()
async def handle_config_reload(bot: Bot, event: Event):
    """重载配置文件"""
    try:
        config_manager = get_config_manager()
        
        # 执行重载
        config_manager._reload_config()
        
        response = "✅ 配置重载成功！\n"
        response += "🔄 已从配置文件重新加载所有设置\n"
        response += "💡 建议执行 '@机器人 验证配置' 确认配置正确性"
        
        await bot.send(event, response)
        
        logger.success(f"用户 {event.get_user_id()} 配置重载成功")
        
    except Exception as e:
        error_msg = f"配置重载失败: {e}"
        await bot.send(event, error_msg)
        logger.error(f"配置重载失败: {e}")

@config_update.handle()
async def handle_config_update(bot: Bot, event: Event):
    """更新配置（交互式）"""
    try:
        response = "🔧 配置更新指南:\n\n"
        response += "📝 直接编辑配置文件:\n"
        response += f"  文件路径: {get_config_manager().config_file}\n"
        response += "  编辑后配置会自动热重载\n\n"
        
        response += "📋 主要配置项:\n"
        response += "  🌐 dmp.base_url - DMP服务器地址\n"
        response += "  🔑 dmp.token - API访问令牌\n"
        response += "  🏢 dmp.default_cluster - 默认集群名\n"
        response += "  👑 bot.superusers - 超级用户列表\n"
        response += "  💬 message.enable_message_sync - 启用消息同步\n\n"
        
        response += "⚠️ 注意事项:\n"
        response += "  • 编辑前建议备份配置文件\n"
        response += "  • 保存后会自动验证配置\n"
        response += "  • 无效配置会回滚到备份\n\n"
        
        response += "🔧 常用命令:\n"
        response += "  @机器人 验证配置 - 验证配置正确性\n"
        response += "  @机器人 测试连接 - 测试DMP连接\n"
        response += "  @机器人 重载配置 - 手动重载配置"
        
        await bot.send(event, response)
        
        logger.info(f"用户 {event.get_user_id()} 配置更新指南发送成功")
        
    except Exception as e:
        error_msg = f"发送配置更新指南失败: {e}"
        await bot.send(event, error_msg)
        logger.error(f"配置更新指南发送失败: {e}")

@config_help.handle()
async def handle_config_help(bot: Bot, event: Event):
    """显示配置管理帮助"""
    try:
        response = "📚 配置管理命令帮助:\n\n"
        
        response += "🔍 查看命令:\n"
        response += "  @机器人 配置状态 - 查看配置状态概览\n"
        response += "  @机器人 查看配置 - 查看完整配置内容\n\n"
        
        response += "✅ 验证命令:\n"
        response += "  @机器人 验证配置 - 验证配置正确性\n"
        response += "  @机器人 测试连接 - 测试DMP服务器连接\n\n"
        
        response += "🔧 管理命令:\n"
        response += "  @机器人 更新配置 - 查看配置更新指南\n"
        response += "  @机器人 重载配置 - 手动重载配置文件\n\n"
        
        response += "📋 配置文件结构:\n"
        response += "  dmp - DMP API配置\n"
        response += "  bot - 机器人基础配置\n"
        response += "  cache - 缓存系统配置\n"
        response += "  message - 消息互通配置\n"
        response += "  logging - 日志系统配置\n\n"
        
        response += "🔥 热重载特性:\n"
        response += "  • 配置文件修改后自动重载\n"
        response += "  • 自动验证配置正确性\n"
        response += "  • 无效配置自动回滚\n"
        response += "  • 实时通知配置变更\n\n"
        
        response += "💡 提示:\n"
        response += "  只有超级用户可以使用配置管理命令\n"
        response += "  配置修改会记录到日志中\n"
        response += "  建议定期备份配置文件"
        
        await bot.send(event, response)
        
        logger.info(f"用户 {event.get_user_id()} 配置管理帮助发送成功")
        
    except Exception as e:
        error_msg = f"发送配置管理帮助失败: {e}"
        await bot.send(event, error_msg)
        logger.error(f"配置管理帮助发送失败: {e}")


