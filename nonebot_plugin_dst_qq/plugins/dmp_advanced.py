
import asyncio
import re
from typing import Dict, Any, List, Optional
import httpx
from nonebot import get_driver
from nonebot.adapters.onebot.v11 import Bot
from nonebot.adapters import Event
from nonebot.permission import SUPERUSER
from nonebot_plugin_alconna import on_alconna, Match
from arclet.alconna import Alconna, Args, Option, Subcommand

# 导入配置和基础API
from ..config import Config
from ..base_api import BaseAPI, APIResponse

# 导入合并转发功能
from .dmp_api import send_long_message
from ..cache_manager import cached

# 创建DMP Advanced API实例
dmp_advanced_api = None

# 导入新的配置管理
from ..config import get_config

# 创建Alconna命令
admin_cmd = Alconna("管理命令")
advanced_cmd = Alconna("高级功能")
admin_cmd_alias = Alconna("管理菜单")
advanced_cmd_alias = Alconna("高级菜单")
backup_cmd = Alconna("查看备份")
exec_cmd = Alconna("执行命令", Args["command", str])
rollback_cmd = Alconna("回滚世界", Args["days", int])
kick_cmd = Alconna("踢出玩家")
ban_cmd = Alconna("封禁玩家")
unban_cmd = Alconna("解封玩家")

# 创建命令别名
admin_cmd_eng = Alconna("admin")
advanced_cmd_eng = Alconna("advanced")
backup_cmd_eng = Alconna("backup")
exec_cmd_eng = Alconna("exec", Args["command", str])
rollback_cmd_eng = Alconna("rollback", Args["days", int])
kick_cmd_eng = Alconna("kick")
ban_cmd_eng = Alconna("ban")
unban_cmd_eng = Alconna("unban")

# 创建响应器 - 先不加权限验证，确保基本功能正常
admin_matcher = on_alconna(admin_cmd)
advanced_matcher = on_alconna(advanced_cmd)
admin_alias_matcher = on_alconna(admin_cmd_alias)
advanced_alias_matcher = on_alconna(advanced_cmd_alias)
backup_matcher = on_alconna(backup_cmd)
exec_matcher = on_alconna(exec_cmd)
rollback_matcher = on_alconna(rollback_cmd)
kick_matcher = on_alconna(kick_cmd)
ban_matcher = on_alconna(ban_cmd)
unban_matcher = on_alconna(unban_cmd)

admin_eng_matcher = on_alconna(admin_cmd_eng)
advanced_eng_matcher = on_alconna(advanced_cmd_eng)
backup_eng_matcher = on_alconna(backup_cmd_eng)
exec_eng_matcher = on_alconna(exec_cmd_eng)
rollback_eng_matcher = on_alconna(rollback_cmd_eng)
kick_eng_matcher = on_alconna(kick_cmd_eng)
ban_eng_matcher = on_alconna(ban_cmd_eng)
unban_eng_matcher = on_alconna(unban_cmd_eng)

