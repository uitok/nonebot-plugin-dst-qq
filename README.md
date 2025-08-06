# nonebot-plugin-dst-qq

[![PyPI](https://img.shields.io/pypi/v/nonebot-plugin-dst-qq)](https://pypi.org/project/nonebot-plugin-dst-qq/)
[![Python](https://img.shields.io/pypi/pyversions/nonebot-plugin-dst-qq)](https://pypi.org/project/nonebot-plugin-dst-qq/)
[![License](https://img.shields.io/pypi/l/nonebot-plugin-dst-qq)](https://pypi.org/project/nonebot-plugin-dst-qq/)

基于 NoneBot2 的饥荒管理平台 (DMP) QQ 机器人插件，支持游戏信息查询、命令执行和消息互通功能。

## ✨ 功能特性

### 🎮 基础功能
- **世界信息查询** - 获取游戏世界状态、运行信息
- **房间信息查询** - 查看房间设置、季节信息、玩家状态
- **系统信息监控** - 监控服务器CPU、内存使用情况
- **玩家管理** - 查看在线玩家列表和详细信息
- **直连信息** - 获取服务器直连代码

### 🔧 管理功能
- **备份管理** - 查看和创建游戏备份文件
- **命令执行** - 在游戏中执行控制台命令
- **世界回档** - 支持1-5天的世界回档功能
- **世界重置** - 重置指定世界（谨慎使用）
- **聊天历史** - 查看游戏内聊天记录
- **聊天统计** - 统计聊天数据和使用情况

### 💬 消息互通
- **双向通信** - QQ消息与游戏内消息双向互通
- **实时同步** - 自动同步游戏内最新消息到QQ
- **用户管理** - 支持多用户独立的消息互通设置
- **消息过滤** - 智能过滤和格式化消息内容

## 📦 安装

### 使用 nb-cli 安装（推荐）

```bash
nb plugin install nonebot-plugin-dst-qq
```

### 使用 pip 安装

```bash
pip install nonebot-plugin-dst-qq
```

## ⚙️ 配置

### 环境变量配置（必需）

在 `.env` 文件中添加以下配置：

```env
# DMP 服务器配置（必需）
SUPERUSERS=["123456789"]（可选）
DMP_BASE_URL=http://your-dmp-server:port/v1
DMP_TOKEN=your-jwt-token
DEFAULT_CLUSTER=your-cluster-name

# OneBot 配置（必需）
ONEBOT_WS_URLS=["ws://your-onebot-server:port"]
ONEBOT_ACCESS_TOKEN=your-access-token
```

### 插件配置

在 `bot.py` 或 `pyproject.toml` 中加载插件：

**注意：** 以上所有环境变量都是必需的，未设置会导致插件启动失败。




```toml
# pyproject.toml
[tool.nonebot]
plugins = ["nonebot_plugin_dst_qq"]
```

## 🚀 使用方法

### 基础命令

| 命令 | 别名 | 功能 |
|------|------|------|
| `/世界` | `/world` | 获取世界信息 |
| `/房间` | `/room` | 获取房间信息 |
| `/系统` | `/sys` | 获取系统信息 |
| `/玩家` | `/players` | 获取在线玩家列表 |
| `/直连` | `/connection` | 获取服务器直连信息 |
| `/菜单` | `/help` | 显示帮助信息 |

### 管理命令

| 命令 | 功能 |
|------|------|
| `/管理命令` | 显示管理员功能菜单 |
| `/查看备份` | 获取备份文件列表 |
| `/创建备份` | 手动创建备份 |
| `/执行 <世界> <命令>` | 执行游戏命令 |
| `/回档 <天数>` | 回档指定天数 (1-5天) |
| `/重置世界 [世界名称]` | 重置世界 (默认Master) |
| `/聊天历史 [世界名] [行数]` | 获取聊天历史 |
| `/聊天统计` | 获取聊天历史统计信息 |

### 消息互通功能

| 命令 | 功能 |
|------|------|
| `消息互通` | 开启游戏内消息与QQ消息互通 |
| `关闭互通` | 关闭消息互通功能 |
| `互通状态` | 查看当前互通状态 |
| `最新消息` | 获取游戏内最新消息 |

## 📋 使用示例

### 基础查询
```
/世界          # 获取世界信息
/房间          # 获取房间信息
/玩家          # 查看在线玩家
```

### 管理操作
```
/执行 World4 c_listallplayers()  # 执行游戏命令
/回档 2                          # 回档2天
/创建备份                        # 创建备份
/查看备份                        # 查看备份列表
```

### 消息互通
```
消息互通        # 开启消息互通
最新消息        # 获取最新游戏消息
关闭互通        # 关闭消息互通
```

## 🔧 开发

### 环境要求

- Python >= 3.9
- NoneBot2 >= 2.4.0
- OneBot V11 适配器

### 本地开发

```bash
# 克隆仓库
git clone https://github.com/uitok/nonebot-plugin-dst-qq.git
cd nonebot-plugin-dst-qq

# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest
```

## 📝 更新日志

### v0.2.4

#### 🎉 新功能
- ✨ 新增 `/查看备份` 命令，替代原有的 `/备份` 命令
- 🎨 优化备份列表显示格式，支持文件大小自动转换（KB/MB/GB）
- 📊 添加磁盘使用率显示
- 🔧 改进备份文件信息展示，包含创建时间、文件大小、游戏周期

#### 🐛 修复
- 🔧 修复插件加载时的相对导入问题
- 🛠️ 解决 `name 'config' is not defined` 错误
- 🔧 统一配置获取方式，使用 `get_config()` 函数
- 🛠️ 修复备份列表数据处理中的切片错误

#### 🎨 优化
- 📱 改进消息显示格式，使用emoji和分隔线提升可读性
- 🔧 优化错误处理和类型检查
- 📝 更新管理命令菜单，反映新的命令名称
- 🎯 提升插件稳定性和用户体验

#### 🔧 技术改进
- 🔧 重构插件加载机制，使用 `require()` 函数
- 🛠️ 简化相对导入逻辑，移除复杂的 `sys.path` 操作
- 📦 更新项目结构，符合 NoneBot2 插件发布规范
- 🔧 优化依赖注入和配置管理

### v0.2.3
- 初始版本发布
- 基础功能实现
- 消息互通功能

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

- [NoneBot2](https://nonebot.dev/) - 优秀的机器人框架
- [OneBot](https://onebot.dev/) - 统一的聊天机器人应用接口标准
- [DMP](https://github.com/your-dmp-repo) - 饥荒管理平台

## 📞 联系方式

- 作者：uitok
- 邮箱：ui_101@qq.com
- 项目主页：[https://github.com/uitok/nonebot-plugin-dst-qq](https://github.com/uitok/nonebot-plugin-dst-qq)

---

如果这个项目对您有帮助，请给个 ⭐️ 支持一下！
