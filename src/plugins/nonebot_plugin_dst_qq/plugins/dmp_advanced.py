
import asyncio
import re
from typing import Dict, Any, List, Optional
import httpx
from nonebot import get_driver, get_plugin_config
from nonebot.adapters.onebot.v11 import Bot
from nonebot.adapters import Event
from nonebot.permission import SUPERUSER
from nonebot_plugin_alconna import on_alconna, Alconna, Args, Command, Option, Subcommand, Match

# 导入配置
from ..config import Config

# 创建DMP Advanced API实例
dmp_advanced_api = None

# 获取配置函数
def get_config() -> Config:
    """获取插件配置"""
    return get_plugin_config(Config)

# 创建Alconna命令
admin_cmd = Alconna("管理命令")
backup_cmd = Alconna("查看备份")
exec_cmd = Alconna("执行命令", Args["command", str])
rollback_cmd = Alconna("回滚世界", Args["days", int])
kick_cmd = Alconna("踢出玩家")
ban_cmd = Alconna("封禁玩家")
unban_cmd = Alconna("解封玩家")

# 创建命令别名
admin_cmd_eng = Alconna("admin")
backup_cmd_eng = Alconna("backup")
exec_cmd_eng = Alconna("exec", Args["command", str])
rollback_cmd_eng = Alconna("rollback", Args["days", int])
kick_cmd_eng = Alconna("kick")
ban_cmd_eng = Alconna("ban")
unban_cmd_eng = Alconna("unban")

# 创建响应器 - 设置明确的优先级和权限
admin_matcher = on_alconna(admin_cmd, priority=1, permission=SUPERUSER)
backup_matcher = on_alconna(backup_cmd, priority=1, permission=SUPERUSER)
exec_matcher = on_alconna(exec_cmd, priority=1, permission=SUPERUSER)
rollback_matcher = on_alconna(rollback_cmd, priority=1, permission=SUPERUSER)
kick_matcher = on_alconna(kick_cmd, priority=1, permission=SUPERUSER)
ban_matcher = on_alconna(ban_cmd, priority=1, permission=SUPERUSER)
unban_matcher = on_alconna(unban_cmd, priority=1, permission=SUPERUSER)

admin_eng_matcher = on_alconna(admin_cmd_eng, priority=1, permission=SUPERUSER)
backup_eng_matcher = on_alconna(backup_cmd_eng, priority=1, permission=SUPERUSER)
exec_eng_matcher = on_alconna(exec_cmd_eng, priority=1, permission=SUPERUSER)
rollback_eng_matcher = on_alconna(rollback_cmd_eng, priority=1, permission=SUPERUSER)
kick_eng_matcher = on_alconna(kick_cmd_eng, priority=1, permission=SUPERUSER)
ban_eng_matcher = on_alconna(ban_cmd_eng, priority=1, permission=SUPERUSER)
unban_eng_matcher = on_alconna(unban_cmd_eng, priority=1, permission=SUPERUSER)

