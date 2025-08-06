import asyncio
import re
from typing import Dict, Any, List, Optional
import httpx
from arclet.alconna import Alconna, Args, Field, Option, Subcommand
from arclet.alconna.typing import CommandMeta
from nonebot import on_alconna
from nonebot.adapters import Event
from nonebot.adapters.onebot.v11 import Bot, Message
from nonebot.params import Depends
from nonebot.permission import SUPERUSER
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
            return {"code": 500, "message": f"未知错误: {str(e)}"}
    
    async def get_backup_list(self, cluster_name: str = None) -> dict:
        """获取备份列表"""
        if not cluster_name:
            cluster_name = await config.get_first_cluster()
        
        url = f"{self.base_url}/backup/list"
        params = {"clusterName": cluster_name}
        
        return await self._make_request("GET", url, params=params)
    
    async def create_backup(self, cluster_name: str = None) -> dict:
        """创建备份"""
        if not cluster_name:
            cluster_name = await config.get_first_cluster()
        
        url = f"{self.base_url}/backup/create"
        data = {"clusterName": cluster_name}
        
        return await self._make_request("POST", url, json=data)
    
    async def get_connection_code(self, cluster_name: str = None) -> dict:
        """获取直连码"""
        if not cluster_name:
            cluster_name = await config.get_first_cluster()
        
        url = f"{self.base_url}/setting/connection"
        params = {"clusterName": cluster_name}
        
        return await self._make_request("GET", url, params=params)
    
    async def get_chat_logs(self, cluster_name: str = None, world_name: str = "World4", lines: int = 1000) -> dict:
        """获取聊天日志"""
        if not cluster_name:
            cluster_name = await config.get_first_cluster()
        
        url = f"{self.base_url}/chat/logs"
        params = {
            "clusterName": cluster_name,
            "worldName": world_name,
            "lines": lines
        }
        
        return await self._make_request("GET", url, params=params)
    
    async def rollback_world(self, cluster_name: str = None, world_name: str = "Master", days: int = 1) -> dict:
        """回档世界"""
        if not cluster_name:
            cluster_name = await config.get_first_cluster()
        
        url = f"{self.base_url}/world/rollback"
        data = {
            "clusterName": cluster_name,
            "worldName": world_name,
            "days": days
        }
        
        return await self._make_request("POST", url, json=data)
    
    async def reset_world(self, cluster_name: str = None, world_name: str = "Master") -> dict:
        """重置世界"""
        if not cluster_name:
            cluster_name = await config.get_first_cluster()
        
        url = f"{self.base_url}/world/reset"
        data = {
            "clusterName": cluster_name,
            "worldName": world_name
        }
        
        return await self._make_request("POST", url, json=data)
    
    async def execute_command(self, cluster_name: str, world_name: str, command: str) -> dict:
        """执行命令"""
        url = f"{self.base_url}/home/exec"
        
        # 准备请求头
        headers = {
            "X-I18n-Lang": "zh",
            "Authorization": self.token,
            "Content-Type": "application/json"
        }
        
        # 准备请求体
        data = {
            "type": "console",
            "extraData": command,
            "clusterName": cluster_name,
            "worldName": world_name
        }
        
        return await self._make_request("POST", url, headers=headers, json=data)
    
    async def send_game_announcement(self, cluster_name: str = None, world_name: str = "", message: str = "") -> dict:
        """发送游戏公告"""
        if not cluster_name:
            cluster_name = await config.get_first_cluster()
        
        url = f"{self.base_url}/chat/announce"
        data = {
            "clusterName": cluster_name,
            "worldName": world_name,
            "message": message
        }
        
        return await self._make_request("POST", url, json=data)


# 创建 DMPAdvancedAPI 实例
dmp_advanced = DMPAdvancedAPI()

# 管理员命令 - 使用 Alconna
admin_cmd = on_alconna(
    Alconna(
        "管理命令",
        meta=CommandMeta(
            description="显示管理员功能菜单",
            usage="管理命令",
            example="管理命令"
        )
    ),
    aliases={"admin", "管理员"},
    permission=SUPERUSER,
    priority=10
)

backup_list_cmd = on_alconna(
    Alconna(
        "查看备份",
        meta=CommandMeta(
            description="获取备份文件列表",
            usage="查看备份",
            example="查看备份"
        )
    ),
    aliases={"backup", "备份"},
    permission=SUPERUSER,
    priority=10
)

