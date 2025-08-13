import httpx
from typing import Optional
from nonebot import get_driver, get_plugin_config
from nonebot.adapters import Event
from nonebot.adapters.onebot.v11 import Bot, Message
from nonebot.permission import SUPERUSER
from nonebot_plugin_alconna import on_alconna, Alconna, Args, Command, Option, Subcommand, Match

# 导入配置
from ..config import Config

# 创建DMP API实例
dmp_api = None

# 获取配置函数
def get_config() -> Config:
    """获取插件配置"""
    return get_plugin_config(Config)

# 创建Alconna命令
world_cmd = Alconna("世界")
room_cmd = Alconna("房间")
sys_cmd = Alconna("系统")
players_cmd = Alconna("玩家")
connection_cmd = Alconna("直连")
help_cmd = Alconna("菜单")

# 创建命令别名
world_cmd_eng = Alconna("world")
room_cmd_eng = Alconna("room")
sys_cmd_eng = Alconna("sys")
players_cmd_eng = Alconna("players")
connection_cmd_eng = Alconna("connection")
help_cmd_eng = Alconna("help")

# 创建响应器
world_matcher = on_alconna(world_cmd)
room_matcher = on_alconna(room_cmd)
sys_matcher = on_alconna(sys_cmd)
players_matcher = on_alconna(players_cmd)
connection_matcher = on_alconna(connection_cmd)
help_matcher = on_alconna(help_cmd)

world_eng_matcher = on_alconna(world_cmd_eng)
room_eng_matcher = on_alconna(room_cmd_eng)
sys_eng_matcher = on_alconna(sys_cmd_eng)
players_eng_matcher = on_alconna(players_cmd_eng)
connection_eng_matcher = on_alconna(connection_cmd_eng)
help_eng_matcher = on_alconna(help_cmd_eng)

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
        
        # 缓存可用集群列表
        self._available_clusters = None
        self._clusters_cache_time = 0
        self._cache_expire_time = 300  # 5分钟缓存过期
    
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
    
    async def get_available_clusters(self) -> list:
        """获取可用的集群列表"""
        import time
        
        # 检查缓存是否有效
        current_time = time.time()
        if (self._available_clusters and 
            current_time - self._clusters_cache_time < self._cache_expire_time):
            return self._available_clusters
        
        try:
            url = f"{self.base_url}/setting/clusters"
            result = await self._make_request("GET", url)
            
            if result.get("code") == 200:
                clusters = result.get("data", [])
                # 更新缓存
                self._available_clusters = clusters
                self._clusters_cache_time = current_time
                return clusters
            else:
                print(f"⚠️ 获取集群列表失败: {result.get('message', '未知错误')}")
                return []
        except Exception as e:
            print(f"⚠️ 获取集群列表异常: {e}")
            return []
    
    async def get_first_available_cluster(self) -> str:
        """获取第一个可用的集群名称"""
        clusters = await self.get_available_clusters()
        if clusters:
            # 返回第一个集群的名称
            first_cluster = clusters[0]
            if isinstance(first_cluster, dict):
                # 根据实际API返回结构获取集群名称
                cluster_name = first_cluster.get("clusterName")
                if cluster_name:
                    return cluster_name
                # 如果没有clusterName，尝试其他可能的字段
                return first_cluster.get("name", first_cluster.get("cluster", "cx"))
            else:
                return str(first_cluster)
        return "cx"  # 默认集群
    
    async def get_cluster_info(self, cluster_name: str = None) -> dict:
        """获取集群详细信息"""
        if not cluster_name:
            cluster_name = await self.get_first_available_cluster()
        
        clusters = await self.get_available_clusters()
        for cluster in clusters:
            if isinstance(cluster, dict) and cluster.get("clusterName") == cluster_name:
                return cluster
        return {}
    
    async def get_world_info(self, cluster_name: str = None) -> dict:
        """获取世界信息"""
        if not cluster_name:
            cluster_name = await self.get_first_available_cluster()
        
        url = f"{self.base_url}/home/world_info"
        params = {"clusterName": cluster_name}
        
        return await self._make_request("GET", url, params=params)
    
    async def get_room_info(self, cluster_name: str = None) -> dict:
        """获取房间信息"""
        if not cluster_name:
            cluster_name = await self.get_first_available_cluster()
        
        url = f"{self.base_url}/home/room_info"
        params = {"clusterName": cluster_name}
        
        return await self._make_request("GET", url, params=params)
    
    async def get_sys_info(self) -> dict:
        """获取系统信息"""
        url = f"{self.base_url}/home/sys_info"
        
        return await self._make_request("GET", url)
    
    async def get_players(self, cluster_name: str = None) -> dict:
        """获取在线玩家列表"""
        if not cluster_name:
            cluster_name = await self.get_first_available_cluster()
        
        url = f"{self.base_url}/setting/player/list"
        params = {"clusterName": cluster_name}
        
        return await self._make_request("GET", url, params=params)
    
    async def get_connection_info(self, cluster_name: str = None) -> dict:
        """获取服务器直连信息"""
        if not cluster_name:
            cluster_name = await self.get_first_available_cluster()
        
        url = f"{self.base_url}/external/api/connection_code"
        params = {"clusterName": cluster_name}
        
        return await self._make_request("GET", url, params=params)

