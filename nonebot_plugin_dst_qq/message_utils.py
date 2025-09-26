"""
通用消息发送工具模块
提供统一的消息发送、错误处理等功能
"""

from functools import wraps
from typing import Optional, Any
import html
import traceback
import base64
import ast
from pathlib import Path

from nonebot import logger
from nonebot.adapters import Bot, Event
from nonebot.adapters.onebot.v11 import MessageSegment

try:
    from nonebot_plugin_htmlrender import html_to_pic as _html_to_pic  # type: ignore
except Exception:  # pragma: no cover - htmlrender 初始化失败时回退
    _html_to_pic = None  # type: ignore

from .message_dedup import is_user_image_mode


CARD_WIDTH = 520  # 图片总宽度，包含外层留白
CONTENT_WIDTH = CARD_WIDTH - 80  # 内层卡片宽度
BASE_HEIGHT = 240
LINE_HEIGHT = 34


_SEASON_ICON_MAP = {
    "spring": ("🌱", "春季"),
    "summer": ("☀️", "夏季"),
    "autumn": ("🍂", "秋季"),
    "fall": ("🍂", "秋季"),
    "winter": ("❄️", "冬季"),
}

_PHASE_ICON_MAP = {
    "day": ("☀️", "白天"),
    "dusk": ("🌆", "黄昏"),
    "night": ("🌙", "夜晚"),
}


def _format_season_info(raw: Any) -> str:
    """将季节信息格式化为易读文本"""

    def _pick_name(data: dict, *keys: str) -> str:
        for key in keys:
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return ""

    if isinstance(raw, dict):
        cycles = raw.get("cycles") or raw.get("cycle") or raw.get("day")
        season_key = (
            _pick_name(raw, "key", "en", "name") or _pick_name(raw, "zh") or ""
        ).lower()
        phase = raw.get("phase")

        icon, label = _SEASON_ICON_MAP.get(season_key, ("📅", _pick_name(raw, "zh", "name", "en") or "未知季节"))

        phase_icon = ""
        phase_label = ""
        if isinstance(phase, dict):
            phase_key = (
                _pick_name(phase, "key", "en") or _pick_name(phase, "zh") or ""
            ).lower()
            phase_icon, phase_label = _PHASE_ICON_MAP.get(
                phase_key, ("🌙", _pick_name(phase, "zh", "name", "en") or "未知时段")
            )
        elif isinstance(phase, str):
            phase_key = phase.lower()
            phase_icon, phase_label = _PHASE_ICON_MAP.get(phase_key, ("🌙", phase))

        parts = []
        if cycles is not None:
            parts.append(f"📆 第{cycles}天")
        parts.append(f"{icon} {label}")
        if phase_label:
            parts.append(f"{phase_icon} {phase_label}")

        return " ｜ ".join(parts)

    if isinstance(raw, str):
        key = raw.strip().lower()
        icon, label = _SEASON_ICON_MAP.get(key, ("🍂", raw.strip()))
        return f"{icon} {label}" if label else raw.strip()

    return ""


def _load_background_data_uri() -> str:
    assets_dir = Path(__file__).resolve().parent / "assets"
    for name in ("menu_background.jpg", "menu_background.png", "menu_background.jpeg"):
        image_path = assets_dir / name
        if image_path.exists():
            mime = "image/png" if image_path.suffix.lower() == ".png" else "image/jpeg"
            encoded = base64.b64encode(image_path.read_bytes()).decode()
            return f"data:{mime};base64,{encoded}"
    return ""


BACKGROUND_DATA_URI = _load_background_data_uri()


