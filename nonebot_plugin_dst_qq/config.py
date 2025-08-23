import json
import asyncio
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable, TypeVar, Union
from pydantic import BaseModel
import httpx
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from .logger import get_logger, LogCategory

T = TypeVar('T')

# ===== 配置常量 =====
DEFAULT_CONFIG_FILE = Path(__file__).parent / "app_config.json"
BACKUP_CONFIG_FILE = Path(__file__).parent / "app_config.backup.json"
TEMPLATE_CONFIG_FILE = Path(__file__).parent / "app_config.template.json"

# ================================================================================
# 饥荒联机版DMP QQ机器人 配置文件
# ================================================================================
# 
# 📖 使用说明：
# 1. 首次使用请修改 DMPConfig 中的服务器地址和令牌
# 2. 在 BotConfig 中设置超级用户QQ号
# 3. 其他配置使用默认值即可，高级用户可根据需要调整
# 
# 🔧 配置方式：
# - 方式1：直接编辑生成的 app_config.json 文件
# - 方式2：修改本文件中的默认值后重启机器人
# 
# ⚠️  重要提醒：
# - 请妥善保管您的DMP令牌，不要泄露给他人
# - 确保DMP服务器地址包含正确的端口号
# 
# ================================================================================

class ConfigSection(BaseModel):
    """配置节基类"""
    pass

class DMPConfig(ConfigSection):
    """DMP API配置"""
    
    base_url: str
    token: str
    timeout: float
    max_retries: int
    retry_delay: float
    auto_discover_clusters: bool
    cluster_cache_ttl: int

class BotConfig(ConfigSection):
    """QQ机器人配置"""
    
    superusers: List[str]
    admin_groups: List[str]
    allowed_groups: List[str]
    command_prefix: str
    enable_private_chat: bool
    enable_group_chat: bool

# ================================================================================
# 系统内部类和高级配置区域 - 以下配置一般情况下无需修改
# ================================================================================

class ConfigValidationError(Exception):
    """配置验证错误"""
    pass

class ConfigReloadError(Exception):
    """配置重载错误"""
    pass

class ConfigChangeHandler(FileSystemEventHandler):
    """配置文件变更监听器"""
    
    def __init__(self, config_manager: 'ConfigManager'):
        self.config_manager = config_manager
        self.logger = get_logger(__name__)
    
    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith('app_config.json'):
            self.logger.info(f"检测到配置文件变更: {event.src_path}", category=LogCategory.SYSTEM)
            # 延迟重载，避免文件正在写入时读取
            threading.Timer(1.0, self.config_manager._reload_config).start()

class CacheConfig(ConfigSection):
    """缓存配置"""
    
    memory_max_size: int
    memory_default_ttl: int
    file_cache_dir: str
    file_max_size: int
    file_default_ttl: int
    cleanup_interval: int
    auto_cleanup: bool

class MessageConfig(ConfigSection):
    """消息互通配置"""
    
    enable_message_bridge: bool
    sync_interval: float
    max_message_length: int
    default_chat_mode: str
    allow_group_chat: bool
    allow_private_chat: bool
    default_target_cluster: str
    default_target_world: str
    auto_select_world: bool
    filter_system_messages: bool
    filter_qq_messages: bool
    blocked_words: List[str]
    blocked_players: List[str]
    qq_to_game_template: str
    game_to_qq_template: str
    system_message_template: str
    enable_message_cache: bool
    cache_duration: int
    max_batch_size: int
    dedupe_window: int
    notify_connection_status: bool
    notify_new_users: bool
    show_player_join_leave: bool

class LoggingConfig(ConfigSection):
    """日志配置"""
    
    level: str
    format: str
    log_to_file: bool
    log_file_path: str
    max_file_size: int
    backup_count: int