# 命令处理函数
@world_matcher.handle()
async def handle_world_cmd(bot: Bot, event: Event):
    """处理世界信息命令"""
    try:
        # 先获取可用的集群
        available_clusters = await dmp_api.get_available_clusters()
        if not available_clusters:
            await bot.send(event, "❌ 无法获取可用集群列表，请检查DMP服务器连接")
            return
        
        # 使用第一个可用集群
        cluster_name = await dmp_api.get_first_available_cluster()
        result = await dmp_api.get_world_info(cluster_name)
        
        if result.get("code") == 200:
            data = result.get("data")
            
            # 检查数据类型并安全处理
            if isinstance(data, dict):
                # 尝试多种可能的数据结构
                response = f"🌍 世界信息 (集群: {cluster_name}):\n"
                
                # 检查是否有世界状态信息
                if 'status' in data:
                    response += f"状态: {data.get('status', '未知')}\n"
                
                # 检查是否有世界数量信息
                if 'worldCount' in data:
                    response += f"世界数量: {data.get('worldCount', 0)}\n"
                elif 'worlds' in data:
                    worlds = data.get('worlds', [])
                    response += f"世界数量: {len(worlds) if isinstance(worlds, list) else 0}\n"
                
                # 检查是否有玩家信息
                if 'onlinePlayers' in data:
                    response += f"在线玩家: {data.get('onlinePlayers', 0)}\n"
                elif 'players' in data:
                    players = data.get('players', [])
                    response += f"在线玩家: {len(players) if isinstance(players, list) else 0}\n"
                
                if 'maxPlayers' in data:
                    response += f"最大玩家: {data.get('maxPlayers', 0)}\n"
                
                # 如果没有找到任何有效信息，显示原始数据结构
                if response == f"🌍 世界信息 (集群: {cluster_name}):\n":
                    response += f"数据结构: {list(data.keys())}\n"
                    response += f"原始数据: {data}"
                    
            elif isinstance(data, list):
                # 根据实际API返回结构解析世界列表
                if data:
                    # 获取集群信息以显示更多详情
                    cluster_info = await dmp_api.get_cluster_info(cluster_name)
                    cluster_display_name = cluster_info.get("clusterDisplayName", cluster_name)
                    cluster_status = "运行中" if cluster_info.get("status") else "已停止"
                    
                    response = f"🌍 世界信息 (集群: {cluster_name}):\n"
                    response += f"显示名称: {cluster_display_name}\n"
                    response += f"集群状态: {cluster_status}\n"
                    response += f"世界数量: {len(data)}\n\n"
                    
                    for i, world in enumerate(data, 1):
                        if isinstance(world, dict):
                            # 世界基本信息
                            world_name = world.get('world', '未知')
                            world_type = world.get('type', '未知')
                            is_master = "主世界" if world.get('isMaster') else "洞穴世界"
                            status = "运行中" if world.get('stat') else "已停止"
                            
                            response += f"🌍 世界 {i}: {world_name}\n"
                            response += f"   类型: {world_type} ({is_master})\n"
                            response += f"   状态: {status}\n"
                            
                            # 资源使用情况
                            cpu_usage = world.get('cpu', 0)
                            mem_usage = world.get('mem', 0)
                            mem_size = world.get('memSize', 0)
                            disk_used = world.get('diskUsed', 0)
                            
                            response += f"   CPU: {cpu_usage:.1f}%\n"
                            response += f"   内存: {mem_usage:.1f}% ({mem_size}MB)\n"
                            response += f"   磁盘: {disk_used / (1024*1024):.1f}MB\n"
                            
                            if i < len(data):  # 不是最后一个世界
                                response += "\n"
                        else:
                            response += f"🌍 世界 {i}: {str(world)}\n"
                else:
                    response = f"🌍 世界信息 (集群: {cluster_name}):\n暂无世界数据"
            else:
                response = f"🌍 世界信息 (集群: {cluster_name}):\n数据格式异常，原始数据: {data}"
        else:
            response = f"❌ 获取世界信息失败: {result.get('message', '未知错误')}"
        
        await bot.send(event, response)
        
    except Exception as e:
        error_msg = f"❌ 处理世界信息命令时发生错误: {str(e)}"
        print(f"⚠️ {error_msg}")
        await bot.send(event, error_msg)

