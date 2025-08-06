import httpx
from nonebot import on_command, on_regex
from nonebot.adapters import Event
from nonebot.adapters.onebot.v11 import Bot, Message
from nonebot.params import CommandArg, RegexGroup
from nonebot.permission import SUPERUSER
from nonebot.rule import to_me
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
        
        url = f"{self.base_url}/setting/player/list"
        params = {"clusterName": cluster_name}
        
        return await self._make_request("GET", url, params=params)
    
    async def get_clusters(self) -> dict:
        """获取集群列表"""
        url = f"{self.base_url}/setting/clusters"
        
        return await self._make_request("GET", url)
    
    async def execute_command(self, cluster_name: str, world_name: str, command: str) -> dict:
        """执行命令"""
        url = f"{self.base_url}/home/exec"
        
        # 准备请求头 - 根据curl示例调整
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


# 创建API客户端实例
dmp_api = DMPAPI()

# 命令处理器
world_info_cmd = on_command("世界", aliases={"world", "worldinfo"}, priority=5)
room_info_cmd = on_command("房间", aliases={"room", "roominfo"}, priority=5)
sys_info_cmd = on_command("系统", aliases={"sys", "sysinfo"}, priority=5)
player_list_cmd = on_command("玩家", aliases={"players", "playerlist"}, priority=5)
connection_cmd = on_command("直连", aliases={"connect", "connection"}, priority=5)


@world_info_cmd.handle()
async def handle_world_info(bot: Bot, event: Event, state: T_State):
    """处理世界信息命令"""
    message = ""
    try:
        # 使用第一个集群
        config = get_config()
        cluster_name = await config.get_first_cluster()
        result = await dmp_api.get_world_info(cluster_name)
        
        if result.get("code") == 200:
            data = result.get("data", {})
            message = f"🌍 世界信息 (集群: {cluster_name}):\n"
            
            # 处理不同类型的响应数据
            if isinstance(data, dict):
                # 如果是字典类型
                for world_name, world_data in data.items():
                    message += f"\n📋 {world_name}:\n"
                    if isinstance(world_data, dict):
                        for key, value in world_data.items():
                            # 自定义字段显示
                            if key == "isMaster":
                                message += f"  • 主世界: {'是' if value else '否'}\n"
                            elif key == "stat":
                                message += f"  • 运行状态: {'运行中' if value else '已停止'}\n"
                            elif key == "type":
                                message += f"  • 地图类型: {value}\n"
                            # 跳过世界ID、世界类型和系统信息字段
                            elif key in ["world", "id", "cpu", "mem", "memSize", "diskUsed"]:
                                continue
                            else:
                                # 限制字段值长度
                                value_str = str(value)
                                if len(value_str) > 100:
                                    value_str = value_str[:100] + "..."
                                message += f"  • {key}: {value_str}\n"
                    else:
                        value_str = str(world_data)
                        if len(value_str) > 100:
                            value_str = value_str[:100] + "..."
                        message += f"  • {value_str}\n"
            elif isinstance(data, list):
                # 如果是列表类型
                for i, item in enumerate(data, 1):
                    message += f"\n📋 世界 {i}:\n"
                    if isinstance(item, dict):
                        for key, value in item.items():
                            # 自定义字段显示
                            if key == "isMaster":
                                message += f"  • 主世界: {'是' if value else '否'}\n"
                            elif key == "stat":
                                message += f"  • 运行状态: {'运行中' if value else '已停止'}\n"
                            elif key == "type":
                                message += f"  • 地图类型: {value}\n"
                            # 跳过世界ID、世界类型和系统信息字段
                            elif key in ["world", "id", "cpu", "mem", "memSize", "diskUsed"]:
                                continue
                            else:
                                # 限制字段值长度
                                value_str = str(value)
                                if len(value_str) > 100:
                                    value_str = value_str[:100] + "..."
                                message += f"  • {key}: {value_str}\n"
                    else:
                        value_str = str(item)
                        if len(value_str) > 100:
                            value_str = value_str[:100] + "..."
                        message += f"  • {value_str}\n"
            else:
                # 其他类型直接显示
                data_str = str(data)
                if len(data_str) > 2000:
                    data_str = data_str[:2000] + "..."
                message += f"  {data_str}"
        else:
            message = f"❌ 获取世界信息失败: {result.get('message', '未知错误')}"
        
    except Exception as e:
        # 简化错误信息
        error_msg = str(e)
        if len(error_msg) > 200:
            error_msg = error_msg[:200] + "..."
        message = f"❌ 获取世界信息时发生错误: {error_msg}"
    
    # 确保消息长度不超过QQ限制
    if len(message) > 4000:
        message = message[:4000] + "\n... (消息过长，已截断)"
    
    # 只调用一次finish
    await world_info_cmd.finish(Message(message))


