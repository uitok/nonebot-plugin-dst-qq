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

async def send_server_info_text(bot: Bot, event: Event, fallback_text: str) -> bool:
    """
    发送服务器信息文字版本
    
    Args:
        bot: Bot实例
        event: 事件
        fallback_text: 文字内容
        
    Returns:
        bool: 是否成功发送
    """
    await send_long_message(bot, event, "服务器综合信息", fallback_text, max_length=1000)
    return True

async def send_help_menu_text(bot: Bot, event: Event, fallback_text: str) -> bool:
    """
    发送帮助菜单文字版本
    
    Args:
        bot: Bot实例
        event: 事件
        fallback_text: 文字内容
        
    Returns:
        bool: 是否成功发送
    """
    await bot.send(event, fallback_text)
    return True

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
            await bot.send(event, content)
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
        await bot.send(event, content)

# 创建Alconna命令 - 优化后的菜单，移除单独的世界、系统、玩家命令
# world_cmd = Alconna("世界")  # 已整合到房间命令中
room_cmd = Alconna("房间")
# sys_cmd = Alconna("系统")  # 已整合到房间命令中
# players_cmd = Alconna("玩家")  # 已整合到房间命令中
connection_cmd = Alconna("直连")
help_cmd = Alconna("菜单")
# mode_cmd 已移至 output_mode_commands.py 中统一管理

# 创建命令别名 - 保留房间、直连和菜单的英文命令
# world_cmd_eng = Alconna("world")  # 已整合到房间命令中
room_cmd_eng = Alconna("room")
# sys_cmd_eng = Alconna("sys")  # 已整合到房间命令中
# players_cmd_eng = Alconna("players")  # 已整合到房间命令中
connection_cmd_eng = Alconna("connection")
help_cmd_eng = Alconna("help")

# 创建响应器 - 仅保留优化后的命令
# world_matcher = on_alconna(world_cmd)  # 已整合到房间命令中
room_matcher = on_alconna(room_cmd)
# sys_matcher = on_alconna(sys_cmd)  # 已整合到房间命令中
# players_matcher = on_alconna(players_cmd)  # 已整合到房间命令中
connection_matcher = on_alconna(connection_cmd)
help_matcher = on_alconna(help_cmd)
# mode_matcher 已移至 output_mode_commands.py 中

# world_eng_matcher = on_alconna(world_cmd_eng)  # 已整合到房间命令中
room_eng_matcher = on_alconna(room_cmd_eng)
# sys_eng_matcher = on_alconna(sys_cmd_eng)  # 已整合到房间命令中
# players_eng_matcher = on_alconna(players_cmd_eng)  # 已整合到房间命令中
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
# 注释：以下世界信息命令已整合到房间命令中
# @world_matcher.handle()
# async def handle_world_cmd(bot: Bot, event: Event):
#     """处理世界信息命令 - 已整合到房间命令中"""
#     pass