create_backup_cmd = on_alconna(
    Alconna(
        "创建备份",
        meta=CommandMeta(
            description="手动创建备份",
            usage="创建备份",
            example="创建备份"
        )
    ),
    aliases={"createbackup", "新建备份"},
    permission=SUPERUSER,
    priority=10
)

execute_cmd = on_alconna(
    Alconna(
        "执行",
        Args["world_name", str] = Field(description="世界名称"),
        Args["command", str] = Field(description="要执行的命令"),
        meta=CommandMeta(
            description="执行游戏命令",
            usage="执行 <世界> <命令>",
            example="执行 Master c_announce('Hello World')"
        )
    ),
    aliases={"exec", "cmd"},
    permission=SUPERUSER,
    priority=10
)

rollback_cmd = on_alconna(
    Alconna(
        "回档",
        Args.days[int] = Field(1, description="回档天数 (1-5)"),
        meta=CommandMeta(
            description="回档指定天数",
            usage="回档 <天数>",
            example="回档 1"
        )
    ),
    aliases={"rollback", "回退"},
    permission=SUPERUSER,
    priority=10
)

reset_world_cmd = on_alconna(
    Alconna(
        "重置世界",
        Args.world_name[str] = Field("Master", description="世界名称"),
        meta=CommandMeta(
            description="重置世界",
            usage="重置世界 [世界名称]",
            example="重置世界 Master"
        )
    ),
    aliases={"reset", "重置"},
    permission=SUPERUSER,
    priority=10
)

clusters_cmd = on_alconna(
    Alconna(
        "集群",
        meta=CommandMeta(
            description="获取集群列表",
            usage="集群",
            example="集群"
        )
    ),
    aliases={"clusters", "cluster"},
    permission=SUPERUSER,
    priority=10
)

chat_history_cmd = on_alconna(
    Alconna(
        "聊天历史",
        Args.world_name[str] = Field("Master", description="世界名称"),
        Args.lines[int] = Field(50, description="显示行数"),
        meta=CommandMeta(
            description="获取聊天历史",
            usage="聊天历史 [世界名] [行数]",
            example="聊天历史 Master 50"
        )
    ),
    aliases={"chathistory", "聊天记录"},
    permission=SUPERUSER,
    priority=10
)

pull_chat_cmd = on_alconna(
    Alconna(
        "拉取聊天",
        Args.world_name[str] = Field("Master", description="世界名称"),
        Args.lines[int] = Field(100, description="拉取行数"),
        meta=CommandMeta(
            description="拉取聊天记录到数据库",
            usage="拉取聊天 [世界名] [行数]",
            example="拉取聊天 Master 100"
        )
    ),
    aliases={"pullchat", "同步聊天"},
    permission=SUPERUSER,
    priority=10
)

chat_stats_cmd = on_alconna(
    Alconna(
        "聊天统计",
        meta=CommandMeta(
            description="获取聊天历史统计信息",
            usage="聊天统计",
            example="聊天统计"
        )
    ),
    aliases={"chatstats", "聊天数据"},
    permission=SUPERUSER,
    priority=10
)


# 命令处理器
@admin_cmd.handle()
async def handle_admin_menu(bot: Bot, event: Event):
    """处理管理员菜单"""
    admin_menu = """🔧 管理员功能菜单

📋 备份管理：
• /查看备份 - 获取备份文件列表
• /创建备份 - 手动创建备份

🎮 游戏控制：
• /执行 <世界> <命令> - 执行游戏命令
• /回档 <天数> - 回档指定天数 (1-5天)
• /重置世界 [世界名称] - 重置世界

💬 聊天管理：
• /聊天历史 [世界名] [行数] - 获取聊天历史
• /拉取聊天 [世界名] [行数] - 拉取聊天记录到数据库
• /聊天统计 - 获取聊天历史统计信息

🌍 系统管理：
• /集群 - 获取集群列表

💡 使用提示：
• 所有管理员命令都需要超级用户权限
• 方括号 [] 表示可选参数
• 尖括号 <> 表示必需参数"""
    
    await admin_cmd.finish(Message(admin_menu))


