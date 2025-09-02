import httpx
from typing import Optional
from nonebot import get_driver
from nonebot.adapters import Event
from nonebot.adapters.onebot.v11 import Bot, Message
from nonebot.permission import SUPERUSER
from nonebot_plugin_alconna import on_alconna, Match
from arclet.alconna import Alconna, Args, Option, Subcommand

# 导入配置和缓存
from ..config import Config
from ..cache_manager import cached, cache_manager
from ..base_api import BaseAPI, APIResponse

# 创建DMP API实例
dmp_api = None

# 导入新的配置管理
from ..config import get_config
from ..message_dedup import send_with_dedup

async def send_long_message(bot: Bot, event: Event, title: str, content: str, max_length: int = 800):
    """
    发送长消息，超过指定长度时自动使用合并转发
    
    Args:
        bot: Bot实例
        event: 事件
        title: 消息标题（用于合并转发的发送者昵称）
        content: 消息内容
        max_length: 最大长度阈值，超过则使用合并转发
    """
    try:
        # 如果消息长度在阈值内，直接发送
        if len(content) <= max_length:
            await send_with_dedup(bot, event, content)
            return
        
        # 获取机器人信息
        bot_info = await bot.get_login_info()
        bot_id = str(bot_info.get("user_id", "机器人"))
        bot_name = bot_info.get("nickname", "饥荒管理机器人")
        
        # 分割消息内容为多个部分
        lines = content.split('\n')
        chunks = []
        current_chunk = ""
        
        for line in lines:
            if len(current_chunk) + len(line) + 1 > 500:  # 每个节点最大500字符
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = line
            else:
                current_chunk += ("\n" if current_chunk else "") + line
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        # 创建合并转发节点
        forward_nodes = []
        for i, chunk in enumerate(chunks):
            node_title = f"{title} - 第{i+1}部分" if len(chunks) > 1 else title
            node = {
                "type": "node",
                "data": {
                    "user_id": bot_id,
                    "nickname": bot_name,
                    "content": f"📋 {node_title}\n\n{chunk}"
                }
            }
            forward_nodes.append(node)
        
        # 发送合并转发消息
        from nonebot.adapters.onebot.v11 import MessageSegment
        
        if hasattr(event, 'group_id'):
            # 群聊使用合并转发
            try:
                await bot.call_api(
                    "send_group_forward_msg",
                    group_id=event.group_id,
                    messages=forward_nodes
                )
            except Exception as e:
                print(f"⚠️ 群聊合并转发失败: {e}")
                # 降级为普通消息
                raise e
        else:
            # 私聊使用合并转发
            try:
                await bot.call_api(
                    "send_private_forward_msg", 
                    user_id=event.user_id,
                    messages=forward_nodes
                )
            except Exception as e:
                print(f"⚠️ 私聊合并转发失败: {e}")
                # 降级为普通消息
                raise e
        
    except Exception as e:
        # 如果合并转发失败，降级为普通消息发送
        print(f"⚠️ 合并转发失败，降级为普通消息: {e}")
        await send_with_dedup(bot, event, content)

# 创建Alconna命令
world_cmd = Alconna("世界")
room_cmd = Alconna("房间")
sys_cmd = Alconna("系统")
players_cmd = Alconna("玩家")
connection_cmd = Alconna("直连")
help_cmd = Alconna("菜单")
# mode_cmd 已移至 output_mode_commands.py 中统一管理

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
# mode_matcher 已移至 output_mode_commands.py 中

world_eng_matcher = on_alconna(world_cmd_eng)
room_eng_matcher = on_alconna(room_cmd_eng)
sys_eng_matcher = on_alconna(sys_cmd_eng)
players_eng_matcher = on_alconna(players_cmd_eng)
connection_eng_matcher = on_alconna(connection_cmd_eng)
help_eng_matcher = on_alconna(help_cmd_eng)