class DMPAdvancedAPI(BaseAPI):
    """DMP 高级API客户端"""
    
    def __init__(self):
        config = get_config()
        super().__init__(config, "DMP-Advanced-API")
        
        # 添加DMP特有的请求头
        self._base_headers.update({
            "X-I18n-Lang": "zh"  # 使用zh而不是zh-CN
        })
    
    @cached(cache_type="api", memory_ttl=300, file_ttl=600)
    async def get_available_clusters(self) -> APIResponse:
        """获取所有可用的集群列表 - 缓存5分钟内存，10分钟文件"""
        return await self.get("/setting/clusters")
    
    async def get_current_cluster(self) -> str:
        """获取当前使用的集群名称，优先使用集群管理器设置的集群"""
        try:
            from ..cluster_manager import get_cluster_manager
            cluster_manager = get_cluster_manager()
            if cluster_manager:
                current_cluster = await cluster_manager.get_current_cluster()
                if current_cluster:
                    return current_cluster
        except ImportError:
            pass
        
        # 如果集群管理器不可用或没有设置当前集群，回退到第一个可用集群
        return await self.get_first_available_cluster()
    
    async def get_first_available_cluster(self) -> str:
        """获取第一个可用的集群名称"""
        response = await self.get_available_clusters()
        if response.success and response.data:
            clusters = response.data
            if isinstance(clusters, list) and clusters:
                first_cluster = clusters[0]
                if isinstance(first_cluster, dict):
                    cluster_name = first_cluster.get("clusterName", "")
                    print(f"🔍 自动选择集群: {cluster_name}")
                    return cluster_name
        return None
    
    @cached(cache_type="api", memory_ttl=60, file_ttl=300)
    async def get_backup_list(self, cluster_name: str = None) -> APIResponse:
        """获取备份列表 - 缓存1分钟内存，5分钟文件"""
        if not cluster_name:
            cluster_name = await self.get_current_cluster()
            if not cluster_name:
                return APIResponse(code=404, message="没有可用的集群")
        
        params = {"clusterName": cluster_name}
        result = await self.get("/tools/backup", params=params)
        
        # 在结果数据中添加集群信息
        if result.success and isinstance(result.data, dict):
            result.data["cluster_name"] = cluster_name
        
        return result
    
    async def create_backup(self, cluster_name: str = None) -> APIResponse:
        """创建备份"""
        if not cluster_name:
            cluster_name = await self.get_current_cluster()
            if not cluster_name:
                return APIResponse(code=404, message="没有可用的集群")
        
        data = {"clusterName": cluster_name}
        result = await self.post("/backup/create", json=data)
        
        # 在结果中添加集群信息
        if result.success and isinstance(result.data, dict):
            result.data["cluster_name"] = cluster_name
        
        return result
    
    async def execute_command(self, cluster_name: str, world_name: str, command: str) -> APIResponse:
        """执行命令"""
        data = {
            "type": "console",
            "extraData": command,
            "clusterName": cluster_name,
            "worldName": world_name
        }
        
        return await self.post("/home/exec", json=data)
    
    async def rollback_world(self, days: int, cluster_name: str = None) -> APIResponse:
        """回档世界"""
        if not cluster_name:
            cluster_name = await self.get_current_cluster()
            if not cluster_name:
                return APIResponse(code=404, message="没有可用的集群")
        
        if days < 1 or days > 5:
            return APIResponse(code=400, message="回档天数必须在1-5天之间")
        
        data = {
            "type": "rollback",
            "extraData": days,
            "clusterName": cluster_name,
            "worldName": ""
        }
        
        result = await self.post("/home/exec", json=data)
        
        # 在结果中添加集群信息
        if result.success and isinstance(result.data, dict):
            result.data["cluster_name"] = cluster_name
        
        return result
    
    async def reset_world(self, cluster_name: str = None, world_name: str = "Master") -> APIResponse:
        """重置世界"""
        if not cluster_name:
            cluster_name = await self.get_current_cluster()
            if not cluster_name:
                return APIResponse(code=404, message="没有可用的集群")
        
        data = {
            "clusterName": cluster_name,
            "worldName": world_name
        }
        
        result = await self.post("/world/reset", json=data)
        
        # 在结果中添加集群信息
        if result.success and isinstance(result.data, dict):
            result.data["cluster_name"] = cluster_name
        
        return result
    
    async def get_chat_history(self, cluster_name: str = None, world_name: str = "", lines: int = 50) -> APIResponse:
        """获取聊天历史"""
        if not cluster_name:
            cluster_name = await self.get_current_cluster()
            if not cluster_name:
                return APIResponse(code=404, message="没有可用的集群")
        
        params = {
            "clusterName": cluster_name,
            "lines": lines
        }
        if world_name:
            params["worldName"] = world_name
        
        result = await self.get("/chat/history", params=params)
        
        # 在结果中添加集群信息
        if result.success and isinstance(result.data, dict):
            result.data["cluster_name"] = cluster_name
        
        return result
    
    async def get_chat_statistics(self, cluster_name: str = None) -> APIResponse:
        """获取聊天统计"""
        if not cluster_name:
            cluster_name = await self.get_current_cluster()
            if not cluster_name:
                return APIResponse(code=404, message="没有可用的集群")
        
        params = {"clusterName": cluster_name}
        
        result = await self.get("/chat/statistics", params=params)
        
        # 在结果中添加集群信息
        if result.success and isinstance(result.data, dict):
            result.data["cluster_name"] = cluster_name
        
        return result

