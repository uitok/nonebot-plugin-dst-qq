"""
饥荒联机版DMP QQ机器人 - 消息互通模块

重新设计的消息互通系统，支持：
- 群聊/私聊模式自由切换
- 智能消息路由和过滤
- 高性能异步处理
- 灵活的配置管理
- 完善的错误处理和日志记录

作者: DST QQ Bot Team
版本: 2.0.0
"""

import asyncio
import hashlib
import re
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple, Any, Union
from dataclasses import dataclass, field
from enum import Enum

import httpx
from nonebot import on_command, on_message, get_bot
from nonebot.adapters import Event
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, PrivateMessageEvent, Message
from nonebot.permission import SUPERUSER
from nonebot.typing import T_State
from nonebot.matcher import Matcher
from nonebot.rule import Rule
from nonebot.exception import FinishedException

# 导入配置和工具
from ..config import get_config
from ..database import ChatHistoryDatabase
from nonebot import logger
from ..cache_manager import cache_manager

# Using nonebot logger directly


class ChatMode(Enum):
    """聊天模式枚举"""
    PRIVATE = "private"
    GROUP = "group"


class MessageType(Enum):
    """消息类型枚举"""
    CHAT = "chat"
    SYSTEM = "system"
    JOIN = "join"
    LEAVE = "leave"
    DEATH = "death"



@dataclass
class UserSession:
    """用户会话信息"""
    user_id: int
    chat_mode: ChatMode
    target_group_id: Optional[int] = None
    target_cluster: str = ""
    target_world: str = ""
    last_activity: datetime = field(default_factory=datetime.now)
    is_active: bool = True
    
    def update_activity(self):
        """更新最后活动时间"""
        self.last_activity = datetime.now()
    
    def is_expired(self, timeout_minutes: int = 30) -> bool:
        """检查会话是否过期"""
        return datetime.now() - self.last_activity > timedelta(minutes=timeout_minutes)


@dataclass
class GameMessage:
    """游戏消息数据结构"""
    timestamp: str
    cluster_name: str
    world_name: str
    player_name: str
    content: str
    message_type: MessageType
    raw_content: str = ""
    hash_value: str = field(default="")
    
    def __post_init__(self):
        """自动生成消息哈希"""
        if not self.hash_value:
            self.hash_value = self._generate_hash()
    
    def _generate_hash(self) -> str:
        """生成消息唯一哈希"""
        content = f"{self.timestamp}_{self.cluster_name}_{self.world_name}_{self.player_name}_{self.content}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def to_qq_message(self, template: str) -> str:
        """转换为QQ消息格式"""
        return template.format(
            timestamp=self.timestamp,
            cluster=self.cluster_name,
            world=self.world_name,
            player=self.player_name,
            message=self.content
        )


class MessageFilter:
    """消息过滤器"""
    
    def __init__(self, config):
        self.config = config.message
        self.blocked_words = set(self.config.blocked_words)
        self.blocked_players = set(self.config.blocked_players)
    
    def should_filter_game_message(self, message: GameMessage) -> bool:
        """判断是否应该过滤游戏消息"""
        # 过滤系统消息
        if self.config.filter_system_messages and message.message_type == MessageType.SYSTEM:
            return True
        
        # 过滤来自QQ的消息
        if self.config.filter_qq_messages and "[QQ]" in message.content:
            return True
        
        # 过滤屏蔽的玩家
        if message.player_name in self.blocked_players:
            return True
        
        # 过滤屏蔽词
        if any(word in message.content for word in self.blocked_words):
            return True
        
        return False
    
    def should_filter_qq_message(self, content: str, user_id: int) -> bool:
        """判断是否应该过滤QQ消息"""
        # 消息长度检查
        if len(content) > self.config.max_message_length:
            return True
        
        # 屏蔽词检查
        if any(word in content for word in self.blocked_words):
            return True
        
        return False