@room_matcher.handle()
async def handle_room_cmd(bot: Bot, event: Event):
    """处理房间信息命令"""
    try:
        # 先获取可用的集群
        available_clusters = await dmp_api.get_available_clusters()
        if not available_clusters:
            await bot.send(event, "❌ 无法获取可用集群列表，请检查DMP服务器连接")
            return
        
        # 使用第一个可用集群
        cluster_name = await dmp_api.get_first_available_cluster()
        result = await dmp_api.get_room_info(cluster_name)
        
        if result.get("code") == 200:
            data = result.get("data")
            
            # 检查数据类型并安全处理
            if isinstance(data, dict):
                # 根据实际API返回结构解析数据
                cluster_setting = data.get('clusterSetting', {})
                season_info = data.get('seasonInfo', {})
                
                # 获取集群信息以显示更多详情
                cluster_info = await dmp_api.get_cluster_info(cluster_name)
                cluster_display_name = cluster_info.get("clusterDisplayName", cluster_name)
                cluster_status = "运行中" if cluster_info.get("status") else "已停止"
                
                response = f"🏠 房间信息 (集群: {cluster_name}):\n"
                response += f"显示名称: {cluster_display_name}\n"
                response += f"集群状态: {cluster_status}\n"
                response += f"房间名: {cluster_setting.get('name', '未知')}\n"
                response += f"密码: {cluster_setting.get('password', '无')}\n"
                response += f"描述: {cluster_setting.get('description', '无')}\n"
                response += f"游戏模式: {cluster_setting.get('gameMode', '未知')}\n"
                response += f"最大玩家: {cluster_setting.get('playerNum', '未知')}\n"
                response += f"PvP: {'开启' if cluster_setting.get('pvp') else '关闭'}\n"
                response += f"回档天数: {cluster_setting.get('backDays', '未知')}\n"
                response += f"投票: {'开启' if cluster_setting.get('vote') else '关闭'}\n"
                response += f"控制台: {'启用' if cluster_setting.get('consoleEnabled') else '禁用'}\n"
                response += f"模组数量: {data.get('modsCount', '未知')}\n"
                
                # 添加季节信息
                if season_info:
                    season = season_info.get('season', {})
                    phase = season_info.get('phase', {})
                    response += f"当前季节: {season.get('zh', season.get('en', '未知'))}\n"
                    response += f"当前阶段: {phase.get('zh', phase.get('en', '未知'))}\n"
                    response += f"已过天数: {season_info.get('elapsedDays', '未知')}\n"
                    response += f"总周期: {season_info.get('cycles', '未知')}"
                
            elif isinstance(data, list):
                # 如果data是列表，尝试获取第一个元素
                if data:
                    first_item = data[0] if isinstance(data[0], dict) else {}
                    response = f"🏠 房间信息 (集群: {cluster_name}):\n"
                    response += f"房间名: {first_item.get('name', '未知')}\n"
                    response += f"密码: {first_item.get('password', '无')}\n"
                    response += f"描述: {first_item.get('description', '无')}\n"
                    response += f"模式: {first_item.get('gameMode', '未知')}"
                else:
                    response = f"🏠 房间信息 (集群: {cluster_name}):\n暂无房间数据"
            else:
                response = f"🏠 房间信息 (集群: {cluster_name}):\n数据格式异常，原始数据: {data}"
        else:
            response = f"❌ 获取房间信息失败: {result.get('message', '未知错误')}"
        
        await bot.send(event, response)
        
    except Exception as e:
        error_msg = f"❌ 处理房间信息命令时发生错误: {str(e)}"
        print(f"⚠️ {error_msg}")
        await bot.send(event, error_msg)

