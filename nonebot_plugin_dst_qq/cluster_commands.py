"""
集群管理命令
提供动态集群管理的命令接口
"""

from nonebot import on_command
from nonebot.adapters.onebot.v11 import Bot, Event, GroupMessageEvent, PrivateMessageEvent, MessageSegment
from nonebot.permission import SUPERUSER
from nonebot.params import CommandArg
from nonebot.typing import T_State
from arclet.alconna import Alconna, Args, Option
from nonebot_plugin_alconna import on_alconna, Match

from .cluster_manager import get_cluster_manager
from nonebot import logger
from .utils import require_admin
from .message_utils import send_message, handle_command_errors

# ========================================
# 集群状态查看命令
# ========================================

cluster_status_cmd = on_alconna(
    Alconna("集群状态"),
    aliases={"cluster", "clusters", "集群列表", "集群信息"},
    priority=5,
    block=True,
)

@cluster_status_cmd.handle()
@handle_command_errors("获取集群状态")
async def handle_cluster_status(bot: Bot, event: Event):
    """处理集群状态查看命令"""
    cluster_manager = get_cluster_manager()
    if not cluster_manager:
        await send_message(bot, event, "❌ 集群管理器未初始化")
        return
    
    # 获取集群状态摘要
    status_summary = await cluster_manager.get_cluster_status_summary()
    await send_message(bot, event, status_summary)


# ========================================
# 切换集群命令（管理员专用）
# ========================================

switch_cluster_cmd = on_alconna(
    Alconna(
        "切换集群",
        Args["cluster_name", str]
    ),
    aliases={"switch", "切换", "选择集群", "设置集群"},
    priority=5,
    block=True,
    permission=SUPERUSER,
)

@switch_cluster_cmd.handle()
@handle_command_errors("切换集群")
async def handle_switch_cluster(
    bot: Bot, 
    event: Event, 
    cluster_name: Match[str]
):
    """处理切换集群命令"""
    
    if not cluster_name.available:
        await send_message(bot, event, "❌ 请指定要切换的集群名称\n使用格式: /切换集群 <集群名称>")
        return
    
    cluster_manager = get_cluster_manager()
    if not cluster_manager:
        await send_message(bot, event, "❌ 集群管理器未初始化")
        return
    
    target_cluster = cluster_name.result
    user_id = str(event.user_id)
    
    # 尝试切换集群
    success = await cluster_manager.set_current_cluster(target_cluster, user_id)
    
    if success:
        # 获取集群详细信息
        cluster_info = await cluster_manager.get_cluster_info(target_cluster)
        
        response_lines = [
            f"✅ 成功切换到集群: {target_cluster}"
        ]
        
        if cluster_info:
            display_name = cluster_info.get("display_name", target_cluster)
            status = cluster_info.get("status", "unknown")
            player_count = cluster_info.get("player_count", 0)
            max_players = cluster_info.get("max_players", 0)
            
            status_icon = "🟢" if status == "online" else "🔴" if status == "offline" else "🟡"
            player_info = f"{player_count}/{max_players}" if max_players > 0 else str(player_count)
            
            response_lines.extend([
                "",
                f"📋 集群信息:",
                f"   名称: {display_name}",
                f"   状态: {status_icon} {status}",
                f"   玩家: {player_info}",
            ])
            
            if cluster_info.get("description"):
                response_lines.append(f"   描述: {cluster_info['description']}")
        
        response_text = "\n".join(response_lines)
        await send_message(bot, event, response_text)
    else:
        # 获取可用集群列表提示用户
        available_clusters = await cluster_manager.get_cluster_names()
        if available_clusters:
            clusters_text = "、".join(available_clusters)
            error_text = (
                f"❌ 集群 '{target_cluster}' 不存在或不可用\n\n"
                f"可用集群: {clusters_text}\n\n"
                f"使用 /集群状态 查看详细信息"
            )
        else:
            error_text = f"❌ 集群 '{target_cluster}' 不存在，且当前没有可用集群"
        
        await send_message(bot, event, error_text)


# ========================================
# 刷新集群命令（管理员专用）
# ========================================

refresh_clusters_cmd = on_alconna(
    Alconna("刷新集群"),
    aliases={"refresh", "更新集群", "刷新集群列表"},
    priority=5,
    block=True,
    permission=SUPERUSER,
)

