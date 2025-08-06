import httpx
from typing import Optional
from arclet.alconna import Alconna, Args, Field, Option, Subcommand
from arclet.alconna.typing import CommandMeta
from nonebot import on_alconna
from nonebot.adapters import Event
from nonebot.adapters.onebot.v11 import Bot, Message
from nonebot.params import Depends
from nonebot.permission import SUPERUSER
from nonebot.typing import T_State

# 导入配置
from ..config import Config
from .. import get_config


class DMPAPI:
    """DMP API客户端"""
    
    def __init__(self):
        config = get_config()
        self.base_url = config.dmp_base_url
        self.token = config.dmp_token
        
        # 检查token是否为空
        if not self.token:
            print("⚠️ 警告: DMP_TOKEN 未设置，请检查配置")
        
        self.headers = {
            "Authorization": self.token,  # 直接使用token，不使用Bearer前缀
            "X-I18n-Lang": "zh"  # 使用zh而不是zh-CN
        }
        # 设置超时时间
        self.timeout = 30.0
    
    async def _make_request(self, method: str, url: str, **kwargs) -> dict:
        """统一的请求处理方法"""
        try:
            # 获取自定义headers，如果没有则使用默认headers
            custom_headers = kwargs.pop('headers', self.headers)
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                if method.upper() == "GET":
                    response = await client.get(url, headers=custom_headers, **kwargs)
                elif method.upper() == "POST":
                    response = await client.post(url, headers=custom_headers, **kwargs)
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
    
    async def get_world_info(self, cluster_name: str = None) -> dict:
        """获取世界信息"""
        if not cluster_name:
            config = get_config()
            cluster_name = await config.get_first_cluster()
        
        url = f"{self.base_url}/home/world_info"
        params = {"clusterName": cluster_name}
        
        return await self._make_request("GET", url, params=params)
    
    async def get_room_info(self, cluster_name: str = None) -> dict:
        """获取房间信息"""
        if not cluster_name:
            config = get_config()
            cluster_name = await config.get_first_cluster()
        
        url = f"{self.base_url}/home/room_info"
        params = {"clusterName": cluster_name}
        
        return await self._make_request("GET", url, params=params)
    
    async def get_sys_info(self) -> dict:
        """获取系统信息"""
        url = f"{self.base_url}/home/sys_info"
        
        return await self._make_request("GET", url)
    
    async def get_player_list(self, cluster_name: str = None) -> dict:
        """获取玩家列表"""
        if not cluster_name:
            config = get_config()
            cluster_name = await config.get_first_cluster()
        
        url = f"{self.base_url}/home/player_list"
        params = {"clusterName": cluster_name}
        
        return await self._make_request("GET", url, params=params)
    
    async def get_clusters(self) -> dict:
        """获取集群列表"""
        url = f"{self.base_url}/setting/clusters"
        
        return await self._make_request("GET", url)


# 创建 DMPAPI 实例
dmp_api = DMPAPI()

# 基础查询命令 - 使用 Alconna
world_info_cmd = on_alconna(
    Alconna(
        "世界",
        Args["world_name?", str] = Field("Master", description="世界名称"),
        meta=CommandMeta(
            description="获取世界信息",
            usage="世界 [世界名称]",
            example="世界 Master"
        )
    ),
    aliases={"world", "worldinfo"},
    priority=5
)

room_info_cmd = on_alconna(
    Alconna(
        "房间",
        Args["world_name?", str] = Field("Master", description="世界名称"),
        meta=CommandMeta(
            description="获取房间信息",
            usage="房间 [世界名称]",
            example="房间 Master"
        )
    ),
    aliases={"room", "roominfo"},
    priority=5
)

sys_info_cmd = on_alconna(
    Alconna(
        "系统",
        meta=CommandMeta(
            description="获取系统信息",
            usage="系统",
            example="系统"
        )
    ),
    aliases={"sys", "system"},
    priority=5
)

player_list_cmd = on_alconna(
    Alconna(
        "玩家",
        Args["world_name?", str] = Field("Master", description="世界名称"),
        meta=CommandMeta(
            description="获取在线玩家列表",
            usage="玩家 [世界名称]",
            example="玩家 Master"
        )
    ),
    aliases={"players", "playerlist"},
    priority=5
)