def _build_text_card_html(text: str) -> str:
    """将纯文本内容转换为便于截图的 HTML 卡片"""
    blocks = [block for block in text.strip().split("\n\n") if block.strip()]

    hero_title = ""
    hero_subtitle = ""
    sections = []
    footer = ""

    if blocks:
        hero_lines = [line for line in blocks[0].splitlines() if line.strip()]
        if hero_lines:
            hero_title = hero_lines[0]
            if len(hero_lines) > 1:
                hero_subtitle = hero_lines[1]
    if not hero_subtitle:
        hero_subtitle = "DST Management Platform Bot"

    for block in blocks[1:]:
        lines = [line for line in block.splitlines() if line.strip()]
        if not lines:
            continue
        if len(lines) == 1 and block == blocks[-1]:
            footer = lines[0]
            continue
        title = lines[0]
        items = lines[1:]
        sections.append((title, items))

    def _render_item(line: str) -> str:
        if " - " in line:
            left, right = line.split(" - ", 1)
            return (
                "<div class=\"item\">"
                f"<span class=\"item-left\">{html.escape(left)}</span>"
                f"<span class=\"item-right\">{html.escape(right)}</span>"
                "</div>"
            )
        return f"<div class=\"item\"><span class=\"item-left\">{html.escape(line)}</span></div>"

    sections_html = []
    for title, items in sections:
        items_html = "".join(_render_item(item) for item in items)
        sections_html.append(
            "<div class=\"section\">"
            f"<div class=\"section-title\">{html.escape(title)}</div>"
            f"<div class=\"section-items\">{items_html}</div>"
            "</div>"
        )

    footer_html = (
        f"<div class=\"footer\">{html.escape(footer)}</div>" if footer else ""
    )

    sections_html_str = "".join(sections_html)

    background_image_css = (
        f"background: url('{BACKGROUND_DATA_URI}') center/cover no-repeat;"
        if BACKGROUND_DATA_URI
        else "background: linear-gradient(160deg, #6f7df7 0%, #9a6bf6 45%, #b779f5 100%);"
    )

    return f"""
    <html>
      <head>
        <meta charset=\"utf-8\" />
        <style>
          * {{ box-sizing: border-box; }}
          html {{
            margin: 0;
            padding: 0;
          }}
          body {{
            width: {CARD_WIDTH}px;
            min-height: 100%;
            margin: 0;
            padding: 24px 0 32px;
            font-family: 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
            color: #1a2b4c;
            position: relative;
            overflow: hidden;
          }}
          body::before {{
            content: "";
            position: fixed;
            inset: 0;
            {background_image_css}
            filter: blur(8px);
            transform: scale(1.08);
            z-index: -2;
          }}
          body::after {{
            content: "";
            position: fixed;
            inset: 0;
            background: linear-gradient(180deg, rgba(112,104,247,0.45), rgba(167,117,245,0.45));
            z-index: -1;
          }}
          .layout {{
            width: {CONTENT_WIDTH}px;
            margin: 0 auto;
            display: flex;
            flex-direction: column;
            gap: 24px;
          }}
          .hero {{
            background: rgba(255,255,255,0.14);
            border-radius: 24px;
            padding: 28px 32px;
            box-shadow: 0 18px 30px rgba(80, 69, 185, 0.25);
            text-align: center;
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
          }}
          .hero-title {{
            font-size: 26px;
            font-weight: 600;
            margin-bottom: 8px;
          }}
          .hero-subtitle {{
            font-size: 16px;
            color: rgba(255,255,255,0.82);
          }}
          .section {{
            background: rgba(255,255,255,0.16);
            border-radius: 24px;
            padding: 24px 28px;
            box-shadow: 0 14px 24px rgba(80, 69, 185, 0.18);
            backdrop-filter: blur(18px);
            -webkit-backdrop-filter: blur(18px);
          }}
          .section-title {{
            font-size: 20px;
            font-weight: 600;
            margin-bottom: 14px;
            color: rgba(255,255,255,0.95);
          }}
          .section-items {{
            display: flex;
            flex-direction: column;
            gap: 12px;
          }}
          .item {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 16px;
            color: rgba(255,255,255,0.92);
            border-bottom: 1px solid rgba(255, 255, 255, 0.18);
            padding-bottom: 8px;
          }}
          .item:last-child {{ border-bottom: none; padding-bottom: 0; }}
          .item-left {{
            font-weight: 500;
            color: rgba(255,255,255,0.95);
          }}
          .item-right {{
            color: rgba(255,255,255,0.75);
            margin-left: 16px;
          }}
          .footer {{
            text-align: center;
            font-size: 15px;
            color: rgba(255,255,255,0.85);
            padding: 12px 0 4px;
          }}
        </style>
      </head>
      <body>
        <div class=\"layout\">
          <div class=\"hero\">
            <div class=\"hero-title\">{html.escape(hero_title)}</div>
            <div class=\"hero-subtitle\">{html.escape(hero_subtitle)}</div>
          </div>
          {sections_html_str}
          {footer_html}
        </div>
      </body>
    </html>
    """