class Config(BaseModel):
    """主配置类"""
    
    dmp: DMPConfig
    bot: BotConfig
    message: MessageConfig
    logging: LoggingConfig
    cache: CacheConfig
    version: str
    last_updated: str
    
    # 兼容性属性（保持向后兼容）
    @property
    def dmp_base_url(self) -> str:
        return self.dmp.base_url
    
    @property
    def dmp_token(self) -> str:
        return self.dmp.token
    
    @property
    def default_cluster(self) -> str:
        # 兼容性：返回空字符串，实际使用中由集群管理器动态获取
        return ""
    

    
    async def get_first_cluster(self) -> str:
        """获取第一个可用的集群名称（兼容性方法）"""
        try:
            headers = {
                "Authorization": self.dmp.token,
                "X-I18n-Lang": "zh"
            }
            
            async with httpx.AsyncClient(timeout=self.dmp.timeout) as client:
                response = await client.get(f"{self.dmp.base_url}/setting/clusters", headers=headers)
                response.raise_for_status()
                data = response.json()
                
                if data.get("code") == 200:
                    clusters = data.get("data", [])
                    if clusters:
                        return clusters[0].get("clusterName", "Master")
                
                return "Master"
        except Exception:
            return "Master"

class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_file: Optional[Path] = None):
        self.config_file = config_file or DEFAULT_CONFIG_FILE
        self.backup_file = BACKUP_CONFIG_FILE
        self.logger = get_logger(__name__)
        
        self._config: Optional[Config] = None
        self._observers: List[Callable[[Config], None]] = []
        self._file_observer: Optional[Observer] = None
        self._lock = threading.Lock()
        
        # 初始化配置
        self._load_config()
        
        # 启动文件监听
        self._start_file_watcher()
    
    def _start_file_watcher(self):
        """启动配置文件监听器"""
        try:
            self._file_observer = Observer()
            event_handler = ConfigChangeHandler(self)
            self._file_observer.schedule(
                event_handler, 
                str(self.config_file.parent), 
                recursive=False
            )
            self._file_observer.start()
            self.logger.info("配置文件监听器启动成功", category=LogCategory.SYSTEM)
        except Exception as e:
            self.logger.error(f"启动配置文件监听器失败: {e}", category=LogCategory.SYSTEM)
    
    def _load_config(self):
        """加载配置"""
        with self._lock:
            try:
                if self.config_file.exists():
                    # 从文件加载
                    with open(self.config_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    self._config = Config(**data)
                    self.logger.info(f"从文件加载配置成功: {self.config_file}", category=LogCategory.SYSTEM)
                else:
                    # 尝试从模板创建配置文件
                    if self._create_config_from_template():
                        # 重新加载刚创建的配置
                        with open(self.config_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        self._config = Config(**data)
                        self.logger.info(f"从模板创建配置文件成功: {self.config_file}", category=LogCategory.SYSTEM)
                    else:
                        # 创建默认配置
                        self._config = Config()
                        self._save_config()
                        self.logger.info("创建默认配置文件", category=LogCategory.SYSTEM)
                

                
            except Exception as e:
                self.logger.error(f"加载配置失败: {e}", category=LogCategory.SYSTEM)
                if self.backup_file.exists():
                    try:
                        # 尝试从备份恢复
                        with open(self.backup_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        self._config = Config(**data)
                        self.logger.info("从备份配置恢复成功", category=LogCategory.SYSTEM)
                    except Exception as backup_error:
                        self.logger.error(f"从备份恢复失败: {backup_error}", category=LogCategory.SYSTEM)
                        self._config = Config()
                else:
                    self._config = Config()
    
    def _create_config_from_template(self) -> bool:
        """从模板创建配置文件"""
        try:
            if TEMPLATE_CONFIG_FILE.exists():
                # 复制模板文件到配置文件
                import shutil
                shutil.copy2(TEMPLATE_CONFIG_FILE, self.config_file)
                
                # 显示配置指南
                print("\n" + "="*60)
                print("🎉 配置文件已生成！")
                print("="*60)
                print(f"📁 配置文件位置: {self.config_file}")
                print("\n📋 接下来请按照以下步骤配置：")
                print("1. 停止机器人 (Ctrl+C)")
                print("2. 编辑配置文件，修改必要设置：")
                print("   - dmp.base_url: 您的DMP服务器地址")
                print("   - dmp.token: 您的DMP访问令牌")
                print("   - bot.superusers: 您的QQ号")
                print("3. 保存文件并重新启动机器人")
                print("\n💡 提示：配置支持热重载，保存后1秒内自动生效")
                print("="*60)
                
                return True
            else:
                self.logger.warning("配置模板文件不存在", category=LogCategory.SYSTEM)
                return False
        except Exception as e:
            self.logger.error(f"从模板创建配置文件失败: {e}", category=LogCategory.SYSTEM)
            return False
    
    def _save_config(self):
        """保存配置"""
        try:
            # 创建备份
            if self.config_file.exists():
                import shutil
                shutil.copy2(self.config_file, self.backup_file)
            
            # 确保目录存在
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 更新时间戳
            self._config.last_updated = datetime.now().isoformat()
            
            # 保存到文件
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self._config.dict(), f, indent=2, ensure_ascii=False)
            
            self.logger.info("配置保存成功", category=LogCategory.SYSTEM)
            
        except Exception as e:
            self.logger.error(f"保存配置失败: {e}", category=LogCategory.SYSTEM)
            raise ConfigReloadError(f"保存配置失败: {e}")
    
    def _reload_config(self):
        """重载配置"""
        try:
            old_config = self._config
            self._load_config()
            
            # 通知观察者
            for observer in self._observers:
                try:
                    observer(self._config)
                except Exception as e:
                    self.logger.error(f"配置变更通知失败: {e}", category=LogCategory.SYSTEM)
            
            self.logger.info("配置热重载成功", category=LogCategory.SYSTEM)
            
        except Exception as e:
            self.logger.error(f"配置热重载失败: {e}", category=LogCategory.SYSTEM)
    
    def get_config(self) -> Config:
        """获取当前配置"""
        if self._config is None:
            self._load_config()
        return self._config
    
    def update_config(self, updates: Dict[str, Any]) -> bool:
        """更新配置"""
        try:
            with self._lock:
                # 创建新配置实例
                current_data = self._config.dict()
                
                # 递归更新配置
                def update_dict(target: dict, source: dict):
                    for key, value in source.items():
                        if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                            update_dict(target[key], value)
                        else:
                            target[key] = value
                
                update_dict(current_data, updates)
                
                # 创建新配置实例
                new_config = Config(**current_data)
                
                # 应用新配置
                self._config = new_config
                self._save_config()
                
                # 通知观察者
                for observer in self._observers:
                    try:
                        observer(self._config)
                    except Exception as e:
                        self.logger.error(f"配置变更通知失败: {e}", category=LogCategory.SYSTEM)
                
                self.logger.info("配置更新成功", category=LogCategory.SYSTEM)
                return True
                
        except Exception as e:
            self.logger.error(f"配置更新失败: {e}", category=LogCategory.SYSTEM)
            return False
    
    def add_observer(self, observer: Callable[[Config], None]):
        """添加配置变更观察者"""
        self._observers.append(observer)
    
    def remove_observer(self, observer: Callable[[Config], None]):
        """移除配置变更观察者"""
        if observer in self._observers:
            self._observers.remove(observer)
    

    
    async def test_dmp_connection(self) -> bool:
        """测试DMP连接"""
        try:
            config = self.get_config()
            headers = {
                "Authorization": config.dmp.token,
                "X-I18n-Lang": "zh"
            }
            
            async with httpx.AsyncClient(timeout=config.dmp.timeout) as client:
                response = await client.get(f"{config.dmp.base_url}/setting/clusters", headers=headers)
                response.raise_for_status()
                return True
                
        except Exception as e:
            self.logger.error(f"DMP连接测试失败: {e}", category=LogCategory.SYSTEM)
            return False
    
    def shutdown(self):
        """关闭配置管理器"""
        if self._file_observer:
            self._file_observer.stop()
            self._file_observer.join()
        self.logger.info("配置管理器已关闭", category=LogCategory.SYSTEM)

# 全局配置管理器实例
_config_manager: Optional[ConfigManager] = None

def get_config_manager() -> ConfigManager:
    """获取配置管理器实例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager

def get_config() -> Config:
    """获取当前配置（兼容性函数）"""
    return get_config_manager().get_config()

# NoneBot 插件配置类（不从环境变量读取）
class PluginConfig(BaseModel):
    """
    NoneBot 插件配置类
    
    这个类只是为了满足 NoneBot 的插件系统要求，实际配置从 app_config.json 读取
    """
    pass

# 兼容性函数
def get_plugin_config(config_class):
    """兼容NoneBot的get_plugin_config"""
    return get_config()