@room_matcher.handle()
async def handle_room_cmd(bot: Bot, event: Event):
    """处理综合房间信息命令 - 包含世界、房间、系统和玩家信息"""
    try:
        # 使用当前选择的集群（这个方法内部会处理集群可用性检查）
        cluster_name = await dmp_api.get_current_cluster()
        if not cluster_name:
            await bot.send(event, "❌ 无法获取可用集群列表，请检查DMP服务器连接")
            return
        
        # 并发获取所有信息以提高响应速度
        import asyncio
        
        try:
            room_result, world_result, sys_result, players_result = await asyncio.gather(
                dmp_api.get_room_info(cluster_name),
                dmp_api.get_world_info(cluster_name),
                dmp_api.get_sys_info(),
                dmp_api.get_players(cluster_name),
                return_exceptions=True
            )
        except Exception as e:
            await bot.send(event, f"❌ 获取服务器信息失败: {str(e)}")
            return
        
        # 获取集群信息
        cluster_info_result = await dmp_api.get_cluster_info(cluster_name)
        cluster_info = cluster_info_result.data if cluster_info_result.success else {}
        cluster_display_name = cluster_info.get("clusterDisplayName", cluster_name)
        cluster_status = "运行中" if cluster_info.get("status") else "已停止"
        status_icon = "🟢" if cluster_status == "运行中" else "🔴"
        
        # 构建综合信息显示
        info_sections = [
            f"🏠 服务器综合信息",
            f"{status_icon} {cluster_display_name} ({cluster_status})",
            ""
        ]
        
        # === 房间基础信息 ===
        if isinstance(room_result, APIResponse) and room_result.success and room_result.data:
            room_data = room_result.data
            if isinstance(room_data, dict):
                cluster_setting = room_data.get('clusterSetting', {})
                season_info = room_data.get('seasonInfo', {})
                
                info_sections.extend([
                    f"🎮 房间名: {cluster_setting.get('name', '未知')}",
                    f"👥 最大玩家: {cluster_setting.get('playerNum', '未知')}",
                    f"⚔️ PvP: {'开启' if cluster_setting.get('pvp') else '关闭'}"
                ])
                
                # 密码信息
                password = cluster_setting.get('password', '')
                if password and password != '无':
                    info_sections.append(f"🔐 密码: {password}")
                
                # 季节信息
                if season_info:
                    season = season_info.get('season', {})
                    phase = season_info.get('phase', {})
                    season_name = season.get('zh', season.get('en', '未知'))
                    phase_name = phase.get('zh', phase.get('en', '未知'))
                    elapsed_days = season_info.get('elapsedDays', '未知')
                    
                    info_sections.extend([
                        f"🌍 {season_name} · {phase_name} (第{elapsed_days}天)"
                    ])
        
        # === 世界运行状态 ===
        info_sections.append("")
        if isinstance(world_result, APIResponse) and world_result.success and world_result.data:
            world_data = world_result.data
            if isinstance(world_data, list) and world_data:
                # 统计运行中的世界
                running_worlds = sum(1 for world in world_data if isinstance(world, dict) and world.get('stat'))
                total_worlds = len(world_data)
                info_sections.append(f"🌍 世界状态: {running_worlds}/{total_worlds} 个世界运行中")
                
                # 显示每个世界的状态
                for world in world_data:
                    if isinstance(world, dict):
                        world_name = world.get('world', '未知')
                        is_master = world.get('isMaster')
                        status = world.get('stat')
                        world_status_icon = "🟢" if status else "🔴"
                        world_type_icon = "🌍" if is_master else "🕳️"
                        world_type = "主世界" if is_master else "洞穴"
                        
                        info_sections.append(f"  {world_type_icon} {world_name} ({world_type}) {world_status_icon}")
        
        # === 系统状态 ===
        info_sections.append("")
        if isinstance(sys_result, APIResponse) and sys_result.success and sys_result.data:
            sys_data = sys_result.data
            if isinstance(sys_data, dict):
                cpu_usage = sys_data.get('cpu') or sys_data.get('cpuUsage')
                memory_usage = sys_data.get('memory') or sys_data.get('memoryUsage')
                
                if cpu_usage is not None and memory_usage is not None:
                    info_sections.append(f"💻 系统负载: CPU {cpu_usage:.1f}% | 内存 {memory_usage:.1f}%")
                else:
                    info_sections.append(f"💻 系统状态: 正常")
        
        # === 玩家信息 ===
        info_sections.append("")
        if isinstance(players_result, APIResponse) and players_result.success and players_result.data:
            players_data = players_result.data
            if isinstance(players_data, dict):
                # 在线玩家
                players = players_data.get('players') or []
                if players and isinstance(players, list) and len(players) > 0:
                    info_sections.append(f"👥 在线玩家 ({len(players)}人):")
                    for i, player in enumerate(players[:5], 1):  # 最多显示5个玩家
                        if isinstance(player, dict):
                            player_name = player.get('name', player.get('playerName', '未知'))
                            info_sections.append(f"  {i}. {player_name}")
                    if len(players) > 5:
                        info_sections.append(f"  ... 还有 {len(players) - 5} 人")
                else:
                    info_sections.append("😴 当前没有在线玩家")
                
                # 管理员信息
                admin_list = players_data.get('adminList') or []
                if admin_list and isinstance(admin_list, list):
                    info_sections.append(f"👑 管理员: {len(admin_list)}人")
                
                # 其他玩家统计
                white_list = players_data.get('whiteList') or []
                block_list = players_data.get('blockList') or []
                if white_list and isinstance(white_list, list):
                    info_sections.append(f"⚪ 白名单: {len(white_list)}人")
                if block_list and isinstance(block_list, list):
                    info_sections.append(f"🚫 封禁: {len(block_list)}人")
        
        # 准备服务器数据用于图片生成
        # 安全获取玩家数据
        safe_players_data = None
        online_players_count = 0
        admin_count = 0
        
        if isinstance(players_result, APIResponse) and players_result.success and players_result.data:
            if isinstance(players_result.data, dict):
                safe_players_data = players_result.data
                players_list = safe_players_data.get('players') or []
                admin_list = safe_players_data.get('adminList') or []
                online_players_count = len(players_list) if players_list is not None else 0
                admin_count = len(admin_list) if admin_list is not None else 0
            elif isinstance(players_result.data, list):
                # 如果数据是列表格式，假设是玩家列表
                online_players_count = len(players_result.data) if players_result.data is not None else 0
                safe_players_data = {'players': players_result.data, 'adminList': []}
        
        # 安全获取系统数据
        safe_system_data = None
        if isinstance(sys_result, APIResponse) and sys_result.success and sys_result.data and isinstance(sys_result.data, dict):
            safe_system_data = {
                'cpu_usage': sys_result.data.get('cpu', sys_result.data.get('cpuUsage', 0)),
                'memory_usage': sys_result.data.get('memory', sys_result.data.get('memoryUsage', 0))
            }
        
        server_data = {
            'cluster_name': cluster_display_name,
            'status': cluster_status,
            'online_players': str(online_players_count),
            'max_players': cluster_info.get('playerNum', '未知') if cluster_info else '未知',
            'admin_count': str(admin_count),
            'room_name': cluster_info.get('name', '未知') if cluster_info else '未知',
            'pvp_status': '开启' if cluster_info and cluster_info.get('pvp') else '关闭',
            'password': cluster_info.get('password') if cluster_info and cluster_info.get('password') != '无' else None,
            'season_info': season_info if 'season_info' in locals() else '未知',
            'system_data': safe_system_data,
            'world_data': world_result.data if isinstance(world_result, APIResponse) and world_result.success else None,
            'players_data': safe_players_data
        }
        
        # 构建文字回退
        response = "\n".join(info_sections)

        # 根据用户输出模式决定是否生成图片
        try_image_mode = False
        try:
            user_id = str(event.get_user_id())
            from ..message_dedup import _user_image_modes
            try_image_mode = user_id in _user_image_modes
            print(f"🔍 房间命令用户检查: user_id={user_id}, image_modes={_user_image_modes}, try_image={try_image_mode}")
        except Exception as e:
            print(f"⚠️ 获取用户图片模式失败: {e}")
            try_image_mode = False

        # 直接使用文字模式
        await send_server_info_text(bot, event, response)
        
    except Exception as e:
        error_msg = f"❌ 处理房间信息命令时发生错误: {str(e)}"
        print(f"⚠️ {error_msg}")
        await bot.send(event, error_msg)