async def _render_text_card(text: str) -> Optional[bytes]:
    """将文本渲染为图片字节，若渲染失败返回None"""
    global _html_to_pic
    if _html_to_pic is None:
        try:
            from nonebot_plugin_htmlrender import html_to_pic as _html_to_pic  # type: ignore
        except Exception as import_error:  # pragma: no cover
            logger.debug(f"图片渲染插件不可用，改用文本输出: {import_error}")
            _html_to_pic = None  # type: ignore
            return None

    try:
        line_count = text.count("\n") + 1
        viewport_height = max(BASE_HEIGHT, line_count * LINE_HEIGHT + 200)
        viewport = {"width": CARD_WIDTH, "height": viewport_height}

        return await _html_to_pic(  # type: ignore[operator]
            html=_build_text_card_html(text),
            wait=100,
            device_scale_factor=2,
            full_page=False,
            viewport=viewport,
        )
    except Exception as render_error:
        logger.warning(f"图片模式渲染失败，回退为文本输出: {render_error}")
        return None


def _generate_stat_block(title: str, value: str, percent: Optional[float] = None) -> str:
    bar_html = ""
    if percent is not None:
        pct = max(0, min(100, percent))
        bar_html = (
            "<div class=\"stat-bar\">"
            f"<div class=\"stat-bar-inner\" style=\"width: {pct:.1f}%\"></div>"
            "</div>"
        )
    return (
        "<div class=\"stat-item\">"
        f"<div class=\"stat-title\">{html.escape(title)}</div>"
        f"<div class=\"stat-value\">{html.escape(value)}</div>"
        f"{bar_html}"
        "</div>"
    )


