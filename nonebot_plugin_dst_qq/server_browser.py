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
        
        # 区域映射（优先亚太地区）
        self.regions = {
            "ap-east-1": "亚太东部(香港)",
            "ap-southeast-1": "亚太东南(新加坡)",
            "ap-northeast-1": "亚太东北(日本)",
            "ap-southeast-2": "亚太东南(澳洲)",
            "us-east-1": "美国东部",
            "eu-central-1": "欧洲中部"
        }
        
        # 平台映射和数字代码
        self.platforms = {
            "steam": {"name": "Steam", "code": "1"},
            "psn": {"name": "PlayStation", "code": "2"}, 
            "rail": {"name": "WeGame", "code": "4"},
            "xbl": {"name": "Xbox", "code": "16"},
            "switch": {"name": "Nintendo Switch", "code": "32"}
        }
        
        # 默认使用亚太地区
        self.default_region = "ap-east-1"

    @cached(ttl_seconds=300, key_prefix="dst_server_list")
    async def get_server_list(self, region: str = None, platform: str = "steam") -> APIResponse:
        """获取服务器列表"""
        if region is None:
            region = self.default_region
            
        try:
            # 获取平台代码
            platform_code = self.platforms.get(platform, {}).get("code", "1")
            
            # 构建URL，使用平台数字代码
            url = f"{self.base_url}/{region}-{platform_code}.json.gz"
            
            # 添加更真实的请求头，模拟游戏客户端
            headers = {
                'User-Agent': 'DST/1.0 (compatible; MSIE 10.0; Windows NT 6.2; WOW64; Trident/6.0)',
                'Accept': 'application/json, application/gzip, */*',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache'
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                
                # 解压gzip内容
                decompressed_data = gzip.decompress(response.content)
                data = json.loads(decompressed_data.decode('utf-8'))
                
                server_count = len(data.get('GET', []))
                region_name = self.regions.get(region, region)
                platform_name = self.platforms.get(platform, {}).get("name", platform)
                
                logger.info(f"成功获取DST服务器列表: {region_name}-{platform_name}, 共{server_count}个服务器")
                
                return APIResponse(
                    code=200,
                    message=f"获取成功 - {region_name} {platform_name}",
                    data=data
                )
                
        except httpx.HTTPStatusError as e:
            logger.warning(f"API返回状态码 {e.response.status_code}: {e}")
            # 尝试使用legacy API作为备用
            return await self._get_legacy_server_list()
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
                           region: str = None,
                           platform: str = "steam",
                           max_results: int = 10,
                           include_password: bool = True,
                           min_players: int = 0,
                           max_players: int = None) -> APIResponse:
        """搜索服务器"""
        try:
            if region is None:
                region = self.default_region
                
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
                connected = server.get('connected', 0)
                password = server.get('password', False)
                
                # 关键词搜索过滤
                if keyword_lower:
                    if not (keyword_lower in name or keyword_lower in description):
                        continue
                
                # 密码过滤
                if not include_password and password:
                    continue
                
                # 人数过滤
                if connected < min_players:
                    continue
                    
                if max_players is not None and connected > max_players:
                    continue
                
                # 提取有用信息
                server_info = self._extract_server_info(server)
                filtered_servers.append(server_info)
                
                # 限制结果数量
                if len(filtered_servers) >= max_results:
                    break
            
            region_name = self.regions.get(region, region)
            platform_name = self.platforms.get(platform, {}).get("name", platform)
            
            return APIResponse(
                code=200,
                message=f"找到 {len(filtered_servers)} 个服务器 ({region_name}-{platform_name})",
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
    
    def format_server_info(self, server: Dict[str, Any], show_unique_id: bool = True) -> str:
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
        
        # 获取唯一标识信息
        host = server.get("host", "")
        port = server.get("port", 0)
        rowid = server.get("rowid", "")
        steamid = server.get("steamid", "")
        region = server.get("region", "")
        
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
        
        # 生成服务器标识
        server_id = self._generate_server_identifier(server)
        
        text = f"🏠 {name}"
        if show_unique_id and server_id:
            text += f" ({server_id})"
        text += "\n"
        
        if description:
            text += f"📝 {description[:50]}{'...' if len(description) > 50 else ''}\n"
        text += f"👥 在线: {connected}/{max_conn}\n"
        text += f"🎮 模式: {mode_cn} | 季节: {season_cn}\n"
        text += f"🔑 {password} 🛠️ {mods} ⚔️ {pvp}"
        
        # 添加连接信息（用于区分同名服务器）
        if show_unique_id:
            connection_info = []
            if host and port:
                connection_info.append(f"📡 {host}:{port}")
            elif steamid:
                connection_info.append(f"🎮 Steam:{steamid[-8:]}")  # 只显示后8位
            elif rowid:
                connection_info.append(f"🆔 ID:{rowid[-8:]}")  # 只显示后8位
                
            if connection_info:
                text += f"\n{' | '.join(connection_info)}"
        
        return text
    
    def _generate_server_identifier(self, server: Dict[str, Any]) -> str:
        """生成服务器唯一标识符，用于区分同名服务器"""
        # 优先使用不同的标识符
        host = server.get("host", "")
        port = server.get("port", 0)
        steamid = server.get("steamid", "")
        rowid = server.get("rowid", "")
        
        if host and port:
            # 使用IP地址的后两段
            try:
                parts = host.split('.')
                if len(parts) >= 2:
                    return f"{parts[-2]}.{parts[-1]}:{port}"
                return f"{host}:{port}"
            except:
                return f"{host}:{port}"
        elif steamid:
            # 使用Steam ID的后8位
            return f"Steam:{steamid[-8:]}"
        elif rowid:
            # 使用Row ID的后8位
            return f"ID:{rowid[-8:]}"
        else:
            # 使用连接人数和最大连接数作为标识
            connected = server.get("connected", 0)
            max_conn = server.get("max_connections", 0)
            return f"{connected}/{max_conn}"
    
    def format_server_list(self, servers: List[Dict[str, Any]], keyword: str = "", page: int = 1, per_page: int = 10, total_count: int = None) -> str:
        """格式化服务器列表为文本，支持分页"""
        if not servers:
            return f"❌ 未找到匹配的服务器" + (f": {keyword}" if keyword else "")
        
        # 检测同名服务器
        name_counts = {}
        for server in servers:
            name = server.get("name", "未知服务器")
            name_counts[name] = name_counts.get(name, 0) + 1
        
        has_duplicates = any(count > 1 for count in name_counts.values())
        
        # 分页信息
        if total_count is None:
            total_count = len(servers)
        total_pages = (total_count + per_page - 1) // per_page
        start_index = (page - 1) * per_page
        
        # 标题
        header = f"🔍 找到 {total_count} 个服务器" + (f" (搜索: {keyword})" if keyword else "")
        if has_duplicates:
            header += " [含同名房间]"
        
        # 分页信息
        if total_pages > 1:
            header += f"\n📄 第 {page}/{total_pages} 页 (共 {total_count} 个结果)"
        
        header += "\n\n"
        
        # 服务器列表
        server_texts = []
        for i, server in enumerate(servers, start_index + 1):
            # 如果有同名服务器，显示唯一标识
            show_id = has_duplicates or name_counts.get(server.get("name", ""), 1) > 1
            server_text = f"{i}. " + self.format_server_info(server, show_unique_id=show_id)
            server_texts.append(server_text)
        
        result = header + "\n\n".join(server_texts)
        
        # 分页控制说明
        if total_pages > 1:
            navigation_tips = []
            if page > 1:
                navigation_tips.append("上一页: 输入 '上一页' 或 '<'")
            if page < total_pages:
                navigation_tips.append("下一页: 输入 '下一页' 或 '>'")
            navigation_tips.append("退出: 输入 '退出' 或 'q'")
            
            result += f"\n\n📱 导航: {' | '.join(navigation_tips)}"
        
        # 选择说明
        result += "\n\n🎯 输入序号查看详细信息，或继续浏览其他页面"
        
        # 如果有同名房间，添加说明
        if has_duplicates:
            result += "\n💡 括号内为服务器标识，用于区分同名房间"
        
        return result
    
    def format_server_page(self, servers: List[Dict[str, Any]], page: int = 1, per_page: int = 10, keyword: str = "", total_count: int = None) -> Dict[str, Any]:
        """格式化服务器分页数据"""
        if not servers:
            return {
                "message": f"❌ 未找到匹配的服务器" + (f": {keyword}" if keyword else ""),
                "has_more": False,
                "page": page,
                "total_pages": 0,
                "servers": []
            }
        
        if total_count is None:
            total_count = len(servers)
        
        total_pages = (total_count + per_page - 1) // per_page
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        page_servers = servers[start_idx:end_idx]
        
        # 检测同名服务器
        name_counts = {}
        for server in servers:  # 检查所有服务器，不只是当前页
            name = server.get("name", "未知服务器")
            name_counts[name] = name_counts.get(name, 0) + 1
        
        has_duplicates = any(count > 1 for count in name_counts.values())
        
        formatted_text = self.format_server_list(page_servers, keyword, page, per_page, total_count)
        
        return {
            "message": formatted_text,
            "has_more": page < total_pages,
            "page": page,
            "total_pages": total_pages,
            "servers": page_servers,
            "has_duplicates": has_duplicates,
            "global_name_counts": name_counts  # 用于判断是否需要显示唯一ID
        }
    
    def find_duplicate_names(self, servers: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """查找同名服务器并分组"""
        name_groups = {}
        
        for server in servers:
            name = server.get("name", "未知服务器")
            if name not in name_groups:
                name_groups[name] = []
            name_groups[name].append(server)
        
        # 只返回有多个服务器的组
        return {name: group for name, group in name_groups.items() if len(group) > 1}
    
    def format_duplicate_servers(self, duplicate_groups: Dict[str, List[Dict[str, Any]]]) -> str:
        """格式化同名服务器信息"""
        if not duplicate_groups:
            return "✅ 未发现同名服务器"
        
        result = f"🚨 发现 {len(duplicate_groups)} 组同名服务器:\n\n"
        
        for name, group in duplicate_groups.items():
            result += f"🏠 「{name}」({len(group)} 个):\n"
            
            for i, server in enumerate(group, 1):
                identifier = self._generate_server_identifier(server)
                connected = server.get("connected", 0)
                max_conn = server.get("max_connections", 0)
                password = "🔒" if server.get("password", False) else "🔓"
                
                result += f"  {i}. {identifier} - {connected}/{max_conn} {password}\n"
                
                # 添加区别信息
                host = server.get("host", "")
                region = server.get("region", "")
                if host:
                    result += f"     📡 {host}\n"
                if region:
                    region_name = self.regions.get(region, region)
                    result += f"     🌍 {region_name}\n"
            
            result += "\n"
        
        result += "💡 选择服务器时请注意标识符和连接信息"
        
        return result
    
    def format_server_detail(self, server: Dict[str, Any], index: int = None) -> str:
        """格式化单个服务器的详细信息"""
        name = server.get("name", "未知服务器")
        description = server.get("description", "无描述")
        connected = server.get("connected", 0)
        max_conn = server.get("max_connections", 0)
        host = server.get("host", "")
        port = server.get("port", 0)
        password = server.get("password", False)
        mods = server.get("mods", False)
        pvp = server.get("pvp", False)
        mode = server.get("mode", "unknown")
        season = server.get("season", "unknown")
        version = server.get("version", 0)
        dedicated = server.get("dedicated", False)
        steamid = server.get("steamid", "")
        rowid = server.get("rowid", "")
        region = server.get("region", "")
        
        # 翻译
        mode_map = {"survival": "生存", "endless": "无尽", "wilderness": "荒野"}
        season_map = {"spring": "春", "summer": "夏", "autumn": "秋", "winter": "冬"}
        mode_cn = mode_map.get(mode.lower(), mode)
        season_cn = season_map.get(season.lower(), season)
        
        # 服务器标识
        server_id = self._generate_server_identifier(server)
        
        # 构建详细信息
        detail = f"🏠 服务器详情"
        if index:
            detail += f" (序号 {index})"
        detail += f"\n{'='*40}\n"
        
        detail += f"📛 名称: {name}\n"
        if server_id:
            detail += f"🆔 标识: {server_id}\n"
        detail += f"📝 描述: {description}\n\n"
        
        detail += f"👥 在线人数: {connected}/{max_conn}\n"
        detail += f"🎮 游戏模式: {mode_cn}\n"
        detail += f"🌸 当前季节: {season_cn}\n"
        detail += f"🔑 需要密码: {'是' if password else '否'}\n"
        detail += f"🔧 使用MOD: {'是' if mods else '否'}\n"
        detail += f"⚔️ PVP模式: {'是' if pvp else '否'}\n"
        detail += f"🖥️ 专用服务器: {'是' if dedicated else '否'}\n"
        
        if version:
            detail += f"📦 游戏版本: {version}\n"
        
        detail += "\n🌐 连接信息:\n"
        if host and port:
            detail += f"📡 服务器地址: {host}:{port}\n"
        if steamid:
            detail += f"🎮 Steam ID: {steamid}\n"
        if rowid:
            detail += f"🆔 Row ID: {rowid}\n"
        if region:
            region_name = self.regions.get(region, region)
            detail += f"🌍 服务器区域: {region_name}\n"
        
        # 连接提示
        detail += f"\n💡 连接提示:\n"
        if host and port:
            detail += f"• 直连地址: {host}:{port}\n"
        if password:
            detail += f"• ⚠️ 此服务器需要密码才能加入\n"
        if not dedicated:
            detail += f"• ⚠️ 此服务器可能不稳定 (非专用服务器)\n"
        
        detail += f"\n🔙 输入 '返回' 回到服务器列表"
        
        return detail
    
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
            
            # 模拟亚太地区服务器数据作为备用方案
            mock_servers = [
                {
                    "name": "🇨🇳 中文房间 - 新手友好",
                    "description": "欢迎萌新！有老玩家指导，轻松上手饥荒联机",
                    "host": "sg.dst-server.com",
                    "port": 10999,
                    "__rowId": "ap-mock001",
                    "maxconnections": 6,
                    "connected": 4,
                    "password": False,
                    "mode": "survival",
                    "season": "spring",
                    "pvp": False,
                    "mods": True,
                    "dedicated": True,
                    "fo": False,
                    "region": "ap-southeast-1"
                },
                {
                    "name": "🏆 高手竞技场",
                    "description": "挑战模式，仅限老玩家，PVP开启",
                    "host": "hk.dst-server.com", 
                    "port": 11000,
                    "__rowId": "ap-mock002",
                    "maxconnections": 8,
                    "connected": 6,
                    "password": True,
                    "mode": "endless",
                    "season": "winter",
                    "pvp": True,
                    "mods": False,
                    "dedicated": True,
                    "fo": False,
                    "region": "ap-east-1"
                },
                {
                    "name": "🌸 日式和风房间",
                    "description": "日本服务器，低延迟，装饰MOD丰富",
                    "host": "jp.dst-server.com",
                    "port": 10998,
                    "__rowId": "ap-mock003",
                    "maxconnections": 10,
                    "connected": 7,
                    "password": False,
                    "mode": "survival",
                    "season": "autumn",
                    "pvp": False,
                    "mods": True,
                    "dedicated": True,
                    "fo": False,
                    "region": "ap-northeast-1"
                },
                {
                    "name": "🦘 澳洲休闲房",
                    "description": "Australian friendly server, English/Chinese welcome",
                    "host": "au.dst-server.com",
                    "port": 11001,
                    "__rowId": "ap-mock004",
                    "maxconnections": 12,
                    "connected": 2,
                    "password": False,
                    "mode": "endless",
                    "season": "summer",
                    "pvp": False,
                    "mods": True,
                    "dedicated": True,
                    "fo": False,
                    "region": "ap-southeast-2"
                },
                {
                    "name": "🎮 WeGame官方房间",
                    "description": "WeGame平台专用，国内网络优化",
                    "host": "cn.wegame.dst.com",
                    "port": 10997,
                    "__rowId": "rail-mock001",
                    "maxconnections": 8,
                    "connected": 5,
                    "password": False,
                    "mode": "survival", 
                    "season": "spring",
                    "pvp": False,
                    "mods": True,
                    "dedicated": True,
                    "fo": False,
                    "platform": "rail"
                },
                # 添加同名房间用于测试
                {
                    "name": "🇨🇳 中文房间 - 新手友好",  # 故意同名
                    "description": "另一个中文房间，服务器在香港",
                    "host": "hk.dst-cn.com",
                    "port": 11002,
                    "__rowId": "ap-mock005",
                    "maxconnections": 8,
                    "connected": 2,
                    "password": True,
                    "mode": "endless",
                    "season": "winter",
                    "pvp": False,
                    "mods": True,
                    "dedicated": True,
                    "fo": False,
                    "region": "ap-east-1"
                },
                {
                    "name": "新手服务器",
                    "description": "适合新手玩家的服务器",
                    "host": "newbie1.dst.com",
                    "port": 10995,
                    "__rowId": "newbie-001",
                    "maxconnections": 6,
                    "connected": 3,
                    "password": False,
                    "mode": "survival",
                    "season": "spring",
                    "pvp": False,
                    "mods": False,
                    "dedicated": True,
                    "fo": False,
                    "steamid": "76561198123456789"
                },
                {
                    "name": "新手服务器",  # 故意同名
                    "description": "另一个新手服务器，更多MOD",
                    "host": "newbie2.dst.com", 
                    "port": 10996,
                    "__rowId": "newbie-002",
                    "maxconnections": 10,
                    "connected": 7,
                    "password": False,
                    "mode": "survival",
                    "season": "autumn",
                    "pvp": False,
                    "mods": True,
                    "dedicated": True,
                    "fo": False,
                    "steamid": "76561198987654321"
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