class DMPAPI(BaseAPI):
    """DMP API客户端"""
    
    def __init__(self):
        config = get_config()
        super().__init__(config, "DMP-API")
        
        # 添加DMP特有的请求头
        self._base_headers.update({
            "X-I18n-Lang": "zh"  # 使用zh而不是zh-CN
        })
    

    
    @cached(cache_type="api", memory_ttl=300, file_ttl=600)
    async def get_available_clusters(self) -> APIResponse:
        """获取可用的集群列表 - 缓存5分钟内存，10分钟文件"""
        try:
            response = await self.get("/setting/clusters")
            return response
        except Exception as e:
            print(f"⚠️ 获取集群列表异常: {e}")
            return APIResponse(code=500, message=f"获取集群列表异常: {e}")
    
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
    
    async def get_cluster_info(self, cluster_name: str = None) -> APIResponse:
        """获取集群详细信息"""
        if not cluster_name:
            cluster_name = await self.get_current_cluster()
        
        response = await self.get_available_clusters()
        if response.success and response.data:
            clusters = response.data
            if isinstance(clusters, list):
                for cluster in clusters:
                    if isinstance(cluster, dict) and cluster.get("clusterName") == cluster_name:
                        return APIResponse(code=200, data=cluster, message="获取集群信息成功")
        return APIResponse(code=404, data={}, message="未找到指定集群")
    
    @cached(cache_type="api", memory_ttl=60, file_ttl=300)
    async def get_world_info(self, cluster_name: str = None) -> APIResponse:
        """获取世界信息 - 缓存1分钟内存，5分钟文件"""
        if not cluster_name:
            cluster_name = await self.get_current_cluster()
        
        params = {"clusterName": cluster_name}
        return await self.get("/home/world_info", params=params)
    
    @cached(cache_type="api", memory_ttl=180, file_ttl=900) 
    async def get_room_info(self, cluster_name: str = None) -> APIResponse:
        """获取房间信息 - 缓存3分钟内存，15分钟文件"""
        if not cluster_name:
            cluster_name = await self.get_current_cluster()
        
        params = {"clusterName": cluster_name}
        return await self.get("/home/room_info", params=params)
    
    @cached(cache_type="api", memory_ttl=30, file_ttl=120)
    async def get_sys_info(self) -> APIResponse:
        """获取系统信息 - 缓存30秒内存，2分钟文件"""
        return await self.get("/home/sys_info")
    
    @cached(cache_type="api", memory_ttl=30, file_ttl=180)
    async def get_players(self, cluster_name: str = None) -> APIResponse:
        """获取在线玩家列表 - 缓存30秒内存，3分钟文件"""
        if not cluster_name:
            cluster_name = await self.get_current_cluster()
        
        params = {"clusterName": cluster_name}
        return await self.get("/setting/player/list", params=params)
    
    @cached(cache_type="api", memory_ttl=600, file_ttl=1800)
    async def get_connection_info(self, cluster_name: str = None) -> APIResponse:
        """获取服务器直连信息 - 缓存10分钟内存，30分钟文件"""
        if not cluster_name:
            cluster_name = await self.get_current_cluster()
        
        params = {"clusterName": cluster_name}
        return await self.get("/external/api/connection_code", params=params)

# 命令处理函数
@world_matcher.handle()
async def handle_world_cmd(bot: Bot, event: Event):
    """处理世界信息命令"""
    try:
        # 使用当前选择的集群（这个方法内部会处理集群可用性检查）
        cluster_name = await dmp_api.get_current_cluster()
        if not cluster_name:
            await send_with_dedup(bot, event, "❌ 无法获取可用集群列表，请检查DMP服务器连接")
            return
        
        result = await dmp_api.get_world_info(cluster_name)
        
        if result.success:
            data = result.data
            
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
                    cluster_info_result = await dmp_api.get_cluster_info(cluster_name)
                    cluster_info = cluster_info_result.data if cluster_info_result.success else {}
                    cluster_display_name = cluster_info.get("clusterDisplayName", cluster_name)
                    cluster_status = "运行中" if cluster_info.get("status") else "已停止"
                    
                    # 构建统一的世界信息显示
                    status_icon = "🟢" if cluster_status == "运行中" else "🔴"
                    
                    world_lines = [
                        f"🌍 世界信息",
                        f"{status_icon} {cluster_display_name} (共 {len(data)} 个世界)",
                        ""
                    ]
                    
                    for i, world in enumerate(data, 1):
                        if isinstance(world, dict):
                            # 世界基本信息
                            world_name = world.get('world', '未知')
                            is_master = world.get('isMaster')
                            status = world.get('stat')
                            
                            # 状态和类型图标
                            world_status_icon = "🟢" if status else "🔴"
                            world_type_icon = "🌍" if is_master else "🕳️"
                            world_type = "主世界" if is_master else "洞穴"
                            
                            # 资源使用情况
                            cpu_usage = world.get('cpu', 0)
                            mem_usage = world.get('mem', 0)
                            
                            # 格式化显示
                            world_lines.append(f"{world_type_icon} {world_name} ({world_type})")
                            world_lines.append(f"  {world_status_icon} 状态 | 💻 CPU {cpu_usage:.1f}% | 📊 内存 {mem_usage:.1f}%")
                            
                            if i < len(data):  # 不是最后一个世界
                                world_lines.append("")
                        else:
                            world_lines.append(f"🌍 世界 {i}: {str(world)}")
                    
                    response = "\n".join(world_lines)
                else:
                    response = f"🌍 世界信息 (集群: {cluster_name}):\n暂无世界数据"
            else:
                response = f"🌍 世界信息 (集群: {cluster_name}):\n数据格式异常，原始数据: {data}"
        else:
            response = f"❌ 获取世界信息失败: {result.message or '未知错误'}"
        
        await send_with_dedup(bot, event, response)
        
    except Exception as e:
        error_msg = f"❌ 处理世界信息命令时发生错误: {str(e)}"
        print(f"⚠️ {error_msg}")
        await send_with_dedup(bot, event, error_msg)