@refresh_clusters_cmd.handle()
@handle_command_errors("刷新集群列表")
async def handle_refresh_clusters(bot: Bot, event: Event):
    """处理刷新集群命令"""
    
    cluster_manager = get_cluster_manager()
    if not cluster_manager:
        await send_message(bot, event, "❌ 集群管理器未初始化")
        return
    
    await send_message(bot, event, "🔄 正在刷新集群列表...")
    
    # 强制刷新集群列表
    success = await cluster_manager.refresh_clusters()
    
    if success:
        # 获取刷新后的集群状态
        clusters = await cluster_manager.get_available_clusters()
        current_cluster = await cluster_manager.get_current_cluster()
        
        response_lines = [
            f"✅ 集群列表刷新成功",
            f"📊 发现 {len(clusters)} 个集群"
        ]
        
        if current_cluster:
            response_lines.append(f"🎯 当前集群: {current_cluster}")
        
        # 列出所有集群
        if clusters:
            response_lines.append("")
            response_lines.append("📋 可用集群:")
            for cluster in clusters:
                name = cluster.get("name", "")
                display_name = cluster.get("display_name", name)
                status = cluster.get("status", "unknown")
                status_icon = "🟢" if status == "online" else "🔴" if status == "offline" else "🟡"
                current_mark = " ⭐" if name == current_cluster else ""
                response_lines.append(f"   {status_icon} {display_name} ({name}){current_mark}")
        
        response_text = "\n".join(response_lines)
        await send_message(bot, event, response_text)
    else:
        await send_message(bot, event, "❌ 刷新集群列表失败，请检查网络连接和API权限")


# ========================================
# 集群详情命令
# ========================================

cluster_info_cmd = on_alconna(
    Alconna(
        "集群详情",
        Args["cluster_name", str]
    ),
    aliases={"cluster_info", "集群信息"},
    priority=5,
    block=True,
)

@cluster_info_cmd.handle()
@handle_command_errors("查看集群详情")
async def handle_cluster_info(
    bot: Bot, 
    event: Event, 
    cluster_name: Match[str]
):
    """处理集群详情查看命令"""
    if not cluster_name.available:
        await send_message(bot, event, "❌ 请指定要查看的集群名称\n使用格式: /集群详情 <集群名称>")
        return
    
    cluster_manager = get_cluster_manager()
    if not cluster_manager:
        await send_message(bot, event, "❌ 集群管理器未初始化")
        return
    
    target_cluster = cluster_name.result
    cluster_info = await cluster_manager.get_cluster_info(target_cluster)
    
    if cluster_info:
        name = cluster_info.get("name", "未知")
        display_name = cluster_info.get("display_name", name)
        status = cluster_info.get("status", "unknown")
        player_count = cluster_info.get("player_count", 0)
        max_players = cluster_info.get("max_players", 0)
        description = cluster_info.get("description", "无描述")
        last_updated = cluster_info.get("last_updated", "未知")
        
        status_icon = "🟢" if status == "online" else "🔴" if status == "offline" else "🟡"
        player_info = f"{player_count}/{max_players}" if max_players > 0 else str(player_count)
        
        current_cluster = await cluster_manager.get_current_cluster()
        current_mark = " ⭐ (当前使用)" if name == current_cluster else ""
        
        response_lines = [
            f"📋 集群详情: {display_name}{current_mark}",
            "",
            f"🏷️  集群名称: {name}",
            f"📛 显示名称: {display_name}",
            f"📊 运行状态: {status_icon} {status}",
            f"👥 在线玩家: {player_info}",
            f"📝 集群描述: {description}",
            f"🕐 更新时间: {last_updated}"
        ]
        
        response_text = "\n".join(response_lines)
        await send_message(bot, event, response_text)
    else:
        # 提供可用集群列表
        available_clusters = await cluster_manager.get_cluster_names()
        if available_clusters:
            clusters_text = "、".join(available_clusters)
            error_text = (
                f"❌ 集群 '{target_cluster}' 不存在\n\n"
                f"可用集群: {clusters_text}\n\n"
                f"使用 /集群状态 查看所有集群信息"
            )
        else:
            error_text = "❌ 集群不存在，且当前没有可用集群"
        
        await send_message(bot, event, error_text)