@room_info_cmd.handle()
async def handle_room_info(bot: Bot, event: Event, state: T_State):
    """处理房间信息命令"""
    message = ""
    try:
        # 使用第一个集群
        config = get_config()
        cluster_name = await config.get_first_cluster()
        result = await dmp_api.get_room_info(cluster_name)
        
        if result.get("code") == 200:
            data = result.get("data", {})
            message = f"🏠 房间信息 (集群: {cluster_name}):\n"
            
            # 处理不同类型的响应数据
            if isinstance(data, dict):
                for key, value in data.items():
                    # 特殊处理不同类型的字段
                    if key == "clusterSetting" and isinstance(value, dict):
                        # 只显示房间名称，跳过其他集群设置
                        cluster_setting = value
                        room_name = cluster_setting.get('name', 'Unknown')
                        message += f"\n📋 房间名称: {room_name}\n"
                        
                    elif key == "seasonInfo" and isinstance(value, dict):
                        message += f"\n🌍 季节信息:\n"
                        season_info = value
                        message += f"  • 周期: {season_info.get('cycles', 'Unknown')}\n"
                        
                        # 处理季节信息
                        phase = season_info.get('phase', {})
                        if isinstance(phase, dict):
                            phase_zh = phase.get('zh', 'Unknown')
                            message += f"  • 阶段: {phase_zh}\n"
                        else:
                            message += f"  • 阶段: {phase}\n"
                        
                        season = season_info.get('season', {})
                        if isinstance(season, dict):
                            season_zh = season.get('zh', 'Unknown')
                            message += f"  • 季节: {season_zh}\n"
                        else:
                            message += f"  • 季节: {season}\n"
                        
                        message += f"  • 已过天数: {season_info.get('elapsedDays', 'Unknown')}\n"
                        
                        # 处理季节长度
                        season_length = season_info.get('seasonLength', {})
                        if isinstance(season_length, dict):
                            message += f"  • 季节长度:\n"
                            for season_name, days in season_length.items():
                                season_names = {'summer': '夏季', 'autumn': '秋季', 'spring': '春季', 'winter': '冬季'}
                                display_name = season_names.get(season_name, season_name)
                                message += f"    - {display_name}: {days}天\n"
                        
                    elif key == "modsCount":
                        message += f"\n🔧 MOD数量: {value}\n"
                        
                    elif key == "players":
                        message += f"\n👥 玩家信息:\n"
                        if value is None:
                            message += "  • 暂无玩家信息\n"
                        elif isinstance(value, list):
                            if value:
                                for player in value:
                                    if isinstance(player, dict):
                                        name = player.get('name', 'Unknown')
                                        userid = player.get('userid', 'Unknown')
                                        message += f"  • {name} (ID: {userid})\n"
                                    else:
                                        message += f"  • {player}\n"
                            else:
                                message += "  • 暂无在线玩家\n"
                        else:
                            message += f"  • {value}\n"
                            
                    else:
                        # 其他字段的通用处理
                        if isinstance(value, dict):
                            message += f"\n📊 {key}:\n"
                            for sub_key, sub_value in value.items():
                                message += f"  • {sub_key}: {sub_value}\n"
                        elif isinstance(value, list):
                            message += f"\n📊 {key}:\n"
                            for i, item in enumerate(value, 1):
                                message += f"  • {i}. {item}\n"
                        else:
                            message += f"• {key}: {value}\n"
                            
            elif isinstance(data, list):
                for i, item in enumerate(data, 1):
                    message += f"• 房间 {i}: {item}\n"
            else:
                message += f"  {data}"
        else:
            message = f"❌ 获取房间信息失败: {result.get('message', '未知错误')}"
        
    except Exception as e:
        message = f"❌ 获取房间信息时发生错误: {str(e)}"
    
    # 确保消息长度不超过QQ限制
    if len(message) > 4000:
        message = message[:4000] + "\n... (消息过长，已截断)"
    
    # 只调用一次finish
    await room_info_cmd.finish(Message(message))