@room_matcher.handle()
async def handle_room_cmd(bot: Bot, event: Event):
    """处理房间信息命令"""
    try:
        # 使用当前选择的集群（这个方法内部会处理集群可用性检查）
        cluster_name = await dmp_api.get_current_cluster()
        if not cluster_name:
            await send_with_dedup(bot, event, "❌ 无法获取可用集群列表，请检查DMP服务器连接")
            return
        
        result = await dmp_api.get_room_info(cluster_name)
        
        if result.success:
            data = result.data
            
            # 检查数据类型并安全处理
            if isinstance(data, dict):
                # 根据实际API返回结构解析数据
                cluster_setting = data.get('clusterSetting', {})
                season_info = data.get('seasonInfo', {})
                
                # 获取集群信息以显示更多详情
                cluster_info_result = await dmp_api.get_cluster_info(cluster_name)
                cluster_info = cluster_info_result.data if cluster_info_result.success else {}
                cluster_display_name = cluster_info.get("clusterDisplayName", cluster_name)
                cluster_status = "运行中" if cluster_info.get("status") else "已停止"
                
                # 构建简洁的房间信息
                status_icon = "🟢" if cluster_status == "运行中" else "🔴"
                
                room_info = [
                    f"🏠 房间信息",
                    f"{status_icon} {cluster_display_name} ({cluster_status})",
                    "",
                    f"🎮 房间名: {cluster_setting.get('name', '未知')}",
                    f"👥 最大玩家: {cluster_setting.get('playerNum', '未知')}",
                    f"⚔️ PvP: {'开启' if cluster_setting.get('pvp') else '关闭'}"
                ]
                
                # 只在有密码时显示
                password = cluster_setting.get('password', '')
                if password and password != '无':
                    room_info.append(f"🔐 密码: {password}")
                
                # 添加季节信息 - 简化显示
                if season_info:
                    season = season_info.get('season', {})
                    phase = season_info.get('phase', {})
                    season_name = season.get('zh', season.get('en', '未知'))
                    phase_name = phase.get('zh', phase.get('en', '未知'))
                    elapsed_days = season_info.get('elapsedDays', '未知')
                    
                    room_info.extend([
                        "",
                        f"🌍 {season_name} · {phase_name}",
                        f"📅 已过 {elapsed_days} 天"
                    ])
                
                response = "\n".join(room_info)
                
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
            response = f"❌ 获取房间信息失败: {result.message or '未知错误'}"
        
        await send_with_dedup(bot, event, response)
        
    except Exception as e:
        error_msg = f"❌ 处理房间信息命令时发生错误: {str(e)}"
        print(f"⚠️ {error_msg}")
        await send_with_dedup(bot, event, error_msg)

