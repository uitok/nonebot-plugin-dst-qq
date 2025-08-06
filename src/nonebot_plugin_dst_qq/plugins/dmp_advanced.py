import asyncio
import re
from typing import Dict, Any, List, Optional
import httpx
from nonebot import on_command, on_regex, on_message
from nonebot.adapters import Event
from nonebot.adapters.onebot.v11 import Bot, Message
from nonebot.params import CommandArg, RegexGroup
from nonebot.permission import SUPERUSER
from nonebot.rule import to_me
from nonebot.typing import T_State
from nonebot.exception import FinishedException

# 导入配置
from ..config import Config
from .. import get_config
from ..database import chat_db
config = get_config()


async def admin_permission(event: Event) -> bool:
    """自定义管理员权限检查器"""
    # 检查是否为超级用户
    try:
        # 获取用户ID
        user_id = event.get_user_id()
        
        # 从配置中获取超级用户列表
        from nonebot import get_driver
        driver = get_driver()
        superusers = driver.config.superusers
        
        # 检查用户是否为超级用户
        if user_id in superusers:
            return True
        
        # 可以在这里添加其他权限检查逻辑
        # 例如：检查用户ID是否在管理员列表中
        # admin_users = ["123456789", "987654321"]  # 示例管理员ID
        # return user_id in admin_users
        
        return False
    except Exception as e:
        # 如果出现错误，返回False
        print(f"权限检查错误: {e}")
        return False


class DMPAdvancedAPI:
    """DMP 高级API客户端"""
    
    def __init__(self):
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
            return {"code": 500, "message": f"请求处理错误: {str(e)}"}
    
    async def get_backup_list(self, cluster_name: str = None) -> dict:
        """获取备份列表"""
        if not cluster_name:
            cluster_name = await config.get_first_cluster()
        
        url = f"{self.base_url}/tools/backup"
        params = {"clusterName": cluster_name}
        
        return await self._make_request("GET", url, params=params)
    
    async def create_backup(self, cluster_name: str = None) -> dict:
        """创建备份"""
        if not cluster_name:
            cluster_name = await config.get_first_cluster()
        
        url = f"{self.base_url}/tools/backup"
        
        # 准备请求头
        headers = {
            "Accept-Language": "X-I18n-Lang",
            "Authorization": self.token,
            "Content-Type": "application/json"
        }
        
        # 准备请求体
        data = {
            "clusterName": cluster_name
        }
        
        return await self._make_request("POST", url, headers=headers, json=data)
    
    async def get_connection_code(self, cluster_name: str = None) -> dict:
        """获取直连代码"""
        if not cluster_name:
            cluster_name = await config.get_first_cluster()
        
        url = f"{self.base_url}/external/api/connection_code"
        params = {"clusterName": cluster_name}
        
        return await self._make_request("GET", url, params=params)
    
    async def get_chat_logs(self, cluster_name: str = None, world_name: str = "World4", lines: int = 1000) -> dict:
        """获取聊天日志"""
        if not cluster_name:
            cluster_name = await config.get_first_cluster()
        
        url = f"{self.base_url}/logs/log_value"
        params = {
            "clusterName": cluster_name,
            "worldName": world_name,
            "line": lines,
            "type": "chat"
        }
        
        return await self._make_request("GET", url, params=params)
    
    async def rollback_world(self, cluster_name: str = None, world_name: str = "Master", days: int = 1) -> dict:
        """回档世界"""
        if not cluster_name:
            cluster_name = await config.get_first_cluster()
        
        url = f"{self.base_url}/home/exec"
        
        # 准备请求头
        headers = {
            "Accept-Language": "X-I18n-Lang",
            "Authorization": self.token,
            "Content-Type": "application/json"
        }
        
        # 准备请求体
        data = {
            "type": "rollback",
            "extraData": days,
            "clusterName": cluster_name,
            "worldName": world_name
        }
        
        return await self._make_request("POST", url, headers=headers, json=data)
    
    async def reset_world(self, cluster_name: str = None, world_name: str = "Master") -> dict:
        """重置世界"""
        if not cluster_name:
            cluster_name = await config.get_first_cluster()
        
        url = f"{self.base_url}/home/exec"
        
        # 准备请求头
        headers = {
            "Accept-Language": "X-I18n-Lang",
            "Authorization": self.token,
            "Content-Type": "application/json"
        }
        
        # 准备请求体
        data = {
            "type": "reset",
            "extraData": None,
            "clusterName": cluster_name,
            "worldName": world_name
        }
        
        return await self._make_request("POST", url, headers=headers, json=data)
    
    async def send_game_announcement(self, cluster_name: str = None, world_name: str = "", message: str = "") -> dict:
        """发送游戏公告 - 使用宣告API"""
        if not cluster_name:
            cluster_name = await config.get_first_cluster()
        
        url = f"{self.base_url}/v1/home/exec"
        
        # 准备请求头 - 按照curl命令的格式
        headers = {
            "X-I18n-Lang": "zh",
            "Authorization": self.token,
            "Content-Type": "application/json"
        }
        
        # 准备请求体 - 使用宣告API格式
        data = {
            "type": "announce",
            "extraData": message,
            "clusterName": cluster_name,
            "worldName": world_name
        }
        
        return await self._make_request("POST", url, headers=headers, json=data)


