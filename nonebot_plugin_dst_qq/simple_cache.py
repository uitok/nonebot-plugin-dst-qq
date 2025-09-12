"""
简化版缓存管理系统
移除复杂功能，保留核心缓存能力
"""

import json
import pickle
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional, Callable
from functools import wraps
from nonebot import logger


def _get_cache_dir() -> Path:
    """获取缓存目录"""
    try:
        from nonebot import require
        require("nonebot_plugin_localstore")
        import nonebot_plugin_localstore as store
        cache_dir = store.get_plugin_cache_dir()
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir
    except Exception as e:
        # 备用方案：使用当前目录下的cache文件夹
        cache_dir = Path("cache")
        cache_dir.mkdir(parents=True, exist_ok=True)
        logger.warning(f"使用备用缓存目录: {cache_dir}")
        return cache_dir


class SimpleCache:
    """简化版缓存管理器"""
    
    def __init__(self):
        self.cache_dir = _get_cache_dir()
        self.memory_cache: Dict[str, tuple] = {}  # (value, expires_at)
        self.stats = {"hits": 0, "misses": 0}
        logger.info(f"📦 简化缓存系统初始化完成: {self.cache_dir}")
    
    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """生成缓存键"""
        key_data = f"{prefix}:{args}:{sorted(kwargs.items())}"
        return hashlib.md5(key_data.encode()).hexdigest()[:12]
    
    def _is_expired(self, expires_at: Optional[datetime]) -> bool:
        """检查是否过期"""
        return expires_at is not None and datetime.now() > expires_at
    
    async def get(self, key: str, default: Any = None) -> Any:
        """获取缓存"""
        self.stats["hits"] += 1 if key in self.memory_cache else 0
        self.stats["misses"] += 1 if key not in self.memory_cache else 0
        
        # 1. 检查内存缓存
        if key in self.memory_cache:
            value, expires_at = self.memory_cache[key]
            if not self._is_expired(expires_at):
                logger.debug(f"🧠 内存缓存命中: {key}")
                return value
            else:
                del self.memory_cache[key]
        
        # 2. 检查文件缓存
        cache_file = self.cache_dir / f"{key}.cache"
        if cache_file.exists():
            try:
                with open(cache_file, 'rb') as f:
                    cache_data = pickle.load(f)
                
                value = cache_data['value']
                expires_at = cache_data.get('expires_at')
                
                if not self._is_expired(expires_at):
                    # 加载到内存缓存
                    self.memory_cache[key] = (value, expires_at)
                    logger.debug(f"📄 文件缓存命中: {key}")
                    return value
                else:
                    # 删除过期文件
                    cache_file.unlink(missing_ok=True)
            except Exception as e:
                logger.error(f"读取缓存文件失败: {e}")
                cache_file.unlink(missing_ok=True)
        
        return default
    
    async def set(self, key: str, value: Any, ttl_seconds: int = 300) -> None:
        """设置缓存"""
        expires_at = datetime.now() + timedelta(seconds=ttl_seconds)
        
        # 设置内存缓存
        self.memory_cache[key] = (value, expires_at)
        
        # 设置文件缓存
        cache_file = self.cache_dir / f"{key}.cache"
        try:
            cache_data = {
                'value': value,
                'expires_at': expires_at,
                'created_at': datetime.now()
            }
            with open(cache_file, 'wb') as f:
                pickle.dump(cache_data, f)
            logger.debug(f"💾 缓存已设置: {key}, TTL: {ttl_seconds}s")
        except Exception as e:
            logger.error(f"写入缓存文件失败: {e}")
    
    async def delete(self, key: str) -> None:
        """删除缓存"""
        # 删除内存缓存
        self.memory_cache.pop(key, None)
        
        # 删除文件缓存
        cache_file = self.cache_dir / f"{key}.cache"
        cache_file.unlink(missing_ok=True)
    
    async def clear(self) -> None:
        """清空所有缓存"""
        self.memory_cache.clear()
        
        # 删除所有缓存文件
        for cache_file in self.cache_dir.glob("*.cache"):
            cache_file.unlink(missing_ok=True)
        
        logger.info("🗑️ 所有缓存已清空")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        total = self.stats["hits"] + self.stats["misses"]
        hit_rate = (self.stats["hits"] / total) if total > 0 else 0
        
        return {
            "memory_items": len(self.memory_cache),
            "file_items": len(list(self.cache_dir.glob("*.cache"))),
            "hit_rate": hit_rate,
            **self.stats
        }


# 全局缓存实例
_cache = None

def get_cache() -> SimpleCache:
    """获取缓存实例"""
    global _cache
    if _cache is None:
        _cache = SimpleCache()
    return _cache


def cached(ttl_seconds: int = 300, key_prefix: str = ""):
    """
    简化版缓存装饰器
    
    Args:
        ttl_seconds: 缓存时间（秒）
        key_prefix: 缓存键前缀
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache = get_cache()
            
            # 生成缓存键
            func_name = f"{func.__module__}.{func.__name__}"
            cache_key = cache._generate_key(key_prefix or func_name, *args, **kwargs)
            
            # 尝试从缓存获取
            cached_result = await cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # 执行函数并缓存结果
            result = await func(*args, **kwargs)
            if result is not None:
                await cache.set(cache_key, result, ttl_seconds)
            
            return result
        
        return wrapper
    return decorator


# 便利函数
async def get_cached(key: str, default: Any = None) -> Any:
    """获取缓存值"""
    return await get_cache().get(key, default)

async def set_cached(key: str, value: Any, ttl_seconds: int = 300) -> None:
    """设置缓存值"""
    await get_cache().set(key, value, ttl_seconds)

async def clear_cache() -> None:
    """清空缓存"""
    await get_cache().clear()