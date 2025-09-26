"""
数据库模块
统一的数据库连接管理和数据模型
"""

import json
import zlib
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List

from nonebot import logger

from .connection import DatabaseManager
from .models import ArchiveModel, ChatHistoryModel, ItemWikiModel
from ..item_data import ITEM_NAME_MAPPING, search_items as builtin_search
from ..wiki_screenshot import screenshot_wiki_item

# 全局数据库管理器实例
db_manager = DatabaseManager()

# 创建兼容接口
class ChatHistoryDatabase:
    """聊天历史数据库管理器（兼容接口）"""
    
    def __init__(self, db_path=None):
        self.model = ChatHistoryModel(db_manager)
        self._init_lock = False
    
    async def init_database(self):
        if not self._init_lock:
            await self.model.init()
            self._init_lock = True
    
    def parse_chat_message(self, raw_message: str):
        return self.model.parse_chat_message(raw_message)
    
    async def add_chat_history(self, cluster_name: str, world_name: str, chat_logs):
        return await self.model.add_chat_history(cluster_name, world_name, chat_logs)
    
    async def get_recent_chat_history(self, cluster_name: str, world_name: str, limit: int = 50):
        return await self.model.get_recent_chat_history(cluster_name, world_name, limit)
    
    async def get_player_chat_history(self, player_name: str, limit: int = 50):
        return await self.model.get_player_chat_history(player_name, limit)
    
    async def add_qq_message(self, user_id: int, username: str, message_content: str):
        return await self.model.add_qq_message(user_id, username, message_content)
    
    async def cleanup_old_records(self, days: int = 30):
        return await self.model.cleanup_old_records(days)
    
    async def get_database_stats(self):
        return await db_manager.get_stats('chat_history')
    
    async def auto_maintenance(self):
        stats_before = await self.get_database_stats()
        deleted = await self.cleanup_old_records(30)
        stats_after = await self.get_database_stats()
        return {
            'success': True,
            'deleted_records': deleted,
            'stats_before': stats_before,
            'stats_after': stats_after
        }
    
    async def get_player_list(self):
        rows = await db_manager.fetchall('chat_history', 'SELECT * FROM player_info ORDER BY last_seen DESC')
        return [dict(row) for row in rows]
    
    async def get_qq_messages(self, user_id=None, limit: int = 50):
        if user_id:
            sql = 'SELECT * FROM qq_messages WHERE user_id = ? ORDER BY id DESC LIMIT ?'
            params = (user_id, limit)
        else:
            sql = 'SELECT * FROM qq_messages ORDER BY id DESC LIMIT ?'
            params = (limit,)
        rows = await db_manager.fetchall('chat_history', sql, params)
        return [dict(row) for row in rows]
    
    async def sync_chat_logs(self, cluster_name=None, world_name="World4", lines: int = 1000):
        return {'success': False, 'message': '此方法需要DMP API集成'}
    
    async def get_current_cluster(self):
        return "default"