# 创建高级API客户端实例
dmp_advanced = DMPAdvancedAPI()

# 高级命令处理器
backup_list_cmd = on_command("查看备份", aliases={"备份", "backup", "backuplist"}, priority=5, permission=SUPERUSER)
create_backup_cmd = on_command("创建备份", aliases={"createbackup"}, priority=5, permission=SUPERUSER)
execute_cmd = on_command("执行", aliases={"exec", "command"}, priority=5, permission=SUPERUSER)
rollback_cmd = on_command("回档", aliases={"rollback"}, priority=5, permission=SUPERUSER)
reset_cmd = on_command("重置世界", aliases={"reset", "resetworld"}, priority=5, permission=SUPERUSER)
clusters_cmd = on_command("集群", aliases={"clusters", "clusterlist"}, priority=5, permission=SUPERUSER)
chat_history_cmd = on_command("聊天历史", aliases={"chathistory", "history"}, priority=5)
# 同步聊天功能已删除
pull_chat_cmd = on_command("拉取聊天", aliases={"pullchat", "pull"}, priority=5, permission=SUPERUSER)
chat_stats_cmd = on_command("聊天统计", aliases={"chatstats", "stats"}, priority=5)
admin_menu_cmd = on_command("管理命令", aliases={"admin", "adminmenu"}, priority=5, permission=SUPERUSER)


