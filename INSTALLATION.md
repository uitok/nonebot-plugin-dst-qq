# 完整安装指南 / Installation Guide

本文档提供 nonebot-plugin-dst-qq 插件的完整安装和配置指南，包含从零开始的详细步骤。

## 📋 系统要求

### 最低要求
- **Python**: 3.9+ (推荐 3.11+)
- **系统内存**: 512MB+ 
- **磁盘空间**: 100MB+
- **网络**: 能访问GitHub和PyPI

### 推荐环境
- **Python**: 3.11 或 3.12
- **系统**: Ubuntu 20.04+, Windows 10+, macOS 12+
- **内存**: 1GB+
- **CPU**: 1核心+

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

# 使用 poetry (推荐)
poetry init
poetry add nonebot2[fastapi] nonebot-adapter-onebot nonebot-plugin-dst-qq
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
# ONEBOT_ACCESS_TOKEN="your-access-token"  # 如果go-cqhttp设置了token

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
```
config/config/app_config.json
```

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
│   └── config/
│       └── app_config.json       # DMP配置文件
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

### 3. 物品查询测试

```
/物品 大理石
```

应该返回物品的 Wiki 截图或相关信息。

## ❌ 常见问题和解决方案

### 问题 1: 插件加载失败
```
ModuleNotFoundError: No module named 'nonebot_plugin_dst_qq'
```

**解决方案:**
```bash
# 确认安装
pip list | grep nonebot-plugin-dst-qq

# 重新安装
pip install --upgrade nonebot-plugin-dst-qq

# 检查Python环境
python -c "import nonebot_plugin_dst_qq; print('OK')"
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

### 问题 7: 物品查询失败

**解决方案:**
```bash
# 重载物品数据
/重载物品

# 检查数据库
ls -la data/database/dst_items.db

# 查看错误日志
LOG_LEVEL=DEBUG 启动机器人
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