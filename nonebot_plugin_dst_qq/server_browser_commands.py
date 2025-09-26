"""
DST服务器浏览器命令模块
实现查房相关的命令处理
"""

from nonebot.adapters import Bot, Event
from nonebot_plugin_alconna import on_alconna, Alconna, Args, Option, Arparma
from nonebot_plugin_waiter import waiter
from nonebot import logger
from typing import Optional, Dict, Any, List

from .server_browser import dst_browser
from .message_utils import send_message

async def _show_server_list_with_pagination(
    bot: Bot,
    event: Event,
    all_servers: List[Dict[str, Any]],
    search_keyword: str,
    page: int = 1,
    per_page: int = 10,
    *,
    summary: Optional[str] = None,
    total_count: Optional[int] = None,
):
    """显示带分页的服务器列表并处理用户交互"""
    
    try:
        if summary:
            await send_message(bot, event, summary)

        while True:
            # 获取当前页数据
            page_data = dst_browser.format_server_page(
                all_servers,
                page=page,
                per_page=per_page,
                keyword=search_keyword,
                total_count=total_count if total_count is not None else len(all_servers),
            )
            
            # 发送当前页信息
            await send_message(bot, event, page_data["message"])
            
            # 如果只有一页，直接返回
            if page_data["total_pages"] <= 1:
                return
            
            # 等待用户输入
            @waiter(waits=["message"], keep_session=True)
            async def wait_for_user_input(waiter_event: Event):
                if waiter_event.get_user_id() != event.get_user_id():
                    return
                return waiter_event.get_message().extract_plain_text().strip()
            
            user_input = await wait_for_user_input.wait(timeout=60)
            
            if user_input is None:
                await send_message(bot, event, "⏰ 操作超时，已退出浏览")
                return
            
            user_input = user_input.lower()
            
            # 处理用户输入
            if user_input in ["退出", "quit", "q", "exit"]:
                await send_message(bot, event, "👋 已退出服务器浏览")
                return
            
            elif user_input in ["上一页", "上页", "<", "prev", "previous"]:
                if page > 1:
                    page -= 1
                else:
                    await send_message(bot, event, "❌ 已经是第一页了")
                    continue
            
            elif user_input in ["下一页", "下页", ">", "next"]:
                if page < page_data["total_pages"]:
                    page += 1
                else:
                    await send_message(bot, event, "❌ 已经是最后一页了")
                    continue
            
            elif user_input.isdigit():
                # 用户输入序号，显示服务器详情
                server_index = int(user_input) - 1
                
                if 0 <= server_index < len(all_servers):
                    selected_server = all_servers[server_index]
                    detail = dst_browser.format_server_detail(selected_server, int(user_input))
                    await send_message(bot, event, detail)
                    
                    # 等待用户返回
                    @waiter(waits=["message"], keep_session=True)
                    async def wait_for_return(waiter_event: Event):
                        if waiter_event.get_user_id() != event.get_user_id():
                            return
                        return waiter_event.get_message().extract_plain_text().strip()
                    
                    return_input = await wait_for_return.wait(timeout=30)
                    if return_input is None:
                        await send_message(bot, event, "⏰ 操作超时，已退出")
                        return
                    
                    # 继续显示列表
                    continue
                else:
                    await send_message(bot, event, f"❌ 序号无效，请输入 1-{len(all_servers)} 之间的数字")
                    continue
            
            else:
                await send_message(bot, event, "❓ 无效输入，请输入页码导航命令或服务器序号")
                continue
    
    except Exception as e:
        logger.error(f"分页交互处理失败: {e}")
        await send_message(bot, event, "❌ 浏览功能出现错误")

# 查房主命令
server_browser_cmd = on_alconna(
    Alconna(
        "查房",
        Args["keyword", str, ""]
    ),
    aliases={"查服务器", "查房间", "dst查房", "服务器列表", "房间列表"},
    priority=5,
    block=True,
)