@sys_matcher.handle()
async def handle_sys_cmd(bot: Bot, event: Event):
    """处理系统信息命令"""
    try:
        result = await dmp_api.get_sys_info()
        if result.get("code") == 200:
            data = result.get("data")
            
            # 检查数据类型并安全处理
            if isinstance(data, dict):
                response = "💻 系统信息:\n"
                
                # 根据实际API返回结构解析数据
                cpu_usage = data.get('cpu')
                memory_usage = data.get('memory')
                
                if cpu_usage is not None:
                    response += f"CPU使用率: {cpu_usage:.1f}%\n"
                else:
                    response += f"CPU使用率: {data.get('cpuUsage', '未知')}%\n"
                
                if memory_usage is not None:
                    response += f"内存使用率: {memory_usage:.1f}%\n"
                else:
                    response += f"内存使用率: {data.get('memoryUsage', '未知')}%\n"
                
                # 检查是否有其他系统信息
                disk_usage = data.get('diskUsage') or data.get('disk')
                if disk_usage is not None:
                    response += f"磁盘使用率: {disk_usage}%\n"
                
                network_status = data.get('networkStatus') or data.get('network')
                if network_status is not None:
                    response += f"网络状态: {network_status}\n"
                
                # 如果没有找到任何有效信息，显示原始数据结构
                if response == "💻 系统信息:\n":
                    response += f"数据结构: {list(data.keys())}\n"
                    response += f"原始数据: {data}"
                    
            elif isinstance(data, list):
                # 如果data是列表，尝试获取第一个元素
                if data:
                    first_item = data[0] if isinstance(data[0], dict) else {}
                    response = "💻 系统信息:\n"
                    
                    # 尝试多种可能的字段名
                    cpu_usage = first_item.get('cpu') or first_item.get('cpuUsage')
                    memory_usage = first_item.get('memory') or first_item.get('memoryUsage')
                    
                    if cpu_usage is not None:
                        response += f"CPU使用率: {cpu_usage:.1f}%\n"
                    else:
                        response += f"CPU使用率: 未知\n"
                    
                    if memory_usage is not None:
                        response += f"内存使用率: {memory_usage:.1f}%\n"
                    else:
                        response += f"内存使用率: 未知\n"
                    
                    # 检查其他字段
                    disk_usage = first_item.get('diskUsage') or first_item.get('disk')
                    if disk_usage is not None:
                        response += f"磁盘使用率: {disk_usage}%\n"
                    
                    network_status = first_item.get('networkStatus') or first_item.get('network')
                    if network_status is not None:
                        response += f"网络状态: {network_status}\n"
                else:
                    response = "💻 系统信息:\n暂无系统数据"
            else:
                response = f"💻 系统信息:\n数据格式异常，原始数据: {data}"
        else:
            response = f"❌ 获取系统信息失败: {result.get('message', '未知错误')}"
        
        await bot.send(event, response)
        
    except Exception as e:
        error_msg = f"❌ 处理系统信息命令时发生错误: {str(e)}"
        print(f"⚠️ {error_msg}")
        await bot.send(event, error_msg)

