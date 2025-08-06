from pathlib import Path

import nonebot
from nonebot import get_plugin_config
from nonebot.plugin import PluginMetadata, require

from .config import Config

__plugin_meta__ = PluginMetadata(
    name="DMP 饥荒管理平台机器人",
    description="基于 NoneBot2 的饥荒管理平台 (DMP) QQ 机器人插件，支持游戏信息查询、命令执行和消息互通功能。",
    usage="""基础命令：
- /世界 [世界名] - 获取世界信息
- /房间 - 获取房间信息  
- /系统 - 获取系统信息
- /玩家 [世界名] - 获取在线玩家列表
- /直连 - 获取服务器直连信息
- /菜单 - 显示帮助信息

管理员命令：
- /管理命令 - 显示管理员功能菜单
- /查看备份 - 获取备份文件列表
- /创建备份 - 手动创建备份
- /执行 <世界> <命令> - 执行游戏命令
- /回档 <天数> - 回档指定天数 (1-5天)
- /重置世界 [世界名称] - 重置世界 (默认Master)
- /聊天历史 [世界名] [行数] - 获取聊天历史 (默认集群，默认50行)
- /聊天统计 - 获取聊天历史统计信息

消息互通功能：
- /消息互通 - 开启游戏内消息与QQ消息互通
- /关闭互通 - 关闭消息互通功能
- /互通状态 - 查看当前互通状态
- /最新消息 [数量] - 获取游戏内最新消息

配置说明：
在 .env 文件中配置以下环境变量：
- DMP_BASE_URL: DMP服务器地址
- DMP_TOKEN: JWT认证令牌
- DEFAULT_CLUSTER: 默认集群名称""",
    
    type="application",
    homepage="https://github.com/uitok/nonebot-plugin-dst-qq",
    config=Config,
    supported_adapters={"~onebot.v11"},
)

# 延迟配置获取，避免在导入时初始化 NoneBot
config = None

def get_config():
    """获取插件配置"""
    global config
    if config is None:
        config = get_plugin_config(Config)
    return config

# 使用 require 函数加载依赖插件
try:
    # 加载 Alconna 插件
    require("nonebot_plugin_alconna")
    
    # 加载子插件模块
    dmp_api = require("nonebot_plugin_dst_qq.plugins.dmp_api")
    dmp_advanced = require("nonebot_plugin_dst_qq.plugins.dmp_advanced")
    message_exchange = require("nonebot_plugin_dst_qq.plugins.message_exchange")
    
    print("✅ DMP 饥荒管理平台机器人插件加载成功！")
    print("📋 支持的命令：")
    print("  • 基础查询：/世界、/房间、/系统、/玩家、/直连、/菜单")
    print("  • 管理员功能：/管理命令、/查看备份、/创建备份、/执行、/回档、/重置世界")
    print("  • 聊天管理：/聊天历史、/聊天统计")
    print("  • 消息互通：/消息互通、/关闭互通、/互通状态、/最新消息")
    
except Exception as e:
    print(f"❌ 警告: 插件加载失败: {e}")
    print("请检查依赖插件是否正确安装：")
    print("  • nonebot_plugin_alconna")
    print("  • nonebot-adapter-onebot")