class MessageDeduplicator:
    """消息去重器"""
    
    def __init__(self, window_seconds: int = 60):
        self.window_seconds = window_seconds
        self.seen_messages: Dict[str, float] = {}
    
    def is_duplicate(self, message_hash: str) -> bool:
        """检查消息是否重复"""
        current_time = time.time()
        
        # 清理过期的消息哈希
        self._cleanup_expired(current_time)
        
        # 检查是否已见过此消息
        if message_hash in self.seen_messages:
            return True
        
        # 记录新消息
        self.seen_messages[message_hash] = current_time
        return False
    
    def _cleanup_expired(self, current_time: float):
        """清理过期的消息哈希"""
        expired_keys = [
            key for key, timestamp in self.seen_messages.items()
            if current_time - timestamp > self.window_seconds
        ]
        for key in expired_keys:
            del self.seen_messages[key]


class DMPApiClient:
    """DMP API客户端"""
    
    def __init__(self):
        self.config = get_config()
    
    async def get_clusters(self) -> List[Dict]:
        """获取集群列表"""
        try:
            headers = {
                "Authorization": self.config.dmp.token,
                "X-I18n-Lang": "zh"
            }
            
            async with httpx.AsyncClient(timeout=self.config.dmp.timeout) as client:
                response = await client.get(
                    f"{self.config.dmp.base_url}/setting/clusters",
                    headers=headers
                )
                response.raise_for_status()
                data = response.json()
                
                if data.get("code") == 200:
                    return data.get("data", [])
                return []
        except Exception as e:
            logger.error(f"获取集群列表失败: {e}")
            return []
    
    async def get_worlds(self, cluster_name: str) -> List[str]:
        """获取指定集群的世界列表"""
        try:
            clusters = await self.get_clusters()
            for cluster in clusters:
                if cluster.get("clusterName") == cluster_name:
                    return cluster.get("worlds", [])
            return []
        except Exception as e:
            logger.error(f"获取世界列表失败: {e}")
            return []
    
    async def get_chat_logs(self, cluster_name: str, world_name: str, lines: int = 50) -> List[str]:
        """获取聊天日志"""
        try:
            headers = {
                "Authorization": self.config.dmp.token,
                "X-I18n-Lang": "zh"
            }
            
            params = {
                "clusterName": cluster_name,
                "worldName": world_name,
                "line": lines,
                "type": "chat"
            }
            
            async with httpx.AsyncClient(timeout=self.config.dmp.timeout) as client:
                response = await client.get(
                    f"{self.config.dmp.base_url}/logs/log_value",
                    headers=headers,
                    params=params
                )
                response.raise_for_status()
                data = response.json()
                
                if data.get("code") == 200:
                    return data.get("data", [])
                return []
        except Exception as e:
            logger.error(f"获取聊天日志失败: {e}, cluster_name={cluster_name}, world_name={world_name}")
            return []
    
    async def send_message_to_game(self, message: str, cluster_name: str, world_name: str = "") -> bool:
        """发送消息到游戏"""
        try:
            headers = {
                "Authorization": self.config.dmp.token,
                "X-I18n-Lang": "zh"
            }
            
            data = {
                "type": "announce",
                "extraData": message,
                "clusterName": cluster_name,
                "worldName": world_name
            }
            
            async with httpx.AsyncClient(timeout=self.config.dmp.timeout) as client:
                response = await client.post(
                    f"{self.config.dmp.base_url}/home/exec",
                    headers=headers,
                    json=data
                )
                response.raise_for_status()
                result = response.json()
                
                success = result.get("code") == 200
                if success:
                    logger.info(f"消息已发送到游戏: {message}, cluster_name={cluster_name}, world_name={world_name}")
                else:
                    logger.error(f"发送消息到游戏失败 cluster:{cluster_name} world:{world_name}: {result}")
                
                return success
        except Exception as e:
            logger.error(f"发送消息到游戏出错 cluster:{cluster_name}: {str(e)}")
            return False


