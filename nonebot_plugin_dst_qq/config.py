from pathlib import Path
from typing import List
from pydantic import BaseModel

class DMPConfig(BaseModel):
    """DMP API配置"""
    base_url: str = "http://localhost:8080/v1"
    token: str = ""
    timeout: float = 30.0
    max_retries: int = 3
    retry_delay: float = 1.0
    auto_discover_clusters: bool = True
    cluster_cache_ttl: int = 300

class BotConfig(BaseModel):
    """QQ机器人配置"""
    superusers: List[str] = []
    admin_groups: List[str] = []
    allowed_groups: List[str] = []
    command_prefix: str = "/"
    enable_private_chat: bool = True
    enable_group_chat: bool = True

class MessageConfig(BaseModel):
    """消息互通配置"""
    enable_message_bridge: bool = True
    sync_interval: float = 5.0
    max_message_length: int = 200
    default_chat_mode: str = "all"
    allow_group_chat: bool = True
    allow_private_chat: bool = True
    default_target_cluster: str = ""
    default_target_world: str = "overworld"
    auto_select_world: bool = True
    filter_system_messages: bool = False
    filter_qq_messages: bool = False
    blocked_words: List[str] = []
    blocked_players: List[str] = []
    qq_to_game_template: str = "[QQ] {qq_name}({qq_id}): {message}"
    game_to_qq_template: str = "[{world}] {player}: {message}"
    system_message_template: str = "[系统] {message}"
    enable_message_cache: bool = True
    cache_duration: int = 300
    max_batch_size: int = 10
    dedupe_window: int = 30
    notify_connection_status: bool = True
    notify_new_users: bool = True
    show_player_join_leave: bool = True

class CacheConfig(BaseModel):
    """缓存配置"""
    memory_max_size: int = 1000
    memory_default_ttl: int = 300
    file_max_size: int = 10000
    file_default_ttl: int = 3600
    cleanup_interval: int = 300
    auto_cleanup: bool = True

class LoggingConfig(BaseModel):
    """日志配置"""
    level: str = "INFO"
    log_to_file: bool = True
    max_file_size: int = 10485760
    backup_count: int = 5

class Config(BaseModel):
    """主配置类"""
    dmp: DMPConfig = DMPConfig()
    bot: BotConfig = BotConfig()
    message: MessageConfig = MessageConfig()
    logging: LoggingConfig = LoggingConfig()
    cache: CacheConfig = CacheConfig()
    version: str = "0.4.5"

# 获取目录的简单函数（延迟加载localstore）
def get_config_dir() -> Path:
    """获取配置目录 - 使用localstore插件"""
    try:
        from nonebot import require
        require("nonebot_plugin_localstore")
        import nonebot_plugin_localstore as store
        # 使用localstore的配置目录
        return store.get_plugin_config_dir()
    except Exception:
        # 备用方案：当前工作目录下的config文件夹
        return Path.cwd() / "config"

def get_cache_dir() -> Path:
    """获取缓存目录 - 使用localstore插件"""
    try:
        from nonebot import require
        require("nonebot_plugin_localstore")
        import nonebot_plugin_localstore as store
        # 使用localstore的缓存目录
        return store.get_plugin_cache_dir()
    except Exception:
        # 备用方案：当前工作目录下的cache文件夹
        return Path.cwd() / "cache"

def get_data_dir() -> Path:
    """获取数据目录 - 使用localstore插件"""
    try:
        from nonebot import require
        require("nonebot_plugin_localstore")
        import nonebot_plugin_localstore as store
        # 使用localstore的数据目录
        return store.get_plugin_data_dir()
    except Exception:
        # 备用方案：当前工作目录下的data文件夹
        return Path.cwd() / "data"

# NoneBot 插件配置类（空实现）
class PluginConfig(BaseModel):
    """NoneBot 插件配置类"""
    pass

# 全局配置实例
_config = None

def _load_config_from_file() -> Config:
    """从文件加载配置"""
    import json
    from pathlib import Path
    
    # 配置文件搜索优先级
    config_paths = [
        # 1. 机器人目录（当前工作目录）下的 config/app_config.json
        Path.cwd() / "config" / "app_config.json",
        # 2. localstore 插件配置目录
        get_config_dir() / "app_config.json",
        # 3. localstore 插件数据目录（向后兼容）
        get_data_dir() / "app_config.json"
    ]
    
    for config_file in config_paths:
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                print(f"✅ 配置已从 {config_file} 加载")
                return Config(**config_data)
            except Exception as e:
                print(f"警告：无法加载配置文件 {config_file}: {e}")
                continue
    
    print("⚠️ 未找到配置文件，使用默认配置")
    return Config()

def get_config() -> Config:
    """获取配置"""
    global _config
    if _config is None:
        _config = _load_config_from_file()
    return _config