@players_matcher.handle()
async def handle_players_cmd(bot: Bot, event: Event):
    """处理玩家列表命令"""
    try:
        # 先获取可用的集群
        available_clusters = await dmp_api.get_available_clusters()
        if not available_clusters:
            await bot.send(event, "❌ 无法获取可用集群列表，请检查DMP服务器连接")
            return
        
        # 使用第一个可用集群
        cluster_name = await dmp_api.get_first_available_cluster()
        result = await dmp_api.get_players(cluster_name)
        
        if result.get("code") == 200:
            data = result.get("data")
            
            # 检查数据类型并安全处理
            if isinstance(data, dict):
                response = f"👥 玩家信息 (集群: {cluster_name}):\n"
                
                # 获取集群信息以显示更多详情
                cluster_info = await dmp_api.get_cluster_info(cluster_name)
                cluster_display_name = cluster_info.get("clusterDisplayName", cluster_name)
                cluster_status = "运行中" if cluster_info.get("status") else "已停止"
                
                response += f"显示名称: {cluster_display_name}\n"
                response += f"集群状态: {cluster_status}\n\n"
                
                # 在线玩家信息
                players = data.get('players')
                if players and isinstance(players, list) and len(players) > 0:
                    response += f"🟢 在线玩家 ({len(players)}人):\n"
                    for i, player in enumerate(players, 1):
                        if isinstance(player, dict):
                            player_name = player.get('name', player.get('playerName', '未知'))
                            player_id = player.get('id', player.get('playerId', '未知'))
                            response += f"  {i}. {player_name} (ID: {player_id})\n"
                        else:
                            response += f"  {i}. {str(player)}\n"
                else:
                    response += "😴 当前没有在线玩家\n"
                
                # 白名单玩家信息
                white_list = data.get('whiteList')
                if white_list and isinstance(white_list, list) and len(white_list) > 0:
                    response += f"\n⚪ 白名单玩家 ({len(white_list)}人):\n"
                    for i, player in enumerate(white_list, 1):
                        response += f"  {i}. {player}\n"
                
                # 管理员列表
                admin_list = data.get('adminList')
                if admin_list and isinstance(admin_list, list) and len(admin_list) > 0:
                    response += f"\n👑 管理员 ({len(admin_list)}人):\n"
                    for i, admin in enumerate(admin_list, 1):
                        response += f"  {i}. {admin}\n"
                
                # 封禁玩家列表
                block_list = data.get('blockList')
                if block_list and isinstance(block_list, list) and len(block_list) > 0:
                    response += f"\n🚫 封禁玩家 ({len(block_list)}人):\n"
                    for i, blocked in enumerate(block_list, 1):
                        response += f"  {i}. {blocked}\n"
                
                # UID映射信息
                uid_map = data.get('uidMap')
                if uid_map and isinstance(uid_map, dict) and len(uid_map) > 0:
                    response += f"\n🆔 玩家UID映射 ({len(uid_map)}人):\n"
                    for i, (uid, name) in enumerate(uid_map.items(), 1):
                        response += f"  {i}. {name} (UID: {uid})\n"
                
                # 如果没有找到任何有效信息，显示原始数据结构
                if response == f"👥 玩家信息 (集群: {cluster_name}):\n显示名称: {cluster_display_name}\n集群状态: {cluster_status}\n\n":
                    response += f"数据结构: {list(data.keys())}\n"
                    response += f"原始数据: {data}"
                    
            elif isinstance(data, list):
                # 如果data是列表，直接使用
                if data:
                    response = f"👥 在线玩家 (集群: {cluster_name}):\n"
                    for i, player in enumerate(data, 1):
                        if isinstance(player, dict):
                            player_name = player.get('name', player.get('playerName', '未知'))
                            player_id = player.get('id', player.get('playerId', '未知'))
                            response += f"{i}. {player_name} (ID: {player_id})\n"
                        else:
                            response += f"{i}. {str(player)}\n"
                else:
                    response = f"😴 当前没有在线玩家 (集群: {cluster_name})"
            else:
                response = f"👥 在线玩家 (集群: {cluster_name}):\n数据格式异常，原始数据: {data}"
        else:
            response = f"❌ 获取玩家列表失败: {result.get('message', '未知错误')}"
        
        await bot.send(event, response)
        
    except Exception as e:
        error_msg = f"❌ 处理玩家列表命令时发生错误: {str(e)}"
        print(f"⚠️ {error_msg}")
        await bot.send(event, error_msg)