# 注释：以下系统信息命令已整合到房间命令中
# @sys_matcher.handle()
# async def handle_sys_cmd(bot: Bot, event: Event):
#     """处理系统信息命令 - 已整合到房间命令中"""
#     pass

# 注释：以下玩家列表命令已整合到房间命令中
# @players_matcher.handle()
# async def handle_players_cmd(bot: Bot, event: Event):
#     """处理玩家列表命令 - 已整合到房间命令中"""
#     pass

@connection_matcher.handle()
async def handle_connection_cmd(bot: Bot, event: Event):
    """处理直连信息命令"""
    try:
        # 使用当前选择的集群（这个方法内部会处理集群可用性检查）
        cluster_name = await dmp_api.get_current_cluster()
        if not cluster_name:
            await bot.send(event, "❌ 无法获取可用集群列表，请检查DMP服务器连接")
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
        
        await bot.send(event, response)
        
    except Exception as e:
        error_msg = f"❌ 处理直连信息命令时发生错误: {str(e)}"
        print(f"⚠️ {error_msg}")
        await bot.send(event, error_msg)

@help_matcher.handle()
async def handle_help_cmd(bot: Bot, event: Event):
    """处理帮助命令 - 使用新的图片生成系统"""
    try:
        # 准备帮助菜单数据
        help_data = {
            "title": "饥荒管理平台机器人",
            "version": "v2.0.0",
            "command_groups": [
                {
                    "title": "🌟 基础功能",
                    "commands": [
                        {
                            "name": "/房间",
                            "description": "服务器综合信息 (世界·房间·系统·玩家)",
                            "aliases": "room"
                        },
                        {
                            "name": "/直连",
                            "description": "服务器直连代码",
                            "aliases": "connection"
                        },
                        {
                            "name": "/集群状态",
                            "description": "所有集群信息",
                            "aliases": "clusters"
                        }
                    ]
                },
                {
                    "title": "📖 物品查询",
                    "commands": [
                        {
                            "name": "/物品",
                            "description": "查询物品Wiki",
                            "aliases": "item"
                        },
                        {
                            "name": "/搜索物品",
                            "description": "搜索物品列表",
                            "aliases": "search"
                        },
                        {
                            "name": "/物品统计",
                            "description": "查看物品统计"
                        },
                        {
                            "name": "/重载物品",
                            "description": "重载物品数据"
                        }
                    ]
                },
                {
                    "title": "💬 消息互通",
                    "commands": [
                        {
                            "name": "/消息互通",
                            "description": "开启QQ游戏通信"
                        },
                        {
                            "name": "/关闭互通",
                            "description": "停止消息互通"
                        },
                        {
                            "name": "/互通状态",
                            "description": "查看互通状态"
                        }
                    ]
                },
                {
                    "title": "🔧 管理功能",
                    "commands": [
                        {
                            "name": "/管理命令",
                            "description": "管理员菜单"
                        },
                        {
                            "name": "/高级功能",
                            "description": "高级管理功能"
                        }
                    ]
                },
                {
                    "title": "🖼️ 输出模式",
                    "commands": [
                        {
                            "name": "/切换模式 文字",
                            "description": "切换到文字输出"
                        },
                        {
                            "name": "/切换模式 图片",
                            "description": "切换到图片输出"
                        },
                        {
                            "name": "/模式状态",
                            "description": "查看当前模式"
                        },
                        {
                            "name": "/重置模式",
                            "description": "重置为默认模式"
                        }
                    ]
                }
            ],
            "tips": [
                "使用 @机器人 + 命令名 来调用命令",
                "支持中英文命令别名",
                "部分命令需要管理员权限",
                "系统会智能选择可用的集群"
            ]
        }
        
        # 帮助菜单文字版本（回退用）
        help_text = """🎮 饥荒管理平台机器人

🌟 基础功能
🏠 /房间 - 服务器综合信息 (世界·房间·系统·玩家)
🔗 /直连 - 服务器直连代码
🗂️ /集群状态 - 所有集群信息

📖 物品查询
🔍 /物品 - 查询物品Wiki
📋 /搜索物品 - 搜索物品列表
📊 /物品统计 - 查看物品统计
🔄 /重载物品 - 重载物品数据

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
        
        # 根据用户输出模式决定是否生成图片
        try_image_mode = False
        try:
            user_id = str(event.get_user_id())
            from ..message_dedup import _user_image_modes
            try_image_mode = user_id in _user_image_modes
            print(f"🔍 房间命令用户检查: user_id={user_id}, image_modes={_user_image_modes}, try_image={try_image_mode}")
        except Exception as e:
            print(f"⚠️ 获取用户图片模式失败: {e}")
            try_image_mode = False

        if False:  # 禁用图片模式
            try:
                # from ..text_to_image import generate_help_menu_image  # 已删除
                from nonebot.adapters.onebot.v11 import MessageSegment
                
                # 使用二次元海报背景主题
                result, image_bytes = await generate_help_menu_image(help_data, theme="anime_poster")
                
                if result == "bytes" and image_bytes:
                    await bot.send(event, MessageSegment.image(image_bytes))
                    print(f"✅ 帮助菜单图片发送成功")
                    return
            except Exception as img_e:
                print(f"⚠️ 生成帮助菜单图片失败，回退到文字模式: {img_e}")

        # 回退到文字模式
        await send_help_menu_text(bot, event, help_text)
        
    except Exception as e:
        error_msg = f"❌ 处理帮助命令时发生错误: {str(e)}"
        print(f"⚠️ {error_msg}")
        await bot.send(event, error_msg)

# handle_mode_cmd 已移至 output_mode_commands.py 中

# 英文命令处理器
# 注释：世界、系统、玩家命令的英文版本已整合到房间命令中
# @world_eng_matcher.handle()
# async def handle_world_cmd_eng(bot: Bot, event: Event):
#     """处理英文世界信息命令 - 已整合到房间命令中"""
#     pass

@room_eng_matcher.handle()
async def handle_room_cmd_eng(bot: Bot, event: Event):
    """处理英文房间信息命令"""
    await handle_room_cmd(bot, event)

# @sys_eng_matcher.handle()
# async def handle_sys_cmd_eng(bot: Bot, event: Event):
#     """处理英文系统信息命令 - 已整合到房间命令中"""
#     pass

# @players_eng_matcher.handle()
# async def handle_players_cmd_eng(bot: Bot, event: Event):
#     """处理英文玩家列表命令 - 已整合到房间命令中"""
#     pass

@connection_eng_matcher.handle()
async def handle_connection_cmd_eng(bot: Bot, event: Event):
    """处理英文直连信息命令"""
    await handle_connection_cmd(bot, event)

@help_eng_matcher.handle()
async def handle_help_cmd_eng(bot: Bot, event: Event):
    """处理英文帮助命令"""
    await handle_help_cmd(bot, event)

# 移除旧的HTML生成函数，现在使用模板系统
# async def _generate_server_info_html(...) - 已移至模板系统

async def _generate_server_info_html_deprecated(info_sections: list, cluster_name: str, cluster_status: str, 
                                     world_result: 'APIResponse' = None, sys_result: 'APIResponse' = None) -> str:
    """生成美观的服务器信息HTML界面，包含圆形系统状态显示"""
    
    # 状态颜色和图标
    status_color = "#10b981" if cluster_status == "运行中" else "#ef4444"
    status_icon = "🟢" if cluster_status == "运行中" else "🔴"
    
    # 解析信息部分
    room_name = "未知"
    max_players = "未知"
    pvp_status = "关闭"
    season_info = ""
    world_status = ""
    online_players = "0人"
    admin_count = "0人"
    
    # 系统状态数据
    cpu_usage = 0
    memory_usage = 0
    cpu_text = "N/A"
    memory_text = "N/A"
    
    # 解析系统状态数据
    if sys_result and sys_result.success and sys_result.data:
        sys_data = sys_result.data
        if isinstance(sys_data, dict):
            cpu_val = sys_data.get('cpu') or sys_data.get('cpuUsage')
            mem_val = sys_data.get('memory') or sys_data.get('memoryUsage')
            
            if cpu_val is not None:
                cpu_usage = float(cpu_val)
                cpu_text = f"{cpu_usage:.1f}%"
            if mem_val is not None:
                memory_usage = float(mem_val)
                memory_text = f"{memory_usage:.1f}%"
    
    for line in info_sections:
        if line.startswith("🎮 房间名:"):
            room_name = line.replace("🎮 房间名: ", "")
        elif line.startswith("👥 最大玩家:"):
            max_players = line.replace("👥 最大玩家: ", "")
        elif line.startswith("⚔️ PvP:"):
            pvp_status = line.replace("⚔️ PvP: ", "")
        elif line.startswith("🌍") and "·" in line:
            season_info = line
        elif line.startswith("🌍 世界状态:"):
            world_status = line.replace("🌍 世界状态: ", "")
        elif line.startswith("👥 在线玩家"):
            online_players = line.replace("👥 在线玩家 ", "").replace(":", "")
        elif line.startswith("👑 管理员:"):
            admin_count = line.replace("👑 管理员: ", "")
    
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
                padding: 25px;
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
                background: linear-gradient(90deg, transparent, rgba(255,255,255,0.6), transparent);
                z-index: 1;
            }}
            .header > * {{
                position: relative;
                z-index: 2;
            }}
            .server-name {{
                font-size: 24px;
                font-weight: bold;
                color: #2d3748;
                margin-bottom: 5px;
            }}
            .status {{
                display: inline-flex;
                align-items: center;
                background: {status_color};
                color: white;
                padding: 5px 15px;
                border-radius: 20px;
                font-size: 14px;
                font-weight: 500;
            }}
            .stats-grid {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 15px;
                margin-bottom: 20px;
            }}
            .stat-card {{
                background: rgba(255, 255, 255, 0.04);
                backdrop-filter: blur(25px) saturate(200%) brightness(1.1);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 18px;
                padding: 20px;
                text-align: center;
                box-shadow: 
                    0 6px 24px rgba(0, 0, 0, 0.08),
                    inset 0 1px 0 rgba(255, 255, 255, 0.7),
                    0 1px 0 rgba(0, 0, 0, 0.03);
                position: relative;
                overflow: hidden;
                transition: all 0.3s ease;
            }}
            .stat-card::before {{
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 1px;
                background: linear-gradient(90deg, transparent, rgba(255,255,255,0.5), transparent);
                z-index: 1;
            }}
            .stat-card > * {{
                position: relative;
                z-index: 2;
            }}
            .stat-value {{
                font-size: 24px;
                font-weight: bold;
                color: #2d3748;
                margin-bottom: 5px;
            }}
            .stat-label {{
                font-size: 14px;
                color: #718096;
            }}
            .info-card {{
                background: rgba(255, 255, 255, 0.04);
                backdrop-filter: blur(25px) saturate(200%) brightness(1.1);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 18px;
                padding: 20px;
                margin-bottom: 15px;
                box-shadow: 
                    0 6px 24px rgba(0, 0, 0, 0.08),
                    inset 0 1px 0 rgba(255, 255, 255, 0.7),
                    0 1px 0 rgba(0, 0, 0, 0.03);
                position: relative;
                overflow: hidden;
            }}
            .info-card::before {{
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 1px;
                background: linear-gradient(90deg, transparent, rgba(255,255,255,0.5), transparent);
                z-index: 1;
            }}
            .info-card > * {{
                position: relative;
                z-index: 2;
            }}
            .info-title {{
                font-size: 16px;
                font-weight: bold;
                color: #2d3748;
                margin-bottom: 15px;
                display: flex;
                align-items: center;
            }}
            .info-item {{
                display: flex;
                justify-content: space-between;
                padding: 8px 0;
                border-bottom: 1px solid #e2e8f0;
            }}
            .info-item:last-child {{
                border-bottom: none;
            }}
            .info-label {{
                color: #718096;
                font-size: 14px;
            }}
            .info-value {{
                color: #2d3748;
                font-weight: 500;
                font-size: 14px;
            }}
            .footer {{
                text-align: center;
                color: rgba(255, 255, 255, 0.8);
                font-size: 12px;
                margin-top: 20px;
            }}
            
            /* 系统状态圆形进度条样式 */
            .system-stats {{
                display: grid;
                grid-template-columns: 1fr 1fr 1fr;
                gap: 20px;
                margin-bottom: 20px;
            }}
            .circle-progress {{
                position: relative;
                width: 70px;
                height: 70px;
                margin: 0 auto 8px;
            }}
            .circle-progress svg {{
                width: 70px;
                height: 70px;
                transform: rotate(-90deg);
            }}
            .circle-progress-bg {{
                fill: none;
                stroke: #e2e8f0;
                stroke-width: 6;
            }}
            .circle-progress-fill {{
                fill: none;
                stroke-width: 6;
                stroke-linecap: round;
                transition: stroke-dasharray 0.6s ease;
            }}
            .cpu-progress {{
                stroke: #3b82f6;
            }}
            .memory-progress {{
                stroke: #10b981;
            }}
            .disk-progress {{
                stroke: #f59e0b;
            }}
            .circle-text {{
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                font-size: 12px;
                font-weight: bold;
                color: #2d3748;
                text-align: center;
            }}
            .circle-label {{
                text-align: center;
                font-size: 14px;
                color: #718096;
                font-weight: 500;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="server-name">{cluster_name}</div>
                <div class="status">{status_icon} {cluster_status}</div>
            </div>
            
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-value">{online_players}</div>
                    <div class="stat-label">在线玩家</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{admin_count}</div>
                    <div class="stat-label">管理员</div>
                </div>
            </div>
            
            <!-- 系统状态圆形进度条 -->
            <div class="info-card">
                <div class="info-title">💻 系统状态</div>
                <div class="system-stats">
                    <div>
                        <div class="circle-progress">
                            <svg>
                                <circle class="circle-progress-bg" cx="35" cy="35" r="28"></circle>
                                <circle class="circle-progress-fill cpu-progress" cx="35" cy="35" r="28" 
                                        stroke-dasharray="{175.93 * cpu_usage / 100:.2f} 175.93"></circle>
                            </svg>
                            <div class="circle-text">{cpu_text}</div>
                        </div>
                        <div class="circle-label">CPU</div>
                    </div>
                    <div>
                        <div class="circle-progress">
                            <svg>
                                <circle class="circle-progress-bg" cx="35" cy="35" r="28"></circle>
                                <circle class="circle-progress-fill memory-progress" cx="35" cy="35" r="28" 
                                        stroke-dasharray="{175.93 * memory_usage / 100:.2f} 175.93"></circle>
                            </svg>
                            <div class="circle-text">{memory_text}</div>
                        </div>
                        <div class="circle-label">内存</div>
                    </div>
                    <div>
                        <div class="circle-progress">
                            <svg>
                                <circle class="circle-progress-bg" cx="35" cy="35" r="28"></circle>
                                <circle class="circle-progress-fill disk-progress" cx="35" cy="35" r="28" 
                                        stroke-dasharray="0 175.93"></circle>
                            </svg>
                            <div class="circle-text">N/A</div>
                        </div>
                        <div class="circle-label">磁盘</div>
                    </div>
                </div>
            </div>
            
            <div class="info-card">
                <div class="info-title">🏠 房间信息</div>
                <div class="info-item">
                    <span class="info-label">房间名</span>
                    <span class="info-value">{room_name}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">最大玩家</span>
                    <span class="info-value">{max_players}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">PvP模式</span>
                    <span class="info-value">{pvp_status}</span>
                </div>
            </div>
            
            {f'''<div class="info-card">
                <div class="info-title">🌍 世界状态</div>
                <div class="info-item">
                    <span class="info-label">运行状态</span>
                    <span class="info-value">{world_status}</span>
                </div>
                {f'<div class="info-item"><span class="info-label">季节信息</span><span class="info-value">{season_info}</span></div>' if season_info else ''}
            </div>''' if world_status else ''}
            
            
            <div class="footer">
                🎮 饥荒管理平台机器人 - {cluster_name}
            </div>
        </div>
    </body>
    </html>
    """
    
    return html_template

