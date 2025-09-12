"""
缓存管理器兼容层
将旧的复杂缓存接口适配到新的简化缓存系统
"""

from .simple_cache import SimpleCache, get_cache


# 为了兼容性，提供旧的接口
class CacheManager:
    """兼容层：将旧的缓存接口映射到简化缓存"""
    
    def __init__(self):
        self.cache = get_cache()
    
    @property
    def cache_dir(self):
        return self.cache.cache_dir
    
    async def get(self, cache_type: str, key: str, default=None, **kwargs):
        """兼容旧的get接口"""
        full_key = f"{cache_type}_{key}"
        return await self.cache.get(full_key, default)
    
    async def set(self, cache_type: str, key: str, value, memory_ttl=None, file_ttl=None, **kwargs):
        """兼容旧的set接口"""
        full_key = f"{cache_type}_{key}"
        ttl = memory_ttl or file_ttl or 300
        await self.cache.set(full_key, value, ttl)
    
    async def delete(self, cache_type: str, key: str):
        """兼容旧的delete接口"""
        full_key = f"{cache_type}_{key}"
        await self.cache.delete(full_key)
    
    async def clear(self, cache_type=None):
        """兼容旧的clear接口"""
        await self.cache.clear()
    
    def get_stats(self):
        """兼容旧的get_stats接口"""
        stats = self.cache.get_stats()
        # 转换为旧格式
        return {
            'total_requests': stats.get('hits', 0) + stats.get('misses', 0),
            'cache_hits': stats.get('hits', 0),
            'hit_rate': stats.get('hit_rate', 0),
            'memory_entries': stats.get('memory_items', 0),
            'file_entries': stats.get('file_items', 0),
            'avg_response_time': 0,
            'last_cleanup': '已简化'
        }
    
    def clear_all_caches(self):
        """同步清理接口（兼容）"""
        import asyncio
        old_stats = self.cache.get_stats()
        asyncio.create_task(self.cache.clear())
        return old_stats.get('memory_items', 0) + old_stats.get('file_items', 0)


# 全局兼容实例
cache_manager = CacheManager()


# 装饰器兼容
def cached(cache_type="api", memory_ttl=300, file_ttl=600, **kwargs):
    """兼容旧的cached装饰器"""
    from .simple_cache import cached as simple_cached
    ttl = memory_ttl or file_ttl or 300
    key_prefix = cache_type
    return simple_cached(ttl_seconds=ttl, key_prefix=key_prefix)