@connection_matcher.handle()
async def handle_connection_cmd(bot: Bot, event: Event):
    """处理直连信息命令"""
    try:
        # 先获取可用的集群
        available_clusters = await dmp_api.get_available_clusters()
        if not available_clusters:
            await bot.send(event, "❌ 无法获取可用集群列表，请检查DMP服务器连接")
            return
        
        # 使用第一个可用集群
        cluster_name = await dmp_api.get_first_available_cluster()
        result = await dmp_api.get_connection_info(cluster_name)
        
        if result.get("code") == 200:
            data = result.get("data")
            
            # 检查数据类型并安全处理
            if isinstance(data, dict):
                # 如果data是字典，尝试获取直连相关字段
                response = f"🔗 直连信息 (集群: {cluster_name}):\n"
                response += f"IP地址: {data.get('ip', '未知')}\n"
                response += f"端口: {data.get('port', '未知')}\n"
                response += f"直连地址: {data.get('connectionString', '未知')}"
            elif isinstance(data, list):
                # 如果data是列表，尝试获取第一个元素
                if data:
                    first_item = data[0] if isinstance(data[0], dict) else {}
                    response = f"🔗 直连信息 (集群: {cluster_name}):\n"
                    response += f"IP地址: {first_item.get('ip', '未知')}\n"
                    response += f"端口: {first_item.get('port', '未知')}\n"
                    response += f"直连地址: {first_item.get('connectionString', '未知')}"
                else:
                    response = f"🔗 直连信息 (集群: {cluster_name}):\n暂无直连数据"
            elif isinstance(data, str):
                # 处理字符串格式的直连代码
                response = f"🔗 直连信息 (集群: {cluster_name}):\n"
                
                # 尝试解析 c_connect 格式的直连代码
                if data.startswith("c_connect(") and data.endswith(")"):
                    try:
                        # 提取括号内的内容
                        content = data[10:-1]  # 去掉 "c_connect(" 和 ")"
                        # 分割参数
                        params = content.split("', ")
                        if len(params) >= 3:
                            ip = params[0].strip("'")
                            port = params[1].strip("'")
                            password = params[2].strip("'")
                            
                            response += f"IP地址: {ip}\n"
                            response += f"端口: {port}\n"
                            response += f"密码: {password}\n"
                            response += f"直连代码: {data}\n\n"
                            response += f"💡 使用方法:\n"
                            response += f"1. 在饥荒游戏中按 ~ 键打开控制台\n"
                            response += f"2. 复制粘贴上面的直连代码\n"
                            response += f"3. 按回车键执行即可连接到服务器"
                        else:
                            response += f"直连代码: {data}\n"
                            response += f"⚠️ 无法解析直连代码格式"
                    except Exception as e:
                        response += f"直连代码: {data}\n"
                        response += f"⚠️ 解析直连代码时出错: {str(e)}"
                else:
                    # 其他字符串格式
                    response += f"直连信息: {data}\n"
                    response += f"⚠️ 未知的直连代码格式"
            else:
                response = f"🔗 直连信息 (集群: {cluster_name}):\n数据格式异常，原始数据: {data}"
        else:
            response = f"❌ 获取直连信息失败: {result.get('message', '未知错误')}"
        
        await bot.send(event, response)
        
    except Exception as e:
        error_msg = f"❌ 处理直连信息命令时发生错误: {str(e)}"
        print(f"⚠️ {error_msg}")
        await bot.send(event, error_msg)

@help_matcher.handle()
async def handle_help_cmd(bot: Bot, event: Event):
    """处理帮助命令"""
    try:
        help_text = """📚 饥荒管理平台机器人帮助菜单

🌍 基础命令:
• /世界 - 获取世界信息
• /房间 - 获取房间信息  
• /系统 - 获取系统信息
• /玩家 - 获取在线玩家列表
• /直连 - 获取服务器直连信息
• /菜单 - 显示此帮助信息

🔧 管理员命令:
• /管理命令 - 显示管理员功能菜单

💬 消息互通:
• /消息互通 - 开启游戏内消息与QQ消息互通
• /关闭互通 - 关闭消息互通功能
• /互通状态 - 查看当前互通状态

📝 使用说明:
• 自动获取可用集群
• 支持中英文命令"""
        
        await bot.send(event, help_text)
        
    except Exception as e:
        error_msg = f"❌ 处理帮助命令时发生错误: {str(e)}"
        print(f"⚠️ {error_msg}")
        await bot.send(event, error_msg)

# 英文命令处理器
@world_eng_matcher.handle()
async def handle_world_cmd_eng(bot: Bot, event: Event):
    """处理英文世界信息命令"""
    await handle_world_cmd(bot, event)

@room_eng_matcher.handle()
async def handle_room_cmd_eng(bot: Bot, event: Event):
    """处理英文房间信息命令"""
    await handle_room_cmd(bot, event)

@sys_eng_matcher.handle()
async def handle_sys_cmd_eng(bot: Bot, event: Event):
    """处理英文系统信息命令"""
    await handle_sys_cmd(bot, event)

@players_eng_matcher.handle()
async def handle_players_cmd_eng(bot: Bot, event: Event):
    """处理英文玩家列表命令"""
    await handle_players_cmd(bot, event)

@connection_eng_matcher.handle()
async def handle_connection_cmd_eng(bot: Bot, event: Event):
    """处理英文直连信息命令"""
    await handle_connection_cmd(bot, event)

@help_eng_matcher.handle()
async def handle_help_cmd_eng(bot: Bot, event: Event):
    """处理英文帮助命令"""
    await handle_help_cmd(bot, event)

# 初始化DMP API实例
def init_dmp_api():
    global dmp_api
    if dmp_api is None:
        dmp_api = DMPAPI()
        print("✅ DMP API 实例初始化成功")

# 在模块加载时初始化
init_dmp_api() 