@sys_matcher.handle()
async def handle_sys_cmd(bot: Bot, event: Event):
    """处理系统信息命令"""
    try:
        result = await dmp_api.get_sys_info()
        if result.success:
            data = result.data
            
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
            response = f"❌ 获取系统信息失败: {result.message or '未知错误'}"
        
        await send_with_dedup(bot, event, response)
        
    except Exception as e:
        error_msg = f"❌ 处理系统信息命令时发生错误: {str(e)}"
        print(f"⚠️ {error_msg}")
        await send_with_dedup(bot, event, error_msg)

@players_matcher.handle()
async def handle_players_cmd(bot: Bot, event: Event):
    """处理玩家列表命令"""
    try:
        # 使用当前选择的集群（这个方法内部会处理集群可用性检查）
        cluster_name = await dmp_api.get_current_cluster()
        if not cluster_name:
            await send_with_dedup(bot, event, "❌ 无法获取可用集群列表，请检查DMP服务器连接")
            return
        result = await dmp_api.get_players(cluster_name)
        
        if result.success:
            data = result.data
            
            # 检查数据类型并安全处理
            if isinstance(data, dict):
                # 获取集群信息
                cluster_info_result = await dmp_api.get_cluster_info(cluster_name)
                cluster_info = cluster_info_result.data if cluster_info_result.success else {}
                cluster_display_name = cluster_info.get("clusterDisplayName", cluster_name)
                cluster_status = "运行中" if cluster_info.get("status") else "已停止"
                
                # 构建简洁的玩家信息显示
                status_icon = "🟢" if cluster_status == "运行中" else "🔴"
                player_info = [
                    f"👥 玩家信息",
                    f"{status_icon} {cluster_display_name}",
                    ""
                ]
                
                # 在线玩家信息
                players = data.get('players')
                if players and isinstance(players, list) and len(players) > 0:
                    player_info.append(f"🟢 在线玩家 ({len(players)}人)")
                    for i, player in enumerate(players, 1):
                        if isinstance(player, dict):
                            player_name = player.get('name', player.get('playerName', '未知'))
                            player_id = player.get('id', player.get('playerId', '未知'))
                            player_info.append(f"  {i}. {player_name}")
                        else:
                            player_info.append(f"  {i}. {str(player)}")
                else:
                    player_info.append("😴 当前没有在线玩家")
                
                # 管理员列表 - 优先显示
                admin_list = data.get('adminList')
                if admin_list and isinstance(admin_list, list) and len(admin_list) > 0:
                    player_info.extend([
                        "",
                        f"👑 管理员 ({len(admin_list)}人)"
                    ])
                    for i, admin in enumerate(admin_list, 1):
                        player_info.append(f"  {i}. {admin}")
                
                # 白名单玩家信息 - 仅显示数量，避免过长
                white_list = data.get('whiteList')
                if white_list and isinstance(white_list, list) and len(white_list) > 0:
                    player_info.extend([
                        "",
                        f"⚪ 白名单玩家: {len(white_list)}人"
                    ])
                
                # 封禁玩家列表
                block_list = data.get('blockList')
                if block_list and isinstance(block_list, list) and len(block_list) > 0:
                    player_info.extend([
                        "",
                        f"🚫 封禁玩家 ({len(block_list)}人)"
                    ])
                    for i, blocked in enumerate(block_list, 1):
                        player_info.append(f"  {i}. {blocked}")
                
                response = "\n".join(player_info)
                
                # 如果只有基本信息且没有玩家数据，显示原始数据结构  
                if len(player_info) <= 3:  # 只有标题和集群信息
                    player_info.extend([
                        f"数据结构: {list(data.keys())}",
                        f"原始数据: {data}"
                    ])
                    response = "\n".join(player_info)
                    
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
            response = f"❌ 获取玩家列表失败: {result.message or '未知错误'}"
        
        await send_with_dedup(bot, event, response)
        
    except Exception as e:
        error_msg = f"❌ 处理玩家列表命令时发生错误: {str(e)}"
        print(f"⚠️ {error_msg}")
        await send_with_dedup(bot, event, error_msg)