class DMPAdvancedAPI:
    """DMP 高级API客户端"""
    
    def __init__(self):
        config = get_config()
        self.base_url = config.dmp_base_url
        self.token = config.dmp_token
        self.headers = {
            "Authorization": self.token  # 直接使用token，不使用Bearer前缀
        }
        # 设置超时时间
        self.timeout = 30.0
    
    async def _make_request(self, method: str, url: str, **kwargs) -> dict:
        """统一的请求处理方法"""
        try:
            # 合并headers，避免重复传递
            headers = self.headers.copy()
            if 'headers' in kwargs:
                headers.update(kwargs.pop('headers'))
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                if method.upper() == "GET":
                    response = await client.get(url, headers=headers, **kwargs)
                elif method.upper() == "POST":
                    response = await client.post(url, headers=headers, **kwargs)
                else:
                    raise ValueError(f"不支持的HTTP方法: {method}")
                
                # 检查HTTP状态码
                response.raise_for_status()
                
                # 尝试解析JSON响应
                try:
                    return response.json()
                except:
                    # 如果不是JSON，返回文本内容
                    return {"code": 200, "data": response.text}
                
        except httpx.TimeoutException:
            return {"code": 408, "message": "请求超时，请稍后重试"}
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                return {"code": 401, "message": "Token认证失败，请检查token是否有效"}
            elif e.response.status_code == 403:
                return {"code": 403, "message": "权限不足"}
            elif e.response.status_code == 404:
                return {"code": 404, "message": "API接口不存在"}
            else:
                return {"code": e.response.status_code, "message": f"HTTP错误: {e.response.status_code}"}
        except httpx.RequestError as e:
            return {"code": 500, "message": f"网络请求错误: {str(e)}"}
        except Exception as e:
            return {"code": 500, "message": f"未知错误: {str(e)}"}
    
    async def get_available_clusters(self) -> dict:
        """获取所有可用的集群列表"""
        url = f"{self.base_url}/setting/clusters"
        return await self._make_request("GET", url)
    
    async def get_first_available_cluster(self) -> str:
        """获取第一个可用的集群名称"""
        clusters_result = await self.get_available_clusters()
        if clusters_result.get("code") == 200:
            clusters = clusters_result.get("data", [])
            if clusters:
                cluster_name = clusters[0].get("clusterName", "")
                print(f"🔍 自动选择集群: {cluster_name}")
                return cluster_name
        return None
    
    async def get_backup_list(self, cluster_name: str = None) -> dict:
        """获取备份列表"""
        if not cluster_name:
            cluster_name = await self.get_first_available_cluster()
            if not cluster_name:
                return {"code": 404, "message": "没有可用的集群"}
        
        url = f"{self.base_url}/tools/backup"
        params = {"clusterName": cluster_name}
        
        result = await self._make_request("GET", url, params=params)
        
        # 在结果中添加集群信息
        if result.get("code") == 200 or result.get("code") == 0:
            result["cluster_name"] = cluster_name
        
        return result
    
    async def create_backup(self, cluster_name: str = None) -> dict:
        """创建备份"""
        if not cluster_name:
            cluster_name = await self.get_first_available_cluster()
            if not cluster_name:
                return {"code": 404, "message": "没有可用的集群"}
        
        url = f"{self.base_url}/backup/create"
        data = {"clusterName": cluster_name}
        
        result = await self._make_request("POST", url, json=data)
        
        # 在结果中添加集群信息
        if result.get("code") == 200 or result.get("code") == 0:
            result["cluster_name"] = cluster_name
        
        return result
    
    async def execute_command(self, cluster_name: str, world_name: str, command: str) -> dict:
        """执行命令"""
        url = f"{self.base_url}/home/exec"
        
        headers = {
            "X-I18n-Lang": "zh",
            "Authorization": self.token,
            "Content-Type": "application/json"
        }
        
        data = {
            "type": "console",
            "extraData": command,
            "clusterName": cluster_name,
            "worldName": world_name
        }
        
        return await self._make_request("POST", url, headers=headers, json=data)
    
    async def rollback_world(self, days: int, cluster_name: str = None) -> dict:
        """回档世界"""
        if not cluster_name:
            cluster_name = await self.get_first_available_cluster()
            if not cluster_name:
                return {"code": 404, "message": "没有可用的集群"}
        
        if days < 1 or days > 5:
            return {"code": 400, "message": "回档天数必须在1-5天之间"}
        
        # 根据API文档，使用 /home/exec 接口
        url = f"{self.base_url}/home/exec"
        
        # 设置必要的headers
        headers = {
            "X-I18n-Lang": "zh",
            "Content-Type": "application/json"
        }
        
        data = {
            "type": "rollback",
            "extraData": days,
            "clusterName": cluster_name,
            "worldName": ""
        }
        
        result = await self._make_request("POST", url, headers=headers, json=data)
        
        # 在结果中添加集群信息
        if result.get("code") == 200 or result.get("code") == 0:
            result["cluster_name"] = cluster_name
        
        return result
    
    async def reset_world(self, cluster_name: str = None, world_name: str = "Master") -> dict:
        """重置世界"""
        if not cluster_name:
            cluster_name = await self.get_first_available_cluster()
            if not cluster_name:
                return {"code": 404, "message": "没有可用的集群"}
        
        url = f"{self.base_url}/world/reset"
        data = {
            "clusterName": cluster_name,
            "worldName": world_name
        }
        
        result = await self._make_request("POST", url, json=data)
        
        # 在结果中添加集群信息
        if result.get("code") == 200 or result.get("code") == 0:
            result["cluster_name"] = cluster_name
        
        return result
    
    async def get_chat_history(self, cluster_name: str = None, world_name: str = "", lines: int = 50) -> dict:
        """获取聊天历史"""
        if not cluster_name:
            cluster_name = await self.get_first_available_cluster()
            if not cluster_name:
                return {"code": 404, "message": "没有可用的集群"}
        
        url = f"{self.base_url}/chat/history"
        params = {
            "clusterName": cluster_name,
            "lines": lines
        }
        if world_name:
            params["worldName"] = world_name
        
        result = await self._make_request("GET", url, params=params)
        
        # 在结果中添加集群信息
        if result.get("code") == 200 or result.get("code") == 0:
            result["cluster_name"] = cluster_name
        
        return result
    
    async def get_chat_statistics(self, cluster_name: str = None) -> dict:
        """获取聊天统计"""
        if not cluster_name:
            config = get_config()
            cluster_name = await config.get_first_cluster()
        
        url = f"{self.base_url}/chat/statistics"
        params = {"clusterName": cluster_name}
        
        return await self._make_request("GET", url, params=params)