class MessageParser:
    """消息解析器"""
    
    @staticmethod
    def parse_game_message(log_entry: str, cluster_name: str, world_name: str, startup_time: Optional[datetime] = None) -> Optional[GameMessage]:
        """解析游戏日志为消息对象"""
        try:
            # 匹配时间戳
            timestamp_pattern = r'\[(\d{2}:\d{2}:\d{2})\]'
            timestamp_match = re.search(timestamp_pattern, log_entry)
            
            if not timestamp_match:
                return None
            
            timestamp = timestamp_match.group(1)
            content_after_timestamp = log_entry[timestamp_match.end():].strip()
            
            # 如果提供了启动时间，检查消息是否是启动前的历史消息
            if startup_time:
                message_time = datetime.strptime(timestamp, '%H:%M:%S').replace(
                    year=startup_time.year,
                    month=startup_time.month,
                    day=startup_time.day
                )
                
                # 如果消息时间早于启动时间（考虑日期边界情况）
                if message_time < startup_time:
                    # 检查是否可能是跨日的情况（消息时间很晚，启动时间很早）
                    if not (message_time.hour >= 20 and startup_time.hour <= 4):
                        logger.debug(f"跳过启动前的历史消息: {timestamp} < {startup_time.strftime('%H:%M:%S')}")
                        return None
            
            # 检查消息类型和内容
            if ': ' in content_after_timestamp:
                # 玩家聊天消息
                player_name, message_content = content_after_timestamp.split(': ', 1)
                return GameMessage(
                    timestamp=timestamp,
                    cluster_name=cluster_name,
                    world_name=world_name,
                    player_name=player_name.strip(),
                    content=message_content.strip(),
                    message_type=MessageType.CHAT,
                    raw_content=log_entry
                )
            else:
                # 系统消息
                return GameMessage(
                    timestamp=timestamp,
                    cluster_name=cluster_name,
                    world_name=world_name,
                    player_name="系统",
                    content=content_after_timestamp,
                    message_type=MessageType.SYSTEM,
                    raw_content=log_entry
                )
        except Exception as e:
            logger.error(f"解析游戏消息失败: {e}")
            return None


class UserSessionManager:
    """用户会话管理器"""
    
    def __init__(self):
        self.sessions: Dict[int, UserSession] = {}
        self.group_sessions: Dict[int, Set[int]] = {}  # 群组ID -> 用户ID集合
    
    def create_session(self, user_id: int, chat_mode: ChatMode, group_id: Optional[int] = None) -> UserSession:
        """创建用户会话"""
        session = UserSession(
            user_id=user_id,
            chat_mode=chat_mode,
            target_group_id=group_id
        )
        
        self.sessions[user_id] = session
        
        # 如果是群聊模式，记录群组关联
        if chat_mode == ChatMode.GROUP and group_id:
            if group_id not in self.group_sessions:
                self.group_sessions[group_id] = set()
            self.group_sessions[group_id].add(user_id)
        
        logger.info(f"创建用户会话 user:{user_id} mode:{chat_mode.value} group:{group_id}")
        
        return session
    
    def get_session(self, user_id: int) -> Optional[UserSession]:
        """获取用户会话"""
        return self.sessions.get(user_id)
    
    def remove_session(self, user_id: int):
        """移除用户会话"""
        if user_id in self.sessions:
            session = self.sessions[user_id]
            
            # 如果是群聊模式，清理群组关联
            if session.chat_mode == ChatMode.GROUP and session.target_group_id:
                group_users = self.group_sessions.get(session.target_group_id, set())
                group_users.discard(user_id)
                if not group_users:
                    del self.group_sessions[session.target_group_id]
            
            del self.sessions[user_id]
            
            logger.info(f"移除用户会话: user_id={user_id}")
    
    def get_active_sessions(self) -> List[UserSession]:
        """获取所有活跃会话"""
        return [session for session in self.sessions.values() if session.is_active]
    
    def get_group_users(self, group_id: int) -> Set[int]:
        """获取群组中的用户"""
        return self.group_sessions.get(group_id, set())
    
    def cleanup_expired_sessions(self, timeout_minutes: int = 30):
        """清理过期会话"""
        expired_users = [
            user_id for user_id, session in self.sessions.items()
            if session.is_expired(timeout_minutes)
        ]
        
        for user_id in expired_users:
            self.remove_session(user_id)
        
        if expired_users:
            logger.info(
                f"清理了 {len(expired_users)} 个过期会话",
                category=LogCategory.MESSAGE
            )