# 权限检查函数
async def _check_admin_permission(bot: Bot, event: Event, user_id: str) -> bool:
    """检查用户是否具有管理员权限"""
    try:
        # 检查是否是超级用户
        from nonebot import get_driver
        driver = get_driver()
        if user_id in driver.config.superusers:
            return True
        
        # 检查插件配置中的超级用户
        from ..config import get_config
        config = get_config()
        if user_id in config.bot.superusers:
            return True
        
        # 如果是群聊，检查是否是群管理员
        if hasattr(event, 'group_id'):
            try:
                group_member_info = await bot.get_group_member_info(
                    group_id=event.group_id, 
                    user_id=int(user_id)
                )
                if group_member_info.get('role') in ['owner', 'admin']:
                    return True
            except Exception:
                pass
        
        return False
    except Exception as e:
        print(f"⚠️ 权限检查失败: {e}")
        return False

def require_admin(func):
    """管理员权限装饰器"""
    async def wrapper(bot: Bot, event: Event):
        user_id = str(event.get_user_id())
        if not await _check_admin_permission(bot, event, user_id):
            await bot.send(event, "❌ 权限不足，只有管理员可以使用此命令", at_sender=True)
            return
        return await func(bot, event)
    return wrapper

# 命令处理函数
@admin_matcher.handle()
@require_admin
async def handle_admin_cmd(bot: Bot, event: Event):
    """处理管理员命令帮助 - 使用图片样式发送"""
    
    try:
        # 根据用户输出模式决定是否生成图片
        try_image_mode = False
        try:
            user_id = str(event.get_user_id())
            from ..message_dedup import _user_image_modes
            try_image_mode = user_id in _user_image_modes
        except Exception:
            try_image_mode = False

        if False:  # 禁用图片模式
            pass
        
        # 图片功能已禁用，使用文字模式
        help_text = """🔧 管理员功能菜单

💾 备份管理
📂 /查看备份 - 查看可用世界备份
⏪ /回滚世界 - 回滚到指定天数前

⚡ 游戏控制  
💻 /执行命令 - 在游戏内执行控制台命令
🏗️ /集群管理 - 集群切换和配置管理

👥 玩家管理
👢 /踢出玩家 - 踢出指定玩家
🚫 /封禁玩家 - 封禁指定玩家  
✅ /解封玩家 - 解封指定玩家

⚠️ 管理员专用: 仅限超级用户使用
💡 高级功能请使用: /高级功能"""
        
        await bot.send(event, help_text, at_sender=True)
        
    except Exception as e:
        error_msg = f"❌ 处理管理命令时发生错误: {str(e)}"
        print(f"⚠️ {error_msg}")
        await bot.send(event, error_msg, at_sender=True)

@admin_alias_matcher.handle()
async def handle_admin_cmd_alias(bot: Bot, event: Event):
    # 复用主处理函数，权限验证也会被复用
    await handle_admin_cmd(bot, event)

