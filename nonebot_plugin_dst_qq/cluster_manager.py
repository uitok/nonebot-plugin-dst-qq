"""
动态集群管理器
提供集群的动态获取、缓存和管理功能
"""

import asyncio
from typing import Dict, List, Optional, Any, TYPE_CHECKING
from datetime import datetime, timedelta
import json

# 避免循环导入，在运行时动态导入
if TYPE_CHECKING:
    from .plugins.dmp_api import DMPAPI

from nonebot import logger
from .simple_cache import SimpleCache


class ClusterManager:
    """动态集群管理器"""
    
    def __init__(self, dmp_api: "DMPAPI", cache: SimpleCache):
        self.dmp_api = dmp_api
        self.cache = cache
        self._clusters_cache_key = "available_clusters"
        self._current_cluster_key = "current_cluster"
        self._cache_ttl = 300  # 5分钟缓存
        self._lock = asyncio.Lock()
    
    async def get_available_clusters(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """获取可用的集群列表
        
        Args:
            force_refresh: 是否强制刷新缓存
            
        Returns:
            集群列表，每个集群包含 name, display_name, status 等信息
        """
        async with self._lock:
            # 尝试从缓存获取
            if not force_refresh:
                cached_clusters = await self.cache.get(self._clusters_cache_key)
                if cached_clusters:
                    logger.debug(f"从缓存获取到 {len(cached_clusters)} 个集群")
                    return cached_clusters
            
            # 从API获取
            try:
                logger.info("正在从服务器获取集群列表...")
                response = await self.dmp_api.get_available_clusters()
                
                if response and response.success:
                    # response.data 直接包含集群列表
                    clusters = response.data if isinstance(response.data, list) else []
                    
                    if clusters:
                        # 处理集群数据，确保包含必要字段
                        processed_clusters = []
                        for cluster in clusters:
                            # 根据实际API响应格式处理集群数据
                            cluster_name = cluster.get("clusterName", cluster.get("name", ""))
                            processed_cluster = {
                                "name": cluster_name,
                                "display_name": cluster.get("clusterDisplayName", cluster.get("display_name", cluster_name)),
                                "status": cluster.get("status", "unknown"),
                                "player_count": cluster.get("player_count", 0),
                                "max_players": cluster.get("max_players", 0),
                                "description": cluster.get("description", ""),
                                "last_updated": datetime.now().isoformat()
                            }
                            processed_clusters.append(processed_cluster)
                        
                        # 缓存结果
                        await self.cache.set(
                            self._clusters_cache_key, 
                            processed_clusters, 
                            self._cache_ttl
                        )
                        
                        logger.info(f"成功获取并缓存了 {len(processed_clusters)} 个集群")
                        return processed_clusters
                    else:
                        logger.warning("服务器返回的集群列表为空")
                        return []
                else:
                    error_msg = response.message if response else "API响应为空"
                    logger.error(f"获取集群列表失败: {error_msg}")
                    return []
                    
            except Exception as e:
                logger.error(f"获取集群列表时发生异常: {e}")
                return []
    
    async def get_cluster_names(self, force_refresh: bool = False) -> List[str]:
        """获取集群名称列表
        
        Args:
            force_refresh: 是否强制刷新缓存
            
        Returns:
            集群名称列表
        """
        clusters = await self.get_available_clusters(force_refresh)
        return [cluster["name"] for cluster in clusters if cluster.get("name")]
    
    async def get_default_cluster(self) -> Optional[str]:
        """获取默认集群名称（第一个可用的集群）
        
        Returns:
            默认集群名称，如果没有可用集群则返回None
        """
        cluster_names = await self.get_cluster_names()
        if cluster_names:
            default_cluster = cluster_names[0]
            logger.info(f"使用默认集群: {default_cluster}")
            return default_cluster
        else:
            logger.warning("没有可用的集群")
            return None
    
    async def set_current_cluster(self, cluster_name: str, user_id: str) -> bool:
        """设置当前使用的集群
        
        Args:
            cluster_name: 集群名称
            user_id: 设置的用户ID
            
        Returns:
            是否设置成功
        """
        # 验证集群是否存在
        available_clusters = await self.get_cluster_names()
        if cluster_name not in available_clusters:
            logger.warning(f"尝试设置不存在的集群: {cluster_name}")
            return False
        
        # 清理相关缓存，让新集群立即生效
        await self._clear_cluster_related_cache()

        # 设置当前集群
        cluster_info = {
            "name": cluster_name,
            "set_by": user_id,
            "set_at": datetime.now().isoformat()
        }

        await self.cache.set(self._current_cluster_key, cluster_info, 3600 * 24)  # 24小时缓存

        logger.info(f"用户 {user_id} 设置当前集群为: {cluster_name}，已清理相关缓存")
        return True
    
    async def get_current_cluster(self) -> Optional[str]:
        """获取当前设置的集群名称
        
        Returns:
            当前集群名称，如果未设置则返回默认集群
        """
        # 尝试获取用户设置的集群
        current_cluster_info = await self.cache.get(self._current_cluster_key)
        if current_cluster_info and isinstance(current_cluster_info, dict):
            cluster_name = current_cluster_info.get("name")
            
            # 验证该集群是否仍然可用
            available_clusters = await self.get_cluster_names()
            if cluster_name in available_clusters:
                return cluster_name
            else:
                logger.warning(f"当前设置的集群 {cluster_name} 不再可用，将使用默认集群")
                # 清除无效的设置
                await self.cache.delete(self._current_cluster_key)
        
        # 返回默认集群
        return await self.get_default_cluster()
    
    async def _clear_cluster_related_cache(self) -> None:
        """清理集群相关的缓存，确保集群切换后立即生效"""
        try:
            await self.cache.clear()
            logger.debug("已清理缓存（集群切换触发）")
            
        except Exception as e:
            logger.warning(f"清理集群相关缓存失败: {e}")
    
    async def get_cluster_info(self, cluster_name: str) -> Optional[Dict[str, Any]]:
        """获取特定集群的详细信息
        
        Args:
            cluster_name: 集群名称
            
        Returns:
            集群信息字典，如果不存在则返回None
        """
        clusters = await self.get_available_clusters()
        for cluster in clusters:
            if cluster.get("name") == cluster_name:
                return cluster
        return None
    
    async def get_cluster_status_summary(self) -> str:
        """获取集群状态摘要
        
        Returns:
            格式化的集群状态摘要字符串
        """
        clusters = await self.get_available_clusters()
        current_cluster = await self.get_current_cluster()
        
        if not clusters:
            return "❌ 暂无可用集群"
        
        summary_lines = []
        summary_lines.append(f"📊 集群状态 (共{len(clusters)}个):")
        summary_lines.append("")
        
        for cluster in clusters:
            name = cluster.get("name", "未知")
            display_name = cluster.get("display_name", name)
            status = cluster.get("status", "unknown")
            player_count = cluster.get("player_count", 0)
            max_players = cluster.get("max_players", 0)
            
            # 状态图标
            status_icon = "🟢" if status == "online" else "🔴" if status == "offline" else "🟡"
            
            # 当前集群标记
            current_mark = " ⭐" if name == current_cluster else ""
            
            # 玩家信息
            player_info = f"{player_count}/{max_players}" if max_players > 0 else str(player_count)
            
            summary_lines.append(f"{status_icon} {display_name} ({name}){current_mark}")
            summary_lines.append(f"   玩家: {player_info}")
            summary_lines.append("")
        
        if current_cluster:
            summary_lines.append(f"当前使用集群: {current_cluster} ⭐")
        else:
            summary_lines.append("⚠️ 未设置当前集群")
        
        return "\n".join(summary_lines)
    
    async def refresh_clusters(self) -> bool:
        """刷新集群列表缓存
        
        Returns:
            是否刷新成功
        """
        try:
            clusters = await self.get_available_clusters(force_refresh=True)
            return len(clusters) > 0
        except Exception as e:
            logger.error(f"刷新集群列表失败: {e}")
            return False


# 全局集群管理器实例
_cluster_manager: Optional[ClusterManager] = None


def init_cluster_manager(dmp_api: "DMPAPI", cache: SimpleCache) -> ClusterManager:
    """初始化全局集群管理器实例"""
    global _cluster_manager
    _cluster_manager = ClusterManager(dmp_api, cache)
    return _cluster_manager


def get_cluster_manager() -> Optional[ClusterManager]:
    """获取全局集群管理器实例"""
    return _cluster_manager