@backup_list_cmd.handle()
async def handle_backup_list(bot: Bot, event: Event, state: T_State, args: Message = CommandArg()):
    """处理备份列表命令"""
    message = ""
    try:
        # 使用第一个集群，忽略用户输入的集群参数
        config = get_config()
        cluster_name = await config.get_first_cluster()
        
        result = await dmp_advanced.get_backup_list(cluster_name)
        
        if result.get("code") == 200:
            data = result.get("data", [])
            message = f"💾 备份列表 (集群: {cluster_name})\n"
            message += "=" * 30 + "\n"
            
            # 检查数据类型
            if isinstance(data, list) and data:
                # 确保只处理前10个备份
                backup_count = min(len(data), 10)
                for i in range(backup_count):
                    backup = data[i]
                    if isinstance(backup, dict):
                        name = backup.get('name', 'Unknown')
                        size = backup.get('size', 'Unknown')
                        date = backup.get('date', 'Unknown')
                        # 格式化文件大小
                        if isinstance(size, (int, float)):
                            if size > 1024 * 1024 * 1024:  # GB
                                size_str = f"{size / (1024**3):.2f} GB"
                            elif size > 1024 * 1024:  # MB
                                size_str = f"{size / (1024**2):.2f} MB"
                            elif size > 1024:  # KB
                                size_str = f"{size / 1024:.2f} KB"
                            else:
                                size_str = f"{size} B"
                        else:
                            size_str = str(size)
                        
                        message += f"📁 {name}\n"
                        message += f"   📅 创建时间: {date}\n"
                        message += f"   💾 文件大小: {size_str}\n"
                        if backup.get('cycles'):
                            message += f"   🎮 游戏周期: {backup.get('cycles')}\n"
                        message += "\n"
                    else:
                        message += f"📁 {str(backup)}\n\n"
                
                if len(data) > 10:
                    message += f"📋 还有 {len(data) - 10} 个备份文件...\n"
            elif isinstance(data, dict):
                # 如果返回的是字典，解析备份文件列表
                backup_files = data.get('backupFiles', [])
                disk_usage = data.get('diskUsage', 0)
                
                if backup_files:
                    message += f"💿 磁盘使用率: {disk_usage:.1f}%\n\n"
                    message += "📋 备份文件列表:\n"
                    message += "-" * 20 + "\n"
                    
                    # 只显示前10个备份
                    backup_count = min(len(backup_files), 10)
                    for i in range(backup_count):
                        backup = backup_files[i]
                        if isinstance(backup, dict):
                            name = backup.get('name', 'Unknown')
                            create_time = backup.get('createTime', 'Unknown')
                            size = backup.get('size', 0)
                            cycles = backup.get('cycles', 0)
                            
                            # 格式化文件大小
                            if isinstance(size, (int, float)):
                                if size > 1024 * 1024 * 1024:  # GB
                                    size_str = f"{size / (1024**3):.2f} GB"
                                elif size > 1024 * 1024:  # MB
                                    size_str = f"{size / (1024**2):.2f} MB"
                                elif size > 1024:  # KB
                                    size_str = f"{size / 1024:.2f} KB"
                                else:
                                    size_str = f"{size} B"
                            else:
                                size_str = str(size)
                            
                            message += f"📁 {name}\n"
                            message += f"   📅 创建时间: {create_time}\n"
                            message += f"   💾 文件大小: {size_str}\n"
                            message += f"   🎮 游戏周期: {cycles}\n"
                            message += "\n"
                        else:
                            message += f"📁 {str(backup)}\n\n"
                    
                    if len(backup_files) > 10:
                        message += f"📋 还有 {len(backup_files) - 10} 个备份文件...\n"
                else:
                    message += "📭 暂无备份文件\n"
            elif data:
                # 其他类型的数据
                message += f"📊 备份数据: {str(data)}\n"
            else:
                message += "📭 暂无备份文件"
        else:
            message = f"❌ 获取备份列表失败: {result.get('message', '未知错误')}"
        
    except Exception as e:
        # 检查是否是NoneBot2框架异常
        error_type = type(e).__name__
        if any(framework_exception in error_type for framework_exception in [
            "FinishedException", "PausedException", "RejectedException", "IgnoredException"
        ]):
            return  # 静默处理框架异常
        
        # 简化错误信息
        error_msg = str(e)
        if len(error_msg) > 200:
            error_msg = error_msg[:200] + "..."
        message = f"❌ 获取备份列表时发生错误: {error_msg}"
    
    # 确保消息长度不超过QQ限制
    if len(message) > 4000:
        message = message[:4000] + "\n... (消息过长，已截断)"
    
    # 只调用一次finish
    await backup_list_cmd.finish(Message(message))


@create_backup_cmd.handle()
async def handle_create_backup(bot: Bot, event: Event, state: T_State):
    """处理创建备份命令"""
    message = ""
    try:
        # 使用第一个集群
        config = get_config()
        cluster_name = await config.get_first_cluster()
        result = await dmp_advanced.create_backup(cluster_name)
        
        if result.get("code") == 200:
            message = f"✅ 备份创建成功！(集群: {cluster_name})"
        else:
            message = f"❌ 创建备份失败: {result.get('message', '未知错误')}"
        
    except Exception as e:
        # 检查是否是NoneBot2框架异常
        error_type = type(e).__name__
        if any(framework_exception in error_type for framework_exception in [
            "FinishedException", "PausedException", "RejectedException", "IgnoredException"
        ]):
            return  # 静默处理框架异常
        
        # 简化错误信息
        error_msg = str(e)
        if len(error_msg) > 200:
            error_msg = error_msg[:200] + "..."
        message = f"❌ 创建备份时发生错误: {error_msg}"
    
    # 确保消息长度不超过QQ限制
    if len(message) > 4000:
        message = message[:4000] + "\n... (消息过长，已截断)"
    
    # 只调用一次finish
    await create_backup_cmd.finish(Message(message))