class MessageBridge:
    """消息互通核心类"""
    
    def __init__(self):
        self.config = get_config()
        self.session_manager = UserSessionManager()
        self.api_client = DMPApiClient()
        self.message_filter = MessageFilter(self.config)
        self.deduplicator = MessageDeduplicator(self.config.message.dedupe_window)
        self.database = ChatHistoryDatabase()
        
        # 同步状态
        self.is_running = False
        self.sync_task: Optional[asyncio.Task] = None
        self.last_sync_time: Dict[str, datetime] = {}
        self.startup_time: Optional[datetime] = None
        
        logger.success("消息互通核心组件初始化完成")
    
    async def start(self):
        """启动消息互通服务"""
        if self.is_running:
            return
        
        if not self.config.message.enable_message_bridge:
            logger.info("消息互通功能已禁用")
            return
        
        # 重启时清理所有会话状态，重新计算互通
        logger.info("清理所有会话状态，重新计算互通")
        self.session_manager.sessions.clear()
        self.session_manager.group_sessions.clear()
        
        # 重置去重器状态
        self.deduplicator.seen_messages.clear()
        
        # 记录启动时间，用于过滤启动前的历史消息
        self.startup_time = datetime.now()
        
        self.is_running = True
        await self.database.init_database()
        
        # 启动消息同步任务
        self.sync_task = asyncio.create_task(self._sync_loop())
        
        logger.success(f"消息互通服务已启动，启动时间: {self.startup_time.strftime('%H:%M:%S')}，将过滤此时间之前的历史消息")
    
    async def stop(self):
        """停止消息互通服务"""
        self.is_running = False
        
        if self.sync_task:
            self.sync_task.cancel()
            try:
                await self.sync_task
            except asyncio.CancelledError:
                pass
        
        logger.info("消息互通服务已停止")
    
    async def create_user_session(self, user_id: int, chat_mode: ChatMode, group_id: Optional[int] = None) -> bool:
        """创建用户会话"""
        try:
            # 检查聊天模式是否被允许
            if chat_mode == ChatMode.GROUP and not self.config.message.allow_group_chat:
                return False
            if chat_mode == ChatMode.PRIVATE and not self.config.message.allow_private_chat:
                return False
            
            # 创建会话
            session = self.session_manager.create_session(user_id, chat_mode, group_id)
            
            # 设置默认目标
            session.target_cluster = self.config.message.default_target_cluster or ""
            session.target_world = self.config.message.default_target_world or "Master"
            
            # 自动选择集群和世界
            if not session.target_cluster or self.config.message.auto_select_world:
                await self._auto_configure_session(session)
            
            return True
        except Exception as e:
            logger.error(f"创建用户会话失败 user:{user_id}: {str(e)}")
            return False
    
    async def _auto_configure_session(self, session: UserSession):
        """自动配置会话的集群和世界"""
        try:
            # 使用集群管理器获取当前集群
            try:
                from ..cluster_manager import get_cluster_manager
                cluster_manager = get_cluster_manager()
                
                # 自动选择集群
                if not session.target_cluster:
                    if cluster_manager:
                        current_cluster = await cluster_manager.get_current_cluster()
                        if current_cluster:
                            session.target_cluster = current_cluster
                            logger.info(
                                f"使用集群管理器的当前集群: {current_cluster}",
                                category=LogCategory.MESSAGE,
                                user_id=session.user_id
                            )
                        else:
                            logger.warning("集群管理器未能提供当前集群，使用配置默认值")
                            session.target_cluster = self.config.message.default_target_cluster or "Master"
                    else:
                        logger.warning("集群管理器未初始化，使用配置默认值")
                        session.target_cluster = self.config.message.default_target_cluster or "Master"
                
                # 自动选择世界
                if session.target_cluster and (not session.target_world or self.config.message.auto_select_world):
                    try:
                        worlds = await self.api_client.get_worlds(session.target_cluster)
                        if worlds:
                            session.target_world = worlds[0] if worlds else self.config.message.default_target_world
                        else:
                            session.target_world = self.config.message.default_target_world or "Master"
                    except Exception as e:
                        logger.warning(f"获取世界列表失败，使用默认世界: {e}")
                        session.target_world = self.config.message.default_target_world or "Master"
                
            except Exception as e:
                logger.error(f"自动配置会话失败，使用默认配置 ERROR: {e}")
                # 确保会话有基本的配置
                if not session.target_cluster:
                    session.target_cluster = self.config.message.default_target_cluster or "Master"
                if not session.target_world:
                    session.target_world = self.config.message.default_target_world or "Master"
            
            logger.info(
                f"自动配置会话完成 cluster:{session.target_cluster} world:{session.target_world}",
                category=LogCategory.MESSAGE,
                user_id=session.user_id
            )
            
        except Exception as e:
            logger.error(f"自动配置会话失败，使用默认配置: {e}")
            # 确保有基本的配置
            if not session.target_cluster:
                session.target_cluster = "Master"
            if not session.target_world:
                session.target_world = "Master"
    
    async def remove_user_session(self, user_id: int):
        """移除用户会话"""
        self.session_manager.remove_session(user_id)
    
    async def send_qq_message_to_game(self, user_id: int, message: str, username: str) -> bool:
        """发送QQ消息到游戏"""
        try:
            session = self.session_manager.get_session(user_id)
            if not session or not session.is_active:
                return False
            
            # 过滤检查
            if self.message_filter.should_filter_qq_message(message, user_id):
                return False
            
            # 格式化消息
            formatted_message = self.config.message.qq_to_game_template.format(
                username=username,
                message=message
            )
            
            # 发送到游戏
            success = await self.api_client.send_message_to_game(
                formatted_message,
                session.target_cluster,
                session.target_world
            )
            
            if success:
                # 记录到数据库
                await self.database.add_qq_message(user_id, username, message)
                session.update_activity()
            
            return success
        except Exception as e:
            logger.error(f"发送QQ消息到游戏失败: {e}")
            return False
    
    async def _sync_loop(self):
        """消息同步循环"""
        while self.is_running:
            try:
                await self._sync_game_messages()
                await asyncio.sleep(self.config.message.sync_interval)
            except Exception as e:
                logger.error(f"消息同步出错: {e}")
                await asyncio.sleep(5)
    
    async def _sync_game_messages(self):
        """同步游戏消息"""
        try:
            active_sessions = self.session_manager.get_active_sessions()
            if not active_sessions:
                return
            
            # 获取所有集群和世界的新消息
            all_new_messages = await self._collect_new_messages()
            
            if not all_new_messages:
                return
            
            # 推送消息给用户
            logger.debug(
                f"准备分发 {len(all_new_messages)} 条新消息给 {len(active_sessions)} 个活跃会话",
                category=LogCategory.MESSAGE
            )
            await self._distribute_messages(all_new_messages, active_sessions)
            
        except Exception as e:
            logger.error(f"同步游戏消息失败: {e}")
    
    async def _collect_new_messages(self) -> List[GameMessage]:
        """收集所有新消息"""
        new_messages = []
        
        try:
            clusters = await self.api_client.get_clusters()
            if not clusters:
                return new_messages
            
            for cluster in clusters:
                cluster_name = cluster.get("clusterName", "")
                if not cluster_name:
                    continue
                
                worlds = await self.api_client.get_worlds(cluster_name)
                if not worlds:
                    continue
                
                for world_name in worlds:
                    if not world_name:
                        continue
                        
                    chat_logs = await self.api_client.get_chat_logs(cluster_name, world_name)
                    if not chat_logs:
                        continue
                    
                    for log_entry in chat_logs:
                        if isinstance(log_entry, str):
                            message = MessageParser.parse_game_message(log_entry, cluster_name, world_name, self.startup_time)
                            
                            if message and not self.message_filter.should_filter_game_message(message):
                                if not self.deduplicator.is_duplicate(message.hash_value):
                                    new_messages.append(message)
                                    logger.debug(
                                        f"收集到新消息: {message.player_name}: {message.content[:50]}... hash={message.hash_value[:8]}",
                                        category=LogCategory.MESSAGE
                                    )
                                else:
                                    logger.debug(
                                        f"跳过重复消息: {message.player_name}: {message.content[:50]}... hash={message.hash_value[:8]}",
                                        category=LogCategory.MESSAGE
                                    )
            
        except Exception as e:
            logger.error(f"收集新消息失败: {e}")
        
        return new_messages
    
    async def _distribute_messages(self, messages: List[GameMessage], sessions: List[UserSession]):
        """分发消息给用户"""
        if not messages:
            return
        
        try:
            bot = get_bot()
            
            # 按聊天模式分组用户
            private_users = [s for s in sessions if s.chat_mode == ChatMode.PRIVATE]
            group_sessions = {}
            
            for session in sessions:
                if session.chat_mode == ChatMode.GROUP and session.target_group_id:
                    if session.target_group_id not in group_sessions:
                        group_sessions[session.target_group_id] = []
                    group_sessions[session.target_group_id].append(session)
            
            # 准备消息内容
            message_content = self._format_messages_batch(messages)
            
            # 发送给私聊用户
            for session in private_users:
                try:
                    await bot.send_private_msg(user_id=session.user_id, message=message_content)
                    session.update_activity()
                except Exception as e:
                    logger.error(f"发送私聊消息失败: {e}")
            
            # 发送给群聊（每个群只发送一次）
            for group_id, group_sessions_list in group_sessions.items():
                try:
                    await bot.send_group_msg(group_id=group_id, message=message_content)
                    # 更新所有相关会话的活动时间
                    for session in group_sessions_list:
                        session.update_activity()
                except Exception as e:
                    logger.error(f"发送群聊消息失败: {e}")
            
            # 输出分发的消息详情（用于调试）
            for i, msg in enumerate(messages):
                logger.debug(
                    f"分发消息 {i+1}: {msg.player_name}: {msg.content[:50]}... hash={msg.hash_value[:8]}",
                    category=LogCategory.MESSAGE
                )
            
            logger.info(
                f"已分发 {len(messages)} 条消息给 {len(sessions)} 个会话 "
                f"(私聊:{len(private_users)}, 群聊:{len(group_sessions)})",
                category=LogCategory.MESSAGE
            )
            
        except Exception as e:
            logger.error(f"分发消息失败: {e}")
    
    def _format_messages_batch(self, messages: List[GameMessage]) -> str:
        """批量格式化消息"""
        if not messages:
            return ""
        
        # 限制消息数量
        max_batch = self.config.message.max_batch_size
        limited_messages = messages[:max_batch]
        
        formatted_messages = []
        
        for message in limited_messages:
            if message.message_type == MessageType.CHAT:
                formatted = message.to_qq_message(self.config.message.game_to_qq_template)
            else:
                formatted = message.to_qq_message(self.config.message.system_message_template)
            
            formatted_messages.append(formatted)
        
        if len(messages) > max_batch:
            formatted_messages.append(f"... 还有 {len(messages) - max_batch} 条消息")
        
        return "\n".join(formatted_messages)
    

    
    def get_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        active_sessions = self.session_manager.get_active_sessions()
        return {
            "is_running": self.is_running,
            "total_sessions": len(active_sessions),
            "private_sessions": len([s for s in active_sessions if s.chat_mode == ChatMode.PRIVATE]),
            "group_sessions": len([s for s in active_sessions if s.chat_mode == ChatMode.GROUP]),
            "sync_interval": self.config.message.sync_interval
        }