@advanced_matcher.handle()
@require_admin
async def handle_advanced_cmd(bot: Bot, event: Event):
    """处理高级功能菜单 - 使用图片样式发送"""
    
    try:
        # 根据用户输出模式决定是否生成图片
        try_image_mode = False
        try:
            user_id = str(event.get_user_id())
            from ..message_dedup import _user_image_modes
            try_image_mode = user_id in _user_image_modes
        except Exception:
            try_image_mode = False

        if False:  # 禁用图片模式
            pass
        
        # 图片功能已禁用，使用文字模式
        help_text = """🏗️ 高级管理功能菜单

🗂️ 集群管理
📊 /集群状态 - 查看所有集群运行状态
🔄 /切换集群 - 切换当前操作集群
🔃 /刷新集群 - 刷新集群列表缓存
📋 /集群详情 - 查看指定集群详细信息

📊 数据管理
💾 /缓存状态 - 查看缓存系统状态
🗑️ /清理缓存 - 清理指定类型缓存
📈 /缓存统计 - 查看详细缓存统计
🔧 /缓存帮助 - 显示缓存管理帮助

🗜️ 数据压缩
📊 /数据分析 - 分析数据库大小分布
🗜️ /压缩数据 - 压缩指定日期数据
📦 /归档数据 - 归档指定月份数据
🤖 /自动压缩 - 自动压缩所有旧数据
📁 /查看归档 - 查看归档文件列表
🧹 /清理归档 - 清理过期归档文件
🔧 /数据维护 - 执行完整数据维护流程

⚙️ 系统配置
📋 /配置状态 - 查看当前配置状态
🔍 /查看配置 - 查看完整配置内容
✅ /验证配置 - 验证配置正确性
🔗 /测试连接 - 测试DMP服务器连接
🔄 /重载配置 - 重新加载配置文件
📝 /更新配置 - 查看配置更新指南

⚠️ 高级功能说明:
• 🔐 所有功能均需超级用户权限
• 🎯 @机器人 <命令> 的格式才能触发部分高级功能
• 💡 使用前请先了解对应功能的作用
• 🚨 某些操作不可逆，请谨慎使用

🔍 特定功能的详细说明请查看对应命令帮助"""
        
        # 使用合并转发发送长菜单
        await send_long_message(bot, event, "高级管理功能菜单", help_text, max_length=600)
        
    except Exception as e:
        error_msg = f"❌ 处理高级功能命令时发生错误: {str(e)}"
        print(f"⚠️ {error_msg}")
        await bot.send(event, error_msg, at_sender=True)

@advanced_alias_matcher.handle()
async def handle_advanced_cmd_alias(bot: Bot, event: Event):
    # 复用主处理函数
    await handle_advanced_cmd(bot, event)

@backup_matcher.handle()
async def handle_backup_cmd(bot: Bot, event: Event):
    """处理查看备份命令"""
    # 由于使用了 permission=SUPERUSER，这里不需要额外的权限检查
    
    try:
        # 自动获取备份列表（不指定集群，让API自动选择）
        result = await dmp_advanced_api.get_backup_list()
        
        if result.code == 200:
            data = result.data or {}
            backup_files = data.get('backupFiles', [])
            disk_usage = data.get('diskUsage', 0)
            
            # 获取实际使用的集群名称
            cluster_name = data.get("cluster_name", "自动选择")
            
            if backup_files:
                response = f"💾 可用备份 (集群: {cluster_name}) - 磁盘使用率: {disk_usage:.1f}%\n"
                for i, backup in enumerate(backup_files, 1):
                    name = backup.get('name', '未知')
                    create_time = backup.get('createTime', '未知时间')
                    size_mb = backup.get('size', 0) / (1024 * 1024)  # 转换为MB
                    cycles = backup.get('cycles', 0)
                    response += f"{i}. {name}\n   📅 创建时间: {create_time}\n   📊 大小: {size_mb:.1f}MB | 天数: {cycles}\n"
            else:
                response = f"😴 当前没有可用备份 (集群: {cluster_name})"
        else:
            response = f"❌ 获取备份列表失败: {result.message or '未知错误'}"
    except Exception as e:
        response = f"❌ 获取备份列表失败: {str(e)}"
    
    await bot.send(event, response, at_sender=True)

@exec_matcher.handle()
@require_admin
async def handle_exec_cmd(bot: Bot, event: Event, command: Match[str]):
    """处理执行命令"""
    
    try:
        # 检查命令参数是否存在
        if not command.available:
            response = "⚠️ 执行命令功能需要指定命令内容，请使用: 执行命令 <命令>"
            await bot.send(event, response, at_sender=True)
            return
        
        command_str = command.result
        
        # 调用执行命令API
        result = await dmp_advanced_api.execute_command("", "", command_str)
        
        if result.success:
            response = f"✅ 命令执行成功！\n"
            response += f"📝 命令: {command_str}\n"
            response += f"📊 状态: 已发送到服务器"
            
            # 如果有额外的响应信息，添加到响应中
            if result.data:
                response += f"\n📋 响应: {result.data}"
        else:
            response = f"❌ 命令执行失败: {result.message or '未知错误'}"
            
    except Exception as e:
        response = f"❌ 命令执行失败: {str(e)}"
    
    await bot.send(event, response, at_sender=True)