class ItemWikiManager:
    """物品Wiki管理器（兼容接口）"""
    
    def __init__(self, db_path=None):
        self.model = ItemWikiModel(db_manager)
        self._init_lock = False
    
    async def init_database(self):
        if not self._init_lock:
            await self.model.init()
            await self._load_builtin_items()
            self._init_lock = True
    
    async def _load_builtin_items(self):
        """加载内置物品数据"""
        try:
            for english_name, chinese_name in ITEM_NAME_MAPPING.items():
                # 为兼容性，添加默认类别和描述
                await self.model.add_item(
                    english_name=english_name,
                    chinese_name=chinese_name,
                    category='general',  # 默认类别
                    description=f'{chinese_name}（{english_name}）'  # 默认描述
                )
        except Exception as e:
            logger.warning(f"加载内置物品数据时出错: {e}")
    
    async def search_items(self, keyword: str, limit: int = 10):
        return await self.model.search_items(keyword, limit)
    
    def search_items_quick(self, keyword: str, limit: int = 10):
        """快速搜索物品（同步方法，用于向下兼容）"""
        try:
            # 使用内置数据进行快速搜索
            results = builtin_search(keyword)[:limit]
            
            # 转换为数据库格式
            formatted_results = []
            for item in results:
                formatted_results.append({
                    'english_name': item['english_name'],
                    'chinese_name': item['chinese_name'],
                    'category': 'general',
                    'description': f"{item['chinese_name']}（{item['english_name']}）"
                })
            
            return formatted_results
        except Exception as e:
            logger.error(f"快速搜索物品失败: {e}")
            return []
    
    async def get_item_wiki_image(self, item_name: str):
        """获取物品Wiki图片"""
        try:
            logger.info(f"尝试获取Wiki图片: {item_name}")
            
            # 使用新的Wiki截图工具
            screenshot_bytes = await screenshot_wiki_item(item_name)
            
            if screenshot_bytes:
                logger.info(f"Wiki截图获取成功: {item_name}, 大小: {len(screenshot_bytes)} bytes")
                return screenshot_bytes
            else:
                logger.warning(f"Wiki截图获取失败: {item_name}")
                return None
                
        except Exception as e:
            logger.error(f"获取Wiki图片失败: {e}")
            return None
    
    async def reload_items_data(self):
        """重载物品数据"""
        try:
            # 重新加载内置物品数据
            await self._load_builtin_items()
            logger.info("物品数据重载成功")
            return True
        except Exception as e:
            logger.error(f"重载物品数据失败: {e}")
            return False