# 全局消息互通实例
message_bridge = MessageBridge()


# ================================ 命令处理器 ================================

# 消息互通开关命令
toggle_bridge_cmd = on_command(
    "消息互通",
    aliases={"开启互通", "bridge", "开启消息互通"},
    priority=1,
    block=True
)

close_bridge_cmd = on_command(
    "关闭互通",
    aliases={"停止互通", "关闭消息互通", "stop_bridge"},
    priority=1,
    block=True
)

# 切换聊天模式命令
switch_mode_cmd = on_command(
    "切换模式",
    aliases={"聊天模式", "切换聊天模式", "switch_mode"},
    priority=1,
    block=True
)

# 状态查询命令
bridge_status_cmd = on_command(
    "互通状态",
    aliases={"消息状态", "bridge_status"},
    priority=1,
    block=True
)


@toggle_bridge_cmd.handle()
async def handle_toggle_bridge(bot: Bot, event: Event, state: T_State):
    """处理开启消息互通命令"""
    user_id = event.user_id
    
    # 判断当前聊天环境
    is_group = isinstance(event, GroupMessageEvent)
    group_id = event.group_id if is_group else None
    
    # 检查是否已有会话
    session = message_bridge.session_manager.get_session(user_id)
    if session:
        await toggle_bridge_cmd.finish("您已经开启了消息互通功能！\n发送「关闭互通」可以关闭功能。")
        return
    
    # 确定聊天模式
    if is_group and message_bridge.config.message.allow_group_chat:
        chat_mode = ChatMode.GROUP
        mode_text = "群聊"
    elif not is_group and message_bridge.config.message.allow_private_chat:
        chat_mode = ChatMode.PRIVATE
        mode_text = "私聊"
    else:
        if is_group:
            await toggle_bridge_cmd.finish("❌ 群聊消息互通功能已被禁用！\n请联系管理员启用该功能。")
        else:
            await toggle_bridge_cmd.finish("❌ 私聊消息互通功能已被禁用！\n请联系管理员启用该功能。")
        return
    
    # 创建会话
    success = await message_bridge.create_user_session(user_id, chat_mode, group_id)
    
    if success:
        await toggle_bridge_cmd.finish(
            f"✅ 消息互通功能已开启！\n"
            f"📱 聊天模式：{mode_text}\n"
            f"💬 您的消息将会发送到游戏中\n"
            f"🎮 游戏内的消息也会推送给您\n\n"
            f"📋 可用命令：\n"
            f"• 发送「关闭互通」关闭功能\n"
            f"• 发送「切换模式」切换聊天模式\n"
            f"• 发送「互通状态」查看状态"
        )
    else:
        await toggle_bridge_cmd.finish("❌ 开启消息互通失败！请稍后重试。")