@backup_list_cmd.handle()
async def handle_backup_list(bot: Bot, event: Event):
    """处理备份列表查询"""
    try:
        result = await dmp_advanced.get_backup_list()
        
        if result.get("code") == 200:
            data = result.get("data", [])
            
            if data:
                backup_list = "📦 备份文件列表\n\n"
                for i, backup in enumerate(data, 1):
                    backup_list += f"{i}. {backup.get('name', 'N/A')}\n"
                    backup_list += f"   创建时间：{backup.get('createTime', 'N/A')}\n"
                    backup_list += f"   文件大小：{backup.get('size', 'N/A')}\n\n"
            else:
                backup_list = "📦 暂无备份文件"
            
            await backup_list_cmd.finish(Message(backup_list))
        else:
            error_msg = result.get("message", "未知错误")
            await backup_list_cmd.finish(Message(f"❌ 获取备份列表失败：{error_msg}"))
            
    except Exception as e:
        await backup_list_cmd.finish(Message(f"❌ 处理备份列表查询时出错：{str(e)}"))


@create_backup_cmd.handle()
async def handle_create_backup(bot: Bot, event: Event):
    """处理创建备份"""
    try:
        result = await dmp_advanced.create_backup()
        
        if result.get("code") == 200:
            await create_backup_cmd.finish(Message("✅ 备份创建成功！"))
        else:
            error_msg = result.get("message", "未知错误")
            await create_backup_cmd.finish(Message(f"❌ 创建备份失败：{error_msg}"))
            
    except Exception as e:
        await create_backup_cmd.finish(Message(f"❌ 处理创建备份时出错：{str(e)}"))


@execute_cmd.handle()
async def handle_execute_command(bot: Bot, event: Event, world_name: str, command: str):
    """处理执行命令"""
    try:
        config = get_config()
        cluster_name = await config.get_first_cluster()
        
        result = await dmp_advanced.execute_command(cluster_name, world_name, command)
        
        if result.get("code") == 200:
            await execute_cmd.finish(Message(f"✅ 命令执行成功：{command}"))
        else:
            error_msg = result.get("message", "未知错误")
            await execute_cmd.finish(Message(f"❌ 命令执行失败：{error_msg}"))
            
    except Exception as e:
        await execute_cmd.finish(Message(f"❌ 处理命令执行时出错：{str(e)}"))


@rollback_cmd.handle()
async def handle_rollback(bot: Bot, event: Event, days: int):
    """处理回档命令"""
    try:
        if days < 1 or days > 5:
            await rollback_cmd.finish(Message("❌ 回档天数必须在 1-5 之间"))
            return
        
        result = await dmp_advanced.rollback_world(days=days)
        
        if result.get("code") == 200:
            await rollback_cmd.finish(Message(f"✅ 回档 {days} 天成功！"))
        else:
            error_msg = result.get("message", "未知错误")
            await rollback_cmd.finish(Message(f"❌ 回档失败：{error_msg}"))
            
    except Exception as e:
        await rollback_cmd.finish(Message(f"❌ 处理回档命令时出错：{str(e)}"))


@reset_world_cmd.handle()
async def handle_reset_world(bot: Bot, event: Event, world_name: str = "Master"):
    """处理重置世界命令"""
    try:
        result = await dmp_advanced.reset_world(world_name=world_name)
        
        if result.get("code") == 200:
            await reset_world_cmd.finish(Message(f"✅ 世界 {world_name} 重置成功！"))
        else:
            error_msg = result.get("message", "未知错误")
            await reset_world_cmd.finish(Message(f"❌ 重置世界失败：{error_msg}"))
            
    except Exception as e:
        await reset_world_cmd.finish(Message(f"❌ 处理重置世界命令时出错：{str(e)}"))


@clusters_cmd.handle()
async def handle_clusters(bot: Bot, event: Event):
    """处理集群列表查询"""
    try:
        result = await dmp_advanced.get_connection_code()
        
        if result.get("code") == 200:
            data = result.get("data", [])
            
            if data:
                clusters_list = "🌍 集群列表\n\n"
                for i, cluster in enumerate(data, 1):
                    clusters_list += f"{i}. {cluster.get('clusterName', 'N/A')}\n"
                    clusters_list += f"   状态：{cluster.get('status', 'N/A')}\n"
                    clusters_list += f"   直连码：{cluster.get('connectionCode', 'N/A')}\n\n"
            else:
                clusters_list = "🌍 暂无可用集群"
            
            await clusters_cmd.finish(Message(clusters_list))
        else:
            error_msg = result.get("message", "未知错误")
            await clusters_cmd.finish(Message(f"❌ 获取集群列表失败：{error_msg}"))
            
    except Exception as e:
        await clusters_cmd.finish(Message(f"❌ 处理集群列表查询时出错：{str(e)}"))