class DataArchiveManager:
    """数据归档管理器（兼容接口）"""
    
    def __init__(self, db_path=None):
        self.model = ArchiveModel(db_manager)
        self._init_lock = False
        self.archive_dir = db_manager.data_dir / "archives"
        self.archive_dir.mkdir(parents=True, exist_ok=True)
    
    async def init_archive_tables(self):
        if not self._init_lock:
            await self.model.init()
            self._init_lock = True

    async def auto_compress_old_data(self, days: int = 14, batch_size: int = 500) -> Dict[str, Any]:
        """自动压缩并归档指定天数之前的数据"""
        await self.init_archive_tables()

        retain_days = max(days, 1)
        batch_size = max(100, min(batch_size, 2000))

        summary = {
            "success": False,
            "total_records_processed": 0,
            "archive_groups_created": 0,
            "raw_size_mb": 0.0,
            "compressed_size_mb": 0.0,
            "total_space_saved_mb": 0.0,
        }

        try:
            while True:
                rows = await db_manager.fetchall(
                    'chat_history',
                    f"""
                    SELECT id, cluster_name, world_name, timestamp, message_type,
                           player_name, player_id, message_content, raw_message, created_at
                    FROM chat_history
                    WHERE created_at < datetime('now', '-{retain_days} days')
                    ORDER BY created_at
                    LIMIT {batch_size}
                    """,
                )

                if not rows:
                    break

                grouped = defaultdict(list)
                for row in rows:
                    row_dict = dict(row)
                    created_at = row_dict.get("created_at") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    archive_date = created_at[:10]
                    cluster = row_dict.get("cluster_name", "default")
                    world = row_dict.get("world_name", "World")
                    grouped[(cluster, world, archive_date)].append(row_dict)

                async with db_manager.transaction('chat_history') as conn:
                    ids_to_delete: List[int] = []

                    for (cluster, world, archive_date), items in grouped.items():
                        payload = [
                            {
                                "id": item.get("id"),
                                "timestamp": item.get("timestamp"),
                                "message_type": item.get("message_type"),
                                "player_name": item.get("player_name"),
                                "player_id": item.get("player_id"),
                                "message_content": item.get("message_content"),
                                "raw_message": item.get("raw_message"),
                                "created_at": item.get("created_at"),
                            }
                            for item in items
                        ]

                        raw_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                        compressed_bytes = zlib.compress(raw_bytes)

                        await conn.execute(
                            """
                            INSERT INTO archived_chat_history (
                                original_id, cluster_name, world_name, archive_date,
                                data_blob, compression_type, record_count
                            ) VALUES (?, ?, ?, ?, ?, 'zlib', ?)
                            """,
                            (
                                items[0].get("id"),
                                cluster,
                                world,
                                archive_date,
                                compressed_bytes,
                                len(items),
                            ),
                        )

                        summary["archive_groups_created"] += 1
                        summary["raw_size_mb"] += len(raw_bytes) / (1024 * 1024)
                        summary["compressed_size_mb"] += len(compressed_bytes) / (1024 * 1024)

                        ids_to_delete.extend(item.get("id") for item in items if item.get("id"))

                    # 删除已归档的数据
                    if ids_to_delete:
                        for index in range(0, len(ids_to_delete), 500):
                            chunk = ids_to_delete[index:index + 500]
                            placeholders = ",".join("?" for _ in chunk)
                            await conn.execute(
                                f"DELETE FROM chat_history WHERE id IN ({placeholders})",
                                chunk,
                            )

                summary["total_records_processed"] += len(rows)

            if summary["raw_size_mb"] > summary["compressed_size_mb"]:
                summary["total_space_saved_mb"] = summary["raw_size_mb"] - summary["compressed_size_mb"]

            summary["success"] = summary["total_records_processed"] > 0
            if not summary["success"] and "error" not in summary:
                summary["message"] = "没有符合条件的历史记录"

        except Exception as error:
            logger.error(f"自动压缩聊天数据失败: {error}")
            summary["error"] = str(error)

        return summary

    async def get_archive_summary(self, limit: int = 20) -> Dict[str, Any]:
        """获取最近的归档摘要信息"""
        await self.init_archive_tables()

        limit = max(1, min(limit, 100))
        rows = await db_manager.fetchall(
            'chat_history',
            f"""
            SELECT cluster_name, world_name, archive_date, record_count,
                   LENGTH(data_blob) AS payload_size
            FROM archived_chat_history
            ORDER BY archive_date DESC, id DESC
            LIMIT {limit}
            """,
        )

        total_records = 0
        total_bytes = 0
        archives: List[Dict[str, Any]] = []

        for row in rows:
            row_dict = dict(row)
            record_count = row_dict.get("record_count", 0)
            payload_size = row_dict.get("payload_size", 0)
            total_records += record_count
            total_bytes += payload_size
            archives.append(
                {
                    "cluster_name": row_dict.get("cluster_name", ""),
                    "world_name": row_dict.get("world_name", ""),
                    "archive_date": row_dict.get("archive_date", ""),
                    "record_count": record_count,
                    "size_kb": round(payload_size / 1024, 2),
                }
            )

        return {
            "total_records": total_records,
            "total_size_mb": round(total_bytes / (1024 * 1024), 2),
            "recent_archives": archives,
        }

    async def purge_archives(self, older_than_days: int = 180) -> Dict[str, Any]:
        """清理过期的归档数据"""
        await self.init_archive_tables()
        retain_days = max(older_than_days, 1)
        cursor = await db_manager.execute(
            'chat_history',
            f"DELETE FROM archived_chat_history WHERE archive_date < date('now', '-{retain_days} days')",
        )
        deleted = cursor.rowcount if cursor else 0
        logger.info(f"🧹 已清理 {deleted} 条超过 {retain_days} 天的归档记录")
        return {"deleted": deleted, "retained_days": retain_days}


# 全局实例（保持兼容性）
chat_history_db = ChatHistoryDatabase()
item_wiki_manager = ItemWikiManager()  
archive_manager = DataArchiveManager()

# 导出主要接口
__all__ = [
    'DatabaseManager',
    'ChatHistoryModel', 
    'ItemWikiModel',
    'ArchiveModel',
    'db_manager',
    'ChatHistoryDatabase',
    'ItemWikiManager',
    'DataArchiveManager',
    'chat_history_db',
    'item_wiki_manager',
    'archive_manager'
]
