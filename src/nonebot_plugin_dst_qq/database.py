import aiosqlite
import os
import re
from datetime import datetime
from typing import List, Optional, Dict, Any


class ChatHistoryDatabase:
    """聊天历史数据库管理器"""
    
    def __init__(self, db_path: str = "chat_history.db"):
        self.db_path = db_path
        self._init_lock = False
    
    async def init_database(self):
        """初始化数据库"""
        if self._init_lock:
            return
        
        self._init_lock = True
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # 创建聊天历史表
                await db.execute('''
                    CREATE TABLE IF NOT EXISTS chat_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        cluster_name TEXT NOT NULL,
                        world_name TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        message_type TEXT NOT NULL,
                        player_name TEXT,
                        player_id TEXT,
                        message_content TEXT,
                        raw_message TEXT NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # 创建玩家信息表
                await db.execute('''
                    CREATE TABLE IF NOT EXISTS player_info (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        player_name TEXT NOT NULL,
                        player_id TEXT,
                        first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                        last_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                        message_count INTEGER DEFAULT 0
                    )
                ''')
                
                # 创建QQ消息表
                await db.execute('''
                    CREATE TABLE IF NOT EXISTS qq_messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        username TEXT NOT NULL,
                        message_content TEXT NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # 创建索引以提高查询性能
                await db.execute('''
                    CREATE INDEX IF NOT EXISTS idx_chat_history_timestamp 
                    ON chat_history(timestamp)
                ''')
                
                await db.execute('''
                    CREATE INDEX IF NOT EXISTS idx_chat_history_cluster_world 
                    ON chat_history(cluster_name, world_name)
                ''')
                
                await db.execute('''
                    CREATE INDEX IF NOT EXISTS idx_chat_history_player 
                    ON chat_history(player_name, player_id)
                ''')
                
                await db.execute('''
                    CREATE INDEX IF NOT EXISTS idx_player_info_name 
                    ON player_info(player_name)
                ''')
                
                await db.execute('''
                    CREATE INDEX IF NOT EXISTS idx_qq_messages_user_id 
                    ON qq_messages(user_id)
                ''')
                
                await db.execute('''
                    CREATE INDEX IF NOT EXISTS idx_qq_messages_created_at 
                    ON qq_messages(created_at)
                ''')
                
                await db.commit()
        finally:
            self._init_lock = False
    
    def parse_chat_message(self, raw_message: str) -> Dict[str, Any]:
        """解析聊天消息"""
        # 匹配时间戳和消息内容
        timestamp_pattern = r'\[(\d{2}:\d{2}:\d{2})\]'
        timestamp_match = re.search(timestamp_pattern, raw_message)
        
        if not timestamp_match:
            return {
                'timestamp': datetime.now().strftime('%H:%M:%S'),
                'message_type': 'unknown',
                'player_name': None,
                'player_id': None,
                'message_content': raw_message
            }
        
        timestamp = timestamp_match.group(1)
        content_after_timestamp = raw_message[timestamp_match.end():].strip()
        
        # 检查是否是QQ消息（避免重复推送）
        if '[QQ]' in content_after_timestamp:
            return None
        
        # 检查是否是玩家消息
        if ': ' in content_after_timestamp:
            player_name, message_content = content_after_timestamp.split(': ', 1)
            return {
                'timestamp': timestamp,
                'message_type': 'say',
                'player_name': player_name.strip(),
                'player_id': None,
                'message_content': message_content.strip()
            }
        else:
            # 系统消息
            return {
                'timestamp': timestamp,
                'message_type': 'system',
                'player_name': '系统',
                'player_id': None,
                'message_content': content_after_timestamp
            }
    
    async def add_chat_message(self, world_name: str, player_name: str, message: str, timestamp: str = None) -> bool:
        """添加聊天消息到数据库（新方法）"""
        try:
            if not timestamp:
                timestamp = datetime.now().strftime('%H:%M:%S')
            
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute('''
                    INSERT INTO chat_history 
                    (cluster_name, world_name, timestamp, message_type, player_name, message_content, raw_message)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', ('default', world_name, timestamp, 'say', player_name, message, f"[{timestamp}] {player_name}: {message}"))
                
                await db.commit()
                return True
        except Exception as e:
            print(f"添加聊天消息失败: {e}")
            return False
    
    async def get_chat_statistics(self) -> Dict[str, Any]:
        """获取聊天统计信息（新方法）"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # 总消息数
                cursor = await db.execute('SELECT COUNT(*) FROM chat_history')
                total_messages = (await cursor.fetchone())[0]
                
                # 唯一玩家数
                cursor = await db.execute('SELECT COUNT(DISTINCT player_name) FROM chat_history WHERE player_name IS NOT NULL')
                unique_players = (await cursor.fetchone())[0]
                
                # 唯一世界数
                cursor = await db.execute('SELECT COUNT(DISTINCT world_name) FROM chat_history')
                unique_worlds = (await cursor.fetchone())[0]
                
                # 最早消息时间
                cursor = await db.execute('SELECT MIN(created_at) FROM chat_history')
                earliest_message = (await cursor.fetchone())[0]
                
                # 最新消息时间
                cursor = await db.execute('SELECT MAX(created_at) FROM chat_history')
                latest_message = (await cursor.fetchone())[0]
                
                # 最活跃的玩家
                cursor = await db.execute('''
                    SELECT player_name, COUNT(*) as count 
                    FROM chat_history 
                    WHERE player_name IS NOT NULL 
                    GROUP BY player_name 
                    ORDER BY count DESC 
                    LIMIT 5
                ''')
                top_players = [{'player': row[0], 'count': row[1]} for row in await cursor.fetchall()]
                
                return {
                    'total_messages': total_messages,
                    'unique_players': unique_players,
                    'unique_worlds': unique_worlds,
                    'earliest_message': earliest_message,
                    'latest_message': latest_message,
                    'top_players': top_players
                }
        except Exception as e:
            print(f"获取聊天统计信息失败: {e}")
            return {}
    
    async def add_chat_history(self, cluster_name: str, world_name: str, chat_logs: List[str]) -> int:
        """添加聊天历史记录"""
        try:
            added_count = 0
            async with aiosqlite.connect(self.db_path) as db:
                for log_entry in chat_logs:
                    if not isinstance(log_entry, str):
                        continue
                    
                    # 解析聊天消息
                    parsed_message = self.parse_chat_message(log_entry)
                    if not parsed_message:
                        continue
                    
                    # 检查是否已存在相同的消息
                    cursor = await db.execute('''
                        SELECT id FROM chat_history 
                        WHERE cluster_name = ? AND world_name = ? AND timestamp = ? AND player_name = ? AND message_content = ?
                    ''', (cluster_name, world_name, parsed_message['timestamp'], 
                          parsed_message['player_name'], parsed_message['message_content']))
                    
                    if await cursor.fetchone():
                        continue  # 消息已存在，跳过
                    
                    # 插入新消息
                    await db.execute('''
                        INSERT INTO chat_history 
                        (cluster_name, world_name, timestamp, message_type, player_name, player_id, message_content, raw_message)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (cluster_name, world_name, parsed_message['timestamp'], 
                          parsed_message['message_type'], parsed_message['player_name'], 
                          parsed_message['player_id'], parsed_message['message_content'], log_entry))
                    
                    added_count += 1
                    
                    # 更新玩家信息
                    if parsed_message['player_name']:
                        await self._update_player_info(db, parsed_message['player_name'], parsed_message['player_id'])
                
                await db.commit()
                return added_count
                
        except Exception as e:
            print(f"添加聊天历史失败: {e}")
            return 0
    
    async def _update_player_info(self, db, player_name: str, player_id: Optional[str]):
        """更新玩家信息"""
        try:
            # 检查玩家是否已存在
            cursor = await db.execute('SELECT id FROM player_info WHERE player_name = ?', (player_name,))
            existing_player = await cursor.fetchone()
            
            if existing_player:
                # 更新现有玩家信息
                await db.execute('''
                    UPDATE player_info 
                    SET last_seen = CURRENT_TIMESTAMP, message_count = message_count + 1
                    WHERE player_name = ?
                ''', (player_name,))
            else:
                # 添加新玩家
                await db.execute('''
                    INSERT INTO player_info (player_name, player_id, first_seen, last_seen, message_count)
                    VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 1)
                ''', (player_name, player_id))
        except Exception as e:
            print(f"更新玩家信息失败: {e}")
    
    async def get_recent_chat_history(self, cluster_name: str, world_name: str, 
                                     limit: int = 50) -> List[Dict[str, Any]]:
        """获取最近的聊天历史"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute('''
                    SELECT timestamp, player_name, message_content, message_type
                    FROM chat_history 
                    WHERE cluster_name = ? AND world_name = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                ''', (cluster_name, world_name, limit))
                
                rows = await cursor.fetchall()
                return [
                    {
                        'timestamp': row[0],
                        'player_name': row[1],
                        'message_content': row[2],
                        'message_type': row[3]
                    }
                    for row in rows
                ]
        except Exception as e:
            print(f"获取聊天历史失败: {e}")
            return []
    
    async def get_player_chat_history(self, player_name: str, limit: int = 50) -> List[Dict[str, Any]]:
        """获取指定玩家的聊天历史"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute('''
                    SELECT timestamp, world_name, message_content, message_type
                    FROM chat_history 
                    WHERE player_name = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                ''', (player_name, limit))
                
                rows = await cursor.fetchall()
                return [
                    {
                        'timestamp': row[0],
                        'world_name': row[1],
                        'message_content': row[2],
                        'message_type': row[3]
                    }
                    for row in rows
                ]
        except Exception as e:
            print(f"获取玩家聊天历史失败: {e}")
            return []
    
    async def get_player_list(self) -> List[Dict[str, Any]]:
        """获取玩家列表"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute('''
                    SELECT player_name, player_id, first_seen, last_seen, message_count
                    FROM player_info 
                    ORDER BY message_count DESC
                ''')
                
                rows = await cursor.fetchall()
                return [
                    {
                        'player_name': row[0],
                        'player_id': row[1],
                        'first_seen': row[2],
                        'last_seen': row[3],
                        'message_count': row[4]
                    }
                    for row in rows
                ]
        except Exception as e:
            print(f"获取玩家列表失败: {e}")
            return []
    
    async def get_database_stats(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # 总消息数
                cursor = await db.execute('SELECT COUNT(*) FROM chat_history')
                total_messages = (await cursor.fetchone())[0]
                
                # 总玩家数
                cursor = await db.execute('SELECT COUNT(*) FROM player_info')
                total_players = (await cursor.fetchone())[0]
                
                # 最近24小时的消息数
                cursor = await db.execute('''
                    SELECT COUNT(*) FROM chat_history 
                    WHERE created_at >= datetime('now', '-1 day')
                ''')
                messages_24h = (await cursor.fetchone())[0]
                
                # 数据库文件大小
                file_size_mb = os.path.getsize(self.db_path) / (1024 * 1024) if os.path.exists(self.db_path) else 0
                
                return {
                    'total_messages': total_messages,
                    'total_players': total_players,
                    'messages_24h': messages_24h,
                    'file_size_mb': round(file_size_mb, 2)
                }
        except Exception as e:
            print(f"获取数据库统计信息失败: {e}")
            return {}
    
    async def cleanup_old_records(self, days: int = 30) -> int:
        """清理旧记录"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute('''
                    DELETE FROM chat_history 
                    WHERE created_at < datetime('now', '-{} days')
                '''.format(days))
                
                deleted_count = cursor.rowcount
                await db.commit()
                return deleted_count
        except Exception as e:
            print(f"清理旧记录失败: {e}")
            return 0
    
    async def add_qq_message(self, user_id: int, username: str, message_content: str) -> bool:
        """添加QQ消息"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute('''
                    INSERT INTO qq_messages (user_id, username, message_content)
                    VALUES (?, ?, ?)
                ''', (user_id, username, message_content))
                
                await db.commit()
                return True
        except Exception as e:
            print(f"添加QQ消息失败: {e}")
            return False
    
    async def get_qq_messages(self, user_id: int = None, limit: int = 50) -> List[Dict[str, Any]]:
        """获取QQ消息"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                if user_id:
                    cursor = await db.execute('''
                        SELECT username, message_content, created_at
                        FROM qq_messages 
                        WHERE user_id = ?
                        ORDER BY created_at DESC
                        LIMIT ?
                    ''', (user_id, limit))
                else:
                    cursor = await db.execute('''
                        SELECT user_id, username, message_content, created_at
                        FROM qq_messages 
                        ORDER BY created_at DESC
                        LIMIT ?
                    ''', (limit,))
                
                rows = await cursor.fetchall()
                return [
                    {
                        'user_id': row[0] if not user_id else user_id,
                        'username': row[1] if user_id else row[1],
                        'message_content': row[2] if user_id else row[2],
                        'created_at': row[3] if user_id else row[3]
                    }
                    for row in rows
                ]
        except Exception as e:
            print(f"获取QQ消息失败: {e}")
            return []
    
    async def sync_chat_logs(self, cluster_name: str, world_name: str = "World4", lines: int = 1000) -> dict:
        """同步聊天日志（兼容性方法）"""
        try:
            # 这里可以调用外部API获取聊天日志
            # 暂时返回空结果
            return {"code": 200, "data": [], "message": "同步功能已弃用，请使用新的API"}
        except Exception as e:
            return {"code": 500, "message": f"同步聊天日志失败: {str(e)}"}


# 创建全局数据库实例
chat_db = ChatHistoryDatabase() 