@execute_cmd.handle()
async def handle_execute_command(bot: Bot, event: Event, state: T_State, args: Message = CommandArg()):
    """处理执行命令"""
    message = ""
    try:
        # 解析命令参数: /执行 <世界> <命令>
        cmd_text = args.extract_plain_text().strip()
        parts = cmd_text.split()
        
        if len(parts) < 2:
            message = "❌ 用法: /执行 <世界名称> <命令>\n\n💡 示例:\n• /执行 World4 c_listallplayers()\n• /执行 Master c_give('gold', 10)"
        else:
            # 使用第一个集群
            config = get_config()
            cluster_name = await config.get_first_cluster()
            world_name = parts[0]
            command = " ".join(parts[1:])
            
            # 显示执行信息
            message = f"🔄 正在执行命令...\n📋 集群: {cluster_name}\n🌍 世界: {world_name}\n💻 命令: {command}"
            
            # 导入基础API模块
            from .dmp_api import dmp_api
            result = await dmp_api.execute_command(cluster_name, world_name, command)
            
            if result.get("code") == 200:
                data = result.get("data", {})
                if data:
                    message = f"✅ 命令执行成功!\n📋 集群: {cluster_name}\n🌍 世界: {world_name}\n💻 命令: {command}\n📊 结果: {data}"
                else:
                    message = f"✅ 命令执行成功!\n📋 集群: {cluster_name}\n🌍 世界: {world_name}\n💻 命令: {command}"
            else:
                error_msg = result.get('message', '未知错误')
                message = f"❌ 命令执行失败: {error_msg}\n📋 集群: {cluster_name}\n🌍 世界: {world_name}\n💻 命令: {command}"
        
    except Exception as e:
        error_msg = str(e)
        if len(error_msg) > 200:
            error_msg = error_msg[:200] + "..."
        message = f"❌ 执行命令时发生错误: {error_msg}"
    
    # 确保消息长度不超过QQ限制
    if len(message) > 4000:
        message = message[:4000] + "\n... (消息过长，已截断)"
    
    # 只调用一次finish
    await execute_cmd.finish(Message(message))


@rollback_cmd.handle()
async def handle_rollback(bot: Bot, event: Event, state: T_State, args: Message = CommandArg()):
    """处理回档命令"""
    message = ""
    try:
        # 解析参数: /回档 [天数]
        cmd_text = args.extract_plain_text().strip()
        
        if not cmd_text:
            message = "❌ 用法: /回档 <天数>\n\n💡 说明:\n• 天数范围: 1-5天\n• 示例: /回档 2 (回档2天)"
        else:
            try:
                days = int(cmd_text)
                
                # 验证天数范围
                if days < 1 or days > 5:
                    message = "❌ 回档天数必须在1-5天之间\n\n💡 用法: /回档 <天数>\n• 示例: /回档 2"
                else:
                    # 使用第一个集群
                    config = get_config()
                    cluster_name = await config.get_first_cluster()
                    
                    # 显示执行信息
                    message = f"🔄 正在执行回档操作...\n📋 集群: {cluster_name}\n🌍 世界: Master\n⏰ 回档天数: {days}天"
                    
                    # 执行回档
                    result = await dmp_advanced.rollback_world(cluster_name, "Master", days)
                    
                    if result.get("code") == 200:
                        data = result.get("data", {})
                        if data:
                            message = f"✅ 回档操作成功!\n📋 集群: {cluster_name}\n🌍 世界: Master\n⏰ 回档天数: {days}天\n📊 结果: {data}"
                        else:
                            message = f"✅ 回档操作成功!\n📋 集群: {cluster_name}\n🌍 世界: Master\n⏰ 回档天数: {days}天"
                    else:
                        error_msg = result.get('message', '未知错误')
                        message = f"❌ 回档操作失败: {error_msg}\n📋 集群: {cluster_name}\n🌍 世界: Master\n⏰ 回档天数: {days}天"
                        
            except ValueError:
                message = "❌ 天数必须是数字\n\n💡 用法: /回档 <天数>\n• 示例: /回档 2"
        
    except Exception as e:
        error_msg = str(e)
        if len(error_msg) > 200:
            error_msg = error_msg[:200] + "..."
        message = f"❌ 回档操作时发生错误: {error_msg}"
    
    # 确保消息长度不超过QQ限制
    if len(message) > 4000:
        message = message[:4000] + "\n... (消息过长，已截断)"
    
    # 只调用一次finish
    await rollback_cmd.finish(Message(message))


