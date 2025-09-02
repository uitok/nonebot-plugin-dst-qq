"""
配置迁移脚本
帮助用户从环境变量配置迁移到新的配置文件系统
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional

from nonebot import logger

def migrate_from_env() -> Optional[Dict[str, Any]]:
    """从环境变量迁移配置到新的配置格式"""
    
    logger.info("开始从环境变量迁移配置")
    
    # 检查是否有环境变量配置
    env_vars = {
        'DMP_BASE_URL': os.getenv('DMP_BASE_URL'),
        'DMP_TOKEN': os.getenv('DMP_TOKEN'),
        'DEFAULT_CLUSTER': os.getenv('DEFAULT_CLUSTER'),
        'DEBUG': os.getenv('DEBUG'),
        'SUPERUSERS': os.getenv('SUPERUSERS')
    }
    
    # 过滤掉None值
    env_vars = {k: v for k, v in env_vars.items() if v is not None}
    
    if not env_vars:
        logger.info("未发现环境变量配置，跳过迁移")
        return None
    
    logger.info(f"发现 {len(env_vars)} 个环境变量配置项")
    
    try:
        # 创建新的配置结构
        new_config = {
            "version": "1.0.0",
            "dmp": {},
            "bot": {},
            "cache": {},
            "message": {},
            "logging": {}
        }
        
        # DMP配置迁移
        if 'DMP_BASE_URL' in env_vars:
            new_config['dmp']['base_url'] = env_vars['DMP_BASE_URL']
            logger.info(f"迁移DMP服务器地址: {env_vars['DMP_BASE_URL']}")
        
        if 'DMP_TOKEN' in env_vars:
            new_config['dmp']['token'] = env_vars['DMP_TOKEN']
            logger.info("迁移DMP API令牌")
        
        if 'DEFAULT_CLUSTER' in env_vars:
            new_config['dmp']['default_cluster'] = env_vars['DEFAULT_CLUSTER']
            logger.info(f"迁移默认集群: {env_vars['DEFAULT_CLUSTER']}")
        
        # 机器人配置迁移
        if 'SUPERUSERS' in env_vars:
            try:
                # 尝试解析超级用户列表
                superusers_str = env_vars['SUPERUSERS']
                if superusers_str.startswith('[') and superusers_str.endswith(']'):
                    # JSON格式
                    superusers = json.loads(superusers_str)
                else:
                    # 逗号分隔格式
                    superusers = [user.strip().strip('"\'') for user in superusers_str.split(',')]
                
                new_config['bot']['superusers'] = superusers
                logger.info(f"迁移超级用户列表: {len(superusers)} 个用户")
            except Exception as e:
                logger.warning(f"解析超级用户列表失败: {e}")
        
        # 日志配置迁移
        if 'DEBUG' in env_vars:
            debug_mode = env_vars['DEBUG'].lower() in ('true', '1', 'yes', 'on')
            new_config['logging']['level'] = 'DEBUG' if debug_mode else 'INFO'
            logger.info(f"迁移调试模式: {'DEBUG' if debug_mode else 'INFO'}")
        
        logger.success("配置迁移完成")
        return new_config
        
    except Exception as e:
        logger.error(f"配置迁移失败: {e}")
        return None

def create_migration_backup():
    """创建环境变量配置的备份"""
    try:
        backup_file = Path(__file__).parent / "env_backup.json"
        
        env_backup = {}
        for key in os.environ:
            if key.startswith(('DMP_', 'DEFAULT_', 'DEBUG', 'SUPERUSERS')):
                env_backup[key] = os.environ[key]
        
        if env_backup:
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(env_backup, f, indent=2, ensure_ascii=False)
            
            logger.info(f"环境变量备份已保存到: {backup_file}")
            return backup_file
        else:
            logger.info("未发现需要备份的环境变量")
            return None
            
    except Exception as e:
        logger.error(f"创建环境变量备份失败: {e}")
        return None

def show_migration_guide() -> str:
    """显示迁移指南"""
    
    guide = """
🔄 配置系统升级指南

📋 新配置系统特性:
  ✅ 统一的配置文件管理
  ✅ 配置验证和错误检查  
  ✅ 配置热重载功能
  ✅ 配置分类管理
  ✅ 敏感信息保护

🔧 迁移步骤:

1️⃣ 备份现有配置:
   - 环境变量会自动备份到 env_backup.json

2️⃣ 配置文件位置:
   - 新配置文件: src/plugins/nonebot_plugin_dst_qq/app_config.json
   - 备份文件: src/plugins/nonebot_plugin_dst_qq/app_config.backup.json

3️⃣ 配置结构:
   - dmp: DMP API相关配置
   - bot: 机器人基础配置  
   - cache: 缓存系统配置
   - message: 消息互通配置
   - logging: 日志系统配置

4️⃣ 迁移后操作:
   - 使用 '@机器人 配置状态' 检查配置
   - 使用 '@机器人 验证配置' 验证配置
   - 使用 '@机器人 测试连接' 测试DMP连接

⚠️ 重要提醒:
   - 配置文件支持热重载，修改后自动生效
   - 无效配置会自动回滚到备份
   - 建议定期备份配置文件
   - 敏感信息（如API令牌）请妥善保管

💡 配置管理命令:
   - @机器人 配置帮助 - 查看详细帮助
   - @机器人 配置状态 - 查看当前状态
   - @机器人 查看配置 - 查看配置内容
"""
    
    return guide

def auto_migrate_if_needed():
    """如果需要的话自动执行迁移"""
    
    config_file = Path(__file__).parent / "app_config.json"
    
    # 如果配置文件不存在，尝试从环境变量迁移
    if not config_file.exists():
        logger.info("配置文件不存在，尝试从环境变量迁移")
        
        # 创建备份
        backup_file = create_migration_backup()
        
        # 执行迁移
        migrated_config = migrate_from_env()
        
        if migrated_config:
            try:
                # 保存迁移后的配置
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump(migrated_config, f, indent=2, ensure_ascii=False)
                
                logger.success(f"配置迁移成功，新配置已保存到: {config_file}")
                
                # 显示迁移指南
                print("\n" + "="*60)
                print("🎉 配置系统升级完成！")
                print("="*60)
                print(show_migration_guide())
                print("="*60)
                
                return True
                
            except Exception as e:
                logger.error(f"保存迁移配置失败: {e}")
                return False
        else:
            logger.info("未发现环境变量配置，创建默认配置")
            return False
    else:
        logger.info("配置文件已存在，跳过迁移")
        return False

if __name__ == "__main__":
    # 可以直接运行此脚本进行迁移
    auto_migrate_if_needed()


