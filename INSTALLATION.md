# 完整安装指南 / Installation Guide

本文档提供 nonebot-plugin-dst-qq 插件的完整安装和配置指南，包含从零开始的详细步骤。

## 📋 系统要求

### 最低要求
- **Python**: 3.9+ (推荐 3.11+)
- **系统内存**: 1GB+ (因为Selenium需求) 
- **磁盘空间**: 500MB+ (包括浏览器驱动)
- **网络**: 能访问GitHub、PyPI和饥荒Wiki
- **系统组件**: Chrome/Chromium浏览器(用于Wiki截图)

### 推荐环境
- **Python**: 3.11 或 3.12
- **系统**: Ubuntu 20.04+, Windows 10+, macOS 12+
- **内存**: 2GB+ (用于稳定的Wiki截图功能)
- **CPU**: 2核心+ (支持并发处理)
- **存储**: SSD磁盘(提升数据库性能)

## 🚀 快速安装

### 方法一：使用 nb-cli (推荐)

1. **安装 NoneBot2 CLI**
```bash
pip install nb-cli
```

2. **创建机器人项目**
```bash
nb create my-dst-bot
cd my-dst-bot
```

3. **安装插件**
```bash
nb plugin install nonebot-plugin-dst-qq
```

4. **启动机器人**
```bash
nb run
```

### 方法二：手动安装

1. **创建项目目录**
```bash
mkdir my-dst-bot
cd my-dst-bot
```

2. **安装依赖**
```bash
# 使用 pip
pip install nonebot2[fastapi] nonebot-adapter-onebot nonebot-plugin-dst-qq

# 或者手动安装全部依赖
pip install nonebot2[fastapi] nonebot-adapter-onebot nonebot-plugin-alconna \
            nonebot-plugin-localstore nonebot-plugin-apscheduler nonebot-plugin-waiter \
            httpx pydantic aiosqlite selenium

# 使用 poetry (推荐)
poetry init
poetry add nonebot2[fastapi] nonebot-adapter-onebot nonebot-plugin-dst-qq
```

**注意：NoneBot插件需要手动安装**

由于NoneBot2的插件加载机制，以下插件需要手动安装：
```bash
# 必需的NoneBot插件
pip install nonebot-plugin-alconna      # 命令解析
pip install nonebot-plugin-localstore  # 本地存储
pip install nonebot-plugin-apscheduler # 任务调度
pip install nonebot-plugin-waiter      # 会话等待

# 验证安装
python -c "import nonebot_plugin_alconna, nonebot_plugin_localstore, nonebot_plugin_apscheduler, nonebot_plugin_waiter; print('所有插件安装成功')"
```

3. **创建启动文件**
创建 `bot.py`:
```python
import nonebot
from nonebot.adapters.onebot.v11 import Adapter as OneBotV11Adapter

# 初始化 NoneBot
nonebot.init()

# 注册适配器
driver = nonebot.get_driver()
driver.register_adapter(OneBotV11Adapter)

# 加载插件
nonebot.load_plugin("nonebot_plugin_dst_qq")

if __name__ == "__main__":
    nonebot.run()
```

## ⚙️ 详细配置

### 1. 环境变量配置

创建 `.env` 文件：
```env
# === 必需配置 ===

# NoneBot2 基本配置
ENVIRONMENT=prod
HOST=127.0.0.1
PORT=8080
LOG_LEVEL=INFO

# OneBot V11 连接配置
ONEBOT_WS_URLS=["ws://127.0.0.1:3001"]
# ONEBOT_ACCESS_TOKEN="your-access-token"  设置了token

# 超级用户 (你的QQ号)
SUPERUSERS=["123456789"]

# === 可选配置 ===

# 调试模式 (开发时使用)
# DEBUG=true
# LOG_LEVEL=DEBUG

# 命令前缀
COMMAND_START=["/", ""]
COMMAND_SEP=["."]

# 会话过期时间 (秒)
SESSION_EXPIRE_TIMEOUT=120
```

### 2. DMP 服务器配置

插件会自动创建配置文件，你需要编辑：

#### 主配置文件位置

插件会按以下优先级查找配置目录：
1. **工作目录下的config目录** (推荐)
   ```
   config/app_config.json
   ```
2. **nonebot-plugin-localstore 目录** (系统默认路径)
   - Linux/macOS: `~/.config/nonebot2/nonebot_plugin_dst_qq/app_config.json`
   - Windows: `%APPDATA%\nonebot2\nonebot_plugin_dst_qq\app_config.json`

**推荐使用工作目录下的config目录**，这样配置文件与机器人在同一位置，便于管理。

#### 配置文件模板
```json
{
    "dmp_url": "http://your-server.com:20000/v1",
    "auth": {
        "username": "your-username",
        "password": "your-password"
    },
    "clusters": ["YourClusterName"],
    "cache_settings": {
        "enable_cache": true,
        "memory_cache_size": 1000,
        "file_cache_ttl": 3600,
        "api_cache_ttl": 300
    },
    "database_settings": {
        "chat_history_days": 30,
        "auto_cleanup": true,
        "backup_enabled": true
    },
    "bridge_settings": {
        "message_filter": true,
        "max_message_length": 200,
        "auto_reconnect": true,
        "session_timeout": 1800
    },
    "wiki_settings": {
        "enable_screenshot": true,
        "screenshot_timeout": 30,
        "headless_mode": true,
        "cache_screenshots": true
    }
}
```