@reset_cmd.handle()
async def handle_reset_world(bot: Bot, event: Event, state: T_State, args: Message = CommandArg()):
    """处理重置世界命令"""
    message = ""
    try:
        # 解析参数: /重置世界 [世界名称]
        cmd_text = args.extract_plain_text().strip()
        world_name = cmd_text if cmd_text else "Master"
        
        # 使用第一个集群
        cluster_name = await config.get_first_cluster()
        
        # 显示执行信息
        message = f"🔄 正在执行重置世界操作...\n📋 集群: {cluster_name}\n🌍 世界: {world_name}\n⚠️ 警告: 此操作将重新生成世界!"
        
        # 执行重置世界
        result = await dmp_advanced.reset_world(cluster_name, world_name)
        
        if result.get("code") == 200:
            data = result.get("data", {})
            if data:
                message = f"✅ 重置世界操作成功!\n📋 集群: {cluster_name}\n🌍 世界: {world_name}\n📊 结果: {data}"
            else:
                message = f"✅ 重置世界操作成功!\n📋 集群: {cluster_name}\n🌍 世界: {world_name}"
        else:
            error_msg = result.get('message', '未知错误')
            message = f"❌ 重置世界操作失败: {error_msg}\n📋 集群: {cluster_name}\n🌍 世界: {world_name}"
        
    except Exception as e:
        error_msg = str(e)
        if len(error_msg) > 200:
            error_msg = error_msg[:200] + "..."
        message = f"❌ 重置世界操作时发生错误: {error_msg}"
    
    # 确保消息长度不超过QQ限制
    if len(message) > 4000:
        message = message[:4000] + "\n... (消息过长，已截断)"
    
    # 只调用一次finish
    await reset_cmd.finish(Message(message))


@clusters_cmd.handle()
async def handle_clusters(bot: Bot, event: Event, state: T_State):
    """处理集群列表命令"""
    message = ""
    try:
        # 导入基础API模块
        from .dmp_api import dmp_api
        result = await dmp_api.get_clusters()
        
        if result.get("code") == 200:
            data = result.get("data", [])
            message = "🌐 集群列表:\n"
            
            if data:
                for cluster in data:
                    name = cluster.get('clusterName', 'Unknown')
                    display_name = cluster.get('clusterDisplayName', name)
                    status = "✅ 启用" if cluster.get('status') else "❌ 禁用"
                    message += f"• {display_name} ({name}) - {status}\n"
            else:
                message += "暂无集群"
        else:
            message = f"❌ 获取集群列表失败: {result.get('message', '未知错误')}"
        
    except Exception as e:
        message = f"❌ 获取集群列表时发生错误: {str(e)}"
    
    # 确保消息长度不超过QQ限制
    if len(message) > 4000:
        message = message[:4000] + "\n... (消息过长，已截断)"
    
    # 只调用一次finish
    await clusters_cmd.finish(Message(message))


