import asyncio
import httpx
import json
from datetime import datetime
from typing import Dict, List, Optional, Set
from nonebot import on_command, on_message
from nonebot.adapters import Event
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, PrivateMessageEvent, Message
from nonebot.rule import to_me
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
                return []
        except Exception as e:
            logger.error(f"获取集群列表失败: {e}")
            return []
    
    async def _get_worlds(self, cluster_name: str) -> List[Dict]:
        """获取世界列表"""
        try:
            # 从集群信息中获取世界列表
            clusters = await self._get_clusters()
            for cluster in clusters:
                if cluster.get("clusterName") == cluster_name:
                    worlds = cluster.get("worlds", [])
                    return [{"worldName": world} for world in worlds]
            return []
        except Exception as e:
            logger.error(f"获取世界列表失败: {e}")
            return []
    
    async def _initialize_message_hashes(self):
        """初始化消息哈希集合，避免推送历史消息"""
        try:
            logger.info("正在初始化消息哈希集合...")
            
            # 获取集群列表
            clusters = await self._get_clusters()
            if not clusters:
                logger.warning("未找到集群，跳过消息哈希初始化")
                return
            
            for cluster in clusters:
                cluster_name = cluster.get("clusterName")
                if not cluster_name:
                    continue
                
                # 获取世界列表
                worlds = await self._get_worlds(cluster_name)
                if not worlds:
                    continue
                
                for world in worlds:
                    world_name = world.get("worldName", "")
                    cluster_key = f"{cluster_name}_{world_name}"
                    
                    # 获取当前聊天日志
                    chat_logs = await self._fetch_latest_chat_logs(cluster_name, world_name, lines=50)
                    
                    if chat_logs:
                        # 生成当前消息的哈希集合
                        current_hashes = set()
                        for log_entry in chat_logs:
                            if isinstance(log_entry, str):
                                message_info = self._parse_chat_log_entry(log_entry)
                                if message_info:
                                    message_hash = self._generate_message_hash(message_info)
                                    current_hashes.add(message_hash)
                        
                        # 初始化该集群世界的消息哈希集合
                        self.last_message_hashes[cluster_key] = current_hashes
                        logger.info(f"已初始化集群 {cluster_name} 世界 {world_name} 的消息哈希集合，包含 {len(current_hashes)} 条消息")
            
            logger.info("消息哈希集合初始化完成")
            self.is_initialized = True  # 标记初始化完成
            
        except Exception as e:
            logger.error(f"初始化消息哈希集合失败: {e}")
    
    async def _sync_cluster_world_messages(self, cluster_name: str, world_name: str):
        """同步指定集群和世界的消息"""
        try:
            # 直接使用API拉取最新的聊天日志
            chat_logs = await self._fetch_latest_chat_logs(cluster_name, world_name, lines=50)
            
            if not chat_logs:
                return
            
            # 检测新消息并推送给用户
            new_messages = await self._detect_and_push_new_messages(cluster_name, world_name, chat_logs)
            
            if new_messages > 0:
                logger.info(f"集群 {cluster_name} 世界 {world_name} 推送了 {new_messages} 条新消息")
                
        except Exception as e:
            logger.error(f"同步集群 {cluster_name} 世界 {world_name} 消息失败: {e}")
    
    async def _fetch_latest_chat_logs(self, cluster_name: str, world_name: str, lines: int = 50) -> List[Dict]:
        """直接从API获取最新的聊天日志"""
        try:
            headers = {
                "Authorization": config.dmp_token,
                "X-I18n-Lang": "zh"
            }
            
            params = {
                "clusterName": cluster_name,
                "worldName": world_name,
                "line": lines,
                "type": "chat"
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{config.dmp_base_url}/logs/log_value", headers=headers, params=params)
                response.raise_for_status()
                data = response.json()
                
                if data.get("code") == 200:
                    return data.get("data", [])
                else:
                    logger.error(f"获取聊天日志失败: {data}")
                    return []
                    
        except Exception as e:
            logger.error(f"获取聊天日志失败: {e}")
            return []
    
    async def _detect_and_push_new_messages(self, cluster_name: str, world_name: str, chat_logs: List[Dict]) -> int:
        """检测新消息并推送给用户"""
        try:
            cluster_key = f"{cluster_name}_{world_name}"
            current_hashes = set()
            new_messages = []
            
            # 处理聊天日志，提取消息并生成哈希
            for log_entry in chat_logs:
                if isinstance(log_entry, str):
                    # 解析日志字符串
                    message_info = self._parse_chat_log_entry(log_entry)
                    if message_info:
                        message_hash = self._generate_message_hash(message_info)
                        current_hashes.add(message_hash)
                        
                        # 检查是否是新消息
                        if cluster_key not in self.last_message_hashes or message_hash not in self.last_message_hashes[cluster_key]:
                            new_messages.append(message_info)
            
            # 更新消息哈希集合
            self.last_message_hashes[cluster_key] = current_hashes
            
            # 如果有新消息，推送给用户
            if new_messages and self.active_users:
                await self._push_new_messages_to_users(cluster_name, world_name, new_messages)
            
            return len(new_messages)
            
        except Exception as e:
            logger.error(f"检测新消息失败: {e}")
            return 0
    
    async def _collect_all_new_messages(self) -> Dict[str, List[Dict]]:
        """收集所有世界的新消息，用于合并推送"""
        try:
            all_new_messages = {}
            
            # 获取集群列表
            clusters = await self._get_clusters()
            if not clusters:
                return all_new_messages
            
            for cluster in clusters:
                cluster_name = cluster.get("clusterName")
                if not cluster_name:
                    continue
                
                # 获取世界列表
                worlds = await self._get_worlds(cluster_name)
                if not worlds:
                    continue
                
                for world in worlds:
                    world_name = world.get("worldName", "")
                    chat_logs = await self._fetch_latest_chat_logs(cluster_name, world_name, lines=50)
                    
                    if not chat_logs:
                        continue
                    
                    # 检测新消息
                    cluster_key = f"{cluster_name}_{world_name}"
                    current_hashes = set()
                    new_messages = []
                    
                    for log_entry in chat_logs:
                        if isinstance(log_entry, str):
                            message_info = self._parse_chat_log_entry(log_entry)
                            if message_info:
                                message_hash = self._generate_message_hash(message_info)
                                current_hashes.add(message_hash)
                                
                                if cluster_key not in self.last_message_hashes or message_hash not in self.last_message_hashes[cluster_key]:
                                    new_messages.append(message_info)
                    
                    # 更新消息哈希集合
                    self.last_message_hashes[cluster_key] = current_hashes
                    
                    if new_messages:
                        all_new_messages[f"{cluster_name}_{world_name}"] = new_messages
            
            return all_new_messages
            
        except Exception as e:
            logger.error(f"收集新消息失败: {e}")
            return {}
    
    async def _merge_and_push_messages(self, all_new_messages: Dict[str, List[Dict]]):
        """合并并推送消息，避免重复"""
        try:
            if not all_new_messages or not self.active_users:
                return
            
            # 获取机器人实例
            from nonebot import get_bot
            bot = get_bot()
            
            # 为每个活跃用户推送消息
            for user_id in self.active_users:
                try:
                    # 合并所有新消息
                    merged_messages = []
                    message_hashes = set()
                    
                    for world_key, messages in all_new_messages.items():
                        cluster_name, world_name = world_key.split('_', 1)
                        
                        for msg in messages:
                            # 生成消息哈希（不包含世界信息，用于去重）
                            content_hash = self._generate_content_hash(msg)
                            
                            if content_hash not in message_hashes:
                                message_hashes.add(content_hash)
                                merged_messages.append({
                                    'cluster_name': cluster_name,
                                    'world_name': world_name,
                                    'message': msg
                                })
                    
                    if merged_messages:
                        # 构建消息内容
                        message_parts = []
                        message_parts.append("🎮 游戏内新消息:")
                        
                        for item in merged_messages[:3]:  # 只推送最新的3条消息
                            msg = item['message']
                            timestamp = msg.get("timestamp", "")
                            player_name = msg.get("player_name", "未知玩家")
                            message_content = msg.get("message_content", "")
                            message_type = msg.get("message_type", "")
                            
                            if message_type == "say" and message_content:
                                message_parts.append(f"[{timestamp}] {player_name}: {message_content}")
                            elif message_type == "system":
                                message_parts.append(f"[{timestamp}] 📢 {message_content}")
                        
                        if len(message_parts) > 1:  # 有实际消息内容
                            full_message = "\n".join(message_parts)
                            
                            # 发送私聊消息
                            await bot.send_private_msg(user_id=user_id, message=full_message)
                            logger.info(f"已推送合并的游戏消息给用户 {user_id}")
                            
                except Exception as e:
                    logger.error(f"推送消息给用户 {user_id} 失败: {e}")
                    
        except Exception as e:
            logger.error(f"合并推送消息失败: {e}")
    
    def _generate_content_hash(self, message_info: Dict) -> str:
        """生成消息内容哈希（不包含世界信息和时间戳）用于去重"""
        import hashlib
        content = f"{message_info.get('player_name', '')}_{message_info.get('message_content', '')}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _parse_chat_log_entry(self, log_entry: str) -> Optional[Dict]:
        """解析聊天日志条目"""
        try:
            # 示例日志格式：[时间] 玩家名: 消息内容
            # 或者：[时间] 系统消息
            import re
            
            # 匹配时间戳和内容
            timestamp_pattern = r'\[(\d{2}:\d{2}:\d{2})\]'
            timestamp_match = re.search(timestamp_pattern, log_entry)
            
            if not timestamp_match:
                return None
            
            timestamp = timestamp_match.group(1)
            content_after_timestamp = log_entry[timestamp_match.end():].strip()
            
            # 检查是否是QQ消息（避免重复推送）
            if '[QQ]' in content_after_timestamp:
                return None
            
            # 检查是否是玩家消息
            if ': ' in content_after_timestamp:
                player_name, message_content = content_after_timestamp.split(': ', 1)
                return {
                    'timestamp': timestamp,
                    'player_name': player_name.strip(),
                    'message_content': message_content.strip(),
                    'message_type': 'say'
                }
            else:
                # 系统消息
                return {
                    'timestamp': timestamp,
                    'player_name': '系统',
                    'message_content': content_after_timestamp,
                    'message_type': 'system'
                }
                
        except Exception as e:
            logger.error(f"解析聊天日志条目失败: {e}")
            return None
    
    def _generate_message_hash(self, message_info: Dict) -> str:
        """生成消息哈希用于去重"""
        import hashlib
        content = f"{message_info.get('timestamp', '')}_{message_info.get('player_name', '')}_{message_info.get('message_content', '')}"
        return hashlib.md5(content.encode()).hexdigest()
    
    async def _push_new_messages_to_users(self, cluster_name: str, world_name: str, new_messages: List[Dict]):
        """推送新消息给开启互通的用户"""
        try:
            # 获取机器人实例
            from nonebot import get_bot
            bot = get_bot()
            
            # 为每个活跃用户推送消息
            for user_id in self.active_users:
                try:
                    # 构建消息内容
                    message_parts = []
                    message_parts.append(f"🎮 游戏内新消息 (集群: {cluster_name}, 世界: {world_name}):")
                    
                    for msg in new_messages[:3]:  # 只推送最新的3条消息
                        timestamp = msg.get("timestamp", "")
                        player_name = msg.get("player_name", "未知玩家")
                        message_content = msg.get("message_content", "")
                        message_type = msg.get("message_type", "")
                        
                        if message_type == "say" and message_content:
                            message_parts.append(f"[{timestamp}] {player_name}: {message_content}")
                        elif message_type == "system":
                            message_parts.append(f"[{timestamp}] 📢 {message_content}")
                    
                    if len(message_parts) > 1:  # 有实际消息内容
                        full_message = "\n".join(message_parts)
                        
                        # 发送私聊消息
                        await bot.send_private_msg(user_id=user_id, message=full_message)
                        logger.info(f"已推送新游戏消息给用户 {user_id}")
                        
                except Exception as e:
                    logger.error(f"推送消息给用户 {user_id} 失败: {e}")
                    
        except Exception as e:
            logger.error(f"推送新消息失败: {e}")
    

    
    async def get_chat_logs(self, cluster_name: str, world_name: str = "World4", lines: int = 100) -> dict:
        """获取聊天日志"""
        try:
            headers = {
                "Authorization": config.dmp_token,
                "X-I18n-Lang": "zh"
            }
            
            params = {
                "clusterName": cluster_name,
                "worldName": world_name,
                "line": lines,
                "type": "chat"
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{config.dmp_base_url}/logs/log_value", headers=headers, params=params)
                response.raise_for_status()
                data = response.json()
                
                if data.get("code") == 200:
                    return data
                else:
                    return {"code": data.get("code", 500), "message": data.get("message", "获取聊天日志失败")}
                    
        except Exception as e:
            logger.error(f"获取聊天日志失败: {e}")
            return {"code": 500, "message": f"获取聊天日志出错: {e}"}
    
    async def send_message_to_game(self, message: str, cluster_name: str = None, world_name: str = ""):
        """发送消息到游戏"""
        if not cluster_name:
            # 获取第一个可用的集群名称
            config = get_config()
            cluster_name = await config.get_first_cluster()
        
        try:
            headers = {
                "X-I18n-Lang": "zh",
                "Authorization": config.dmp_token
            }
            
            data = {
                "type": "announce",
                "extraData": message,
                "clusterName": cluster_name,
                "worldName": world_name
            }
            
            logger.info(f"正在发送消息到集群 {cluster_name}: {message}")
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{config.dmp_base_url}/home/exec",
                    headers=headers,
                    json=data
                )
                response.raise_for_status()
                result = response.json()
                
                if result.get("code") == 200:
                    logger.info(f"消息已发送到游戏: {message}")
                    return True
                else:
                    logger.error(f"发送消息到游戏失败: {result}")
                    return False
                    
        except Exception as e:
            logger.error(f"发送消息到游戏出错: {e}")
            return False
    
    async def add_qq_message(self, user_id: int, username: str, message: str):
        """添加QQ消息到数据库"""
        try:
            # 存储QQ消息到数据库
            await self.db.add_qq_message(user_id, username, message)
            logger.info(f"QQ消息已存储: {username}({user_id}): {message}")
        except Exception as e:
            logger.error(f"存储QQ消息失败: {e}")


# 创建消息互通管理器实例
message_manager = MessageExchangeManager()


# 命令处理器
message_exchange_cmd = on_command("消息互通", aliases={"开启互通", "start_exchange"}, priority=5)
close_exchange_cmd = on_command("关闭互通", aliases={"stop_exchange"}, priority=5)
status_cmd = on_command("互通状态", aliases={"exchange_status"}, priority=5)
push_latest_cmd = on_command("最新消息", aliases={"latest", "get_latest"}, priority=5)


@message_exchange_cmd.handle()
async def handle_message_exchange(bot: Bot, event: Event, state: T_State):
    """处理开启消息互通命令"""
    from nonebot.adapters.onebot.v11 import GroupMessageEvent, PrivateMessageEvent
    
    user_id = event.user_id
    
    # 检查是否在群聊中
    if isinstance(event, GroupMessageEvent):
        await message_exchange_cmd.finish(
            f"🎮 消息互通功能需要在私聊中使用！\n"
            f"请私聊机器人发送「消息互通」来开启功能。\n"
            f"开启后，您的私聊消息将会发送到游戏中。"
        )
        return
    
    # 私聊处理
    if isinstance(event, PrivateMessageEvent):
        try:
            user_info = await bot.get_stranger_info(user_id=user_id)
            username = user_info.get("nickname", f"用户{user_id}")
        except:
            username = f"用户{user_id}"
        
        if user_id in message_manager.active_users:
            await message_exchange_cmd.finish("您已经开启了消息互通功能！")
            return
        
        # 添加到活跃用户列表
        message_manager.active_users.add(user_id)
        
        # 启动同步任务（如果还没启动）
        if not message_manager.is_running:
            await message_manager.start_sync()
            # 初始化消息哈希集合，避免推送历史消息
            await message_manager._initialize_message_hashes()
        
        await message_exchange_cmd.finish(
            f"✅ 消息互通功能已开启！\n"
            f"您的私聊消息将会发送到游戏中。\n"
            f"发送「关闭互通」可以关闭此功能。"
        )


@close_exchange_cmd.handle()
async def handle_close_exchange(bot: Bot, event: Event, state: T_State):
    """处理关闭消息互通命令"""
    from nonebot.adapters.onebot.v11 import GroupMessageEvent, PrivateMessageEvent
    
    user_id = event.user_id
    
    # 检查是否在群聊中
    if isinstance(event, GroupMessageEvent):
        await close_exchange_cmd.finish(
            f"🎮 消息互通功能需要在私聊中使用！\n"
            f"请私聊机器人发送「关闭互通」来关闭功能。"
        )
        return
    
    # 私聊处理
    if isinstance(event, PrivateMessageEvent):
        if user_id not in message_manager.active_users:
            await close_exchange_cmd.finish("您还没有开启消息互通功能！")
            return
        
        # 从活跃用户列表移除
        message_manager.active_users.discard(user_id)
        
        # 如果没有活跃用户，停止同步任务
        if not message_manager.active_users and message_manager.is_running:
            await message_manager.stop_sync()
        
        await close_exchange_cmd.finish("✅ 消息互通功能已关闭！")


@status_cmd.handle()
async def handle_exchange_status(bot: Bot, event: Event, state: T_State):
    """处理查看互通状态命令"""
    from nonebot.adapters.onebot.v11 import GroupMessageEvent, PrivateMessageEvent
    
    user_id = event.user_id
    
    # 检查是否在群聊中
    if isinstance(event, GroupMessageEvent):
        await status_cmd.finish(
            f"🎮 消息互通功能需要在私聊中使用！\n"
            f"请私聊机器人发送「互通状态」来查看状态。"
        )
        return
    
    # 私聊处理
    if isinstance(event, PrivateMessageEvent):
        if user_id in message_manager.active_users:
            status = "已开启"
        else:
            status = "未开启"
        
        active_count = len(message_manager.active_users)
        sync_status = "运行中" if message_manager.is_running else "已停止"
        
        await status_cmd.finish(
            f"📊 消息互通状态：{status}\n"
            f"当前活跃用户数：{active_count}\n"
            f"同步任务状态：{sync_status}"
        )


@push_latest_cmd.handle()
async def handle_push_latest(bot: Bot, event: Event, state: T_State):
    """处理获取最新消息命令"""
    from nonebot.adapters.onebot.v11 import GroupMessageEvent, PrivateMessageEvent
    
    user_id = event.user_id
    
    # 检查是否在群聊中
    if isinstance(event, GroupMessageEvent):
        await push_latest_cmd.finish(
            f"🎮 消息互通功能需要在私聊中使用！\n"
            f"请私聊机器人发送「最新消息」来获取游戏内最新消息。"
        )
        return
    
    # 私聊处理
    if isinstance(event, PrivateMessageEvent):
        # 检查用户是否开启了消息互通
        if user_id not in message_manager.active_users:
            await push_latest_cmd.finish("请先开启消息互通功能！")
            return
    
    try:
        # 获取第一个集群
        config = get_config()
        cluster_name = await config.get_first_cluster()
        
        # 获取该集群的世界列表
        worlds = await message_manager._get_worlds(cluster_name)
        
        if not worlds:
            await push_latest_cmd.finish("未找到可用的游戏世界！")
            return
        
        # 获取第一个世界的最新消息
        world_name = worlds[0].get("worldName", "")
        
        # 直接从API获取最新聊天记录
        chat_logs = await message_manager._fetch_latest_chat_logs(cluster_name, world_name, lines=20)
        
        if not chat_logs:
            await push_latest_cmd.finish("暂无游戏内消息记录！")
            return
        
        # 解析聊天记录
        parsed_messages = []
        for log_entry in chat_logs:
            if isinstance(log_entry, str):
                message_info = message_manager._parse_chat_log_entry(log_entry)
                if message_info:
                    parsed_messages.append(message_info)
        
        if not parsed_messages:
            await push_latest_cmd.finish("暂无游戏内消息记录！")
            return
        
        # 构建消息内容
        message_parts = []
        message_parts.append(f"🎮 游戏内最新消息 (集群: {cluster_name}, 世界: {world_name}):")
        
        for msg in parsed_messages[:5]:  # 只显示最新的5条消息
            timestamp = msg.get("timestamp", "")
            player_name = msg.get("player_name", "未知玩家")
            message_content = msg.get("message_content", "")
            message_type = msg.get("message_type", "")
            
            if message_type == "say" and message_content:
                message_parts.append(f"[{timestamp}] {player_name}: {message_content}")
            elif message_type == "system":
                message_parts.append(f"[{timestamp}] 📢 {message_content}")
        
        if len(message_parts) > 1:  # 有实际消息内容
            full_message = "\n".join(message_parts)
            await push_latest_cmd.finish(full_message)
        else:
            await push_latest_cmd.finish("暂无新的游戏内消息！")
            
    except Exception as e:
        logger.error(f"获取最新消息失败: {e}")
        await push_latest_cmd.finish("获取最新消息失败，请稍后重试！")


# 私聊消息处理器
def is_private_message(event: PrivateMessageEvent) -> bool:
    """检查是否为私聊消息"""
    return isinstance(event, PrivateMessageEvent)

private_message_handler = on_message(rule=is_private_message, priority=10, block=False)


@private_message_handler.handle()
async def handle_private_message(bot: Bot, event: PrivateMessageEvent, state: T_State):
    """处理私聊消息"""
    user_id = event.user_id
    
    # 检查用户是否开启了消息互通
    if user_id not in message_manager.active_users:
        return
    
    # 获取用户信息
    try:
        user_info = await bot.get_stranger_info(user_id=user_id)
        nickname = user_info.get("nickname", "")
        
        # 清理昵称中的特殊字符和空白字符
        if nickname and nickname.strip():
            # 移除不可见字符和特殊字符
            import re
            cleaned_nickname = re.sub(r'[^\w\s\u4e00-\u9fff]', '', nickname.strip())
            # 如果清理后为空，使用默认名称
            if cleaned_nickname:
                username = cleaned_nickname
            else:
                username = f"QQ用户{user_id}"
        else:
            username = f"QQ用户{user_id}"
    except Exception as e:
        logger.warning(f"获取用户昵称失败: {e}")
        username = f"QQ用户{user_id}"
    
    # 获取消息内容
    message_content = event.get_plaintext().strip()
    
    # 过滤命令消息
    if message_content.startswith(("/", "消息互通", "关闭互通", "互通状态", "最新消息")):
        return
    
    # 存储QQ消息到数据库
    await message_manager.add_qq_message(user_id, username, message_content)
    
    # 发送消息到游戏
    success = await message_manager.send_message_to_game(
        f"[QQ] {username}: {message_content}"
    )
    
    if success:
        await private_message_handler.finish("消息已发送到游戏！")
    else:
        await private_message_handler.finish("消息发送失败，请稍后重试！")


# 插件加载时启动消息同步
from nonebot import get_driver

@get_driver().on_startup
async def startup():
    """插件启动时初始化"""
    logger.info("消息互通插件正在启动...")
    await message_manager.db.init_database()


# 插件卸载时停止消息同步
@get_driver().on_shutdown
async def shutdown():
    """插件卸载时清理"""
    logger.info("消息互通插件正在关闭...")
    await message_manager.stop_sync() 