#### 配置项说明

| 配置项 | 类型 | 说明 | 默认值 |
|--------|------|------|--------|
| `dmp_url` | string | DMP服务器API地址 | 必需 |
| `auth.username` | string | DMP用户名 | 必需 |
| `auth.password` | string | DMP密码 | 必需 |
| `clusters` | array | 集群名称列表 | `[]` |
| `cache_settings.enable_cache` | boolean | 是否启用缓存 | `true` |
| `cache_settings.api_cache_ttl` | number | API缓存时间(秒) | `300` |
| `database_settings.chat_history_days` | number | 聊天记录保存天数 | `30` |
| `bridge_settings.session_timeout` | number | 会话超时时间(秒) | `1800` |
| `wiki_settings.enable_screenshot` | boolean | 是否启用Wiki截图 | `true` |
| `wiki_settings.screenshot_timeout` | number | 截图超时时间(秒) | `30` |
| `wiki_settings.headless_mode` | boolean | 是否使用无头模式 | `true` |

## 🤖 OneBot 客户端配置

### go-cqhttp 配置

1. **下载 go-cqhttp**
   - [官方发布页面](https://github.com/Mrs4s/go-cqhttp/releases)
   - 选择适合你系统的版本

2. **配置 config.yml**
```yaml
account:
  uin: 你的机器人QQ号
  password: '你的机器人QQ密码'

heartbeat:
  interval: 5

message:
  post-format: string
  ignore-invalid-cqcode: false
  force-fragment: false
  fix-url: false
  proxy-rewrite: ''
  report-self-message: false
  remove-reply-at: false
  extra-reply-data: false
  skip-mime-scan: false

output:
  log-level: warn
  log-aging: 15
  log-force-new: true
  log-colorful: true
  debug: false

default-middlewares: &default
  access-token: ''
  filter: ''
  rate-limit:
    enabled: false
    frequency: 1
    bucket: 1

database:
  leveldb:
    enable: true

servers:
  - ws:
      address: 127.0.0.1:3001
      middlewares:
        <<: *default
```

3. **启动 go-cqhttp**
```bash
# Windows
./go-cqhttp.exe

# Linux/macOS
./go-cqhttp
```

### 其他 OneBot 实现

- **[NapCat](https://github.com/NapNeko/NapCat)** - 现代化 OneBot 实现
- **[Lagrange](https://github.com/LagrangeDev/Lagrange.Core)** - C# 实现的 OneBot
- **[LLOneBot](https://github.com/LLOneBot/LLOneBot)** - 基于 LiteLoader 的实现

## 🗂️ 目录结构

安装完成后，你的项目结构应该是这样的：

```
my-dst-bot/
├── .env                          # 环境变量配置
├── bot.py                        # 启动文件
├── config/
│   └── app_config.json           # DMP配置文件
├── data/
│   └── database/                 # 数据库文件
│       ├── chat_history.db       # 聊天记录
│       └── dst_items.db          # 物品数据
├── cache/
│   └── simple_cache/             # 缓存文件
└── logs/                         # 日志文件 (如果启用)
```

## 🎯 功能测试

### 1. 基础连接测试

启动机器人后，向机器人私聊或在群里发送：

```
/调试信息
```

应该收到类似回复：
```
🔍 调试信息

👤 用户ID: 123456789
📱 事件类型: PrivateMessageEvent
🤖 Bot类型: Bot

🧪 测试命令:
• 测试文字 - 测试文字发送
• 调试信息 - 显示此信息

📝 当前模式: 文字模式（图片功能已禁用）
```

### 2. DMP 连接测试

```
/房间
```

如果配置正确，应该显示服务器信息。如果出错，检查 DMP 配置。

### 3. Wiki截图测试

```
/物品 大理石
```

应该返回物品的 Wiki 截图。如果截图失败，请检查：
- Chrome/Chromium 是否正确安装
- 网络连接是否正常
- Selenium 驱动是否安装

### 4. 服务器浏览测试

```
/查房
```

应该返回 DST 官方服务器列表。

## ❌ 常见问题和解决方案

### 问题 1: 插件加载失败
```
ModuleNotFoundError: No module named 'nonebot_plugin_dst_qq'
或
ModuleNotFoundError: No module named 'nonebot_plugin_alconna'
```

**解决方案:**
```bash
# 确认主插件安装
pip list | grep nonebot-plugin-dst-qq

# 确认所有依赖插件安装
pip list | grep -E "(alconna|localstore|apscheduler|waiter)"

# 重新安装主插件
pip install --upgrade nonebot-plugin-dst-qq

# 重新安装所有必需的NoneBot插件
pip install --upgrade nonebot-plugin-alconna nonebot-plugin-localstore \
                      nonebot-plugin-apscheduler nonebot-plugin-waiter

# 检查所有模块
python -c "
import nonebot_plugin_dst_qq
import nonebot_plugin_alconna
import nonebot_plugin_localstore  
import nonebot_plugin_apscheduler
import nonebot_plugin_waiter
print('✅ 所有插件安装成功')
"
```

### 问题 2: OneBot 连接失败
```
WebSocket connection failed
```

**解决方案:**
1. 检查 go-cqhttp 是否正常启动
2. 确认端口号一致 (默认 3001)
3. 检查防火墙设置
4. 验证 access_token 配置

**调试命令:**
```bash
# 检查端口
netstat -tlnp | grep 3001

# 测试连接
telnet 127.0.0.1 3001
```

### 问题 3: DMP 服务器连接失败
```
DMP服务器连接失败: HTTPConnectionPool
```

**解决方案:**
1. 检查 DMP 服务器是否正常运行
2. 确认网络连接和端口开放
3. 验证用户名密码正确
4. 检查 URL 格式

**手动测试:**
```bash
# 测试连接
curl -X GET "http://your-server:20000/v1/auth/login"

# 测试登录
curl -X POST "http://your-server:20000/v1/auth/login" \
     -H "Content-Type: application/json" \
     -d '{"username":"your-user","password":"your-pass"}'
```

### 问题 4: 权限不足
```
Permission denied: 只有超级用户可以使用此命令
```

**解决方案:**
1. 确认 `.env` 中 `SUPERUSERS` 配置正确
2. 使用机器人账号发送命令
3. 检查QQ号是否写对 (不要有空格)

### 问题 5: 数据库错误
```
database is locked
```

**解决方案:**
```bash
# 停止机器人
# 删除锁文件
find . -name "*.db-wal" -delete
find . -name "*.db-shm" -delete

# 重新启动
```

### 问题 6: 消息互通不工作

**检查步骤:**
1. 确认已开启消息互通: `/消息互通`
2. 检查DMP连接状态: `/调试信息`
3. 查看日志错误信息
4. 确认集群配置正确

### 问题 7: Wiki截图失败

**常见错误:**
```
WebDriverException: chrome not reachable
selenium.common.exceptions.WebDriverException
```

**解决方案:**
```bash
# 安装Chrome/Chromium
# Ubuntu
sudo apt-get update && sudo apt-get install -y chromium-browser

# CentOS/RHEL
sudo yum install -y chromium

# 检查安装
chromium-browser --version

# 重载物品数据
/重载物品

# 查看错误日志
LOG_LEVEL=DEBUG 启动机器人
```

### 问题 8: 服务器浏览失败

**解决方案:**
```bash
# 测试网络连接
curl -I "https://dstserverlist.appspot.com/"

# 检查DNS解析
nslookup dstserverlist.appspot.com

# 重启机器人尝试
```

## 🔧 性能优化

### 1. 缓存配置优化
```json
{
    "cache_settings": {
        "enable_cache": true,
        "memory_cache_size": 2000,
        "file_cache_ttl": 7200,
        "api_cache_ttl": 600
    }
}
```

### 2. 数据库优化
```json
{
    "database_settings": {
        "chat_history_days": 7,
        "auto_cleanup": true,
        "backup_enabled": false
    }
}
```

### 3. 系统资源优化
- 定期清理日志文件
- 使用 SSD 存储数据库
- 调整缓存大小适应内存

## 📊 监控和维护

### 日志检查
```bash
# 实时查看日志
tail -f logs/nonebot.log

# 搜索错误
grep -i error logs/nonebot.log

# 查看最近100行
tail -n 100 logs/nonebot.log
```

### 性能监控
```bash
# 检查内存使用
ps aux | grep python

# 检查磁盘空间
df -h

# 检查网络连接
netstat -tlnp | grep python
```

### 定期维护
- 每周重启机器人
- 清理过期缓存文件
- 备份重要配置文件
- 更新插件版本

## 🔄 升级指南

### 升级插件
```bash
# 检查当前版本
pip show nonebot-plugin-dst-qq

# 升级到最新版本
pip install --upgrade nonebot-plugin-dst-qq

# 重启机器人
```

### 配置迁移
升级后请检查配置文件是否有新增选项，对比模板文件进行更新。

### 数据备份
升级前建议备份重要数据：
```bash
# 备份配置
cp -r config/ config_backup/

# 备份数据库
cp -r data/ data_backup/
```

## 🆘 获取帮助

### 官方资源
- **项目地址**: https://github.com/uitok/nonebot-plugin-dst-qq
- **问题反馈**: https://github.com/uitok/nonebot-plugin-dst-qq/issues
- **更新日志**: [CHANGELOG.md](CHANGELOG.md)
- **文档首页**: [README.md](README.md)

### 社区支持
- **NoneBot 文档**: https://nonebot.dev/
- **OneBot 标准**: https://onebot.dev/
- **Alconna 文档**: https://arcletproject.github.io/docs/

### 联系方式
- **作者**: uitok
- **邮箱**: ui_101@qq.com

---

如果本指南对你有帮助，请给项目一个 ⭐ Star 支持一下！