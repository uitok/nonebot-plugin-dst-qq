"""
数据库模型抽象层
提供统一的数据访问接口
"""

import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from nonebot import logger

from .connection import DatabaseManager


class BaseModel:
    """数据模型基类"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    async def init(self):
        """初始化模型（由子类实现）"""
        pass


class ChatHistoryModel(BaseModel):
    """聊天历史数据模型"""
    
    DB_NAME = 'chat_history'
    
    INIT_SQL = '''
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
    );
    
    CREATE TABLE IF NOT EXISTS player_info (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        player_name TEXT NOT NULL,
        player_id TEXT,
        first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
        last_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
        message_count INTEGER DEFAULT 0
    );
    
    CREATE TABLE IF NOT EXISTS qq_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        username TEXT NOT NULL,
        message_content TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE INDEX IF NOT EXISTS idx_chat_cluster_world ON chat_history(cluster_name, world_name);
    CREATE INDEX IF NOT EXISTS idx_chat_timestamp ON chat_history(timestamp);
    CREATE INDEX IF NOT EXISTS idx_player_name ON player_info(player_name);
    '''
    
    async def init(self):
        """初始化聊天历史表"""
        await self.db.init_database(self.DB_NAME, self.INIT_SQL)
    
    def parse_chat_message(self, raw_message: str) -> Dict[str, Any]:
        """解析聊天消息"""
        patterns = {
            'chat': r'^\[(\d{2}:\d{2}:\d{2})\]:\s*\[Chat\]\s*(.+?):\s*(.+)$',
            'join': r'^\[(\d{2}:\d{2}:\d{2})\]:\s*(.+?)\s+\((.+?)\)\s+joined\s+the\s+game$',
            'leave': r'^\[(\d{2}:\d{2}:\d{2})\]:\s*(.+?)\s+\((.+?)\)\s+left\s+the\s+game$',
            'death': r'^\[(\d{2}:\d{2}:\d{2})\]:\s*(.+?)\s+\((.+?)\)\s+died\.?\s*(.*)$',
            'respawn': r'^\[(\d{2}:\d{2}:\d{2})\]:\s*(.+?)\s+\((.+?)\)\s+respawned$',
            'rollback': r'^\[(\d{2}:\d{2}:\d{2})\]:\s*Rollback\s+(\d+)\s+day\(s\)\s+requested\s+by\s+(.+?)\s*$'
        }
        
        for msg_type, pattern in patterns.items():
            match = re.match(pattern, raw_message.strip())
            if match:
                groups = match.groups()
                if msg_type == 'chat':
                    return {
                        'timestamp': groups[0],
                        'message_type': 'chat',
                        'player_name': groups[1],
                        'player_id': None,
                        'message_content': groups[2]
                    }
                elif msg_type in ['join', 'leave', 'death', 'respawn']:
                    return {
                        'timestamp': groups[0],
                        'message_type': msg_type,
                        'player_name': groups[1],
                        'player_id': groups[2] if len(groups) > 2 else None,
                        'message_content': groups[3] if len(groups) > 3 else ''
                    }
                elif msg_type == 'rollback':
                    return {
                        'timestamp': groups[0],
                        'message_type': 'rollback',
                        'player_name': groups[2],
                        'player_id': None,
                        'message_content': f'Rollback {groups[1]} day(s)'
                    }
        
        return {
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'message_type': 'system',
            'player_name': None,
            'player_id': None,
            'message_content': raw_message
        }
    
    async def add_chat_history(self, cluster_name: str, world_name: str, 
                              chat_logs: List[str]) -> int:
        """添加聊天历史记录"""
        if not chat_logs:
            return 0
        
        added_count = 0
        
        async with self.db.transaction(self.DB_NAME) as conn:
            for raw_message in chat_logs:
                if not raw_message.strip():
                    continue
                
                # 解析消息
                parsed = self.parse_chat_message(raw_message)
                
                # 插入聊天记录
                await conn.execute('''
                    INSERT INTO chat_history 
                    (cluster_name, world_name, timestamp, message_type, 
                     player_name, player_id, message_content, raw_message)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    cluster_name, world_name, parsed['timestamp'],
                    parsed['message_type'], parsed['player_name'],
                    parsed['player_id'], parsed['message_content'],
                    raw_message
                ))
                
                # 更新玩家信息
                if parsed['player_name']:
                    await self._update_player_info(
                        conn, parsed['player_name'], parsed['player_id']
                    )
                
                added_count += 1
        
        logger.info(f"📊 添加聊天记录: {added_count} 条")
        return added_count
    
    async def _update_player_info(self, conn, player_name: str, player_id: Optional[str]):
        """更新玩家信息"""
        # 检查玩家是否存在
        cursor = await conn.execute(
            'SELECT id, message_count FROM player_info WHERE player_name = ?',
            (player_name,)
        )
        existing = await cursor.fetchone()
        
        if existing:
            # 更新现有玩家
            await conn.execute('''
                UPDATE player_info 
                SET last_seen = CURRENT_TIMESTAMP, 
                    message_count = message_count + 1,
                    player_id = COALESCE(player_id, ?)
                WHERE player_name = ?
            ''', (player_id, player_name))
        else:
            # 添加新玩家
            await conn.execute('''
                INSERT INTO player_info (player_name, player_id, message_count)
                VALUES (?, ?, 1)
            ''', (player_name, player_id))
    
    async def get_recent_chat_history(self, cluster_name: str, world_name: str,
                                     limit: int = 50) -> List[Dict[str, Any]]:
        """获取最近的聊天历史"""
        sql = '''
            SELECT * FROM chat_history 
            WHERE cluster_name = ? AND world_name = ?
            ORDER BY id DESC LIMIT ?
        '''
        
        rows = await self.db.fetchall(self.DB_NAME, sql, (cluster_name, world_name, limit))
        
        return [dict(row) for row in rows]
    
    async def get_player_chat_history(self, player_name: str, 
                                     limit: int = 50) -> List[Dict[str, Any]]:
        """获取玩家聊天历史"""
        sql = '''
            SELECT * FROM chat_history 
            WHERE player_name = ?
            ORDER BY id DESC LIMIT ?
        '''
        
        rows = await self.db.fetchall(self.DB_NAME, sql, (player_name, limit))
        return [dict(row) for row in rows]
    
    async def add_qq_message(self, user_id: int, username: str, message_content: str) -> bool:
        """添加QQ消息记录"""
        try:
            await self.db.execute(self.DB_NAME, '''
                INSERT INTO qq_messages (user_id, username, message_content)
                VALUES (?, ?, ?)
            ''', (user_id, username, message_content))
            return True
        except Exception as e:
            logger.error(f"添加QQ消息失败: {e}")
            return False
    
    async def cleanup_old_records(self, days: int = 30) -> int:
        """清理旧记录"""
        deleted_count = 0
        deleted_count += await self.db.cleanup_old_data(
            self.DB_NAME, 'chat_history', 'created_at', days
        )
        deleted_count += await self.db.cleanup_old_data(
            self.DB_NAME, 'qq_messages', 'created_at', days
        )
        return deleted_count


class ItemWikiModel(BaseModel):
    """物品Wiki数据模型"""
    
    DB_NAME = 'items'
    
    INIT_SQL = '''
    CREATE TABLE IF NOT EXISTS dst_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        english_name TEXT NOT NULL UNIQUE,
        chinese_name TEXT NOT NULL,
        category TEXT,
        description TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE INDEX IF NOT EXISTS idx_items_chinese ON dst_items(chinese_name);
    CREATE INDEX IF NOT EXISTS idx_items_english ON dst_items(english_name);
    '''
    
    async def init(self):
        """初始化物品数据库"""
        await self.db.init_database(self.DB_NAME, self.INIT_SQL)
        
        # 数据库迁移：为旧表添加新列
        await self._migrate_table_schema()
    
    async def _migrate_table_schema(self):
        """迁移表结构，添加缺失的列"""
        try:
            # 检查表是否存在以及列结构
            async with self.db.get_connection(self.DB_NAME) as conn:
                cursor = await conn.execute("PRAGMA table_info(dst_items)")
                columns_info = await cursor.fetchall()
                
                if columns_info:
                    # 获取现有列名
                    existing_columns = [col[1] for col in columns_info]
                    
                    # 添加缺失的列
                    if 'category' not in existing_columns:
                        await conn.execute("ALTER TABLE dst_items ADD COLUMN category TEXT")
                        logger.info("✅ 已添加 category 列到 dst_items 表")
                    
                    if 'description' not in existing_columns:
                        await conn.execute("ALTER TABLE dst_items ADD COLUMN description TEXT")
                        logger.info("✅ 已添加 description 列到 dst_items 表")
                    
                    await conn.commit()
        except Exception as e:
            logger.warning(f"数据库表结构迁移出错: {e}")
    
    async def search_items(self, keyword: str, limit: int = 10) -> List[Dict[str, Any]]:
        """搜索物品"""
        sql = '''
            SELECT * FROM dst_items 
            WHERE chinese_name LIKE ? OR english_name LIKE ?
            ORDER BY 
                CASE 
                    WHEN chinese_name = ? THEN 1
                    WHEN english_name = ? THEN 2
                    WHEN chinese_name LIKE ? THEN 3
                    WHEN english_name LIKE ? THEN 4
                    ELSE 5
                END
            LIMIT ?
        '''
        
        keyword_pattern = f'%{keyword}%'
        params = (keyword_pattern, keyword_pattern, keyword, keyword, 
                 f'{keyword}%', f'{keyword}%', limit)
        
        rows = await self.db.fetchall(self.DB_NAME, sql, params)
        return [dict(row) for row in rows]
    
    async def add_item(self, english_name: str, chinese_name: str, 
                      category: str = '', description: str = '') -> bool:
        """添加物品"""
        try:
            await self.db.execute(self.DB_NAME, '''
                INSERT OR REPLACE INTO dst_items 
                (english_name, chinese_name, category, description)
                VALUES (?, ?, ?, ?)
            ''', (english_name, chinese_name, category, description))
            return True
        except Exception as e:
            logger.error(f"添加物品失败: {e}")
            return False


class ArchiveModel(BaseModel):
    """数据归档模型"""
    
    DB_NAME = 'archive'  # 使用chat_history数据库
    
    INIT_SQL = '''
    CREATE TABLE IF NOT EXISTS archived_chat_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        original_id INTEGER,
        cluster_name TEXT NOT NULL,
        world_name TEXT NOT NULL,
        archive_date DATE NOT NULL,
        data_blob BLOB NOT NULL,
        compression_type TEXT DEFAULT 'zlib',
        record_count INTEGER DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE INDEX IF NOT EXISTS idx_archive_date ON archived_chat_history(archive_date);
    CREATE INDEX IF NOT EXISTS idx_archive_cluster ON archived_chat_history(cluster_name, world_name);
    '''
    
    async def init(self):
        """初始化归档表"""
        await self.db.init_database(self.DB_NAME, self.INIT_SQL)
    
    async def archive_old_data(self, days: int = 30) -> Dict[str, Any]:
        """归档旧数据"""
        # 这里可以实现数据归档逻辑
        # 暂时返回统计信息
        return {
            'archived_records': 0,
            'archive_date': datetime.now().date(),
            'compression_ratio': 0.0
        }