@server_browser_cmd.handle()
async def handle_server_browser(bot: Bot, event: Event, result: Arparma):
    """处理查房命令"""
    try:
        # 获取参数
        keyword = result.main_args.get("keyword", "").strip()
        region = result.options.get("region", {}).get("region")
        platform = result.options.get("platform", {}).get("platform", "steam")
        max_results = result.options.get("num", {}).get("num", 10)
        exclude_password = result.options.get("no-password", {}).get("flag", False)
        min_players = result.options.get("min", {}).get("min_players", 0)
        max_players = result.options.get("max", {}).get("max_players")
        
        # 限制结果数量
        max_results = min(max_results, 20)
        
        logger.info(
            "执行查房命令: 关键词='%s', 区域=%s, 平台=%s, 数量=%s",
            keyword,
            region,
            platform,
            max_results,
        )

        requested_limit = max_results or 10
        fetch_limit = min(max(requested_limit * 2, 20), 60)

        region_candidates: List[str] = []
        if region:
            region_candidates.append(region)
        else:
            region_candidates.append(dst_browser.default_region)

        # 追加其他可用区域作为自动兜底
        for candidate in dst_browser.regions.keys():
            if candidate not in region_candidates:
                region_candidates.append(candidate)

        aggregated_servers: List[Dict[str, Any]] = []
        attempted_regions: List[str] = []
        error_messages: List[str] = []

        for candidate in region_candidates:
            response = await dst_browser.search_servers(
                keyword=keyword,
                region=candidate,
                platform=platform,
                max_results=fetch_limit,
                include_password=not exclude_password,
                min_players=min_players,
                max_players=max_players,
            )

            if not response.success:
                if response.message:
                    error_messages.append(response.message)
                continue

            servers = response.data or []
            if servers:
                attempted_regions.append(candidate)
                aggregated_servers.extend(servers)

            if len(aggregated_servers) >= requested_limit:
                break

        if not aggregated_servers:
            if error_messages:
                await send_message(bot, event, f"❌ 查房失败: {error_messages[0]}")
            else:
                search_info = []
                if keyword:
                    search_info.append(f"关键词: {keyword}")
                if region:
                    region_name = dst_browser.regions.get(region, region)
                    search_info.append(f"区域: {region_name}")
                if min_players:
                    search_info.append(f"玩家≥{min_players}")
                if max_players:
                    search_info.append(f"玩家≤{max_players}")
                if exclude_password:
                    search_info.append("排除密码房")
                filters_desc = f" ({', '.join(search_info)})" if search_info else ""
                await send_message(bot, event, f"❌ 未找到匹配的服务器{filters_desc}")
            return

        # 去重并按活跃度排序
        unique_servers: List[Dict[str, Any]] = []
        seen_keys = set()
        for server in aggregated_servers:
            key = (
                server.get("guid")
                or (server.get("host"), server.get("port"))
                or server.get("rowid")
            )

            if isinstance(key, tuple):
                key = ":".join(str(part) for part in key if part)

            if not key:
                key = f"{server.get('name','')}-{server.get('region','')}-{server.get('connected',0)}-{server.get('timestamp','')}"

            if key in seen_keys:
                continue

            seen_keys.add(key)
            unique_servers.append(server)

        unique_servers.sort(
            key=lambda s: (s.get("connected", 0), s.get("max_connections", 0)),
            reverse=True,
        )

        total_found = len(unique_servers)
        display_servers = unique_servers[:requested_limit]

        region_labels = [
            dst_browser.regions.get(item, item) for item in (attempted_regions or region_candidates[:1])
        ]

        filter_parts: List[str] = []
        if keyword:
            filter_parts.append(f"关键词「{keyword}」")
        if min_players:
            filter_parts.append(f"玩家≥{min_players}")
        if max_players:
            filter_parts.append(f"玩家≤{max_players}")
        if exclude_password:
            filter_parts.append("排除密码房")
        if platform != "steam":
            platform_name = dst_browser.platforms.get(platform, {}).get("name", platform)
            filter_parts.append(f"平台: {platform_name}")

        top_server = display_servers[0] if display_servers else None
        summary_lines = ["📊 查房结果概览"]
        if filter_parts:
            summary_lines.append(f"• 筛选条件: {', '.join(filter_parts)}")
        summary_lines.append(
            "• 检索区域: " + ", ".join(region_labels)
        )
        summary_lines.append(
            "• 匹配总数: {} 个{}".format(
                total_found,
                "（展示前 {} 个）".format(len(display_servers)) if total_found > len(display_servers) else "",
            )
        )
        if top_server:
            summary_lines.append(
                "• 最活跃: {} ({}/{})".format(
                    top_server.get("name", "未知"),
                    top_server.get("connected", 0),
                    top_server.get("max_connections", 0),
                )
            )

        summary_message = "\n".join(summary_lines)

        per_page = min(8, max(1, len(display_servers)))
        await _show_server_list_with_pagination(
            bot,
            event,
            display_servers,
            keyword,
            per_page=per_page,
            summary=summary_message,
        )

    except Exception as e:
        logger.error(f"查房命令执行失败: {e}")
        await send_message(bot, event, f"❌ 查房功能出错: {str(e)}")