async def render_room_info_card(card: dict) -> Optional[bytes]:
    global _html_to_pic
    if _html_to_pic is None:
        try:
            from nonebot_plugin_htmlrender import html_to_pic as _html_to_pic  # type: ignore
        except Exception:
            _html_to_pic = None  # type: ignore
            return None

    try:
        cluster_name = card.get("cluster_name", "未知集群")
        room_name = card.get("room_name") or cluster_name
        status = card.get("status", "未知状态")
        online = card.get("online_players")
        max_players = card.get("max_players")

        try:
            online_value = int(str(online))
        except Exception:
            online_value = 0
        max_value = None
        if max_players not in (None, "", "未知"):
            try:
                max_value = int(str(max_players))
            except Exception:
                max_value = None

        player_percent = (online_value / max_value * 100) if max_value and max_value > 0 else None

        system_data = card.get("system_data") or {}
        cpu_usage = system_data.get("cpu_usage")
        mem_usage = system_data.get("memory_usage")

        world_summary = []
        season_info = ""
        world_data = card.get("world_data") or []
        if isinstance(world_data, list):
            for world in world_data[:3]:
                if isinstance(world, dict):
                    name = world.get("world", "未知")
                    status_icon = "🟢" if world.get("stat") else "🔴"
                    world_type_icon = "🪐" if world.get("isMaster") else "🕳️"
                    world_type_label = "主世界" if world.get("isMaster") else "洞穴"
                    world_summary.append(f"{status_icon}{world_type_icon} {name} · {world_type_label}")
                    if not season_info:
                        season = world.get("season")
                        if isinstance(season, dict):
                            season_info = _format_season_info(season)

        if not season_info and card.get("season_info") and card.get("season_info") != "未知":
            raw_season = card.get("season_info")
            parsed_season: Any = raw_season
            if isinstance(raw_season, str):
                try:
                    parsed_season = ast.literal_eval(raw_season)
                except (ValueError, SyntaxError):
                    parsed_season = raw_season
            season_info = _format_season_info(parsed_season)

        players = []
        players_data = card.get("players_data") or {}
        if isinstance(players_data, dict):
            for player in (players_data.get("players") or [])[:5]:
                if isinstance(player, dict):
                    players.append(player.get("name") or player.get("playerName") or "未知玩家")

        badges = []
        badges.append(("在线", f"{online_value}/{max_value if max_value else '-'}"))
        badges.append(("状态", status))
        if card.get("pvp_status"):
            badges.append(("PVP", card.get("pvp_status")))
        if season_info:
            badges.append(("季节", season_info))

        stats_html = "".join(
            [
                _generate_stat_block("在线玩家", f"{online_value}{' / ' + str(max_value) if max_value else ''}", player_percent),
                _generate_stat_block(
                    "CPU 占用",
                    f"{cpu_usage:.1f}%" if isinstance(cpu_usage, (int, float)) else str(cpu_usage or "-"),
                    float(cpu_usage) if isinstance(cpu_usage, (int, float)) else None,
                ),
                _generate_stat_block(
                    "内存占用",
                    f"{mem_usage:.1f}%" if isinstance(mem_usage, (int, float)) else str(mem_usage or "-"),
                    float(mem_usage) if isinstance(mem_usage, (int, float)) else None,
                ),
            ]
        )

        players_html = "".join(
            f"<div class=\"pill\">{html.escape(name)}</div>" for name in players
        ) or "<div class=\"pill pill-empty\">暂无在线玩家</div>"

        worlds_html = "".join(
            f"<div class=\"pill\">{html.escape(item)}</div>" for item in world_summary
        ) or "<div class=\"pill pill-empty\">暂无世界信息</div>"

        background_image_css = (
            f"background: url('{BACKGROUND_DATA_URI}') center/cover no-repeat;"
            if BACKGROUND_DATA_URI
            else "background: linear-gradient(180deg, #a8b8ff 0%, #c1a4ff 100%);"
        )

        html_content = f"""
        <html>
          <head>
            <meta charset=\"utf-8\" />
            <style>
              * {{ box-sizing: border-box; }}
              html {{ margin: 0; padding: 0; }}
              body {{
                margin: 0;
                padding: 24px 0 32px;
                width: {CARD_WIDTH}px;
                font-family: 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
                color: #1f2748;
                position: relative;
                overflow: hidden;
              }}
              body::before {{
                content: "";
                position: fixed;
                inset: 0;
                {background_image_css}
                filter: blur(14px) brightness(0.92);
                transform: scale(1.08);
                z-index: -2;
              }}
              body::after {{
                content: "";
                position: fixed;
                inset: 0;
                background: linear-gradient(180deg, rgba(38, 48, 82, 0.32) 0%, rgba(98, 73, 142, 0.28) 55%, rgba(255,255,255,0.12) 100%);
                z-index: -1;
              }}
              .layout {{
                width: {CONTENT_WIDTH}px;
                margin: 0 auto;
                display: flex;
                flex-direction: column;
                gap: 18px;
              }}
              .card {{
                background: rgba(255, 255, 255, 0.78);
                border-radius: 22px;
                padding: 22px 26px;
                backdrop-filter: blur(26px);
                -webkit-backdrop-filter: blur(26px);
                box-shadow: 0 18px 36px rgba(44, 52, 90, 0.18);
              }}
              .hero-title {{ font-size: 24px; font-weight: 600; margin-bottom: 6px; color: #1a2140; }}
              .hero-subtitle {{ font-size: 15px; color: rgba(26, 33, 64, 0.72); margin-bottom: 12px; }}
              .badge-list {{ display: flex; flex-wrap: wrap; gap: 8px; }}
              .badge {{
                padding: 6px 12px;
                border-radius: 999px;
                background: rgba(31, 39, 72, 0.08);
                color: rgba(31, 39, 72, 0.92);
                font-size: 13px;
                font-weight: 500;
                backdrop-filter: blur(20px);
              }}
              .stats {{ display: flex; gap: 16px; flex-wrap: wrap; }}
              .stat-item {{
                flex: 1 1 140px;
                background: rgba(255,255,255,0.88);
                border-radius: 18px;
                padding: 14px 16px;
                display: flex;
                flex-direction: column;
                gap: 6px;
                backdrop-filter: blur(16px);
                box-shadow: 0 12px 24px rgba(44, 52, 90, 0.08);
              }}
              .stat-title {{ font-size: 14px; color: rgba(31,39,72,0.7); }}
              .stat-value {{ font-size: 20px; font-weight: 600; color: rgba(58,43,124,0.95); }}
              .stat-bar {{
                height: 6px;
                border-radius: 999px;
                background: rgba(255,255,255,0.25);
                overflow: hidden;
              }}
              .stat-bar-inner {{
                height: 100%;
                background: linear-gradient(90deg, #7b91f5, #a5d4ff);
              }}
              .pill-list {{ display: flex; flex-wrap: wrap; gap: 8px; }}
              .pill {{
                padding: 6px 14px;
                border-radius: 999px;
                background: rgba(46, 56, 92, 0.08);
                color: rgba(31,39,72,0.92);
                font-size: 13px;
                font-weight: 500;
                backdrop-filter: blur(18px);
              }}
              .pill-empty {{ opacity: 0.65; }}
              .section-heading {{
                font-size: 16px;
                font-weight: 600;
                margin-bottom: 10px;
                color: rgba(26, 33, 64, 0.85);
              }}
              .two-column {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 12px;
              }}
              .info-block {{
                background: rgba(255,255,255,0.9);
                border-radius: 18px;
                padding: 16px 18px;
                backdrop-filter: blur(18px);
                display: flex;
                flex-direction: column;
                gap: 6px;
                color: rgba(31,39,72,0.9);
                box-shadow: 0 12px 26px rgba(44, 52, 90, 0.08);
              }}
              .info-label {{ font-size: 13px; opacity: 0.7; text-transform: uppercase; letter-spacing: 0.04em; }}
              .info-value {{ font-size: 16px; font-weight: 600; color: rgba(58,43,124,0.92); }}
            </style>
          </head>
          <body>
            <div class=\"layout\">
              <div class=\"card\">
                <div class=\"hero-title\">{html.escape(room_name)}</div>
                <div class=\"hero-subtitle\">所属集群: {html.escape(cluster_name)}</div>
                <div class=\"badge-list\">{''.join(f'<span class=\"badge\">{html.escape(k)}: {html.escape(str(v))}</span>' for k, v in badges if v)}</div>
              </div>

              <div class=\"stats\">
                {stats_html}
              </div>

              <div class=\"card\">
                <div class=\"section-heading\">在线玩家</div>
                <div class=\"pill-list\">{players_html}</div>
              </div>

              <div class=\"card\">
                <div class=\"section-heading\">世界状态</div>
                <div class=\"pill-list\">{worlds_html}</div>
              </div>

              <div class=\"two-column\">
                <div class=\"info-block\">
                  <div class=\"info-label\">管理员数量</div>
                  <div class=\"info-value\">{html.escape(str(card.get('admin_count', '-')))}</div>
                </div>
                <div class=\"info-block\">
                  <div class=\"info-label\">密码</div>
                  <div class=\"info-value\">{html.escape(card.get('password') or '无')}</div>
                </div>
              </div>

            </div>
          </body>
        </html>
        """

        players_count = len(players_data.get("players") or []) if isinstance(players_data, dict) else 0
        worlds_count = len(world_summary)
        blocks_height = 240 + players_count * 38 + worlds_count * 38
        viewport_height = max(BASE_HEIGHT, blocks_height)
        viewport = {"width": CARD_WIDTH, "height": viewport_height}

        return await _html_to_pic(  # type: ignore[operator]
            html=html_content,
            wait=100,
            device_scale_factor=2,
            full_page=False,
            viewport=viewport,
        )
    except Exception as render_error:
        logger.warning(f"房间信息图片渲染失败，回退为文本输出: {render_error}")
        return None