@rollback_matcher.handle()
@require_admin
async def handle_rollback_cmd(bot: Bot, event: Event, days: Match[int]):
    """处理回滚世界命令"""
    
    try:
        # 检查天数参数是否存在
        if not days.available:
            response = "❌ 请指定回滚天数，例如：回滚世界 2"
            await bot.send(event, response, at_sender=True)
            return
        
        days_value = days.result
        
        # 验证天数参数
        if days_value < 1 or days_value > 5:
            response = "❌ 回滚天数必须在1-5天之间"
            await bot.send(event, response, at_sender=True)
            return
        
        # 调用回滚API
        result = await dmp_advanced_api.rollback_world(days_value)
        
        if result.success:
            cluster_name = result.data.get("cluster_name", "自动选择") if result.data else "自动选择"
            
            # 安全地获取data字段，处理null的情况
            if result.data:
                rollback_version = result.data.get("rollbackVersion", days)
                status = result.data.get("status", "进行中")
            else:
                rollback_version = days
                status = "已完成"
            
            response = f"✅ 回滚世界成功！\n"
            response += f"📅 回滚天数: {days}天\n"
            response += f"🏗️ 集群: {cluster_name}\n"
            response += f"🔄 回滚版本: {rollback_version}\n"
            response += f"📊 状态: {status}"
        else:
            response = f"❌ 回滚世界失败: {result.message or '未知错误'}"
            
    except Exception as e:
        response = f"❌ 回滚世界失败: {str(e)}"
    
    await bot.send(event, response, at_sender=True)

@kick_matcher.handle()
@require_admin
async def handle_kick_cmd(bot: Bot, event: Event):
    """处理踢出玩家命令"""
    
    response = "⚠️ 踢出玩家功能需要指定玩家名称，请使用: /踢出玩家 <玩家名>"
    await bot.send(event, response, at_sender=True)

@ban_matcher.handle()
@require_admin
async def handle_ban_cmd(bot: Bot, event: Event):
    """处理封禁玩家命令"""
    
    response = "⚠️ 封禁玩家功能需要指定玩家名称，请使用: /封禁玩家 <玩家名>"
    await bot.send(event, response, at_sender=True)

@unban_matcher.handle()
@require_admin
async def handle_unban_cmd(bot: Bot, event: Event):
    """处理解封玩家命令"""
    
    response = "⚠️ 解封玩家功能需要指定玩家名称，请使用: /解封玩家 <玩家名>"
    await bot.send(event, response, at_sender=True)

# 英文命令处理器
@admin_eng_matcher.handle()
async def handle_admin_cmd_eng(bot: Bot, event: Event):
    """处理英文管理员命令帮助"""
    await handle_admin_cmd(bot, event)

@advanced_eng_matcher.handle()
async def handle_advanced_cmd_eng(bot: Bot, event: Event):
    """处理英文高级功能菜单"""
    await handle_advanced_cmd(bot, event)

@backup_eng_matcher.handle()
async def handle_backup_cmd_eng(bot: Bot, event: Event):
    """处理英文查看备份命令"""
    await handle_backup_cmd(bot, event)

@exec_eng_matcher.handle()
async def handle_exec_cmd_eng(bot: Bot, event: Event, command: Match[str]):
    """处理英文执行命令"""
    await handle_exec_cmd(bot, event, command)

@rollback_eng_matcher.handle()
async def handle_rollback_cmd_eng(bot: Bot, event: Event, days: Match[int]):
    """处理英文回滚世界命令"""
    await handle_rollback_cmd(bot, event, days)

@kick_eng_matcher.handle()
async def handle_kick_cmd_eng(bot: Bot, event: Event):
    """处理英文踢出玩家命令"""
    await handle_kick_cmd(bot, event)

@ban_eng_matcher.handle()
async def handle_ban_cmd_eng(bot: Bot, event: Event):
    """处理英文封禁玩家命令"""
    await handle_ban_cmd(bot, event)