# 区域概况命令
region_summary_cmd = on_alconna(
    Alconna("区域概况"),
    aliases={"查看区域", "服务器概况", "区域统计"},
    priority=5,
    block=True,
)

@region_summary_cmd.handle()
async def handle_region_summary(bot: Bot, event: Event):
    """处理区域概况命令"""
    try:
        logger.info("执行区域概况命令")
        
        response = await dst_browser.get_region_summary()
        
        if not response.success:
            await send_message(bot, event, f"❌ 获取区域概况失败: {response.message}")
            return
        
        summaries = response.data
        if not summaries:
            await send_message(bot, event, "❌ 暂无区域数据")
            return
        
        # 格式化区域概况
        message = "🌏 DST服务器区域概况\n\n"
        for region_name, info in summaries.items():
            total = info.get("total", 0)
            message += f"📍 {region_name}: {total} 个服务器\n"
        
        message += f"\n💡 使用 /查房 -r 区域代码 来查看特定区域的服务器"
        
        await send_message(bot, event, message)
        
    except Exception as e:
        logger.error(f"区域概况命令执行失败: {e}")
        await send_message(bot, event, f"❌ 区域概况功能出错: {str(e)}")

# 热门房间命令
hot_servers_cmd = on_alconna(
    Alconna("热门房间"),
    aliases={"热门服务器", "人多的房间", "活跃房间"},
    priority=5,
    block=True,
)

@hot_servers_cmd.handle()
async def handle_hot_servers(bot: Bot, event: Event):
    """处理热门房间命令"""
    try:
        logger.info("执行热门房间命令")
        
        # 搜索有人数的服务器，按人数排序
        response = await dst_browser.search_servers(
            keyword="",
            region=None,  # 默认亚太地区
            platform="steam",
            max_results=15,
            include_password=True,
            min_players=1  # 至少有1个人
        )
        
        if not response.success:
            await send_message(bot, event, f"❌ 获取热门房间失败: {response.message}")
            return
        
        servers = response.data
        if not servers:
            await send_message(bot, event, "❌ 暂无活跃的服务器")
            return
        
        # 按在线人数排序
        servers.sort(key=lambda x: x.get("connected", 0), reverse=True)
        
        # 使用分页交互显示热门房间
        await _show_server_list_with_pagination(bot, event, servers, "热门房间")
        
    except Exception as e:
        logger.error(f"热门房间命令执行失败: {e}")
        await send_message(bot, event, f"❌ 热门房间功能出错: {str(e)}")

# 无密码房间命令
no_password_cmd = on_alconna(
    Alconna("无密码房间"),
    aliases={"公开房间", "免密码", "开放房间"},
    priority=5,
    block=True,
)

@no_password_cmd.handle()
async def handle_no_password_servers(bot: Bot, event: Event):
    """处理无密码房间命令"""
    try:
        logger.info("执行无密码房间命令")
        
        # 搜索无密码的服务器
        response = await dst_browser.search_servers(
            keyword="",
            region=None,  # 默认亚太地区
            platform="steam", 
            max_results=12,
            include_password=False,  # 排除有密码的
            min_players=0
        )
        
        if not response.success:
            await send_message(bot, event, f"❌ 获取无密码房间失败: {response.message}")
            return
        
        servers = response.data
        if not servers:
            await send_message(bot, event, "❌ 暂无无密码的服务器")
            return
        
        # 使用分页交互显示无密码房间
        await _show_server_list_with_pagination(bot, event, servers, "无密码房间")
        
    except Exception as e:
        logger.error(f"无密码房间命令执行失败: {e}")
        await send_message(bot, event, f"❌ 无密码房间功能出错: {str(e)}")

# 新手房间命令
newbie_servers_cmd = on_alconna(
    Alconna("新手房间"),
    aliases={"萌新房间", "新人房间", "友好房间", "新手服务器"},
    priority=5,
    block=True,
)