@close_bridge_cmd.handle()
async def handle_close_bridge(bot: Bot, event: Event, state: T_State):
    """处理关闭消息互通命令"""
    user_id = event.user_id
    
    session = message_bridge.session_manager.get_session(user_id)
    if not session:
        await close_bridge_cmd.finish("您还没有开启消息互通功能！")
        return
    
    await message_bridge.remove_user_session(user_id)
    await close_bridge_cmd.finish("✅ 消息互通功能已关闭！")


@switch_mode_cmd.handle()
async def handle_switch_mode(bot: Bot, event: Event, state: T_State):
    """处理切换聊天模式命令"""
    user_id = event.user_id
    
    session = message_bridge.session_manager.get_session(user_id)
    if not session:
        await switch_mode_cmd.finish("请先开启消息互通功能！")
        return
    
    is_group = isinstance(event, GroupMessageEvent)
    group_id = event.group_id if is_group else None
    
    # 确定新的聊天模式
    if is_group and message_bridge.config.message.allow_group_chat:
        new_mode = ChatMode.GROUP
        new_mode_text = "群聊"
    elif not is_group and message_bridge.config.message.allow_private_chat:
        new_mode = ChatMode.PRIVATE
        new_mode_text = "私聊"
    else:
        await switch_mode_cmd.finish("❌ 当前环境不支持切换到对应的聊天模式！")
        return
    
    # 检查是否需要切换
    if session.chat_mode == new_mode:
        await switch_mode_cmd.finish(f"当前已经是{new_mode_text}模式了！")
        return
    
    # 移除旧会话并创建新会话
    await message_bridge.remove_user_session(user_id)
    success = await message_bridge.create_user_session(user_id, new_mode, group_id)
    
    if success:
        await switch_mode_cmd.finish(f"✅ 已切换到{new_mode_text}模式！")
    else:
        await switch_mode_cmd.finish("❌ 切换聊天模式失败！")


