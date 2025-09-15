from pathlib import Path
import nonebot
from nonebot.plugin import PluginMetadata

from .config import PluginConfig

__plugin_meta__ = PluginMetadata(
    name="DMP 饥荒管理平台机器人",
    description="基于 NoneBot2 的饥荒管理平台 (DMP) QQ 机器人插件，支持游戏信息查询、命令执行和消息互通功能，具有多级缓存系统和数据压缩归档功能。",
    usage="""🎮 DMP 饥荒管理平台机器人

🚀 快速开始：
• /菜单 - 显示所有功能
• /查房 - 搜索服务器房间  
• /物品 - 查询物品信息
• /房间 - 查看服务器状态

🏠 服务器查房：
• /查房 [关键词] - 智能搜索 (支持分页)
• /热门房间 - 查看活跃服务器
• /无密码房间 - 查看开放房间
• /快速查房 - 随机推荐房间

📖 物品查询：
• /物品 [物品名] - 查询Wiki信息
• /搜索物品 [关键词] - 搜索物品列表

💬 消息互通：
• /消息互通 - 开启QQ与游戏通信
• /关闭互通 - 关闭通信功能

⚙️ 管理功能（超级用户）：
• /管理菜单 - 管理员功能入口
• /系统状态 - 查看系统状态

⚡ 核心特性 (v0.4.5)：
• 🚀 多级缓存系统 - 性能提升10-50倍  
• 🎯 智能集群管理 - 自动选择最优集群
• 💬 实时消息互通 - QQ与游戏双向通信
• 📖 物品Wiki查询 - 支持2800+物品查询
• 🏠 亚太优化查房 - 专为亚太地区优化

💡 使用提示：
• 支持中英文命令和搜索
• 查房功能支持自动分页浏览
• 所有基础功能对所有用户开放
• 管理功能仅限超级用户使用

📞 获取帮助：
• /帮助 - 查看详细使用说明
• /菜单 - 查看完整功能列表""",
    
    type="application",
    homepage="https://github.com/uitok/nonebot-plugin-dst-qq",
    config=PluginConfig,
    supported_adapters={"~onebot.v11"},
)

# 使用简化的配置管理
from .config import get_config

# 导入子插件模块将在启动时进行，避免在插件加载时导入Alconna
# 这样可以避免与其他插件的加载冲突

async def init_components():
    """初始化各组件"""
    components = []
    
    try:
        # 延迟导入命令模块，避免在插件加载时导入Alconna
        print("🔍 开始导入子插件模块...")
        
        # 核心功能模块
        from .plugins import dmp_api, dmp_advanced, message_bridge
        print("✅ 核心功能模块导入成功")

        # 命令模块
        from . import main_menu, admin_commands, cluster_commands, debug_commands, item_commands, server_commands, server_browser_commands
        print("✅ 命令模块导入成功")
        
        print("✅ 所有子插件模块加载成功")
        
        # 配置系统
        config = get_config()
        print(f"✅ 配置加载: {config.dmp.base_url}")
        
        # 集群管理器
        from .simple_cache import get_cache
        from .cluster_manager import init_cluster_manager
        from .plugins.dmp_api import dmp_api
        
        cluster_manager = init_cluster_manager(dmp_api, get_cache())
        clusters = await cluster_manager.get_available_clusters()
        if clusters:
            print(f"✅ 集群管理器启动 ({len(clusters)} 个集群)")
        
        # 核心服务
        from .plugins.message_bridge import start_message_bridge
        await start_message_bridge()
        print("✅ 消息互通服务启动")
        
        from .database import item_wiki_manager, chat_history_db
        await item_wiki_manager.init_database()
        print("✅ 物品Wiki系统启动")
        
        await chat_history_db.init_database()
        print("✅ 数据库系统启动")
        
        from .scheduler import init_maintenance_scheduler
        await init_maintenance_scheduler()
        print("✅ 定时任务调度器启动")
        
    except Exception as e:
        print(f"⚠️ 组件初始化异常: {e}")

# 插件生命周期函数
def setup_lifecycle_handlers():
    """设置生命周期处理器"""
    driver = nonebot.get_driver()
    
    @driver.on_startup
    async def startup():
        """插件启动初始化"""
        print("🚀 DMP饥荒管理平台插件启动中...")
        await init_components()
        print("✅ 插件启动完成")

    @driver.on_shutdown
    async def shutdown():
        """插件关闭清理"""
        print("🔄 DMP插件正在关闭...")
        
        try:
            # 停止消息互通
            from .plugins.message_bridge import stop_message_bridge
            await stop_message_bridge()
            print("✅ 消息互通服务已停止")
            
            # 显示缓存统计
            try:
                from .simple_cache import get_cache
                cache = get_cache()
                stats = cache.get_stats()
                print(f"📊 缓存统计: 内存项目 {stats.get('memory_items', 0)}, 命中率 {stats.get('hit_rate', 0):.1%}")
            except Exception:
                print("📊 缓存统计获取失败")
            
        except Exception as e:
            print(f"⚠️ 清理异常: {e}")
        
        print("👋 DMP插件已关闭")

# 尝试设置生命周期处理器（如果NoneBot已初始化）
try:
    setup_lifecycle_handlers()
except ValueError:
    # NoneBot未初始化时延迟设置
    pass