@unban_eng_matcher.handle()
async def handle_unban_cmd_eng(bot: Bot, event: Event):
    """处理英文解封玩家命令"""
    await handle_unban_cmd(bot, event)

async def _generate_admin_menu_html() -> str:
    """生成美观的管理员菜单HTML界面"""
    
    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            body {{
                font-family: 'Microsoft YaHei', Arial, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                margin: 0;
                padding: 20px;
                min-height: 100vh;
            }}
            body::before {{
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: 
                    radial-gradient(circle at 20% 20%, rgba(255,255,255,0.1) 0%, transparent 50%),
                    radial-gradient(circle at 80% 80%, rgba(255,255,255,0.1) 0%, transparent 50%),
                    radial-gradient(circle at 40% 60%, rgba(255,255,255,0.05) 0%, transparent 50%);
                pointer-events: none;
            }}
            .container {{
                max-width: 420px;
                margin: 0 auto;
                position: relative;
                z-index: 1;
            }}
            .header {{
                background: rgba(255, 255, 255, 0.05);
                backdrop-filter: blur(30px) saturate(200%) brightness(1.2);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 20px;
                padding: 20px;
                margin-bottom: 20px;
                box-shadow: 
                    0 8px 32px rgba(0, 0, 0, 0.12),
                    inset 0 1px 0 rgba(255, 255, 255, 0.8),
                    0 1px 0 rgba(0, 0, 0, 0.05);
                text-align: center;
                position: relative;
                overflow: hidden;
            }}
            .header::before {{
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 1px;
                background: linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.8) 50%, transparent 100%);
                z-index: -1;
            }}
            .title {{
                font-size: 24px;
                font-weight: bold;
                color: #2d3748;
                margin-bottom: 5px;
            }}
            .subtitle {{
                font-size: 14px;
                color: #e53e3e;
                font-weight: 500;
            }}
            .menu-section {{
                background: rgba(255, 255, 255, 0.04);
                backdrop-filter: blur(25px) saturate(200%) brightness(1.1);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 18px;
                padding: 20px;
                margin-bottom: 15px;
                box-shadow: 
                    0 8px 32px rgba(0, 0, 0, 0.1),
                    inset 0 1px 0 rgba(255, 255, 255, 0.6),
                    0 1px 0 rgba(0, 0, 0, 0.03);
                position: relative;
                overflow: hidden;
            }}
            .menu-section::before {{
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 1px;
                background: linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.6) 50%, transparent 100%);
                z-index: -1;
            }}
            .section-title {{
                font-size: 16px;
                font-weight: bold;
                color: #2d3748;
                margin-bottom: 15px;
                display: flex;
                align-items: center;
            }}
            .menu-item {{
                display: flex;
                justify-content: space-between;
                padding: 8px 0;
                border-bottom: 1px solid #e2e8f0;
            }}
            .menu-item:last-child {{
                border-bottom: none;
            }}
            .command {{
                color: #3182ce;
                font-weight: 500;
                font-size: 14px;
            }}
            .description {{
                color: #718096;
                font-size: 14px;
                text-align: right;
            }}
            .warning {{
                background: rgba(255, 245, 157, 0.95);
                border-radius: 10px;
                padding: 15px;
                margin-top: 20px;
                border-left: 4px solid #f59e0b;
            }}
            .warning-text {{
                color: #92400e;
                font-size: 13px;
                font-weight: 500;
            }}
            .footer {{
                text-align: center;
                color: rgba(255, 255, 255, 0.8);
                font-size: 12px;
                margin-top: 20px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="title">🔧 管理员功能菜单</div>
                <div class="subtitle">Administrator Functions</div>
            </div>
            
            <div class="menu-section">
                <div class="section-title">💾 备份管理</div>
                <div class="menu-item">
                    <span class="command">📂 /查看备份</span>
                    <span class="description">查看可用世界备份</span>
                </div>
                <div class="menu-item">
                    <span class="command">⏪ /回滚世界</span>
                    <span class="description">回滚到指定天数前</span>
                </div>
            </div>
            
            <div class="menu-section">
                <div class="section-title">⚡ 游戏控制</div>
                <div class="menu-item">
                    <span class="command">💻 /执行命令</span>
                    <span class="description">在游戏内执行控制台命令</span>
                </div>
                <div class="menu-item">
                    <span class="command">🏗️ /集群管理</span>
                    <span class="description">集群切换和配置管理</span>
                </div>
            </div>
            
            <div class="menu-section">
                <div class="section-title">👥 玩家管理</div>
                <div class="menu-item">
                    <span class="command">👢 /踢出玩家</span>
                    <span class="description">踢出指定玩家</span>
                </div>
                <div class="menu-item">
                    <span class="command">🚫 /封禁玩家</span>
                    <span class="description">封禁指定玩家</span>
                </div>
                <div class="menu-item">
                    <span class="command">✅ /解封玩家</span>
                    <span class="description">解封指定玩家</span>
                </div>
            </div>
            
            <div class="warning">
                <div class="warning-text">
                    ⚠️ 管理员专用: 仅限超级用户使用<br>
                    💡 高级功能请使用: /高级功能
                </div>
            </div>
            
            <div class="footer">
                🔐 仅限超级用户使用 | 谨慎操作
            </div>
        </div>
    </body>
    </html>
    """
    
    return html_template

async def _generate_advanced_menu_html() -> str:
    """生成美观的高级功能菜单HTML界面"""
    
    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            body {{
                font-family: 'Microsoft YaHei', Arial, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                margin: 0;
                padding: 20px;
                min-height: 100vh;
            }}
            body::before {{
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: 
                    radial-gradient(circle at 20% 20%, rgba(255,255,255,0.1) 0%, transparent 50%),
                    radial-gradient(circle at 80% 80%, rgba(255,255,255,0.1) 0%, transparent 50%),
                    radial-gradient(circle at 40% 60%, rgba(255,255,255,0.05) 0%, transparent 50%);
                pointer-events: none;
            }}
            .container {{
                max-width: 420px;
                margin: 0 auto;
                position: relative;
                z-index: 1;
            }}
            .header {{
                background: rgba(255, 255, 255, 0.05);
                backdrop-filter: blur(30px) saturate(200%) brightness(1.2);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 20px;
                padding: 20px;
                margin-bottom: 20px;
                box-shadow: 
                    0 8px 32px rgba(0, 0, 0, 0.12),
                    inset 0 1px 0 rgba(255, 255, 255, 0.8),
                    0 1px 0 rgba(0, 0, 0, 0.05);
                text-align: center;
                position: relative;
                overflow: hidden;
            }}
            .header::before {{
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 1px;
                background: linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.8) 50%, transparent 100%);
                z-index: -1;
            }}
            .title {{
                font-size: 24px;
                font-weight: bold;
                color: #2d3748;
                margin-bottom: 5px;
            }}
            .subtitle {{
                font-size: 14px;
                color: #805ad5;
                font-weight: 500;
            }}
            .menu-section {{
                background: rgba(255, 255, 255, 0.04);
                backdrop-filter: blur(25px) saturate(200%) brightness(1.1);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 18px;
                padding: 20px;
                margin-bottom: 15px;
                box-shadow: 
                    0 8px 32px rgba(0, 0, 0, 0.1),
                    inset 0 1px 0 rgba(255, 255, 255, 0.6),
                    0 1px 0 rgba(0, 0, 0, 0.03);
                position: relative;
                overflow: hidden;
            }}
            .menu-section::before {{
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 1px;
                background: linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.6) 50%, transparent 100%);
                z-index: -1;
                backdrop-filter: blur(10px);
            }}
            .section-title {{
                font-size: 16px;
                font-weight: bold;
                color: #2d3748;
                margin-bottom: 15px;
                display: flex;
                align-items: center;
            }}
            .menu-item {{
                display: flex;
                justify-content: space-between;
                padding: 6px 0;
                border-bottom: 1px solid #e2e8f0;
            }}
            .menu-item:last-child {{
                border-bottom: none;
            }}
            .command {{
                color: #3182ce;
                font-weight: 500;
                font-size: 13px;
            }}
            .description {{
                color: #718096;
                font-size: 13px;
                text-align: right;
            }}
            .warning {{
                background: rgba(255, 245, 157, 0.95);
                border-radius: 10px;
                padding: 15px;
                margin-top: 20px;
                border-left: 4px solid #f59e0b;
            }}
            .warning-text {{
                color: #92400e;
                font-size: 12px;
                font-weight: 500;
                line-height: 1.4;
            }}
            .footer {{
                text-align: center;
                color: rgba(255, 255, 255, 0.8);
                font-size: 12px;
                margin-top: 20px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="title">🏗️ 高级管理功能</div>
                <div class="subtitle">Advanced Management Features</div>
            </div>
            
            <div class="menu-section">
                <div class="section-title">🗂️ 集群管理</div>
                <div class="menu-item">
                    <span class="command">📊 /集群状态</span>
                    <span class="description">查看所有集群运行状态</span>
                </div>
                <div class="menu-item">
                    <span class="command">🔄 /切换集群</span>
                    <span class="description">切换当前操作集群</span>
                </div>
                <div class="menu-item">
                    <span class="command">🔃 /刷新集群</span>
                    <span class="description">刷新集群列表缓存</span>
                </div>
                <div class="menu-item">
                    <span class="command">📋 /集群详情</span>
                    <span class="description">查看指定集群详细信息</span>
                </div>
            </div>
            
            <div class="menu-section">
                <div class="section-title">📊 数据管理</div>
                <div class="menu-item">
                    <span class="command">💾 /缓存状态</span>
                    <span class="description">查看缓存系统状态</span>
                </div>
                <div class="menu-item">
                    <span class="command">🗑️ /清理缓存</span>
                    <span class="description">清理指定类型缓存</span>
                </div>
                <div class="menu-item">
                    <span class="command">📈 /缓存统计</span>
                    <span class="description">查看详细缓存统计</span>
                </div>
                <div class="menu-item">
                    <span class="command">🔧 /缓存帮助</span>
                    <span class="description">显示缓存管理帮助</span>
                </div>
            </div>
            
            <div class="menu-section">
                <div class="section-title">🗜️ 数据压缩</div>
                <div class="menu-item">
                    <span class="command">📊 /数据分析</span>
                    <span class="description">分析数据库大小分布</span>
                </div>
                <div class="menu-item">
                    <span class="command">🗜️ /压缩数据</span>
                    <span class="description">压缩指定日期数据</span>
                </div>
                <div class="menu-item">
                    <span class="command">📦 /归档数据</span>
                    <span class="description">归档指定月份数据</span>
                </div>
                <div class="menu-item">
                    <span class="command">📁 /查看归档</span>
                    <span class="description">查看归档文件列表</span>
                </div>
            </div>
            
            <div class="menu-section">
                <div class="section-title">⚙️ 系统配置</div>
                <div class="menu-item">
                    <span class="command">📋 /配置状态</span>
                    <span class="description">查看当前配置状态</span>
                </div>
                <div class="menu-item">
                    <span class="command">🔍 /查看配置</span>
                    <span class="description">查看完整配置内容</span>
                </div>
                <div class="menu-item">
                    <span class="command">✅ /验证配置</span>
                    <span class="description">验证配置正确性</span>
                </div>
                <div class="menu-item">
                    <span class="command">🔗 /测试连接</span>
                    <span class="description">测试DMP服务器连接</span>
                </div>
            </div>
            
            <div class="warning">
                <div class="warning-text">
                    ⚠️ 高级功能说明:<br>
                    • 🔐 所有功能均需超级用户权限<br>
                    • 💡 使用前请先了解对应功能的作用<br>
                    • 🚨 某些操作不可逆，请谨慎使用
                </div>
            </div>
            
            <div class="footer">
                🔐 超级用户专用 | 高级管理功能
            </div>
        </div>
    </body>
    </html>
    """
    
    return html_template

# 初始化DMP Advanced API实例
def init_dmp_advanced_api():
    global dmp_advanced_api
    if dmp_advanced_api is None:
        dmp_advanced_api = DMPAdvancedAPI()
        print("✅ DMP Advanced API 实例初始化成功")

# 在模块加载时初始化
init_dmp_advanced_api() 