@bridge_status_cmd.handle()
async def handle_bridge_status(bot: Bot, event: Event, state: T_State):
    """处理查看互通状态命令"""
    user_id = event.user_id
    
    session = message_bridge.session_manager.get_session(user_id)
    status = message_bridge.get_status()
    
    if session:
        user_status = "已开启"
        mode_text = "群聊" if session.chat_mode == ChatMode.GROUP else "私聊"
        target_info = f"目标集群：{session.target_cluster or '自动选择'}\n目标世界：{session.target_world or '自动选择'}"
    else:
        user_status = "未开启"
        mode_text = "无"
        target_info = "无"
    
    status_text = f"""📊 消息互通状态报告

👤 您的状态：{user_status}
💬 聊天模式：{mode_text}
🎯 {target_info}

🌐 系统状态：
• 服务状态：{'运行中' if status['is_running'] else '已停止'}
• 总会话数：{status['total_sessions']}
• 私聊会话：{status['private_sessions']}
• 群聊会话：{status['group_sessions']}
• 同步间隔：{status['sync_interval']}秒"""
    
    await bridge_status_cmd.finish(status_text)


# ================================ 消息处理器 ================================

def create_message_rule() -> Rule:
    """创建消息处理规则"""
    def rule(event: Event) -> bool:
        # 只处理群聊和私聊消息
        if not isinstance(event, (GroupMessageEvent, PrivateMessageEvent)):
            return False
        
        user_id = event.user_id
        session = message_bridge.session_manager.get_session(user_id)
        
        # 检查用户是否有活跃会话
        if not session or not session.is_active:
            return False
        
        # 检查消息是否为命令
        message_text = event.get_plaintext().strip()
        
        # 检查是否以 / 开头的命令
        if message_text.startswith("/"):
            return False
            
        # 检查是否为已知的命令关键词（精确匹配和前缀匹配）
        command_keywords = [
            "消息互通", "开启互通", "关闭互通", "停止互通", "关闭消息互通",
            "切换模式", "聊天模式", "切换聊天模式", "互通状态", "消息状态",
            "菜单", "世界", "房间", "系统", "玩家", "直连",
            "管理命令", "查看备份", "执行命令", "回滚世界",
            "踢出玩家", "封禁玩家", "解封玩家", "缓存状态", "清理缓存",
            "压缩数据", "查看归档"
        ]
        
        # 如果是命令，不处理
        for keyword in command_keywords:
            if message_text == keyword or message_text.startswith(keyword + " "):
                return False
        
        # 检查聊天模式匹配
        if isinstance(event, GroupMessageEvent):
            return (session.chat_mode == ChatMode.GROUP and 
                   session.target_group_id == event.group_id)
        else:
            return session.chat_mode == ChatMode.PRIVATE
    
    return Rule(rule)