# 命令处理函数
@admin_matcher.handle()
async def handle_admin_cmd(bot: Bot, event: Event):
    """处理管理员命令帮助"""
    # 由于使用了 permission=SUPERUSER，这里不需要额外的权限检查
    # 如果函数被执行，说明用户已经通过了权限检查
    
    help_text = """🔧 管理员命令帮助

📋 备份管理:
• /查看备份 - 查看可用的世界备份
• /回滚世界 - 将世界回滚到指定备份

⚡ 命令执行:
• /执行命令 - 在游戏内执行控制台命令

👥 玩家管理:
• /踢出玩家 - 踢出指定玩家
• /封禁玩家 - 封禁指定玩家
• /解封玩家 - 解封指定玩家

📝 使用说明:
• 默认集群为: cx
• 支持中英文命令"""
    
    await bot.send(event, help_text, at_sender=True)

@backup_matcher.handle()
async def handle_backup_cmd(bot: Bot, event: Event):
    """处理查看备份命令"""
    # 由于使用了 permission=SUPERUSER，这里不需要额外的权限检查
    
    try:
        # 自动获取备份列表（不指定集群，让API自动选择）
        result = await dmp_advanced_api.get_backup_list()
        
        if result.get("code") == 200:
            data = result.get("data", {})
            backup_files = data.get('backupFiles', [])
            disk_usage = data.get('diskUsage', 0)
            
            # 获取实际使用的集群名称
            cluster_name = result.get("cluster_name", "自动选择")
            
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
            response = f"❌ 获取备份列表失败: {result.get('message', '未知错误')}"
    except Exception as e:
        response = f"❌ 获取备份列表失败: {str(e)}"
    
    await bot.send(event, response, at_sender=True)

@exec_matcher.handle()
async def handle_exec_cmd(bot: Bot, event: Event):
    """处理执行命令"""
    # 由于使用了 permission=SUPERUSER，这里不需要额外的权限检查
    
    try:
        # 从事件中获取命令参数
        message = event.get_message()
        if not message:
            response = "❌ 无法获取命令参数"
            await bot.send(event, response, at_sender=True)
            return
        
        # 解析命令参数
        text = message.extract_plain_text()
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            response = "⚠️ 执行命令功能需要指定命令内容，请使用: 执行命令 <命令>"
            await bot.send(event, response, at_sender=True)
            return
        
        command = parts[1]
        
        # 调用执行命令API
        result = await dmp_advanced_api.execute_command("", "", command)
        
        if result.get("code") == 200 or result.get("code") == 0:
            response = f"✅ 命令执行成功！\n"
            response += f"📝 命令: {command}\n"
            response += f"📊 状态: 已发送到服务器"
            
            # 如果有额外的响应信息，添加到响应中
            if result.get("data"):
                response += f"\n📋 响应: {result.get('data')}"
        else:
            response = f"❌ 命令执行失败: {result.get('message', '未知错误')}"
            
    except Exception as e:
        response = f"❌ 命令执行失败: {str(e)}"
    
    await bot.send(event, response, at_sender=True)

@rollback_matcher.handle()
async def handle_rollback_cmd(bot: Bot, event: Event):
    """处理回滚世界命令"""
    # 由于使用了 permission=SUPERUSER，这里不需要额外的权限检查
    
    try:
        # 从事件中获取命令参数
        message = event.get_message()
        if not message:
            response = "❌ 无法获取命令参数"
            await bot.send(event, response, at_sender=True)
            return
        
        # 解析天数参数
        text = message.extract_plain_text()
        parts = text.split()
        if len(parts) < 2:
            response = "❌ 请指定回滚天数，例如：回滚世界 2"
            await bot.send(event, response, at_sender=True)
            return
        
        try:
            days = int(parts[1])
        except ValueError:
            response = "❌ 回滚天数必须是数字"
            await bot.send(event, response, at_sender=True)
            return
        
        # 验证天数参数
        if days < 1 or days > 5:
            response = "❌ 回滚天数必须在1-5天之间"
            await bot.send(event, response, at_sender=True)
            return
        
        # 调用回滚API
        result = await dmp_advanced_api.rollback_world(days)
        
        if result.get("code") == 200 or result.get("code") == 0:
            cluster_name = result.get("cluster_name", "自动选择")
            
            # 安全地获取data字段，处理null的情况
            data = result.get("data")
            if data:
                rollback_version = data.get("rollbackVersion", days)
                status = data.get("status", "进行中")
            else:
                rollback_version = days
                status = "已完成"
            
            response = f"✅ 回滚世界成功！\n"
            response += f"📅 回滚天数: {days}天\n"
            response += f"🏗️ 集群: {cluster_name}\n"
            response += f"🔄 回滚版本: {rollback_version}\n"
            response += f"📊 状态: {status}"
        else:
            response = f"❌ 回滚世界失败: {result.get('message', '未知错误')}"
            
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

@backup_eng_matcher.handle()
async def handle_backup_cmd_eng(bot: Bot, event: Event):
    """处理英文查看备份命令"""
    await handle_backup_cmd(bot, event)

@exec_eng_matcher.handle()
async def handle_exec_cmd_eng(bot: Bot, event: Event):
    """处理英文执行命令"""
    await handle_exec_cmd(bot, event)

@rollback_eng_matcher.handle()
async def handle_rollback_cmd_eng(bot: Bot, event: Event):
    """处理英文回滚世界命令"""
    await handle_rollback_cmd(bot, event)

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