connection_cmd = on_alconna(
    Alconna(
        "直连",
        meta=CommandMeta(
            description="获取服务器直连信息",
            usage="直连",
            example="直连"
        )
    ),
    aliases={"connection", "connect"},
    priority=5
)

help_cmd = on_alconna(
    Alconna(
        "菜单",
        meta=CommandMeta(
            description="显示帮助信息",
            usage="菜单",
            example="菜单"
        )
    ),
    aliases={"help", "帮助"},
    priority=5
)


# 命令处理器
@world_info_cmd.handle()
async def handle_world_info(bot: Bot, event: Event, world_name: str = "Master"):
    """处理世界信息查询"""
    try:
        result = await dmp_api.get_world_info()
        
        if result.get("code") == 200:
            data = result.get("data", {})
            worlds = data.get("worlds", [])
            
            # 查找指定世界的信息
            target_world = None
            for world in worlds:
                if world.get("name") == world_name:
                    target_world = world
                    break
            
            if target_world:
                # 格式化世界信息
                world_info = f"""🌍 世界信息 - {world_name}
                
📊 基本信息：
• 名称：{target_world.get('name', 'N/A')}
• 状态：{target_world.get('status', 'N/A')}
• 模式：{target_world.get('mode', 'N/A')}
• 季节：{target_world.get('season', 'N/A')}
• 天数：{target_world.get('days', 'N/A')}

👥 玩家信息：
• 在线玩家：{target_world.get('players', 'N/A')}
• 最大玩家：{target_world.get('maxPlayers', 'N/A')}

⏰ 运行时间：
• 运行时长：{target_world.get('uptime', 'N/A')}
• 最后更新：{target_world.get('lastUpdate', 'N/A')}"""
                
                await world_info_cmd.finish(Message(world_info))
            else:
                await world_info_cmd.finish(Message(f"❌ 未找到世界 '{world_name}' 的信息"))
        else:
            error_msg = result.get("message", "未知错误")
            await world_info_cmd.finish(Message(f"❌ 获取世界信息失败：{error_msg}"))
            
    except Exception as e:
        await world_info_cmd.finish(Message(f"❌ 处理世界信息查询时出错：{str(e)}"))


@room_info_cmd.handle()
async def handle_room_info(bot: Bot, event: Event, world_name: str = "Master"):
    """处理房间信息查询"""
    try:
        result = await dmp_api.get_room_info()
        
        if result.get("code") == 200:
            data = result.get("data", {})
            room_info = f"""🏠 房间信息
            
📊 基本信息：
• 房间名称：{data.get('roomName', 'N/A')}
• 房间描述：{data.get('description', 'N/A')}
• 房间模式：{data.get('mode', 'N/A')}
• 房间状态：{data.get('status', 'N/A')}

👥 玩家统计：
• 当前玩家：{data.get('currentPlayers', 'N/A')}
• 最大玩家：{data.get('maxPlayers', 'N/A')}
• 在线玩家：{data.get('onlinePlayers', 'N/A')}

🌍 世界信息：
• 世界数量：{data.get('worldCount', 'N/A')}
• 活跃世界：{data.get('activeWorlds', 'N/A')}

⏰ 时间信息：
• 运行时长：{data.get('uptime', 'N/A')}
• 最后更新：{data.get('lastUpdate', 'N/A')}"""
            
            await room_info_cmd.finish(Message(room_info))
        else:
            error_msg = result.get("message", "未知错误")
            await room_info_cmd.finish(Message(f"❌ 获取房间信息失败：{error_msg}"))
            
    except Exception as e:
        await room_info_cmd.finish(Message(f"❌ 处理房间信息查询时出错：{str(e)}"))


@sys_info_cmd.handle()
async def handle_sys_info(bot: Bot, event: Event):
    """处理系统信息查询"""
    try:
        result = await dmp_api.get_sys_info()
        
        if result.get("code") == 200:
            data = result.get("data", {})
            sys_info = f"""💻 系统信息
            
🖥️ 硬件信息：
• CPU使用率：{data.get('cpuUsage', 'N/A')}%
• 内存使用率：{data.get('memoryUsage', 'N/A')}%
• 内存总量：{data.get('totalMemory', 'N/A')}
• 可用内存：{data.get('availableMemory', 'N/A')}

💾 存储信息：
• 磁盘使用率：{data.get('diskUsage', 'N/A')}%
• 磁盘总量：{data.get('totalDisk', 'N/A')}
• 可用磁盘：{data.get('availableDisk', 'N/A')}

🌐 网络信息：
• 网络状态：{data.get('networkStatus', 'N/A')}
• 网络延迟：{data.get('networkLatency', 'N/A')}

⏰ 运行信息：
• 系统运行时间：{data.get('uptime', 'N/A')}
• 最后更新：{data.get('lastUpdate', 'N/A')}"""
            
            await sys_info_cmd.finish(Message(sys_info))
        else:
            error_msg = result.get("message", "未知错误")
            await sys_info_cmd.finish(Message(f"❌ 获取系统信息失败：{error_msg}"))
            
    except Exception as e:
        await sys_info_cmd.finish(Message(f"❌ 处理系统信息查询时出错：{str(e)}"))