# 消息处理器
message_handler = on_message(rule=create_message_rule(), priority=999, block=True)


@message_handler.handle()
async def handle_user_message(bot: Bot, event: Union[GroupMessageEvent, PrivateMessageEvent], state: T_State):
    """处理用户消息"""
    user_id = event.user_id
    message_content = event.get_plaintext().strip()
    
    if not message_content:
        return
    
    try:
        # 获取用户信息
        if isinstance(event, GroupMessageEvent):
            user_info = await bot.get_group_member_info(group_id=event.group_id, user_id=user_id)
            username = user_info.get("card") or user_info.get("nickname", f"用户{user_id}")
        else:
            user_info = await bot.get_stranger_info(user_id=user_id)
            username = user_info.get("nickname", f"用户{user_id}")
        
        # 清理用户名
        import re
        username = re.sub(r'[^\w\s\u4e00-\u9fff]', '', username.strip())
        if not username:
            username = f"用户{user_id}"
        
        # 发送消息到游戏
        success = await message_bridge.send_qq_message_to_game(user_id, message_content, username)
        
        # 根据聊天模式决定是否回复
        session = message_bridge.session_manager.get_session(user_id)
        if session and session.chat_mode == ChatMode.PRIVATE:
            # 私聊模式下发送确认消息
            if success:
                await message_handler.finish("✅ 消息发送成功！")
            else:
                await message_handler.finish("❌ 消息发送失败，请稍后重试！")
        # 群聊模式下不回复，避免刷屏
            
    except FinishedException:
        # NoneBot 的正常结束流程，重新抛出
        raise
    except Exception as e:
        logger.error(f"处理用户消息失败 user:{user_id}: {str(e)}")
        # 只在私聊模式下提示错误
        session = message_bridge.session_manager.get_session(user_id)
        if session and session.chat_mode == ChatMode.PRIVATE:
            await message_handler.finish("❌ 处理消息时出现错误！")


# ================================ 生命周期管理 ================================

async def start_message_bridge():
    """启动消息互通服务"""
    await message_bridge.start()


async def stop_message_bridge():
    """停止消息互通服务"""
    await message_bridge.stop()


# 定时清理过期会话
async def cleanup_expired_sessions():
    """清理过期会话"""
    if message_bridge.is_running:
        message_bridge.session_manager.cleanup_expired_sessions()
