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
        timestamp = timestamp_match.group(1) if timestamp_match else ""
        
        # 匹配消息类型
        message_type = "unknown"
        player_name = None
        player_id = None
        message_content = None
        
        # 加入公告
        if "[Join Announcement]" in raw_message:
            message_type = "join"
            player_name = raw_message.split("[Join Announcement]")[1].strip()
        
        # 离开公告
        elif "[Leave Announcement]" in raw_message:
            message_type = "leave"
            player_name = raw_message.split("[Leave Announcement]")[1].strip()
        
        # 死亡公告
        elif "[Death Announcement]" in raw_message:
            message_type = "death"
            death_part = raw_message.split("[Death Announcement]")[1].strip()
            if " 死于：" in death_part:
                player_name = death_part.split(" 死于：")[0].strip()
                message_content = death_part.split(" 死于：")[1].strip()
            else:
                player_name = death_part
        
        # 聊天消息
        elif "[Say]" in raw_message:
            message_type = "say"
            say_part = raw_message.split("[Say]")[1].strip()
            player_pattern = r'\(([^)]+)\)\s*([^:]+):\s*(.*)'
            player_match = re.search(player_pattern, say_part)
            if player_match:
                player_id = player_match.group(1)
                player_name = player_match.group(2).strip()
                message_content = player_match.group(3).strip()
            else:
                if ":" in say_part:
                    parts = say_part.split(":", 1)
                    player_name = parts[0].strip()
                    message_content = parts[1].strip()
        
        return {
            "timestamp": timestamp,
            "message_type": message_type,
            "player_name": player_name,
            "player_id": player_id,
            "message_content": message_content,
            "raw_message": raw_message
        }
    
    async def add_chat_history(self, cluster_name: str, world_name: str, chat_logs: List[str]) -> int:
        """添加聊天历史记录"""
        try:
            await self.init_database()
            added_count = 0
            
            async with aiosqlite.connect(self.db_path) as db:
                for log in chat_logs:
                    # 解析日志
                    parsed = self.parse_chat_message(log)
                    
                    # 插入聊天历史记录
                    cursor = await db.execute('''
                        INSERT INTO chat_history 
                        (cluster_name, world_name, timestamp, message_type, player_name, player_id, message_content, raw_message)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        cluster_name, world_name, parsed.get("timestamp"), parsed.get("message_type"),
                        parsed.get("player_name"), parsed.get("player_id"), parsed.get("message_content"), log
                    ))
                    
                    # 如果有玩家信息，更新玩家信息表
                    if parsed.get("player_name"):
                        await self._update_player_info(db, parsed.get("player_name"), parsed.get("player_id"))
                    
                    added_count += 1
                
                await db.commit()
                return added_count
        except Exception as e:
            print(f"添加聊天历史失败: {e}")
            return 0
    
    async def _update_player_info(self, db, player_name: str, player_id: Optional[str]):
        """更新玩家信息"""
        try:
            # 检查玩家是否已存在
            cursor = await db.execute(
                'SELECT id, message_count FROM player_info WHERE player_name = ?',
                (player_name,)
            )
            existing = await cursor.fetchone()
            
            if existing:
                # 更新现有玩家信息
                await db.execute('''
                    UPDATE player_info 
                    SET last_seen = CURRENT_TIMESTAMP, message_count = message_count + 1
                    WHERE player_name = ?
                ''', (player_name,))
            else:
                # 创建新玩家信息
                await db.execute('''
                    INSERT INTO player_info (player_name, player_id, message_count)
                    VALUES (?, ?, 1)
                ''', (player_name, player_id))
        except Exception as e:
            print(f"更新玩家信息失败: {e}")
    
    async def get_recent_chat_history(self, cluster_name: str, world_name: str, 
                                     limit: int = 50) -> List[Dict[str, Any]]:
        """获取最近的聊天历史"""
        try:
            await self.init_database()
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute('''
                    SELECT timestamp, message_type, player_name, player_id, message_content, raw_message
                    FROM chat_history 
                    WHERE cluster_name = ? AND world_name = ?
                    ORDER BY created_at DESC 
                    LIMIT ?
                ''', (cluster_name, world_name, limit))
                
                rows = await cursor.fetchall()
                return [
                    {
                        "timestamp": row[0],
                        "message_type": row[1],
                        "player_name": row[2],
                        "player_id": row[3],
                        "message_content": row[4],
                        "raw_message": row[5]
                    }
                    for row in rows
                ]
        except Exception as e:
            print(f"获取聊天历史失败: {e}")
            return []
    
    async def get_player_chat_history(self, player_name: str, limit: int = 50) -> List[Dict[str, Any]]:
        """获取指定玩家的聊天历史"""
        try:
            await self.init_database()
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute('''
                    SELECT timestamp, message_type, player_name, player_id, message_content, raw_message
                    FROM chat_history 
                    WHERE player_name = ?
                    ORDER BY created_at DESC 
                    LIMIT ?
                ''', (player_name, limit))
                
                rows = await cursor.fetchall()
                return [
                    {
                        "timestamp": row[0],
                        "message_type": row[1],
                        "player_name": row[2],
                        "player_id": row[3],
                        "message_content": row[4],
                        "raw_message": row[5]
                    }
                    for row in rows
                ]
        except Exception as e:
            print(f"获取玩家聊天历史失败: {e}")
            return []
    
    async def get_player_list(self) -> List[Dict[str, Any]]:
        """获取玩家列表"""
        try:
            await self.init_database()
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute('''
                    SELECT player_name, player_id, message_count, last_seen
                    FROM player_info 
                    ORDER BY message_count DESC, last_seen DESC
                ''')
                
                rows = await cursor.fetchall()
                return [
                    {
                        "player_name": row[0],
                        "player_id": row[1],
                        "message_count": row[2],
                        "last_seen": row[3]
                    }
                    for row in rows
                ]
        except Exception as e:
            print(f"获取玩家列表失败: {e}")
            return []
    
    async def get_database_stats(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        try:
            await self.init_database()
            async with aiosqlite.connect(self.db_path) as db:
                # 获取总消息数
                cursor = await db.execute('SELECT COUNT(*) FROM chat_history')
                total_messages = (await cursor.fetchone())[0]
                
                # 获取总玩家数
                cursor = await db.execute('SELECT COUNT(*) FROM player_info')
                total_players = (await cursor.fetchone())[0]
                
                # 获取最近24小时的消息数
                cursor = await db.execute('''
                    SELECT COUNT(*) FROM chat_history 
                    WHERE created_at >= datetime('now', '-1 day')
                ''')
                messages_24h = (await cursor.fetchone())[0]
                
                # 获取文件大小
                file_size_mb = 0
                if os.path.exists(self.db_path):
                    file_size_mb = round(os.path.getsize(self.db_path) / (1024 * 1024), 2)
                
                return {
                    "total_messages": total_messages,
                    "total_players": total_players,
                    "messages_24h": messages_24h,
                    "file_size_mb": file_size_mb
                }
        except Exception as e:
            print(f"获取数据库统计失败: {e}")
            return {
                "total_messages": 0,
                "total_players": 0,
                "messages_24h": 0,
                "file_size_mb": 0
            }
    
    async def cleanup_old_records(self, days: int = 30) -> int:
        """清理旧记录"""
        try:
            await self.init_database()
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
        """添加QQ消息到数据库"""
        try:
            await self.init_database()
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
        """获取QQ消息历史"""
        try:
            await self.init_database()
            async with aiosqlite.connect(self.db_path) as db:
                if user_id:
                    cursor = await db.execute('''
                        SELECT id, user_id, username, message_content, created_at
                        FROM qq_messages
                        WHERE user_id = ?
                        ORDER BY created_at DESC
                        LIMIT ?
                    ''', (user_id, limit))
                else:
                    cursor = await db.execute('''
                        SELECT id, user_id, username, message_content, created_at
                        FROM qq_messages
                        ORDER BY created_at DESC
                        LIMIT ?
                    ''', (limit,))
                
                rows = await cursor.fetchall()
                return [
                    {
                        "id": row[0],
                        "user_id": row[1],
                        "username": row[2],
                        "message_content": row[3],
                        "created_at": row[4]
                    }
                    for row in rows
                ]
        except Exception as e:
            print(f"获取QQ消息失败: {e}")
            return []
    
    async def sync_chat_logs(self, cluster_name: str, world_name: str = "World4", lines: int = 1000) -> dict:
        """同步聊天日志到数据库"""
        try:
            # 导入API模块
            from .dmp_api import dmp_api
            
            # 获取聊天日志
            result = await dmp_api.get_chat_logs(cluster_name, world_name, lines)
            
            if result.get("code") == 200:
                chat_logs = result.get("data", [])
                if isinstance(chat_logs, list) and chat_logs:
                    # 保存到数据库
                    added_count = await self.add_chat_history(cluster_name, world_name, chat_logs)
                    
                    return {
                        "code": 200,
                        "message": f"同步成功，添加了 {added_count} 条记录",
                        "data": {
                            "cluster_name": cluster_name,
                            "world_name": world_name,
                            "lines": lines,
                            "added_count": added_count,
                            "new_messages": added_count
                        }
                    }
                else:
                    return {
                        "code": 200,
                        "message": "同步成功，但没有新的聊天记录",
                        "data": {
                            "cluster_name": cluster_name,
                            "world_name": world_name,
                            "lines": lines,
                            "added_count": 0,
                            "new_messages": 0
                        }
                    }
            else:
                return {
                    "code": result.get("code", 500),
                    "message": f"获取聊天日志失败: {result.get('message', '未知错误')}",
                    "data": None
                }
        except Exception as e:
            return {
                "code": 500,
                "message": f"同步聊天日志失败: {str(e)}",
                "data": None
            }


# 创建全局聊天历史数据库实例
chat_db = ChatHistoryDatabase() 