@newbie_servers_cmd.handle()
async def handle_newbie_servers(bot: Bot, event: Event):
    """处理新手房间命令"""
    try:
        logger.info("执行新手房间命令")
        
        # 搜索新手友好的关键词
        newbie_keywords = ["新手", "萌新", "新人", "友好", "欢迎", "指导", "beginner", "newbie", "welcome", "friendly"]
        
        all_servers = []
        for keyword in newbie_keywords[:3]:  # 只用前3个关键词避免请求过多
            response = await dst_browser.search_servers(
                keyword=keyword,
                region=None,
                platform="steam",
                max_results=5,
                include_password=False,  # 新手房间通常不设密码
                min_players=0
            )
            
            if response.success:
                servers = response.data
                # 避免重复
                for server in servers:
                    if server not in all_servers:
                        all_servers.append(server)
        
        if not all_servers:
            await send_message(bot, event, "❌ 暂未找到新手友好的服务器，建议查看无密码房间")
            return
        
        # 使用分页交互显示新手房间
        await _show_server_list_with_pagination(bot, event, all_servers, "新手友好房间")
        
    except Exception as e:
        logger.error(f"新手房间命令执行失败: {e}")
        await send_message(bot, event, f"❌ 新手房间功能出错: {str(e)}")

# 同名房间检测命令
duplicate_check_cmd = on_alconna(
    Alconna("同名房间", Args["keyword", str, ""]),
    aliases={"检查同名", "重复房间", "同名检测"},
    priority=5,
    block=True,
)

@duplicate_check_cmd.handle()
async def handle_duplicate_check(bot: Bot, event: Event, result: Arparma):
    """处理同名房间检测命令"""
    try:
        keyword = result.main_args.get("keyword", "").strip()
        
        logger.info(f"执行同名房间检测: 关键词='{keyword}'")
        
        # 获取更多服务器数据用于检测
        response = await dst_browser.search_servers(
            keyword=keyword,
            region=None,
            platform="steam",
            max_results=50,  # 获取更多数据
            include_password=True,
            min_players=0
        )
        
        if not response.success:
            await send_message(bot, event, f"❌ 获取服务器数据失败: {response.message}")
            return
        
        servers = response.data
        if not servers:
            await send_message(bot, event, "❌ 未找到服务器数据")
            return
        
        # 查找同名服务器
        duplicate_groups = dst_browser.find_duplicate_names(servers)
        
        if not duplicate_groups:
            search_text = f" (搜索: {keyword})" if keyword else ""
            await send_message(bot, event, f"✅ 未发现同名服务器{search_text}")
            return
        
        # 将同名服务器组展开为列表，用于分页显示
        duplicate_servers = []
        for name, group in duplicate_groups.items():
            for server in group:
                # 标记这是同名服务器
                server["_is_duplicate"] = True
                server["_duplicate_group"] = name
                duplicate_servers.append(server)
        
        # 使用分页交互显示同名服务器
        search_text = f"同名服务器{f' ({keyword})' if keyword else ''}"
        await _show_server_list_with_pagination(bot, event, duplicate_servers, search_text)
        
    except Exception as e:
        logger.error(f"同名房间检测失败: {e}")
        await send_message(bot, event, f"❌ 同名房间检测出错: {str(e)}")

# 快速查房命令（简化版）
quick_browse_cmd = on_alconna(
    Alconna("快速查房"),
    aliases={"随机房间", "看看房间", "快速浏览"},
    priority=5,
    block=True,
)

@quick_browse_cmd.handle()
async def handle_quick_browse(bot: Bot, event: Event):
    """处理快速查房命令"""
    try:
        logger.info("执行快速查房命令")
        
        # 获取一些随机服务器
        response = await dst_browser.search_servers(
            keyword="",
            region=None,  # 默认亚太地区
            platform="steam",
            max_results=6,
            include_password=True,
            min_players=0
        )
        
        if not response.success:
            await send_message(bot, event, f"❌ 快速查房失败: {response.message}")
            return
        
        servers = response.data
        if not servers:
            await send_message(bot, event, "❌ 暂无可用的服务器")
            return
        
        # 使用分页交互显示随机房间
        await _show_server_list_with_pagination(bot, event, servers, "随机房间推荐")
        
    except Exception as e:
        logger.error(f"快速查房命令执行失败: {e}")
        await send_message(bot, event, f"❌ 快速查房功能出错: {str(e)}")