@player_list_cmd.handle()
async def handle_player_list(bot: Bot, event: Event, world_name: str = "Master"):
    """处理玩家列表查询"""
    try:
        result = await dmp_api.get_player_list()
        
        if result.get("code") == 200:
            data = result.get("data", {})
            players = data.get("players", [])
            
            if players:
                player_list = f"👥 在线玩家列表 ({len(players)}人)\n\n"
                for i, player in enumerate(players, 1):
                    player_list += f"{i}. {player.get('name', 'N/A')} (ID: {player.get('id', 'N/A')})\n"
                    if player.get('world'):
                        player_list += f"   所在世界：{player.get('world')}\n"
                    if player.get('joinTime'):
                        player_list += f"   加入时间：{player.get('joinTime')}\n"
                    player_list += "\n"
            else:
                player_list = "👥 当前没有在线玩家"
            
            await player_list_cmd.finish(Message(player_list))
        else:
            error_msg = result.get("message", "未知错误")
            await player_list_cmd.finish(Message(f"❌ 获取玩家列表失败：{error_msg}"))
            
    except Exception as e:
        await player_list_cmd.finish(Message(f"❌ 处理玩家列表查询时出错：{str(e)}"))


@connection_cmd.handle()
async def handle_connection(bot: Bot, event: Event):
    """处理直连信息查询"""
    try:
        result = await dmp_api.get_clusters()
        
        if result.get("code") == 200:
            clusters = result.get("data", [])
            
            if clusters:
                connection_info = "🔗 服务器直连信息\n\n"
                for cluster in clusters:
                    cluster_name = cluster.get("clusterName", "N/A")
                    connection_code = cluster.get("connectionCode", "N/A")
                    connection_info += f"🌍 集群：{cluster_name}\n"
                    connection_info += f"🔗 直连码：{connection_code}\n\n"
            else:
                connection_info = "❌ 未找到可用的集群信息"
            
            await connection_cmd.finish(Message(connection_info))
        else:
            error_msg = result.get("message", "未知错误")
            await connection_cmd.finish(Message(f"❌ 获取直连信息失败：{error_msg}"))
            
    except Exception as e:
        await connection_cmd.finish(Message(f"❌ 处理直连信息查询时出错：{str(e)}"))


@help_cmd.handle()
async def handle_help(bot: Bot, event: Event):
    """处理帮助信息"""
    help_text = """🤖 DMP 饥荒管理平台机器人

📋 基础命令：
• /世界 [世界名] - 获取世界信息
• /房间 - 获取房间信息  
• /系统 - 获取系统信息
• /玩家 [世界名] - 获取在线玩家列表
• /直连 - 获取服务器直连信息
• /菜单 - 显示此帮助信息

🔧 管理员命令：
• /管理命令 - 显示管理员功能菜单
• /查看备份 - 获取备份文件列表
• /创建备份 - 手动创建备份
• /执行 <世界> <命令> - 执行游戏命令
• /回档 <天数> - 回档指定天数 (1-5天)
• /重置世界 [世界名称] - 重置世界
• /聊天历史 [世界名] [行数] - 获取聊天历史
• /聊天统计 - 获取聊天历史统计信息

💬 消息互通功能：
• /消息互通 - 开启游戏内消息与QQ消息互通
• /关闭互通 - 关闭消息互通功能
• /互通状态 - 查看当前互通状态
• /最新消息 [数量] - 获取游戏内最新消息

💡 使用提示：
• 方括号 [] 表示可选参数
• 尖括号 <> 表示必需参数
• 管理员命令需要超级用户权限"""
    
    await help_cmd.finish(Message(help_text)) 