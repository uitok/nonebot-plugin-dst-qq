
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

# 创建响应器 - 设置明确的优先级和权限
admin_matcher = on_alconna(admin_cmd, priority=1, permission=SUPERUSER)
advanced_matcher = on_alconna(advanced_cmd, priority=1, permission=SUPERUSER)
backup_matcher = on_alconna(backup_cmd, priority=1, permission=SUPERUSER)
exec_matcher = on_alconna(exec_cmd, priority=1, permission=SUPERUSER)
rollback_matcher = on_alconna(rollback_cmd, priority=1, permission=SUPERUSER)
kick_matcher = on_alconna(kick_cmd, priority=1, permission=SUPERUSER)
ban_matcher = on_alconna(ban_cmd, priority=1, permission=SUPERUSER)
unban_matcher = on_alconna(unban_cmd, priority=1, permission=SUPERUSER)

admin_eng_matcher = on_alconna(admin_cmd_eng, priority=1, permission=SUPERUSER)
advanced_eng_matcher = on_alconna(advanced_cmd_eng, priority=1, permission=SUPERUSER)
backup_eng_matcher = on_alconna(backup_cmd_eng, priority=1, permission=SUPERUSER)
exec_eng_matcher = on_alconna(exec_cmd_eng, priority=1, permission=SUPERUSER)
rollback_eng_matcher = on_alconna(rollback_cmd_eng, priority=1, permission=SUPERUSER)
kick_eng_matcher = on_alconna(kick_cmd_eng, priority=1, permission=SUPERUSER)
ban_eng_matcher = on_alconna(ban_cmd_eng, priority=1, permission=SUPERUSER)
unban_eng_matcher = on_alconna(unban_cmd_eng, priority=1, permission=SUPERUSER)

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
            cluster_name = await self.get_first_available_cluster()
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
            cluster_name = await self.get_first_available_cluster()
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
            cluster_name = await self.get_first_available_cluster()
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
            cluster_name = await self.get_first_available_cluster()
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
            cluster_name = await self.get_first_available_cluster()
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
            cluster_name = await self.get_first_available_cluster()
            if not cluster_name:
                return APIResponse(code=404, message="没有可用的集群")
        
        params = {"clusterName": cluster_name}
        
        result = await self.get("/chat/statistics", params=params)
        
        # 在结果中添加集群信息
        if result.success and isinstance(result.data, dict):
            result.data["cluster_name"] = cluster_name
        
        return result

# 命令处理函数
@admin_matcher.handle()
async def handle_admin_cmd(bot: Bot, event: Event):
    """处理管理员命令帮助"""
    # 由于使用了 permission=SUPERUSER，这里不需要额外的权限检查
    # 如果函数被执行，说明用户已经通过了权限检查
    
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

@advanced_matcher.handle()
async def handle_advanced_cmd(bot: Bot, event: Event):
    """处理高级功能菜单"""
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
async def handle_exec_cmd(bot: Bot, event: Event, command: Match[str]):
    """处理执行命令"""
    # 由于使用了 permission=SUPERUSER，这里不需要额外的权限检查
    
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
async def handle_rollback_cmd(bot: Bot, event: Event, days: Match[int]):
    """处理回滚世界命令"""
    # 由于使用了 permission=SUPERUSER，这里不需要额外的权限检查
    
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
async def handle_kick_cmd(bot: Bot, event: Event):
    """处理踢出玩家命令"""
    # 由于使用了 permission=SUPERUSER，这里不需要额外的权限检查
    
    response = "⚠️ 踢出玩家功能需要指定玩家名称，请使用: /踢出玩家 <玩家名>"
    await bot.send(event, response, at_sender=True)

@ban_matcher.handle()
async def handle_ban_cmd(bot: Bot, event: Event):
    """处理封禁玩家命令"""
    # 由于使用了 permission=SUPERUSER，这里不需要额外的权限检查
    
    response = "⚠️ 封禁玩家功能需要指定玩家名称，请使用: /封禁玩家 <玩家名>"
    await bot.send(event, response, at_sender=True)

@unban_matcher.handle()
async def handle_unban_cmd(bot: Bot, event: Event):
    """处理解封玩家命令"""
    # 由于使用了 permission=SUPERUSER，这里不需要额外的权限检查
    
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

# 初始化DMP Advanced API实例
def init_dmp_advanced_api():
    global dmp_advanced_api
    if dmp_advanced_api is None:
        dmp_advanced_api = DMPAdvancedAPI()
        print("✅ DMP Advanced API 实例初始化成功")

# 在模块加载时初始化
init_dmp_advanced_api() 