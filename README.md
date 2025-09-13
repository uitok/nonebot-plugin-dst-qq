# nonebot-plugin-dst-qq

[![PyPI](https://img.shields.io/pypi/v/nonebot-plugin-dst-qq)](https://pypi.org/project/nonebot-plugin-dst-qq/)
[![Python](https://img.shields.io/pypi/pyversions/nonebot-plugin-dst-qq)](https://pypi.org/pypi/nonebot-plugin-dst-qq/)
[![License](https://img.shields.io/pypi/l/nonebot-plugin-dst-qq)](https://pypi.org/project/nonebot-plugin-dst-qq/)
[![NoneBot](https://img.shields.io/badge/nonebot-2.4.0+-red.svg)](https://nonebot.dev/)

🎮 功能丰富的饥荒管理平台 (DMP) QQ 机器人插件，基于 NoneBot2 和 Alconna 构建，提供服务器管理、消息互通、物品百科等全方位功能。

## 🚀 快速开始

**新用户？** 查看 **[完整安装指南 (INSTALLATION.md)](INSTALLATION.md)** 立即体验！包含从零开始的详细教程和故障排除。

## ✨ 功能特性

### 🎮 核心功能
- **🏠 房间信息** - 综合显示服务器状态、世界信息、玩家列表
- **🌍 世界管理** - 世界状态监控、备份管理、回档重置
- **👥 玩家管理** - 在线玩家列表、管理员列表、封禁白名单
- **💻 系统监控** - CPU/内存使用率、服务器负载状态
- **🔗 服务器浏览** - 官方服务器列表查询和筛选

### 💬 消息互通
- **双向通信** - QQ消息与游戏内消息实时双向互通
- **智能路由** - 支持私聊/群聊模式，自动消息过滤
- **会话管理** - 多用户独立会话，自动超时清理
- **消息去重** - 防止消息重复发送，优化用户体验

### 🔍 物品百科 
- **智能搜索** - 支持中英文搜索，覆盖2863个饥荒物品（包含角色）
- **Wiki截图** - Selenium自动截图，精准捕获Wiki正文内容
- **分离截图** - 信息栏和正文内容分开截图，查看更清晰
- **自适应大小** - 智能计算截图尺寸，避免内容截断
- **快速响应** - 双层缓存系统，毫秒级查询速度
- **模糊匹配** - 支持模糊搜索和多结果选择
- **内容优化** - 自动隐藏导航栏、侧边栏等无关元素

### 🛠️ 管理功能
- **集群管理** - 动态集群切换和状态监控
- **缓存管理** - 智能缓存统计和清理功能
- **服务器浏览** - 查询DST官方服务器列表
- **配置管理** - 动态配置更新，热重载支持
- **调试工具** - 完整的调试和监控命令集

### ⚡ 性能优化
- **🧠 双层缓存** - 内存+文件缓存，减少70%重复请求
- **🗄️ 连接池** - 统一数据库连接管理，提升30%性能
- **📦 模块化** - 清晰架构设计，代码量减少33%
- **🔄 异步处理** - 全异步设计，支持高并发访问

## 📦 安装

### 使用 nb-cli 安装 (推荐)
```bash
nb plugin install nonebot-plugin-dst-qq
```

### 使用 pip 安装
```bash
pip install nonebot-plugin-dst-qq
```

### 使用 poetry 安装
```bash
poetry add nonebot-plugin-dst-qq
```

## ⚙️ 配置

### 1. 环境变量配置
在 `.env` 文件中添加：
```env
# OneBot V11 配置 (必需)
ONEBOT_WS_URLS=["ws://your-onebot-server:port"]
ONEBOT_ACCESS_TOKEN="your-access-token"

# 超级用户 (必需)
SUPERUSERS=["your-qq-number"]

# 调试模式 (可选)
DEBUG=true
LOG_LEVEL=DEBUG
```

### 2. DMP 配置文件
插件会自动在以下位置创建配置文件：
- `config/config/app_config.json` - 主配置文件
- `nonebot_plugin_dst_qq/app_config.template.json` - 配置模板

配置示例：
```json
{
    "dmp_url": "http://your-dmp-server:port/v1",
    "auth": {
        "username": "your-username",
        "password": "your-password"
    },
    "clusters": ["YourClusterName"],
    "cache_settings": {
        "enable_cache": true,
        "cache_ttl": 300
    }
}
```

## 🎯 命令使用

### 基础命令
| 命令 | 别名 | 功能 | 示例 |
|------|------|------|------|
| `/房间` | `room`, `状态` | 综合服务器信息 | `/房间` |
| `/世界` | `world`, `worlds` | 世界状态列表 | `/世界` |
| `/玩家` | `players`, `在线` | 在线玩家列表 | `/玩家` |
| `/系统` | `sys`, `system` | 系统状态信息 | `/系统` |
| `/查房 [<关键词>]` | `服务器列表`, `server_list` | 查询官方服务器 | `/查房 PVP` |
| `/集群状态` | `cluster`, `集群列表` | 查看集群信息 | `/集群状态` |

### 物品查询
| 命令 | 别名 | 功能 | 示例 |
|------|------|------|------|
| `/物品 <关键词>` | `查物品`, `item`, `wiki`, `查` | 物品Wiki截图查询 | `/查 大理石` |
| `/物品分离 <关键词>` | `分离物品`, `物品详情`, `详细物品` | 分离截图信息栏和正文 | `/物品分离 大理石` |
| `/搜索物品 <关键词>` | `search`, `搜物品` | 物品搜索列表 | `/搜索物品 石头` |
| `/物品统计` | `item_stats`, `物品数量` | 物品数据统计 | `/物品统计` |
| `/重载物品` | `reload_items` | 重载物品数据(管理员) | `/重载物品` |

### 消息互通
| 命令 | 别名 | 功能 | 示例 |
|------|------|------|------|
| `/消息互通` | `bridge`, `互通` | 开启消息互通 | `/消息互通` |
| `/关闭互通` | `stop_bridge` | 关闭消息互通 | `/关闭互通` |
| `/互通状态` | `bridge_status` | 查看互通状态 | `/互通状态` |

## 📝 功能示例

### Wiki截图查询

输入：
```
/物品 大理石
```

机器人会：
1. 🔍 搜索匹配的物品
2. 🖼️ 自动截取Wiki页面正文内容
3. 📷 返回高质量截图图片

### 服务器浏览

输入：
```
/查房 PVP
```

显示结果：
```
🏠 找到5个服务器 (搜索: PVP)

1. [PVP] Klei Official Server
   模式: Survival | 玩家: 12/16 | 地区: 亚太
   季节: 夏天 15天 | 密码: 无

2. [PVP Arena] Combat Zone  
   模式: Endless | 玩家: 8/20 | 地区: 美洲
   季节: 秋天 3天 | 密码: 无

...
```

### 集群管理

输入：
```
/集群状态
```

显示结果：
```
📊 集群状态概览

✅ 当前集群: Master
📊 可用集群: Master, Caves
🔍 最后检查: 2分钟前

集群详情:
• Master: 正常运行 | 5个世界
• Caves: 正常运行 | 2个世界
```


### 管理员命令
| 命令 | 功能 | 示例 |
|------|------|------|
| `/缓存状态` | 显示缓存统计信息 | `/缓存状态` |
| `/清理缓存` | 清空所有缓存 | `/清理缓存` |
| `/切换集群 <名称>` | 切换操作集群 | `/切换集群 Master` |
| `/重载配置` | 重新加载配置 | `/重载配置` |

### 调试命令
| 命令 | 功能 | 示例 |
|------|------|------|
| `/测试文字` | 测试消息发送 | `/测试文字` |
| `/调试信息` | 显示调试信息 | `/调试信息` |
| `/版本信息` | 显示版本信息 | `/版本信息` |

## 🏗️ 架构设计

### 模块化结构
```
nonebot_plugin_dst_qq/
├── __init__.py              # 🚀 插件入口和生命周期管理
├── database/                # 🗄️ 数据库模块
│   ├── __init__.py          # 统一接口和兼容层
│   ├── connection.py        # 连接池管理器
│   └── models.py           # 数据模型层
├── plugins/                 # 🔌 核心插件
│   ├── dmp_api.py          # DMP API集成
│   ├── dmp_advanced.py     # DMP高级功能
│   └── message_bridge.py   # 消息互通桥接
├── 命令模块/                # 🎯 命令处理器
│   ├── admin_commands.py   # 管理员命令
│   ├── cluster_commands.py # 集群管理命令
│   ├── debug_commands.py   # 调试命令
│   ├── item_commands.py    # 物品查询命令
│   └── server_commands.py  # 服务器命令
├── 核心组件/               # 🧠 核心功能组件
│   ├── simple_cache.py     # 简化缓存系统
│   ├── message_utils.py    # 消息工具
│   ├── server_browser.py   # 服务器浏览器
│   ├── cluster_manager.py  # 集群管理器
│   └── wiki_screenshot.py  # Wiki截图系统
└── 工具模块/              # 🛠️ 通用工具
    ├── config.py           # 配置管理
    ├── utils.py            # 通用工具
    ├── scheduler.py        # 任务调度
    └── item_data.py        # 物品数据
```

### 性能特性
- **🚀 异步优先**: 全异步设计，支持高并发
- **🧠 智能缓存**: LRU算法，内存+文件双层缓存
- **🔗 连接池**: 数据库连接复用，减少开销
- **📦 模块化**: 按需加载，降低内存占用
- **⚡ 优化算法**: 缓存命中率90%+，响应时间<100ms

## 🔧 高级配置

### 缓存配置
```json
{
    "cache_settings": {
        "enable_cache": true,
        "memory_cache_size": 1000,
        "file_cache_ttl": 3600,
        "api_cache_ttl": 300
    }
}
```

### 数据库配置
```json
{
    "database_settings": {
        "chat_history_days": 30,
        "auto_cleanup": true,
        "backup_enabled": true
    }
}
```

### 消息互通配置
```json
{
    "bridge_settings": {
        "message_filter": true,
        "max_message_length": 200,
        "auto_reconnect": true,
        "session_timeout": 1800
    }
}
```

## 🐛 故障排除

### 常见问题

**1. 插件无法连接DMP服务器**
```bash
# 检查配置文件
cat config/config/app_config.json
# 测试网络连通性
curl -X GET "http://your-dmp-server:port/v1/auth/login"
```

**2. 消息互通不工作**  
```bash
# 检查OneBot连接状态
# 确认超级用户配置正确
# 查看日志错误信息
```

**3. 物品查询失败**
```bash
# 重载物品数据
/重载物品
# 检查数据库文件
ls -la data/database/
```

### 日志位置
- NoneBot2日志: 控制台输出
- 插件日志: 使用 `LOG_LEVEL=DEBUG` 查看详细日志
- 数据库日志: `data/database/` 目录

## 🤝 贡献指南

欢迎贡献代码！请遵循以下步骤：

1. Fork 项目
2. 创建功能分支: `git checkout -b feature/amazing-feature`
3. 提交更改: `git commit -m 'Add amazing feature'`
4. 推送分支: `git push origin feature/amazing-feature`
5. 创建 Pull Request

### 开发环境
```bash
# 克隆项目
git clone https://github.com/uitok/nonebot-plugin-dst-qq.git
cd nonebot-plugin-dst-qq

# 安装依赖
poetry install
# 或
pip install -r requirements.txt

# 运行测试
pytest tests/
```

## 📋 版本历史

查看 [CHANGELOG.md](CHANGELOG.md) 了解详细更新历史。

### 最新版本 v0.4.5
- 🖼️ 全新Wiki截图系统，智能内容捕获
- 🔍 增强物品搜索功能，支持快速查询
- 🌐 新增服务器浏览功能，支持DST官方服务器列表
- 🗄️ 完善数据库连接池管理
- ⚡ 优化缓存系统，提升响应速度
- 📦 完整模块化架构，25个核心文件

## 📄 许可证

本项目采用 [MIT](LICENSE) 许可证。

## 🙏 致谢

- [NoneBot2](https://nonebot.dev/) - 优秀的Python异步机器人框架
- [Alconna](https://github.com/ArcletProject/Alconna) - 强大的命令解析器
- [OneBot](https://onebot.dev/) - 聊天机器人应用接口标准

## 📞 联系方式

- 作者: uitok
- 邮箱: ui_101@qq.com  
- 项目地址: https://github.com/uitok/nonebot-plugin-dst-qq
- 问题反馈: https://github.com/uitok/nonebot-plugin-dst-qq/issues

---

如果这个项目对你有帮助，欢迎给一个 ⭐ Star！