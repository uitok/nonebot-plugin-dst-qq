"""
插件基本功能测试
"""
import pytest
from nonebot import get_driver
from nonebot.plugin import require

# 测试插件是否可以正常导入
def test_plugin_import():
    """测试插件是否可以正常导入"""
    try:
        plugin = require("nonebot_plugin_dst_qq")
        assert plugin is not None
    except Exception as e:
        pytest.fail(f"插件导入失败: {e}")

# 测试插件元数据
def test_plugin_metadata():
    """测试插件元数据是否正确"""
    try:
        plugin = require("nonebot_plugin_dst_qq")
        # 检查插件是否有元数据
        assert hasattr(plugin, "__plugin_meta__")
        metadata = plugin.__plugin_meta__
        
        # 检查必要字段
        assert hasattr(metadata, "name")
        assert hasattr(metadata, "description")
        assert hasattr(metadata, "usage")
        assert hasattr(metadata, "type")
        assert hasattr(metadata, "homepage")
        
        # 检查类型
        assert metadata.type == "application"
        
    except Exception as e:
        pytest.fail(f"插件元数据检查失败: {e}")

# 测试配置类
def test_config_class():
    """测试配置类是否正确"""
    try:
        from nonebot_plugin_dst_qq.config import Config
        config = Config()
        assert isinstance(config, Config)
    except Exception as e:
        pytest.fail(f"配置类测试失败: {e}")

if __name__ == "__main__":
    pytest.main([__file__]) 