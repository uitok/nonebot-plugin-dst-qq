import asyncio
import httpx
import json
from datetime import datetime
from typing import Dict, List, Optional, Set
from arclet.alconna import Alconna, Args, Field, Option, Subcommand
from arclet.alconna.typing import CommandMeta
from nonebot import on_alconna, get_driver
from nonebot.adapters import Event
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, PrivateMessageEvent, Message
from nonebot.params import Depends
from nonebot.permission import SUPERUSER
from nonebot.typing import T_State
from nonebot.log import logger
from nonebot.matcher import Matcher

# 导入配置
from ..config import Config
from .. import get_config
from ..database import ChatHistoryDatabase
config = get_config()


class MessageExchangeManager:
    """消息互通管理器"""
    
    def __init__(self):
        self.db = ChatHistoryDatabase()
        self.active_users: Set[int] = set()  # 启用消息互通的用户ID集合
        self.last_sync_time: Dict[str, datetime] = {}  # 每个集群的最后同步时间
        self.sync_interval = 5  # 同步间隔（秒）- 改为5秒
        self.is_running = False
        self.sync_task: Optional[asyncio.Task] = None
        self.last_message_hashes: Dict[str, Set[str]] = {}  # 存储每个集群的最后消息哈希，用于检测新消息
        self.user_preferences: Dict[int, Dict] = {}  # 用户偏好设置，如只监控特定世界
        self.is_initialized = False  # 标记是否已初始化消息哈希集合
    
    async def start_sync(self):
        """启动消息同步任务"""
        if self.is_running:
            return
        
        self.is_running = True
        await self.db.init_database()
        self.sync_task = asyncio.create_task(self._sync_loop())
        logger.info("消息同步任务已启动")
    
    async def stop_sync(self):
        """停止消息同步任务"""
        self.is_running = False
        if self.sync_task:
            self.sync_task.cancel()
            try:
                await self.sync_task
            except asyncio.CancelledError:
                pass
        logger.info("消息同步任务已停止")
    
    async def _sync_loop(self):
        """消息同步循环"""
        while self.is_running:
            try:
                await self._sync_game_messages()
                await asyncio.sleep(self.sync_interval)
            except Exception as e:
                logger.error(f"消息同步出错: {e}")
                await asyncio.sleep(5)
    
    async def _sync_game_messages(self):
        """同步游戏内消息"""
        try:
            # 如果还没有初始化，跳过同步
            if not self.is_initialized:
                logger.debug("消息哈希集合尚未初始化，跳过同步")
                return
            
            # 收集所有世界的新消息
            all_new_messages = await self._collect_all_new_messages()
            
            # 合并并推送消息
            if all_new_messages:
                await self._merge_and_push_messages(all_new_messages)
                
                # 统计推送的消息数量
                total_new_messages = sum(len(messages) for messages in all_new_messages.values())
                logger.info(f"推送了 {total_new_messages} 条新消息")
                    
        except Exception as e:
            logger.error(f"同步游戏消息失败: {e}")
    
    async def _get_clusters(self) -> List[Dict]:
        """获取集群列表"""
        try:
            headers = {
                "Authorization": config.dmp_token,
                "X-I18n-Lang": "zh"
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{config.dmp_base_url}/setting/clusters", headers=headers)
                response.raise_for_status()
                data = response.json()
                
                if data.get("code") == 200:
                    return data.get("data", [])
                else:
                    logger.error(f"获取集群列表失败: {data.get('message', '未知错误')}")
                    return []
        except Exception as e:
            logger.error(f"获取集群列表时出错: {e}")
            return []
    
    async def _get_worlds(self, cluster_name: str) -> List[Dict]:
        """获取指定集群的世界列表"""
        try:
            headers = {
                "Authorization": config.dmp_token,
                "X-I18n-Lang": "zh"
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{config.dmp_base_url}/home/world_info", headers=headers, params={"clusterName": cluster_name})
                response.raise_for_status()
                data = response.json()
                
                if data.get("code") == 200:
                    worlds_data = data.get("data", {})
                    if isinstance(worlds_data, dict):
                        return worlds_data.get("worlds", [])
                    elif isinstance(worlds_data, list):
                        return worlds_data
                    else:
                        return []
                else:
                    logger.error(f"获取世界列表失败: {data.get('message', '未知错误')}")
                    return []
        except Exception as e:
            logger.error(f"获取世界列表时出错: {e}")
            return []
    
    async def _initialize_message_hashes(self):
        """初始化消息哈希集合"""
        try:
            clusters = await self._get_clusters()
            
            for cluster in clusters:
                cluster_name = cluster.get("clusterName")
                if not cluster_name:
                    continue
                
                worlds = await self._get_worlds(cluster_name)
                
                for world in worlds:
                    world_name = world.get("name")
                    if not world_name:
                        continue
                    
                    # 获取最新的聊天记录来初始化哈希集合
                    chat_logs = await self._fetch_latest_chat_logs(cluster_name, world_name, lines=50)
                    
                    # 为每个世界初始化哈希集合
                    hash_key = f"{cluster_name}_{world_name}"
                    self.last_message_hashes[hash_key] = set()
                    
                    # 将现有消息的哈希添加到集合中
                    for chat_log in chat_logs:
                        message_hash = self._generate_message_hash(chat_log)
                        self.last_message_hashes[hash_key].add(message_hash)
            
            self.is_initialized = True
            logger.info("消息哈希集合初始化完成")
            
        except Exception as e:
            logger.error(f"初始化消息哈希集合失败: {e}")
    
    async def _sync_cluster_world_messages(self, cluster_name: str, world_name: str):
        """同步指定集群和世界的消息"""
        try:
            # 获取最新的聊天记录
            chat_logs = await self._fetch_latest_chat_logs(cluster_name, world_name, lines=50)
            
            # 检测并推送新消息
            new_message_count = await self._detect_and_push_new_messages(cluster_name, world_name, chat_logs)
            
            if new_message_count > 0:
                logger.info(f"集群 {cluster_name} 世界 {world_name} 推送了 {new_message_count} 条新消息")
                
        except Exception as e:
            logger.error(f"同步集群 {cluster_name} 世界 {world_name} 消息失败: {e}")
    
    async def _fetch_latest_chat_logs(self, cluster_name: str, world_name: str, lines: int = 50) -> List[Dict]:
        """获取最新的聊天记录"""
        try:
            headers = {
                "Authorization": config.dmp_token,
                "X-I18n-Lang": "zh"
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{config.dmp_base_url}/chat/logs",
                    headers=headers,
                    params={
                        "clusterName": cluster_name,
                        "worldName": world_name,
                        "lines": lines
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                if data.get("code") == 200:
                    return data.get("data", [])
                else:
                    logger.error(f"获取聊天记录失败: {data.get('message', '未知错误')}")
                    return []
        except Exception as e:
            logger.error(f"获取聊天记录时出错: {e}")
            return []
    
    async def _detect_and_push_new_messages(self, cluster_name: str, world_name: str, chat_logs: List[Dict]) -> int:
        """检测并推送新消息"""
        try:
            hash_key = f"{cluster_name}_{world_name}"
            if hash_key not in self.last_message_hashes:
                self.last_message_hashes[hash_key] = set()
            
            new_messages = []
            
            for chat_log in chat_logs:
                message_hash = self._generate_message_hash(chat_log)
                
                # 如果消息哈希不在已处理集合中，说明是新消息
                if message_hash not in self.last_message_hashes[hash_key]:
                    new_messages.append(chat_log)
                    self.last_message_hashes[hash_key].add(message_hash)
            
            # 推送新消息给启用了消息互通的用户
            if new_messages:
                await self._push_new_messages_to_users(cluster_name, world_name, new_messages)
            
            return len(new_messages)
            
        except Exception as e:
            logger.error(f"检测新消息失败: {e}")
            return 0
    
    async def _collect_all_new_messages(self) -> Dict[str, List[Dict]]:
        """收集所有世界的新消息"""
        try:
            all_new_messages = {}
            clusters = await self._get_clusters()
            
            for cluster in clusters:
                cluster_name = cluster.get("clusterName")
                if not cluster_name:
                    continue
                
                worlds = await self._get_worlds(cluster_name)
                
                for world in worlds:
                    world_name = world.get("name")
                    if not world_name:
                        continue
                    
                    # 同步该世界的消息
                    await self._sync_cluster_world_messages(cluster_name, world_name)
            
            return all_new_messages
            
        except Exception as e:
            logger.error(f"收集新消息失败: {e}")
            return {}
    
    async def _merge_and_push_messages(self, all_new_messages: Dict[str, List[Dict]]):
        """合并并推送消息"""
        try:
            # 这里可以实现消息合并逻辑
            # 例如：将多个世界的消息合并成一条消息发送
            pass
        except Exception as e:
            logger.error(f"合并推送消息失败: {e}")
    
    def _generate_content_hash(self, message_info: Dict) -> str:
        """生成消息内容哈希"""
        content = f"{message_info.get('player', '')}_{message_info.get('message', '')}_{message_info.get('time', '')}"
        return str(hash(content))
    
    def _parse_chat_log_entry(self, log_entry: str) -> Optional[Dict]:
        """解析聊天日志条目"""
        try:
            # 尝试解析不同格式的聊天日志
            if not log_entry or not isinstance(log_entry, str):
                return None
            
            # 移除多余的空格和换行符
            log_entry = log_entry.strip()
            
            # 尝试解析时间戳格式 [时间] 玩家名: 消息内容
            import re
            pattern = r'\[([^\]]+)\]\s*([^:]+):\s*(.+)'
            match = re.match(pattern, log_entry)
            
            if match:
                timestamp, player, message = match.groups()
                return {
                    'time': timestamp.strip(),
                    'player': player.strip(),
                    'message': message.strip()
                }
            
            # 如果正则匹配失败，尝试其他格式
            if ':' in log_entry:
                parts = log_entry.split(':', 1)
                if len(parts) == 2:
                    player_part = parts[0].strip()
                    message = parts[1].strip()
                    
                    # 尝试从玩家部分提取时间戳
                    time_match = re.search(r'\[([^\]]+)\]', player_part)
                    if time_match:
                        timestamp = time_match.group(1)
                        player = player_part.replace(f'[{timestamp}]', '').strip()
                    else:
                        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        player = player_part
                    
                    return {
                        'time': timestamp,
                        'player': player,
                        'message': message
                    }
            
            # 如果都无法解析，返回原始内容
            return {
                'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'player': 'Unknown',
                'message': log_entry
            }
            
        except Exception as e:
            logger.error(f"解析聊天日志条目失败: {e}")
            return None
    
    def _generate_message_hash(self, message_info: Dict) -> str:
        """生成消息哈希"""
        content = f"{message_info.get('player', '')}_{message_info.get('message', '')}_{message_info.get('time', '')}"
        return str(hash(content))
    
    async def _push_new_messages_to_users(self, cluster_name: str, world_name: str, new_messages: List[Dict]):
        """推送新消息给用户"""
        try:
            if not self.active_users:
                return
            
            # 获取机器人实例
            from nonebot import get_bot
            bot = get_bot()
            
            if not bot:
                logger.error("无法获取机器人实例")
                return
            
            # 构建消息内容
            message_content = f"💬 游戏消息 - {cluster_name}/{world_name}\n\n"
            
            for i, msg in enumerate(new_messages[-10:], 1):  # 只显示最新的10条消息
                player = msg.get('player', 'Unknown')
                message = msg.get('message', '')
                time = msg.get('time', '')
                
                message_content += f"{i}. [{time}] {player}: {message}\n"
            
            # 发送给所有启用了消息互通的用户
            for user_id in self.active_users:
                try:
                    await bot.send_private_msg(user_id=user_id, message=Message(message_content))
                except Exception as e:
                    logger.error(f"发送消息给用户 {user_id} 失败: {e}")
                    
        except Exception as e:
            logger.error(f"推送新消息失败: {e}")
    
    async def get_chat_logs(self, cluster_name: str, world_name: str = "World4", lines: int = 100) -> dict:
        """获取聊天日志"""
        try:
            headers = {
                "Authorization": config.dmp_token,
                "X-I18n-Lang": "zh"
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{config.dmp_base_url}/chat/logs",
                    headers=headers,
                    params={
                        "clusterName": cluster_name,
                        "worldName": world_name,
                        "lines": lines
                    }
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            return {"code": 500, "message": f"获取聊天日志失败: {str(e)}"}
    
    async def send_message_to_game(self, message: str, cluster_name: str = None, world_name: str = ""):
        """发送消息到游戏"""
        try:
            if not cluster_name:
                cluster_name = await config.get_first_cluster()
            
            headers = {
                "Authorization": config.dmp_token,
                "Content-Type": "application/json"
            }
            
            data = {
                "clusterName": cluster_name,
                "worldName": world_name,
                "message": message
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{config.dmp_base_url}/chat/announce",
                    headers=headers,
                    json=data
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            return {"code": 500, "message": f"发送消息到游戏失败: {str(e)}"}
    
    async def add_qq_message(self, user_id: int, username: str, message: str):
        """添加QQ消息到数据库"""
        try:
            await self.db.init_database()
            await self.db.add_chat_message(
                world_name="QQ",
                player_name=username,
                message=message,
                timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            )
        except Exception as e:
            logger.error(f"添加QQ消息到数据库失败: {e}")


# 创建消息互通管理器实例
message_exchange_manager = MessageExchangeManager()

# 消息互通命令 - 使用 Alconna
message_exchange_cmd = on_alconna(
    Alconna(
        "消息互通",
        meta=CommandMeta(
            description="开启游戏内消息与QQ消息互通",
            usage="消息互通",
            example="消息互通"
        )
    ),
    aliases={"开启互通", "互通"},
    priority=10
)

close_exchange_cmd = on_alconna(
    Alconna(
        "关闭互通",
        meta=CommandMeta(
            description="关闭消息互通功能",
            usage="关闭互通",
            example="关闭互通"
        )
    ),
    aliases={"停止互通", "关闭消息互通"},
    priority=10
)

exchange_status_cmd = on_alconna(
    Alconna(
        "互通状态",
        meta=CommandMeta(
            description="查看当前互通状态",
            usage="互通状态",
            example="互通状态"
        )
    ),
    aliases={"状态", "互通状态查询"},
    priority=10
)

latest_messages_cmd = on_alconna(
    Alconna(
        "最新消息",
        Args.count[int] = Field(10, description="消息数量"),
        meta=CommandMeta(
            description="获取游戏内最新消息",
            usage="最新消息 [数量]",
            example="最新消息 10"
        )
    ),
    aliases={"最新聊天", "最新消息"},
    priority=10
)

# 私聊消息处理器
private_message_handler = on_alconna(
    Alconna(
        "发送",
        Args.message[str] = Field(description="要发送的消息"),
        meta=CommandMeta(
            description="发送消息到游戏",
            usage="发送 <消息>",
            example="发送 Hello World"
        )
    ),
    aliases={"say", "发送消息"},
    priority=10
)


# 命令处理器
@message_exchange_cmd.handle()
async def handle_message_exchange(bot: Bot, event: Event):
    """处理开启消息互通"""
    try:
        user_id = int(event.get_user_id())
        message_exchange_manager.active_users.add(user_id)
        
        # 如果还没有启动同步任务，则启动
        if not message_exchange_manager.is_running:
            await message_exchange_manager.start_sync()
            await message_exchange_manager._initialize_message_hashes()
        
        await message_exchange_cmd.finish(Message("✅ 消息互通功能已开启！\n\n💬 游戏内的聊天消息将会推送到您的QQ\n📝 您也可以发送消息到游戏中"))
        
    except Exception as e:
        await message_exchange_cmd.finish(Message(f"❌ 开启消息互通失败：{str(e)}"))


@close_exchange_cmd.handle()
async def handle_close_exchange(bot: Bot, event: Event):
    """处理关闭消息互通"""
    try:
        user_id = int(event.get_user_id())
        message_exchange_manager.active_users.discard(user_id)
        
        # 如果没有用户使用消息互通，则停止同步任务
        if not message_exchange_manager.active_users and message_exchange_manager.is_running:
            await message_exchange_manager.stop_sync()
        
        await close_exchange_cmd.finish(Message("✅ 消息互通功能已关闭！"))
        
    except Exception as e:
        await close_exchange_cmd.finish(Message(f"❌ 关闭消息互通失败：{str(e)}"))


@exchange_status_cmd.handle()
async def handle_exchange_status(bot: Bot, event: Event):
    """处理查看互通状态"""
    try:
        user_id = int(event.get_user_id())
        is_active = user_id in message_exchange_manager.active_users
        
        status_info = f"📊 消息互通状态\n\n"
        status_info += f"个人状态：{'✅ 已开启' if is_active else '❌ 已关闭'}\n"
        status_info += f"同步任务：{'✅ 运行中' if message_exchange_manager.is_running else '❌ 已停止'}\n"
        status_info += f"活跃用户：{len(message_exchange_manager.active_users)} 人\n"
        status_info += f"同步间隔：{message_exchange_manager.sync_interval} 秒"
        
        await exchange_status_cmd.finish(Message(status_info))
        
    except Exception as e:
        await exchange_status_cmd.finish(Message(f"❌ 获取互通状态失败：{str(e)}"))


@latest_messages_cmd.handle()
async def handle_latest_messages(bot: Bot, event: Event, count: int = 10):
    """处理获取最新消息"""
    try:
        config = get_config()
        cluster_name = await config.get_first_cluster()
        
        result = await message_exchange_manager.get_chat_logs(cluster_name, "Master", count)
        
        if result.get("code") == 200:
            data = result.get("data", [])
            
            if data:
                messages_info = f"💬 最新消息 ({len(data)} 条)\n\n"
                for i, msg in enumerate(data, 1):
                    messages_info += f"{i}. {msg.get('time', 'N/A')} - {msg.get('player', 'N/A')}: {msg.get('message', 'N/A')}\n"
            else:
                messages_info = "💬 暂无最新消息"
            
            await latest_messages_cmd.finish(Message(messages_info))
        else:
            error_msg = result.get("message", "未知错误")
            await latest_messages_cmd.finish(Message(f"❌ 获取最新消息失败：{error_msg}"))
            
    except Exception as e:
        await latest_messages_cmd.finish(Message(f"❌ 处理获取最新消息时出错：{str(e)}"))


def is_private_message(event: PrivateMessageEvent) -> bool:
    """检查是否为私聊消息"""
    return isinstance(event, PrivateMessageEvent)


@private_message_handler.handle()
async def handle_private_message(bot: Bot, event: PrivateMessageEvent, message: str):
    """处理私聊消息发送到游戏"""
    try:
        # 检查用户是否启用了消息互通
        user_id = int(event.get_user_id())
        if user_id not in message_exchange_manager.active_users:
            await private_message_handler.finish(Message("❌ 您还没有开启消息互通功能，请先使用 /消息互通 开启"))
            return
        
        # 发送消息到游戏
        result = await message_exchange_manager.send_message_to_game(message)
        
        if result.get("code") == 200:
            # 将消息保存到数据库
            username = event.sender.nickname if hasattr(event.sender, 'nickname') else f"用户{user_id}"
            await message_exchange_manager.add_qq_message(user_id, username, message)
            
            await private_message_handler.finish(Message(f"✅ 消息已发送到游戏：{message}"))
        else:
            error_msg = result.get("message", "未知错误")
            await private_message_handler.finish(Message(f"❌ 发送消息失败：{error_msg}"))
            
    except Exception as e:
        await private_message_handler.finish(Message(f"❌ 处理消息发送时出错：{str(e)}"))


# 启动和关闭钩子
@get_driver().on_startup
async def startup():
    """启动时的初始化"""
    try:
        await message_exchange_manager.db.init_database()
        logger.info("消息互通数据库初始化完成")
    except Exception as e:
        logger.error(f"消息互通数据库初始化失败: {e}")


@get_driver().on_shutdown
async def shutdown():
    """关闭时的清理"""
    try:
        await message_exchange_manager.stop_sync()
        logger.info("消息互通服务已停止")
    except Exception as e:
        logger.error(f"停止消息互通服务失败: {e}") 