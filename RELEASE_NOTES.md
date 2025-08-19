# Release Notes - v0.2.6

## 🎉 重大更新

本次发布包含了多项重要改进和重构，提升了插件的稳定性和易用性。

## ✨ 新功能

- **集成 nonebot-plugin-localstore**: 使用 `localstore` 插件管理插件数据存储目录
- **简化配置系统**: 移除环境变量依赖，使用 NoneBot2 原生配置系统
- **优化依赖管理**: 移除 pydantic 版本限制，提升兼容性

## 🔧 技术改进

### 配置系统重构
- 移除 `Field` 和 `os` 导入
- 移除 `default_factory` 和默认值设置
- 移除 `model_post_init` 和 `_validate_config` 方法
- 简化配置类，依赖 NoneBot2 配置加载

### 数据存储优化
- 使用 `nonebot_plugin_localstore.get_plugin_data_dir` 获取存储目录
- 自动创建插件专用数据目录
- 提升数据存储的安全性和隔离性

### 函数参数优化
- 移除所有函数参数的默认值
- 确保参数传递的明确性和一致性
- 修复因参数变化导致的函数调用问题

## 🐛 问题修复

- 修复函数调用时缺少必需参数的问题
- 修复配置验证和加载逻辑
- 修复数据存储路径问题
- 修复命令参数处理问题

## 📚 文档更新

- 更新 `README.md` 使用说明
- 更新 `INSTALLATION.md` 安装指南
- 新增 `CONFIGURATION.md` 详细配置说明
- 新增 `PUBLISHING.md` 发布指南
- 更新 `CHANGELOG.md` 变更记录
- 更新插件元数据和使用说明

## 🚀 发布信息

- **版本**: 0.2.6
- **发布日期**: 2025-08-19
- **Python 版本**: >=3.9, <4.0
- **NoneBot2 版本**: >=2.4.0

## 📦 安装方式

```bash
pip install nonebot-plugin-dst-qq==0.2.6
```

## 🔄 升级说明

### 从 v0.2.5 升级
1. 更新插件: `pip install --upgrade nonebot-plugin-dst-qq`
2. 确保安装 `nonebot-plugin-localstore`: `pip install nonebot-plugin-localstore`
3. 检查配置文件，确保所有必需配置项都已设置
4. 重启机器人

### 配置变更
- 移除环境变量依赖
- 使用 NoneBot2 配置系统
- 数据存储自动使用 `localstore` 目录

## 🎯 下一步计划

- 添加更多游戏管理功能
- 优化消息互通性能
- 增加插件配置验证
- 完善错误处理和日志记录

## 📞 支持

如有问题或建议，请：
- 在 GitHub Issues 中反馈
- 联系维护者：ui_101@qq.com

---

**感谢所有贡献者和用户的支持！** 🎉