async def send_message(bot: Bot, event: Event, text: str):
    """统一的消息发送方法，支持图片模式输出"""
    use_image = False
    try:
        user_id = str(event.get_user_id())
        use_image = is_user_image_mode(user_id)
    except Exception:
        use_image = False

    if use_image:
        image_bytes = await _render_text_card(text)
        if image_bytes:
            await bot.send(event, MessageSegment.image(image_bytes))
            return

    await bot.send(event, text)


async def send_error_message(bot: Bot, event: Event, error: Exception, operation: str):
    """统一的错误消息发送"""
    logger.error(f"{operation}失败: {error}")
    logger.debug(f"错误详情: {traceback.format_exc()}")
    error_msg = f"❌ {operation}失败: {str(error)}"
    await send_message(bot, event, error_msg)


async def send_success_message(bot: Bot, event: Event, message: str, operation: str = None):
    """统一的成功消息发送"""
    if operation:
        logger.info(f"✅ {operation}成功")
    success_msg = f"✅ {message}"
    await send_message(bot, event, success_msg)


async def send_warning_message(bot: Bot, event: Event, message: str, operation: str = None):
    """统一的警告消息发送"""
    if operation:
        logger.warning(f"⚠️ {operation}: {message}")
    warning_msg = f"⚠️ {message}"
    await send_message(bot, event, warning_msg)