@chat_history_cmd.handle()
async def handle_chat_history(bot: Bot, event: Event, state: T_State, args: Message = CommandArg()):
    """处理获取聊天历史命令 - 自动拉取聊天日志"""
    message = ""
    try:
        # 解析参数: /聊天历史 [世界名] [行数]
        cmd_text = args.extract_plain_text().strip()
        parts = cmd_text.split()
        
        # 使用默认集群
        cluster_name = await config.get_first_cluster()
        world_name = "World4"  # 默认世界
        lines = 50  # 默认50行
        
        # 解析可选参数
        if parts:
            # 第一个参数可能是世界名或行数
            if parts[0].isdigit():
                # 第一个参数是行数
                lines = int(parts[0])
                if lines < 1:
                    lines = 50
            else:
                # 第一个参数是世界名
                world_name = parts[0]
                
                # 检查是否有第二个参数（行数）
                if len(parts) > 1 and parts[1].isdigit():
                    lines = int(parts[1])
                    if lines < 1:
                        lines = 50
        
        # 显示执行信息
        message = f"🔄 正在获取聊天历史...\n📋 集群: {cluster_name}\n🌍 世界: {world_name}\n⏰ 行数: {lines}"
        
        # 获取聊天日志
        result = await dmp_advanced.get_chat_logs(cluster_name, world_name, lines)
        
        if result.get("code") == 200:
            chat_logs = result.get("data", [])
            if isinstance(chat_logs, list) and chat_logs:
                # 格式化聊天记录
                formatted_logs = []
                for log in chat_logs[-lines:]:  # 只显示最新的指定行数
                    if isinstance(log, dict):
                        timestamp = log.get('timestamp', '')
                        player = log.get('player', '')
                        content = log.get('content', '')
                        if timestamp and player and content:
                            formatted_logs.append(f"[{timestamp}] {player}: {content}")
                        elif content:
                            formatted_logs.append(content)
                    elif isinstance(log, str):
                        formatted_logs.append(log)
                
                if formatted_logs:
                    message = f"✅ 聊天历史获取成功!\n📋 集群: {cluster_name}\n🌍 世界: {world_name}\n⏰ 显示最新 {len(formatted_logs)} 条记录:\n\n"
                    message += "\n".join(formatted_logs)
                else:
                    message = f"✅ 聊天历史获取成功!\n📋 集群: {cluster_name}\n🌍 世界: {world_name}\n⏰ 行数: {lines}\n📊 结果: 暂无聊天记录"
            else:
                message = f"✅ 聊天历史获取成功!\n📋 集群: {cluster_name}\n🌍 世界: {world_name}\n⏰ 行数: {lines}\n📊 结果: 暂无聊天记录"
        else:
            error_msg = result.get('message', '未知错误')
            message = f"❌ 获取聊天历史失败: {error_msg}\n📋 集群: {cluster_name}\n🌍 世界: {world_name}\n⏰ 行数: {lines}"
        
    except Exception as e:
        # 检查是否是NoneBot2框架异常
        error_type = type(e).__name__
        if any(framework_exception in error_type for framework_exception in [
            "FinishedException", "PausedException", "RejectedException", "IgnoredException"
        ]):
            return  # 静默处理框架异常
        
        # 简化错误信息
        error_msg = str(e)
        if len(error_msg) > 200:
            error_msg = error_msg[:200] + "..."
        message = f"❌ 获取聊天历史时发生错误: {error_msg}"
    
    # 确保消息长度不超过QQ限制
    if len(message) > 4000:
        message = message[:4000] + "\n... (消息过长，已截断)"
    
    # 只调用一次finish
    await chat_history_cmd.finish(Message(message))


# 同步聊天命令处理函数已删除


# 关闭聊天命令处理函数已删除


@pull_chat_cmd.handle()
async def handle_pull_chat(bot: Bot, event: Event, state: T_State, args: Message = CommandArg()):
    """处理拉取聊天命令"""
    message = ""
    try:
        # 解析参数: /拉取聊天 [集群名] [世界名] [行数]
        cmd_text = args.extract_plain_text().strip()
        parts = cmd_text.split()
        
        cluster_name = None
        world_name = "World4"
        lines = 1000
        
        if parts:
            if parts[0].lower() in ["all", "allclusters"]:
                cluster_name = "all"
            elif parts[0].lower() in ["allworlds", "allworld"]:
                world_name = "all"
            elif parts[0].lower() in ["alllines", "all"]:
                lines = "all"
            else:
                cluster_name = parts[0]
            
            if len(parts) > 1:
                world_name = parts[1]
            
            if len(parts) > 2:
                try:
                    lines = int(parts[2])
                    if lines < 1:
                        lines = 1000 # 默认行数
                except ValueError:
                    lines = 1000 # 默认行数
        
        if not cluster_name:
            message = "❌ 用法: /拉取聊天 [集群名] [世界名] [行数]\n\n💡 说明:\n• 集群名: 集群名称或all\n• 世界名: 世界名称或all\n• 行数: 数字或all\n• 示例: /拉取聊天 MyCluster World4 100"
        else:
            # 使用第一个集群
            cluster_name = await config.get_first_cluster() if cluster_name == "all" else cluster_name
            
            # 显示执行信息
            message = f"🔄 正在拉取聊天日志...\n📋 集群: {cluster_name}\n🌍 世界: {world_name}\n⏰ 行数: {lines}"
            
            # 获取聊天日志
            result = await dmp_advanced.get_chat_logs(cluster_name, world_name, lines)
            
            if result.get("code") == 200:
                chat_logs = result.get("data", [])
                if isinstance(chat_logs, list) and chat_logs:
                    # 保存到数据库
                    from ..database import chat_db
                    added_count = await chat_db.add_chat_history(cluster_name, world_name, chat_logs)
                    
                    message = f"✅ 聊天日志拉取并保存成功!\n📋 集群: {cluster_name}\n🌍 世界: {world_name}\n⏰ 行数: {lines}\n📊 拉取记录: {len(chat_logs)} 条\n💾 保存记录: {added_count} 条"
                else:
                    message = f"✅ 聊天日志拉取成功!\n📋 集群: {cluster_name}\n🌍 世界: {world_name}\n⏰ 行数: {lines}\n📊 结果: 暂无聊天记录"
            else:
                error_msg = result.get('message', '未知错误')
                message = f"❌ 拉取聊天日志失败: {error_msg}\n📋 集群: {cluster_name}\n🌍 世界: {world_name}\n⏰ 行数: {lines}"
        
    except Exception as e:
        error_msg = str(e)
        if len(error_msg) > 200:
            error_msg = error_msg[:200] + "..."
        message = f"❌ 拉取聊天日志时发生错误: {error_msg}"
    
    # 确保消息长度不超过QQ限制
    if len(message) > 4000:
        message = message[:4000] + "\n... (消息过长，已截断)"
    
    # 只调用一次finish
    await pull_chat_cmd.finish(Message(message))