@chat_history_cmd.handle()
async def handle_chat_history(bot: Bot, event: Event, world_name: str = "Master", lines: int = 50):
    """处理聊天历史查询"""
    try:
        result = await dmp_advanced.get_chat_logs(world_name=world_name, lines=lines)
        
        if result.get("code") == 200:
            data = result.get("data", [])
            
            if data:
                chat_history = f"💬 聊天历史 - {world_name} (最近 {lines} 条)\n\n"
                for i, chat in enumerate(data[-lines:], 1):
                    chat_history += f"{i}. {chat.get('time', 'N/A')} - {chat.get('player', 'N/A')}: {chat.get('message', 'N/A')}\n"
            else:
                chat_history = f"💬 世界 {world_name} 暂无聊天记录"
            
            await chat_history_cmd.finish(Message(chat_history))
        else:
            error_msg = result.get("message", "未知错误")
            await chat_history_cmd.finish(Message(f"❌ 获取聊天历史失败：{error_msg}"))
            
    except Exception as e:
        await chat_history_cmd.finish(Message(f"❌ 处理聊天历史查询时出错：{str(e)}"))


@pull_chat_cmd.handle()
async def handle_pull_chat(bot: Bot, event: Event, world_name: str = "Master", lines: int = 100):
    """处理拉取聊天记录"""
    try:
        result = await dmp_advanced.get_chat_logs(world_name=world_name, lines=lines)
        
        if result.get("code") == 200:
            data = result.get("data", [])
            
            if data:
                # 将聊天记录保存到数据库
                await chat_db.init_database()
                count = 0
                for chat in data:
                    try:
                        await chat_db.add_chat_message(
                            world_name=world_name,
                            player_name=chat.get('player', 'Unknown'),
                            message=chat.get('message', ''),
                            timestamp=chat.get('time', '')
                        )
                        count += 1
                    except Exception as e:
                        print(f"保存聊天记录失败: {e}")
                        continue
                
                await pull_chat_cmd.finish(Message(f"✅ 成功拉取并保存 {count} 条聊天记录到数据库"))
            else:
                await pull_chat_cmd.finish(Message(f"💬 世界 {world_name} 暂无聊天记录"))
        else:
            error_msg = result.get("message", "未知错误")
            await pull_chat_cmd.finish(Message(f"❌ 拉取聊天记录失败：{error_msg}"))
            
    except Exception as e:
        await pull_chat_cmd.finish(Message(f"❌ 处理拉取聊天记录时出错：{str(e)}"))


@chat_stats_cmd.handle()
async def handle_chat_stats(bot: Bot, event: Event):
    """处理聊天统计查询"""
    try:
        await chat_db.init_database()
        stats = await chat_db.get_chat_statistics()
        
        if stats:
            chat_stats = "📊 聊天统计信息\n\n"
            chat_stats += f"总消息数：{stats.get('total_messages', 0)}\n"
            chat_stats += f"活跃玩家数：{stats.get('unique_players', 0)}\n"
            chat_stats += f"活跃世界数：{stats.get('unique_worlds', 0)}\n"
            chat_stats += f"最早消息：{stats.get('earliest_message', 'N/A')}\n"
            chat_stats += f"最新消息：{stats.get('latest_message', 'N/A')}\n"
            
            # 显示最活跃的玩家
            top_players = stats.get('top_players', [])
            if top_players:
                chat_stats += "\n🏆 最活跃玩家：\n"
                for i, player in enumerate(top_players[:5], 1):
                    chat_stats += f"{i}. {player['player']} ({player['count']} 条消息)\n"
        else:
            chat_stats = "📊 暂无聊天统计数据"
        
        await chat_stats_cmd.finish(Message(chat_stats))
        
    except Exception as e:
        await chat_stats_cmd.finish(Message(f"❌ 处理聊天统计查询时出错：{str(e)}")) 