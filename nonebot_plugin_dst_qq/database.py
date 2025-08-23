import aiosqlite
import os
import re
import shutil
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path
from nonebot import require
from nonebot.log import logger

# 声明插件依赖
require("nonebot_plugin_localstore")

# 导入 localstore 插件和缓存管理器
import nonebot_plugin_localstore as store
from .cache_manager import cached, cache_manager
from .data_archive_manager import archive_manager


class ChatHistoryDatabase:
    """聊天历史数据库管理器"""
    
    def __init__(self, db_path: Optional[str] = None):
        # 使用 localstore 获取插件数据目录
        if db_path is None:
            plugin_data_dir = store.get_plugin_data_dir()
            self.db_path = str(plugin_data_dir / "chat_history.db")
        else:
            self.db_path = db_path
        
        # 确保数据目录存在
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # 执行数据迁移（如果需要）
        self._migrate_old_database()
        
        self._init_lock = False
    
    def _migrate_old_database(self):
        """迁移旧的数据库文件"""
        try:
            old_db_path = Path("chat_history.db")
            new_db_path = Path(self.db_path)
            
            # 如果旧文件存在且新文件不存在，进行迁移
            if old_db_path.exists() and not new_db_path.exists():
                logger.info("🔄 检测到旧数据库文件，开始迁移...")
                shutil.move(str(old_db_path), str(new_db_path))
                logger.info(f"✅ 数据库已成功迁移到: {new_db_path}")
            elif old_db_path.exists() and new_db_path.exists():
                logger.warning("⚠️ 新旧数据库文件均存在，请手动处理旧文件")
                # 重命名旧文件为备份
                backup_path = old_db_path.with_suffix(".db.backup")
                if not backup_path.exists():
                    old_db_path.rename(backup_path)
                    logger.info(f"📦 旧数据库文件已重命名为: {backup_path}")
                    
        except Exception as e:
            logger.error(f"❌ 数据库迁移失败: {e}")
            # 迁移失败不影响插件运行，继续使用新路径
    
    async def init_database(self):
        """初始化数据库"""
        if self._init_lock:
            return
        
        self._init_lock = True
        try:
            # 同时初始化归档表结构
            await archive_manager.init_archive_tables()
            
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
                
                # 数据更新后清除相关缓存
                await self._invalidate_related_cache(cluster_name, world_name)
                
                return added_count
        except Exception as e:
            print(f"添加聊天历史失败: {e}")
            return 0
    
    async def _invalidate_related_cache(self, cluster_name: str, world_name: str) -> None:
        """清除相关缓存"""
        try:
            # 清除聊天历史相关缓存
            recent_history_key = cache_manager._generate_cache_key(
                "get_recent_chat_history", self, cluster_name, world_name, 50
            )
            await cache_manager.delete("db", recent_history_key)
            
            # 清除数据库统计缓存
            stats_key = cache_manager._generate_cache_key("get_database_stats", self)
            await cache_manager.delete("db", stats_key)
            
            # 清除玩家列表缓存
            player_list_key = cache_manager._generate_cache_key("get_player_list", self)
            await cache_manager.delete("db", player_list_key)
            
            logger.debug(f"🗑️ 清除数据库缓存: {cluster_name}/{world_name}")
            
        except Exception as e:
            logger.warning(f"⚠️ 清除缓存失败: {e}")
    
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
    
    @cached(cache_type="db", memory_ttl=120, file_ttl=300)
    async def get_recent_chat_history(self, cluster_name: str, world_name: str, 
                                     limit: int = 50) -> List[Dict[str, Any]]:
        """获取最近的聊天历史 - 缓存2分钟内存，5分钟文件"""
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
    
    @cached(cache_type="db", memory_ttl=180, file_ttl=600) 
    async def get_player_chat_history(self, player_name: str, limit: int = 50) -> List[Dict[str, Any]]:
        """获取指定玩家的聊天历史 - 缓存3分钟内存，10分钟文件"""
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
    
    @cached(cache_type="db", memory_ttl=300, file_ttl=900)
    async def get_player_list(self) -> List[Dict[str, Any]]:
        """获取玩家列表 - 缓存5分钟内存，15分钟文件"""
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
    
    @cached(cache_type="db", memory_ttl=60, file_ttl=300) 
    async def get_database_stats(self) -> Dict[str, Any]:
        """获取数据库统计信息 - 缓存1分钟内存，5分钟文件"""
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
    
    async def auto_maintenance(self) -> Dict[str, Any]:
        """执行数据库自动维护"""
        try:
            logger.info("🔧 开始执行数据库自动维护...")
            
            # 执行自动压缩
            compress_result = await archive_manager.auto_compress_old_data()
            
            # 执行自动归档
            archive_result = await archive_manager.auto_archive_old_compressed_data()
            
            # 清理过期归档
            cleanup_result = await archive_manager.cleanup_old_archives()
            
            maintenance_summary = {
                "success": True,
                "compress_result": compress_result,
                "archive_result": archive_result,
                "cleanup_result": cleanup_result,
                "total_records_processed": (
                    compress_result.get('total_records_processed', 0) + 
                    archive_result.get('total_records_processed', 0)
                ),
                "total_space_saved_mb": (
                    compress_result.get('total_space_saved_mb', 0) + 
                    cleanup_result.get('space_freed_mb', 0)
                )
            }
            
            logger.info(f"✅ 数据库维护完成，处理记录: {maintenance_summary['total_records_processed']:,} 条")
            return maintenance_summary
            
        except Exception as e:
            logger.error(f"❌ 数据库自动维护失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_data_size_analysis(self) -> Dict[str, Any]:
        """获取数据大小分析（结合归档管理器）"""
        try:
            # 获取基础统计
            db_stats = await self.get_database_stats()
            
            # 获取详细分析
            archive_stats = await archive_manager.analyze_data_size()
            
            return {
                **db_stats,
                "detailed_analysis": archive_stats,
                "recommendations": self._generate_recommendations(db_stats, archive_stats)
            }
            
        except Exception as e:
            logger.error(f"❌ 获取数据分析失败: {e}")
            return {}
    
    def _generate_recommendations(self, db_stats: Dict, archive_stats: Dict) -> List[str]:
        """生成数据库优化建议"""
        recommendations = []
        
        total_messages = db_stats.get('total_messages', 0)
        file_size_mb = db_stats.get('file_size_mb', 0)
        
        # 基于记录数的建议
        if total_messages > 100000:
            recommendations.append("🔧 记录数较多，建议执行自动压缩")
        elif total_messages > 500000:
            recommendations.append("⚠️ 记录数过多，强烈建议执行数据维护")
        
        # 基于文件大小的建议
        if file_size_mb > 100:
            recommendations.append("💾 数据库文件较大，建议压缩和归档")
        elif file_size_mb > 500:
            recommendations.append("📦 数据库文件过大，建议立即执行维护")
        
        # 基于压缩机会的建议
        compression_opportunities = archive_stats.get('compression_opportunities', {})
        compressible = compression_opportunities.get('compressible_records', 0)
        archivable = compression_opportunities.get('archivable_records', 0)
        
        if compressible > 10000:
            recommendations.append("🗜️ 有大量数据可以压缩，建议执行自动压缩")
        
        if archivable > 50000:
            recommendations.append("📁 有大量数据可以归档，建议执行自动归档")
        
        if not recommendations:
            recommendations.append("✅ 数据库状态良好，暂无优化建议")
        
        return recommendations
    
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
                
                # 清除QQ消息相关缓存
                await self._invalidate_qq_message_cache(user_id)
                
                return True
        except Exception as e:
            print(f"添加QQ消息失败: {e}")
            return False
    
    async def _invalidate_qq_message_cache(self, user_id: int) -> None:
        """清除QQ消息相关缓存"""
        try:
            # 清除指定用户的消息缓存
            user_messages_key = cache_manager._generate_cache_key(
                "get_qq_messages", self, user_id, 50
            )
            await cache_manager.delete("db", user_messages_key)
            
            # 清除所有消息缓存
            all_messages_key = cache_manager._generate_cache_key(
                "get_qq_messages", self, None, 50
            )
            await cache_manager.delete("db", all_messages_key)
            
            logger.debug(f"🗑️ 清除QQ消息缓存: user_id={user_id}")
            
        except Exception as e:
            logger.warning(f"⚠️ 清除QQ消息缓存失败: {e}")
    
    @cached(cache_type="db", memory_ttl=90, file_ttl=300)
    async def get_qq_messages(self, user_id: int = None, limit: int = 50) -> List[Dict[str, Any]]:
        """获取QQ消息历史 - 缓存90秒内存，5分钟文件"""
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
            from .plugins.dmp_api import dmp_api
            
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