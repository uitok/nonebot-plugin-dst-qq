"""
统一数据库连接管理器
提供连接池、事务管理和统一的数据库操作接口
"""

import aiosqlite
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, AsyncGenerator, List
from contextlib import asynccontextmanager
from nonebot import logger, require

# 声明插件依赖
require("nonebot_plugin_localstore")
import nonebot_plugin_localstore as store


class DatabaseManager:
    """统一数据库管理器"""
    
    def __init__(self):
        # 使用 localstore 获取数据目录
        self.data_dir = store.get_plugin_data_dir()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 数据库文件路径
        self.databases = {
            'chat_history': self.data_dir / "chat_history.db",
            'items': self.data_dir / "dst_items.db", 
            'archive': self.data_dir / "chat_history.db"  # 归档表在同一数据库
        }
        
        # 连接池管理
        self._connections: Dict[str, Optional[aiosqlite.Connection]] = {}
        self._locks: Dict[str, asyncio.Lock] = {}
        self._initialized = set()
        
        # 为每个数据库创建锁
        for db_name in self.databases:
            self._locks[db_name] = asyncio.Lock()
        
        logger.info(f"🗄️ 数据库管理器初始化完成: {self.data_dir}")
    
    @asynccontextmanager
    async def get_connection(self, db_name: str = 'chat_history') -> AsyncGenerator[aiosqlite.Connection, None]:
        """获取数据库连接（上下文管理器）"""
        if db_name not in self.databases:
            raise ValueError(f"未知的数据库名称: {db_name}")
        
        async with self._locks[db_name]:
            # 如果连接不存在，创建新连接
            if self._connections.get(db_name) is None:
                db_path = self.databases[db_name]
                self._connections[db_name] = await aiosqlite.connect(str(db_path))
                logger.debug(f"📊 创建数据库连接: {db_name}")
            
            conn = self._connections[db_name]
            
            try:
                yield conn
            finally:
                # 连接保持打开状态，由管理器统一管理
                pass
    
    async def execute(self, db_name: str, sql: str, parameters=None) -> aiosqlite.Cursor:
        """执行SQL语句"""
        async with self.get_connection(db_name) as conn:
            if parameters:
                cursor = await conn.execute(sql, parameters)
            else:
                cursor = await conn.execute(sql)
            await conn.commit()
            return cursor
    
    async def fetchone(self, db_name: str, sql: str, parameters=None) -> Optional[aiosqlite.Row]:
        """查询单条记录"""
        async with self.get_connection(db_name) as conn:
            if parameters:
                cursor = await conn.execute(sql, parameters)
            else:
                cursor = await conn.execute(sql)
            return await cursor.fetchone()
    
    async def fetchall(self, db_name: str, sql: str, parameters=None) -> List[aiosqlite.Row]:
        """查询多条记录"""
        async with self.get_connection(db_name) as conn:
            if parameters:
                cursor = await conn.execute(sql, parameters)
            else:
                cursor = await conn.execute(sql)
            return await cursor.fetchall()
    
    @asynccontextmanager
    async def transaction(self, db_name: str = 'chat_history'):
        """事务管理器"""
        async with self.get_connection(db_name) as conn:
            try:
                await conn.execute('BEGIN')
                yield conn
                await conn.execute('COMMIT')
            except Exception:
                await conn.execute('ROLLBACK')
                raise
    
    async def init_database(self, db_name: str, init_sql: str) -> None:
        """初始化数据库表结构"""
        if db_name in self._initialized:
            return
        
        async with self.get_connection(db_name) as conn:
            # 执行初始化SQL
            for sql_statement in init_sql.strip().split(';'):
                sql_statement = sql_statement.strip()
                if sql_statement:
                    await conn.execute(sql_statement)
            await conn.commit()
        
        self._initialized.add(db_name)
        logger.info(f"✅ 数据库初始化完成: {db_name}")
    
    async def get_stats(self, db_name: str = 'chat_history') -> Dict[str, Any]:
        """获取数据库统计信息"""
        db_path = self.databases[db_name]
        stats = {
            'database_name': db_name,
            'database_path': str(db_path),
            'file_size': 0,
            'table_count': 0,
            'tables': {}
        }
        
        if db_path.exists():
            stats['file_size'] = db_path.stat().st_size
        
        try:
            async with self.get_connection(db_name) as conn:
                # 获取表列表
                cursor = await conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
                tables = await cursor.fetchall()
                stats['table_count'] = len(tables)
                
                # 获取每个表的记录数
                for table in tables:
                    table_name = table[0]
                    cursor = await conn.execute(f"SELECT COUNT(*) FROM {table_name}")
                    count = await cursor.fetchone()
                    stats['tables'][table_name] = count[0] if count else 0
                    
        except Exception as e:
            logger.error(f"获取数据库统计失败: {e}")
            stats['error'] = str(e)
        
        return stats
    
    async def cleanup_old_data(self, db_name: str, table: str, 
                              date_column: str, days: int) -> int:
        """清理旧数据"""
        sql = f"""
        DELETE FROM {table} 
        WHERE {date_column} < datetime('now', '-{days} days')
        """
        
        cursor = await self.execute(db_name, sql)
        deleted_count = cursor.rowcount
        logger.info(f"🗑️ 清理 {table} 表 {days} 天前的数据: {deleted_count} 条")
        return deleted_count
    
    async def migrate_old_database(self, old_path: str, db_name: str) -> bool:
        """迁移旧数据库文件"""
        try:
            old_db = Path(old_path)
            new_db = self.databases[db_name]
            
            if old_db.exists() and not new_db.exists():
                logger.info(f"🔄 迁移数据库文件: {old_path} -> {new_db}")
                old_db.rename(new_db)
                logger.info("✅ 数据库迁移成功")
                return True
            elif old_db.exists() and new_db.exists():
                # 重命名为备份文件
                backup_path = old_db.with_suffix('.db.backup')
                if not backup_path.exists():
                    old_db.rename(backup_path)
                    logger.info(f"📦 旧数据库已备份: {backup_path}")
                return True
                
        except Exception as e:
            logger.error(f"❌ 数据库迁移失败: {e}")
            return False
        
        return False
    
    async def close_all(self):
        """关闭所有数据库连接"""
        for db_name, conn in self._connections.items():
            if conn:
                try:
                    await conn.close()
                    logger.debug(f"📊 关闭数据库连接: {db_name}")
                except Exception as e:
                    logger.warning(f"关闭连接时出错 {db_name}: {e}")
        
        self._connections.clear()
        logger.info("🔒 所有数据库连接已关闭")