def handle_command_errors(operation_name: str):
    """命令错误处理装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(bot: Bot, event: Event, *args, **kwargs):
            try:
                return await func(bot, event, *args, **kwargs)
            except Exception as e:
                await send_error_message(bot, event, e, operation_name)
                logger.error(f"命令处理异常 - {operation_name}: {traceback.format_exc()}")
        return wrapper

    return decorator


async def safe_api_call(bot: Bot, event: Event, api_func, error_message: str, *args, **kwargs) -> Optional[Any]:
    """安全的API调用封装"""
    try:
        result = await api_func(*args, **kwargs)
        if hasattr(result, "success") and result.success:
            return result
        elif hasattr(result, "success"):
            await send_error_message(bot, event, Exception(result.message or "未知错误"), error_message)
            return None
        else:
            return result
    except Exception as e:
        await send_error_message(bot, event, e, error_message)
        return None


async def ensure_cluster_available(bot: Bot, event: Event, dmp_api) -> Optional[str]:
    """确保集群可用的通用函数"""
    try:
        cluster_name = await dmp_api.get_current_cluster()
        if not cluster_name:
            await send_error_message(bot, event, Exception("无法获取可用集群列表，请检查DMP服务器连接"), "获取集群")
            return None
        return cluster_name
    except Exception as e:
        await send_error_message(bot, event, e, "获取集群")
        return None


async def validate_response_data(bot: Bot, event: Event, response, operation: str) -> bool:
    """验证API响应数据的通用函数"""
    if not response:
        await send_error_message(bot, event, Exception("响应为空"), operation)
        return False

    if hasattr(response, "success"):
        if not response.success:
            await send_error_message(bot, event, Exception(response.message or "API调用失败"), operation)
            return False

        if not response.data:
            await send_warning_message(bot, event, f"{operation}返回空数据", operation)
            return False

    return True