@chat_stats_cmd.handle()
async def handle_chat_stats(bot: Bot, event: Event, state: T_State):
    """处理获取聊天历史统计命令"""
    message = ""
    try:
        # 获取数据库统计信息
        from ..database import chat_db
        stats = await chat_db.get_database_stats()
        
        message = "📊 聊天历史统计:\n"
        message += f"• 总聊天记录数: {stats.get('total_messages', 0)}\n"
        message += f"• 总玩家数: {stats.get('total_players', 0)}\n"
        message += f"• 最近24小时消息数: {stats.get('messages_24h', 0)}\n"
        message += f"• 数据库文件大小: {stats.get('file_size_mb', 0)} MB\n"
        
        # 获取玩家列表
        players = await chat_db.get_player_list()
        if players:
            message += f"\n👥 活跃玩家列表 (前10名):\n"
            for i, player in enumerate(players[:10], 1):
                message += f"{i}. {player.get('player_name', 'Unknown')} (ID: {player.get('player_id', 'N/A')}) - {player.get('message_count', 0)} 条消息\n"
        
    except Exception as e:
        error_msg = str(e)
        if len(error_msg) > 200:
            error_msg = error_msg[:200] + "..."
        message = f"❌ 获取聊天统计时发生错误: {error_msg}"
    
    # 确保消息长度不超过QQ限制
    if len(message) > 4000:
        message = message[:4000] + "\n... (消息过长，已截断)"
    
    # 只调用一次finish
    await chat_stats_cmd.finish(Message(message))


@admin_menu_cmd.handle()
async def handle_admin_menu(bot: Bot, event: Event, state: T_State):
    """处理管理命令菜单命令"""
    # 检查用户是否为管理员
    if not await admin_permission(event):
        await admin_menu_cmd.finish(Message("您不是管理员哦"))
        return
    
    help_text = """
🔧 晨曦 管理命令菜单

📋 管理命令:
• /查看备份 - 获取备份文件列表
• /创建备份 - 手动创建备份
• /执行 <世界> <命令> - 执行游戏命令
• /回档 <天数> - 回档指定天数 (1-5天)
• /重置世界 [世界名称] - 重置世界 (默认Master)
• /集群 - 获取集群列表
• /聊天历史 [世界名] [行数] - 获取聊天历史 (默认集群，默认50行)
• /聊天统计 - 获取聊天历史统计信息

💡 使用示例:
• /查看备份 - 获取备份列表
• /创建备份 - 创建备份
• /执行 World4 c_listallplayers() - 执行游戏命令
• /回档 2 - 回档2天
• /重置世界 - 重置Master世界
• /重置世界 Caves - 重置Caves世界
• /聊天历史 - 获取默认集群World4的最新50条聊天记录
• /聊天历史 Caves - 获取默认集群Caves的最新50条聊天记录
• /聊天历史 World4 100 - 获取默认集群World4的最新100条聊天记录

⚠️ 注意事项:
• 回档天数必须在1-5天之间
• 重置世界将重新生成世界，请谨慎使用
• 建议在执行危险操作前先创建备份
• 聊天历史功能会自动使用默认集群，无需指定集群名
    """
    
    await admin_menu_cmd.finish(Message(help_text))


# 私聊消息处理器已删除 