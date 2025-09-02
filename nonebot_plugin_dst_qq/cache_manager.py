"""
多级缓存管理系统

使用 LocalStore 插件实现标准化的缓存存储：
- 配置缓存: 长期有效，存储用户配置和插件设置
- 数据缓存: 中期有效，存储API调用结果和查询结果  
- 内存缓存: 短期有效，存储频繁访问的数据

缓存策略：
- LRU: 内存缓存使用最近最少使用策略
- TTL: 所有缓存支持生存时间
- 分级存储: 内存 -> 文件缓存 -> 源数据
"""

import json
import pickle
import asyncio
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Callable, Awaitable
from functools import wraps
from collections import OrderedDict
from nonebot.log import logger

# Lazy import localstore
def _get_localstore():
    """Lazy import and initialization of localstore"""
    try:
        from nonebot import require
        require("nonebot_plugin_localstore")
        import nonebot_plugin_localstore as store
        return store
    except Exception:
        # Fallback to None if localstore fails
        return None


class LRUCache:
    """LRU缓存实现"""
    
    def __init__(self, max_size: int = 128):
        self.max_size = max_size
        self.cache: OrderedDict = OrderedDict()
        self.ttl_data: Dict[str, datetime] = {}
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取缓存值"""
        # 检查是否过期
        if key in self.ttl_data:
            if datetime.now() > self.ttl_data[key]:
                self._remove(key)
                return default
        
        if key in self.cache:
            # 移到末尾（最近使用）
            self.cache.move_to_end(key)
            return self.cache[key]
        
        return default
    
    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """设置缓存值"""
        if key in self.cache:
            # 更新现有值
            self.cache.move_to_end(key)
        else:
            # 检查容量限制
            if len(self.cache) >= self.max_size:
                # 移除最旧的项
                oldest_key = next(iter(self.cache))
                self._remove(oldest_key)
        
        self.cache[key] = value
        
        # 设置TTL
        if ttl_seconds:
            self.ttl_data[key] = datetime.now() + timedelta(seconds=ttl_seconds)
    
    def _remove(self, key: str) -> None:
        """移除缓存项"""
        self.cache.pop(key, None)
        self.ttl_data.pop(key, None)
    
    def clear(self) -> None:
        """清空缓存"""
        self.cache.clear()
        self.ttl_data.clear()
    
    def size(self) -> int:
        """获取缓存大小"""
        return len(self.cache)
    
    def keys(self) -> List[str]:
        """获取所有键"""
        return list(self.cache.keys())


class CacheManager:
    """多级缓存管理器"""
    
    def __init__(self, 
                 memory_cache_size: int = 256,
                 default_memory_ttl: int = 300,    # 5分钟
                 default_file_ttl: int = 1800,     # 30分钟
                 default_config_ttl: int = 3600):  # 1小时
        
        # 初始化存储目录
        store = _get_localstore()
        if store:
            try:
                self.cache_dir = store.get_plugin_cache_dir()
                self.config_dir = store.get_plugin_config_dir()
                self.data_dir = store.get_plugin_data_dir()
            except Exception:
                # Fallback to plugin directory
                plugin_dir = Path(__file__).parent
                self.cache_dir = plugin_dir / "cache"
                self.config_dir = plugin_dir / "config"
                self.data_dir = plugin_dir / "data"
        else:
            # Fallback to plugin directory
            plugin_dir = Path(__file__).parent
            self.cache_dir = plugin_dir / "cache"
            self.config_dir = plugin_dir / "config"
            self.data_dir = plugin_dir / "data"
        
        # 创建子目录
        self.api_cache_dir = self.cache_dir / "api"
        self.db_cache_dir = self.cache_dir / "database" 
        self.config_cache_dir = self.config_dir / "cache"
        
        # 确保目录存在
        for directory in [self.api_cache_dir, self.db_cache_dir, self.config_cache_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # 内存缓存
        self.memory_cache = LRUCache(memory_cache_size)
        
        # 缓存配置
        self.default_memory_ttl = default_memory_ttl
        self.default_file_ttl = default_file_ttl
        self.default_config_ttl = default_config_ttl
        
        # 缓存统计
        self.stats = {
            "memory_hits": 0,
            "file_hits": 0,
            "misses": 0,
            "total_requests": 0
        }
        
        logger.info("🗄️ 多级缓存管理器初始化完成")
        logger.info(f"📁 API缓存目录: {self.api_cache_dir}")
        logger.info(f"📁 数据库缓存目录: {self.db_cache_dir}")
        logger.info(f"📁 配置缓存目录: {self.config_cache_dir}")
    
    def _generate_cache_key(self, prefix: str, *args, **kwargs) -> str:
        """生成缓存键"""
        # 创建唯一标识符
        key_data = {
            "prefix": prefix,
            "args": args,
            "kwargs": sorted(kwargs.items())
        }
        
        # 使用MD5生成短键名
        key_str = json.dumps(key_data, sort_keys=True, default=str)
        hash_key = hashlib.md5(key_str.encode()).hexdigest()[:16]
        
        return f"{prefix}_{hash_key}"
    
    def _get_file_cache_path(self, cache_type: str, key: str) -> Path:
        """获取文件缓存路径"""
        if cache_type == "api":
            return self.api_cache_dir / f"{key}.cache"
        elif cache_type == "db":
            return self.db_cache_dir / f"{key}.cache"  
        elif cache_type == "config":
            return self.config_cache_dir / f"{key}.cache"
        else:
            return self.cache_dir / f"{key}.cache"
    
    async def get(self, 
                  cache_type: str,
                  key: str, 
                  default: Any = None,
                  memory_ttl: Optional[int] = None,
                  file_ttl: Optional[int] = None) -> Any:
        """
        获取缓存数据
        
        Args:
            cache_type: 缓存类型 (api/db/config)
            key: 缓存键
            default: 默认值
            memory_ttl: 内存缓存TTL
            file_ttl: 文件缓存TTL
        """
        self.stats["total_requests"] += 1
        
        # 1. 尝试从内存缓存获取
        memory_value = self.memory_cache.get(key)
        if memory_value is not None:
            self.stats["memory_hits"] += 1
            logger.debug(f"🧠 内存缓存命中: {key}")
            return memory_value
        
        # 2. 尝试从文件缓存获取
        file_path = self._get_file_cache_path(cache_type, key)
        if file_path.exists():
            try:
                # 读取缓存文件
                with open(file_path, 'rb') as f:
                    cache_data = pickle.load(f)
                
                # 检查是否过期
                if cache_data.get("expires_at"):
                    expires_at = datetime.fromisoformat(cache_data["expires_at"])
                    if datetime.now() > expires_at:
                        # 过期，删除文件
                        file_path.unlink()
                        logger.debug(f"🗑️ 文件缓存过期已删除: {key}")
                    else:
                        # 未过期，加载到内存并返回
                        value = cache_data["data"]
                        
                        # 重新加载到内存缓存
                        ttl = memory_ttl or self.default_memory_ttl
                        self.memory_cache.set(key, value, ttl)
                        
                        self.stats["file_hits"] += 1
                        logger.debug(f"📄 文件缓存命中: {key}")
                        return value
                else:
                    # 没有过期时间，直接使用
                    value = cache_data["data"]
                    ttl = memory_ttl or self.default_memory_ttl
                    self.memory_cache.set(key, value, ttl)
                    
                    self.stats["file_hits"] += 1
                    logger.debug(f"📄 文件缓存命中（无TTL）: {key}")
                    return value
                    
            except Exception as e:
                logger.warning(f"⚠️ 读取文件缓存失败: {key}, 错误: {e}")
                # 如果是模块导入错误（通常是因为路径变更），则清空对应类型的所有缓存
                if "No module named" in str(e):
                    logger.warning(f"🧹 检测到模块路径变更，清空 {cache_type} 类型缓存")
                    await self._clear_cache_type_silent(cache_type)
                else:
                    # 删除损坏的缓存文件
                    try:
                        file_path.unlink()
                    except:
                        pass
        
        # 3. 缓存未命中
        self.stats["misses"] += 1
        logger.debug(f"❌ 缓存未命中: {key}")
        return default
    
    async def set(self, 
                  cache_type: str,
                  key: str, 
                  value: Any,
                  memory_ttl: Optional[int] = None,
                  file_ttl: Optional[int] = None,
                  persist_to_file: bool = True) -> None:
        """
        设置缓存数据
        
        Args:
            cache_type: 缓存类型 (api/db/config)
            key: 缓存键
            value: 缓存值
            memory_ttl: 内存缓存TTL
            file_ttl: 文件缓存TTL  
            persist_to_file: 是否持久化到文件
        """
        # 1. 设置内存缓存
        ttl = memory_ttl or self.default_memory_ttl
        self.memory_cache.set(key, value, ttl)
        logger.debug(f"🧠 内存缓存已设置: {key}, TTL: {ttl}s")
        
        # 2. 设置文件缓存
        if persist_to_file:
            try:
                file_path = self._get_file_cache_path(cache_type, key)
                
                # 准备缓存数据
                cache_data = {"data": value}
                
                # 设置过期时间
                if file_ttl:
                    expires_at = datetime.now() + timedelta(seconds=file_ttl)
                    cache_data["expires_at"] = expires_at.isoformat()
                elif cache_type == "config":
                    expires_at = datetime.now() + timedelta(seconds=self.default_config_ttl)
                    cache_data["expires_at"] = expires_at.isoformat()
                elif cache_type in ("api", "db"):
                    expires_at = datetime.now() + timedelta(seconds=self.default_file_ttl)
                    cache_data["expires_at"] = expires_at.isoformat()
                
                # 写入文件
                with open(file_path, 'wb') as f:
                    pickle.dump(cache_data, f)
                
                logger.debug(f"📄 文件缓存已设置: {key}")
                
            except Exception as e:
                logger.warning(f"⚠️ 设置文件缓存失败: {key}, 错误: {e}")
    
    async def delete(self, cache_type: str, key: str) -> None:
        """删除缓存"""
        # 删除内存缓存
        self.memory_cache._remove(key)
        
        # 删除文件缓存
        file_path = self._get_file_cache_path(cache_type, key)
        if file_path.exists():
            try:
                file_path.unlink()
                logger.debug(f"🗑️ 缓存已删除: {key}")
            except Exception as e:
                logger.warning(f"⚠️ 删除文件缓存失败: {key}, 错误: {e}")
    
    async def _clear_cache_type_silent(self, cache_type: str) -> None:
        """静默清空指定类型的缓存（用于错误恢复）"""
        try:
            # 清空指定类型的文件缓存
            cache_dir = self._get_file_cache_path(cache_type, "").parent
            for cache_file in cache_dir.glob("*.cache"):
                try:
                    cache_file.unlink()
                except:
                    pass  # 静默忽略错误
        except:
            pass  # 静默忽略所有错误
    
    async def clear(self, cache_type: Optional[str] = None) -> None:
        """清空缓存"""
        if cache_type is None:
            # 清空所有缓存
            self.memory_cache.clear()
            
            # 清空所有文件缓存目录
            for directory in [self.api_cache_dir, self.db_cache_dir, self.config_cache_dir]:
                for cache_file in directory.glob("*.cache"):
                    try:
                        cache_file.unlink()
                    except Exception as e:
                        logger.warning(f"⚠️ 删除缓存文件失败: {cache_file}, 错误: {e}")
            
            logger.info("🗑️ 所有缓存已清空")
        else:
            # 清空指定类型的文件缓存
            cache_dir = self._get_file_cache_path(cache_type, "").parent
            for cache_file in cache_dir.glob("*.cache"):
                try:
                    cache_file.unlink()
                except Exception as e:
                    logger.warning(f"⚠️ 删除缓存文件失败: {cache_file}, 错误: {e}")
            
            logger.info(f"🗑️ {cache_type} 类型缓存已清空")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        total = self.stats["total_requests"]
        if total > 0:
            hit_rate = (self.stats["memory_hits"] + self.stats["file_hits"]) / total
            memory_hit_rate = self.stats["memory_hits"] / total
            file_hit_rate = self.stats["file_hits"] / total
        else:
            hit_rate = memory_hit_rate = file_hit_rate = 0.0
        
        return {
            **self.stats,
            "hit_rate": hit_rate,
            "memory_hit_rate": memory_hit_rate,
            "file_hit_rate": file_hit_rate,
            "memory_cache_size": self.memory_cache.size(),
            "memory_cache_keys": self.memory_cache.keys()
        }


# 缓存装饰器
def cached(cache_type: str = "api", 
           memory_ttl: Optional[int] = None,
           file_ttl: Optional[int] = None,
           key_generator: Optional[Callable] = None,
           persist_to_file: bool = True):
    """
    缓存装饰器
    
    Args:
        cache_type: 缓存类型 (api/db/config)
        memory_ttl: 内存缓存TTL
        file_ttl: 文件缓存TTL
        key_generator: 自定义键生成器
        persist_to_file: 是否持久化到文件
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 生成缓存键
            if key_generator:
                cache_key = key_generator(*args, **kwargs)
            else:
                cache_key = cache_manager._generate_cache_key(func.__name__, *args, **kwargs)
            
            # 尝试从缓存获取
            cached_result = await cache_manager.get(
                cache_type=cache_type,
                key=cache_key,
                memory_ttl=memory_ttl,
                file_ttl=file_ttl
            )
            
            if cached_result is not None:
                return cached_result
            
            # 执行原函数
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            # 存储到缓存
            if result is not None:  # 只缓存非空结果
                await cache_manager.set(
                    cache_type=cache_type,
                    key=cache_key,
                    value=result,
                    memory_ttl=memory_ttl,
                    file_ttl=file_ttl,
                    persist_to_file=persist_to_file
                )
            
            return result
        
        return wrapper
    return decorator


# 创建全局缓存管理器实例
cache_manager = CacheManager()


# 便捷函数
async def get_api_cache(key: str, default: Any = None) -> Any:
    """获取API缓存"""
    return await cache_manager.get("api", key, default)


async def set_api_cache(key: str, value: Any, ttl: int = 300) -> None:
    """设置API缓存"""
    await cache_manager.set("api", key, value, memory_ttl=ttl, file_ttl=ttl*2)


async def get_db_cache(key: str, default: Any = None) -> Any:
    """获取数据库缓存"""
    return await cache_manager.get("db", key, default)


async def set_db_cache(key: str, value: Any, ttl: int = 600) -> None:
    """设置数据库缓存"""
    await cache_manager.set("db", key, value, memory_ttl=ttl, file_ttl=ttl*3)


async def get_config_cache(key: str, default: Any = None) -> Any:
    """获取配置缓存"""
    return await cache_manager.get("config", key, default)


async def set_config_cache(key: str, value: Any, ttl: int = 3600) -> None:
    """设置配置缓存"""
    await cache_manager.set("config", key, value, memory_ttl=ttl, file_ttl=ttl*2)