async def _generate_help_menu_html() -> str:
    """生成美观的帮助菜单HTML界面"""
    
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
                padding: 25px;
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
                background: linear-gradient(90deg, transparent, rgba(255,255,255,0.6), transparent);
                z-index: 1;
            }}
            .header > * {{
                position: relative;
                z-index: 2;
            }}
            .title {{
                font-size: 24px;
                font-weight: bold;
                color: #2d3748;
                margin-bottom: 5px;
            }}
            .subtitle {{
                font-size: 14px;
                color: #718096;
            }}
            .menu-section {{
                background: rgba(255, 255, 255, 0.04);
                backdrop-filter: blur(25px) saturate(200%) brightness(1.1);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 18px;
                padding: 20px;
                margin-bottom: 15px;
                box-shadow: 
                    0 6px 24px rgba(0, 0, 0, 0.08),
                    inset 0 1px 0 rgba(255, 255, 255, 0.7),
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
                background: linear-gradient(90deg, transparent, rgba(255,255,255,0.5), transparent);
                z-index: 1;
            }}
            .menu-section > * {{
                position: relative;
                z-index: 2;
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
                <div class="title">🎮 饥荒管理平台机器人</div>
                <div class="subtitle">DST Management Platform Bot</div>
            </div>
            
            <div class="menu-section">
                <div class="section-title">🌟 基础功能</div>
                <div class="menu-item">
                    <span class="command">🏠 /房间</span>
                    <span class="description">服务器综合信息</span>
                </div>
                <div class="menu-item">
                    <span class="command">🔗 /直连</span>
                    <span class="description">服务器直连代码</span>
                </div>
                <div class="menu-item">
                    <span class="command">🗂️ /集群状态</span>
                    <span class="description">所有集群信息</span>
                </div>
            </div>
            
            <div class="menu-section">
                <div class="section-title">📖 物品查询</div>
                <div class="menu-item">
                    <span class="command">🔍 /物品</span>
                    <span class="description">查询物品Wiki</span>
                </div>
                <div class="menu-item">
                    <span class="command">📋 /搜索物品</span>
                    <span class="description">搜索物品列表</span>
                </div>
                <div class="menu-item">
                    <span class="command">📊 /物品统计</span>
                    <span class="description">查看物品统计</span>
                </div>
            </div>
            
            <div class="menu-section">
                <div class="section-title">💬 消息互通</div>
                <div class="menu-item">
                    <span class="command">📱 /消息互通</span>
                    <span class="description">开启QQ游戏通信</span>
                </div>
                <div class="menu-item">
                    <span class="command">⏹️ /关闭互通</span>
                    <span class="description">停止消息互通</span>
                </div>
                <div class="menu-item">
                    <span class="command">📊 /互通状态</span>
                    <span class="description">查看互通状态</span>
                </div>
            </div>
            
            <div class="menu-section">
                <div class="section-title">🔧 管理功能</div>
                <div class="menu-item">
                    <span class="command">⚙️ /管理命令</span>
                    <span class="description">管理员菜单</span>
                </div>
                <div class="menu-item">
                    <span class="command">🏗️ /高级功能</span>
                    <span class="description">高级管理功能</span>
                </div>
            </div>
            
            <div class="menu-section">
                <div class="section-title">🖼️ 输出模式</div>
                <div class="menu-item">
                    <span class="command">📝 /切换模式</span>
                    <span class="description">切换输出模式</span>
                </div>
                <div class="menu-item">
                    <span class="command">📊 /模式状态</span>
                    <span class="description">查看当前模式</span>
                </div>
            </div>
            
            <div class="footer">
                💡 提示: 支持中英文命令，智能集群选择
            </div>
        </div>
    </body>
    </html>
    """
    
    return html_template

# 初始化DMP API实例
def init_dmp_api():
    global dmp_api
    if dmp_api is None:
        dmp_api = DMPAPI()
        print("✅ DMP API 实例初始化成功")

# 在模块加载时初始化
init_dmp_api() 