@connection_matcher.handle()
async def handle_connection_cmd(bot: Bot, event: Event):
    """处理直连信息命令"""
    try:
        # 使用当前选择的集群（这个方法内部会处理集群可用性检查）
        cluster_name = await dmp_api.get_current_cluster()
        if not cluster_name:
            await send_with_dedup(bot, event, "❌ 无法获取可用集群列表，请检查DMP服务器连接")
            return
        result = await dmp_api.get_connection_info(cluster_name)
        
        if result.success:
            data = result.data
            
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
                        
                        # 使用正则表达式更准确地解析参数
                        import re
                        
                        # 先尝试匹配三个参数: 'ip', port, 'password'
                        pattern_3_params = r"'([^']*)',\s*(\d+),\s*'([^']*)'"
                        match_3 = re.match(pattern_3_params, content)
                        
                        # 再尝试匹配两个参数: 'ip', port (无密码)
                        pattern_2_params = r"'([^']*)',\s*(\d+)"
                        match_2 = re.match(pattern_2_params, content)
                        
                        if match_3:
                            # 三参数格式
                            ip = match_3.group(1)
                            port = match_3.group(2)
                            password = match_3.group(3)
                            
                            response += f"IP地址: {ip}\n"
                            response += f"端口: {port}\n"
                            response += f"密码: {password}\n"
                            response += f"直连代码: {data}\n\n"
                            response += f"💡 使用方法:\n"
                            response += f"1. 在饥荒游戏中按 ~ 键打开控制台\n"
                            response += f"2. 复制粘贴上面的直连代码\n"
                            response += f"3. 按回车键执行即可连接到服务器"
                        elif match_2:
                            # 两参数格式（无密码）
                            ip = match_2.group(1)
                            port = match_2.group(2)
                            
                            response += f"IP地址: {ip}\n"
                            response += f"端口: {port}\n"
                            response += f"密码: 无密码\n"
                            response += f"直连代码: {data}\n\n"
                            response += f"💡 使用方法:\n"
                            response += f"1. 在饥荒游戏中按 ~ 键打开控制台\n"
                            response += f"2. 复制粘贴上面的直连代码\n"
                            response += f"3. 按回车键执行即可连接到服务器"
                        else:
                            # 如果正则匹配失败，尝试简单的分割方式作为备用
                            params = [p.strip(" '\"") for p in content.split(",")]
                            if len(params) >= 3:
                                response += f"IP地址: {params[0]}\n"
                                response += f"端口: {params[1]}\n"
                                response += f"密码: {params[2]}\n"
                                response += f"直连代码: {data}\n"
                            elif len(params) == 2:
                                response += f"IP地址: {params[0]}\n"
                                response += f"端口: {params[1]}\n"
                                response += f"密码: 无密码\n"
                                response += f"直连代码: {data}\n"
                            else:
                                response += f"直连代码: {data}\n"
                                response += f"⚠️ 无法解析直连代码格式 (参数数量: {len(params)})"
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
            response = f"❌ 获取直连信息失败: {result.message or '未知错误'}"
        
        await send_with_dedup(bot, event, response)
        
    except Exception as e:
        error_msg = f"❌ 处理直连信息命令时发生错误: {str(e)}"
        print(f"⚠️ {error_msg}")
        await send_with_dedup(bot, event, error_msg)

@help_matcher.handle()
async def handle_help_cmd(bot: Bot, event: Event):
    """处理帮助命令"""
    try:
        help_text = """🎮 饥荒管理平台机器人

🌟 基础功能
🌍 /世界 - 世界运行状态
🏠 /房间 - 房间设置信息  
💻 /系统 - 服务器状态
👥 /玩家 - 在线玩家列表
🔗 /直连 - 服务器直连代码
🗂️ /集群状态 - 所有集群信息

💬 消息互通
📱 /消息互通 - 开启QQ游戏通信
⏹️ /关闭互通 - 停止消息互通
📊 /互通状态 - 查看互通状态

🔧 管理功能
⚙️ /管理命令 - 管理员菜单
🏗️ /高级功能 - 高级管理功能

🖼️ 输出模式
📝 /切换模式 文字 - 切换到文字输出
📄 /切换模式 图片 - 切换到图片输出
📊 /模式状态 - 查看当前模式
🔄 /重置模式 - 重置为默认模式

💡 提示: 支持中英文命令，智能集群选择"""
        
        await send_with_dedup(bot, event, help_text)
        
    except Exception as e:
        error_msg = f"❌ 处理帮助命令时发生错误: {str(e)}"
        print(f"⚠️ {error_msg}")
        await send_with_dedup(bot, event, error_msg)

# handle_mode_cmd 已移至 output_mode_commands.py 中

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