"""
数据库模块
统一的数据库连接管理和数据模型
"""

from nonebot import logger
from .connection import DatabaseManager
from .models import ChatHistoryModel, ItemWikiModel, ArchiveModel

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
            from ..item_data import ITEM_NAME_MAPPING
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
            from ..item_data import search_items as builtin_search
            results = builtin_search(keyword)[:limit]
            
            # 转换为数据库格式
            formatted_results = []
            for english_name, chinese_name in results:
                formatted_results.append({
                    'english_name': english_name,
                    'chinese_name': chinese_name,
                    'category': 'general',
                    'description': f'{chinese_name}（{english_name}）'
                })
            
            return formatted_results
        except Exception as e:
            logger.error(f"快速搜索物品失败: {e}")
            return []
    
    async def get_item_wiki_image(self, item_name: str):
        """获取物品Wiki图片（占位实现）"""
        try:
            logger.info(f"尝试获取Wiki图片: {item_name}")
            # 这里应该实现实际的Wiki图片获取逻辑
            # 目前返回None表示获取失败
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
    
    async def init_archive_tables(self):
        if not self._init_lock:
            await self.model.init()
            self._init_lock = True


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