@sys_info_cmd.handle()
async def handle_sys_info(bot: Bot, event: Event, state: T_State):
    """处理系统信息命令"""
    message = ""
    try:
        result = await dmp_api.get_sys_info()
        
        if result.get("code") == 200:
            data = result.get("data", {})
            message = "💻 系统信息:\n"
            
            # 处理不同类型的响应数据
            if isinstance(data, dict):
                for key, value in data.items():
                    # 限制字段值长度
                    value_str = str(value)
                    if len(value_str) > 100:
                        value_str = value_str[:100] + "..."
                    message += f"• {key}: {value_str}\n"
            elif isinstance(data, list):
                for i, item in enumerate(data, 1):
                    item_str = str(item)
                    if len(item_str) > 100:
                        item_str = item_str[:100] + "..."
                    message += f"• 信息 {i}: {item_str}\n"
            else:
                data_str = str(data)
                if len(data_str) > 2000:
                    data_str = data_str[:2000] + "..."
                message += f"  {data_str}"
        else:
            message = f"❌ 获取系统信息失败: {result.get('message', '未知错误')}"
        
    except Exception as e:
        message = f"❌ 获取系统信息时发生错误: {str(e)}"
    
    # 确保消息长度不超过QQ限制
    if len(message) > 4000:
        message = message[:4000] + "\n... (消息过长，已截断)"
    
    # 只调用一次finish
    await sys_info_cmd.finish(Message(message))


@player_list_cmd.handle()
async def handle_player_list(bot: Bot, event: Event, state: T_State):
    """处理玩家列表命令"""
    message = ""
    try:
        # 使用第一个集群
        config = get_config()
        cluster_name = await config.get_first_cluster()
        result = await dmp_api.get_player_list(cluster_name)
        
        if result.get("code") == 200:
            data = result.get("data", [])
            message = f"👥 在线玩家 (集群: {cluster_name}):\n"
            
            if data:
                for player in data:
                    if isinstance(player, dict):
                        name = player.get('name', 'Unknown')
                        userid = player.get('userid', 'Unknown')
                        # 限制玩家名称长度
                        if len(name) > 50:
                            name = name[:50] + "..."
                        message += f"• {name} (ID: {userid})\n"
                    else:
                        player_str = str(player)
                        if len(player_str) > 100:
                            player_str = player_str[:100] + "..."
                        message += f"• {player_str}\n"
            else:
                message += "暂无在线玩家"
        else:
            message = f"❌ 获取玩家列表失败: {result.get('message', '未知错误')}"
        
    except Exception as e:
        message = f"❌ 获取玩家列表时发生错误: {str(e)}"
    
    # 确保消息长度不超过QQ限制
    if len(message) > 4000:
        message = message[:4000] + "\n... (消息过长，已截断)"
    
    # 只调用一次finish
    await player_list_cmd.finish(Message(message))


@connection_cmd.handle()
async def handle_connection(bot: Bot, event: Event, state: T_State, args: Message = CommandArg()):
    """处理直连命令"""
    message = ""
    try:
        # 使用第一个集群，忽略用户输入的集群参数
        config = get_config()
        cluster_name = await config.get_first_cluster()
        
        # 导入高级API模块来获取直连信息
        from .dmp_advanced import dmp_advanced
        result = await dmp_advanced.get_connection_code(cluster_name)
        
        if result.get("code") == 200:
            data = result.get("data", {})
            message = f"🔗 直连信息 (集群: {cluster_name}):\n"
            
            if isinstance(data, dict):
                for key, value in data.items():
                    # 限制字段值长度
                    value_str = str(value)
                    if len(value_str) > 100:
                        value_str = value_str[:100] + "..."
                    message += f"• {key}: {value_str}\n"
            else:
                data_str = str(data)
                if len(data_str) > 2000:
                    data_str = data_str[:2000] + "..."
                message += f"  {data_str}"
        else:
            message = f"❌ 获取直连信息失败: {result.get('message', '未知错误')}"
        
    except Exception as e:
        message = f"❌ 获取直连信息时发生错误: {str(e)}"
    
    # 确保消息长度不超过QQ限制
    if len(message) > 4000:
        message = message[:4000] + "\n... (消息过长，已截断)"
    
    # 只调用一次finish
    await connection_cmd.finish(Message(message))


# 帮助命令
help_cmd = on_command("菜单", aliases={"help", "dmp", "menu"}, priority=5)


@help_cmd.handle()
async def handle_help(bot: Bot, event: Event, state: T_State):
    """处理菜单命令"""
    help_text = """
🤖 晨曦 饥荒管理平台机器人

📋 基础命令:
• /世界 - 获取世界信息
• /房间 - 获取房间信息  
• /系统 - 获取系统信息
• /玩家 - 获取在线玩家列表
• /直连 - 获取服务器直连信息

📋 管理命令:
• /管理命令 - 显示管理员功能菜单

📋 帮助命令:
• /菜单 - 显示此菜单信息

💬 聊天功能:
• 使用 消息互通
• 使用 关闭互通
    """
    
    await help_cmd.finish(Message(help_text)) 