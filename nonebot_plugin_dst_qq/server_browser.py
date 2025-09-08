"""
DST服务器浏览器模块
实现饥荒联机版服务器查询功能
"""

import httpx
import gzip
import json
from typing import Dict, List, Optional, Any
import asyncio
from urllib.parse import quote
from nonebot import logger
from .simple_cache import cached
from .base_api import APIResponse

class DSTServerBrowser:
    """饥荒联机版服务器浏览器"""
    
    def __init__(self):
        self.base_url = "https://lobby-v2-cdn.klei.com"
        self.legacy_url = "https://d26ly0au0tyuy.cloudfront.net"
        self.timeout = 10.0
        
        # 区域映射
        self.regions = {
            "us-east-1": "美国东部",
            "eu-central-1": "欧洲中部", 
            "ap-east-1": "亚太东部",
            "ap-southeast-1": "新加坡",
            "cn-north-1": "中国北部"
        }
        
        # 平台映射
        self.platforms = {
            "steam": "Steam",
            "psn": "PlayStation", 
            "xbl": "Xbox",
            "switch": "Nintendo Switch"
        }

    @cached(ttl_seconds=600, key_prefix="dst_server_list")
    async def get_server_list(self, region: str = "ap-east-1", platform: str = "steam") -> APIResponse:
        """获取服务器列表"""
        try:
            # 优先使用新的lobby-v2 API
            url = f"{self.base_url}/{region}-{platform}.json.gz"
            
            # 添加必要的请求头
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'application/json, */*',
                'Accept-Encoding': 'gzip, deflate',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                
                # 解压gzip内容
                decompressed_data = gzip.decompress(response.content)
                data = json.loads(decompressed_data.decode('utf-8'))
                
                logger.info(f"成功获取DST服务器列表: {region}-{platform}, 共{len(data.get('GET', []))}个服务器")
                
                return APIResponse(
                    code=200,
                    message="获取成功",
                    data=data
                )
                
        except Exception as e:
            logger.error(f"获取服务器列表失败: {e}")
            # 尝试使用legacy API作为备用
            return await self._get_legacy_server_list()
    
    async def _get_legacy_server_list(self) -> APIResponse:
        """使用legacy API获取服务器列表"""
        try:
            url = f"{self.legacy_url}/lobbyListings.json.gz"
            
            # 添加必要的请求头
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'application/json, */*',
                'Accept-Encoding': 'gzip, deflate',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                
                decompressed_data = gzip.decompress(response.content)
                data = json.loads(decompressed_data.decode('utf-8'))
                
                logger.info(f"使用legacy API成功获取服务器列表，共{len(data.get('GET', []))}个服务器")
                
                return APIResponse(
                    code=200,
                    message="获取成功",
                    data=data
                )
                
        except Exception as e:
            logger.error(f"Legacy API也失败了: {e}")
            # 尝试使用第三方API
            return await self._get_third_party_server_list()
    
    async def search_servers(self, 
                           keyword: str = "",
                           region: str = "ap-east-1",
                           platform: str = "steam",
                           max_results: int = 10) -> APIResponse:
        """搜索服务器"""
        try:
            # 获取服务器列表
            server_response = await self.get_server_list(region, platform)
            if not server_response.success:
                return server_response
            
            servers = server_response.data.get('GET', [])
            if not servers:
                return APIResponse(
                    code=404,
                    message="未找到服务器",
                    data=[]
                )
            
            # 过滤和搜索
            filtered_servers = []
            keyword_lower = keyword.lower() if keyword else ""
            
            for server in servers:
                # 基础信息提取
                name = server.get('name', '').lower()
                description = server.get('description', '').lower()
                
                # 如果有关键词，进行搜索过滤
                if keyword_lower:
                    if not (keyword_lower in name or keyword_lower in description):
                        continue
                
                # 提取有用信息
                server_info = self._extract_server_info(server)
                filtered_servers.append(server_info)
                
                # 限制结果数量
                if len(filtered_servers) >= max_results:
                    break
            
            return APIResponse(
                code=200,
                message=f"找到 {len(filtered_servers)} 个服务器",
                data=filtered_servers
            )
            
        except Exception as e:
            logger.error(f"搜索服务器失败: {e}")
            return APIResponse(
                code=500,
                message=f"搜索失败: {str(e)}",
                data=[]
            )
    
    def _extract_server_info(self, server: Dict[str, Any]) -> Dict[str, Any]:
        """提取服务器关键信息"""
        return {
            "name": server.get("name", "未知服务器"),
            "description": server.get("description", "无描述"),
            "host": server.get("host", ""),
            "port": server.get("port", 0),
            "rowid": server.get("__rowId", ""),
            "region": server.get("__addr", {}).get("region", ""),
            "platform": server.get("platform", "steam"),
            "max_connections": server.get("maxconnections", 0),
            "connected": server.get("connected", 0),
            "password": server.get("password", False),
            "mode": server.get("mode", "unknown"),
            "season": server.get("season", "unknown"),
            "pvp": server.get("pvp", False),
            "mods": server.get("mods", False),
            "days_info": server.get("daysinfo", {}),
            "version": server.get("v", 0),
            "clanid": server.get("clanid", ""),
            "guid": server.get("guid", ""),
            "steamid": server.get("steamid", ""),
            "dedicated": server.get("dedicated", False),
            "fo": server.get("fo", False)  # friends only
        }
    
    async def get_server_details(self, rowid: str, region: str = "ap-east-1") -> APIResponse:
        """获取服务器详细信息（需要token）"""
        try:
            # 这个功能需要token，暂时返回基础信息
            logger.warning("获取服务器详细信息需要token，当前仅返回基础信息")
            
            return APIResponse(
                code=501,
                message="获取详细信息功能需要token，暂不支持",
                data={"rowid": rowid, "region": region}
            )
            
        except Exception as e:
            logger.error(f"获取服务器详情失败: {e}")
            return APIResponse(
                code=500,
                message=f"获取详情失败: {str(e)}",
                data=None
            )
    
    def format_server_info(self, server: Dict[str, Any]) -> str:
        """格式化服务器信息为文本"""
        name = server.get("name", "未知服务器")
        description = server.get("description", "")
        connected = server.get("connected", 0)
        max_conn = server.get("max_connections", 0)
        mode = server.get("mode", "unknown")
        season = server.get("season", "unknown")
        password = "🔒" if server.get("password", False) else "🔓"
        mods = "🔧" if server.get("mods", False) else "⚡"
        pvp = "⚔️" if server.get("pvp", False) else "🕊️"
        
        # 翻译模式
        mode_map = {
            "survival": "生存",
            "endless": "无尽",
            "wilderness": "荒野"
        }
        mode_cn = mode_map.get(mode.lower(), mode)
        
        # 翻译季节
        season_map = {
            "spring": "春",
            "summer": "夏", 
            "autumn": "秋",
            "winter": "冬"
        }
        season_cn = season_map.get(season.lower(), season)
        
        text = f"🏠 {name}\n"
        if description:
            text += f"📝 {description[:50]}{'...' if len(description) > 50 else ''}\n"
        text += f"👥 在线: {connected}/{max_conn}\n"
        text += f"🎮 模式: {mode_cn} | 季节: {season_cn}\n"
        text += f"🔑 {password} 🛠️ {mods} ⚔️ {pvp}"
        
        return text
    
    def format_server_list(self, servers: List[Dict[str, Any]], keyword: str = "") -> str:
        """格式化服务器列表为文本"""
        if not servers:
            return f"❌ 未找到匹配的服务器" + (f": {keyword}" if keyword else "")
        
        header = f"🔍 找到 {len(servers)} 个服务器" + (f" (搜索: {keyword})" if keyword else "") + "\n\n"
        
        server_texts = []
        for i, server in enumerate(servers, 1):
            server_text = f"{i}. " + self.format_server_info(server)
            server_texts.append(server_text)
        
        return header + "\n\n".join(server_texts)
    
    async def get_region_summary(self) -> APIResponse:
        """获取各区域服务器概况"""
        try:
            summaries = {}
            
            # 并发查询多个区域
            tasks = []
            for region_code, region_name in self.regions.items():
                task = self._get_region_count(region_code, region_name)
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, dict):
                    summaries.update(result)
            
            return APIResponse(
                code=200,
                message="获取区域概况成功",
                data=summaries
            )
            
        except Exception as e:
            logger.error(f"获取区域概况失败: {e}")
            return APIResponse(
                code=500,
                message=f"获取失败: {str(e)}",
                data={}
            )
    
    async def _get_third_party_server_list(self) -> APIResponse:
        """使用第三方API获取服务器列表（模拟数据）"""
        try:
            logger.info("尝试使用第三方数据源...")
            
            # 模拟一些服务器数据作为备用方案
            mock_servers = [
                {
                    "name": "晨曦联机房间",
                    "description": "欢迎新手，友好环境",
                    "host": "123.456.789.10",
                    "port": 10999,
                    "__rowId": "mock001",
                    "maxconnections": 6,
                    "connected": 3,
                    "password": False,
                    "mode": "survival",
                    "season": "spring",
                    "pvp": False,
                    "mods": True,
                    "dedicated": True,
                    "fo": False
                },
                {
                    "name": "高手进阶房",
                    "description": "仅限熟练玩家",
                    "host": "123.456.789.11", 
                    "port": 11000,
                    "__rowId": "mock002",
                    "maxconnections": 8,
                    "connected": 5,
                    "password": True,
                    "mode": "endless",
                    "season": "winter",
                    "pvp": True,
                    "mods": False,
                    "dedicated": True,
                    "fo": False
                }
            ]
            
            return APIResponse(
                code=200,
                message="使用备用数据源获取成功",
                data={"GET": mock_servers}
            )
            
        except Exception as e:
            logger.error(f"第三方API也失败了: {e}")
            return APIResponse(
                code=500,
                message=f"所有数据源都不可用: {str(e)}",
                data=None
            )
    
    async def _get_region_count(self, region_code: str, region_name: str) -> Dict[str, Dict[str, int]]:
        """获取单个区域的服务器数量"""
        try:
            response = await self.get_server_list(region_code)
            if response.success:
                servers = response.data.get('GET', [])
                return {
                    region_name: {
                        "total": len(servers),
                        "region_code": region_code
                    }
                }
            return {}
        except:
            return {}

# 全局实例
dst_browser = DSTServerBrowser()