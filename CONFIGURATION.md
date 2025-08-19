# 配置说明

本文档详细说明 `nonebot-plugin-dst-qq` 插件的配置方法。

## 🔧 配置方式

### 方式一：环境变量配置

在 `.env` 文件中设置以下环境变量：

```bash
# DMP API 配置
DMP_BASE_URL=https://your-dmp-server.com
DMP_TOKEN=your_dmp_token_here
DEFAULT_CLUSTER=your_default_cluster_name

# OneBot 配置
ONEBOT_WS_URLS=ws://127.0.0.1:6700
ONEBOT_ACCESS_TOKEN=your_access_token_here

# 超级用户配置
SUPERUSERS=["123456789", "987654321"]

# 调试模式
DEBUG=false
```

### 方式二：Python 配置文件

在 `config.py` 文件中设置：

```python
from nonebot import get_driver

class Config:
    # DMP API 配置
    dmp_base_url: str = "https://your-dmp-server.com"
    dmp_token: str = "your_dmp_token_here"
    default_cluster: str = "your_default_cluster_name"
    
    # OneBot 配置
    onebot_ws_urls: str = "ws://127.0.0.1:6700"
    onebot_access_token: str = "your_access_token_here"
    
    # 超级用户配置
    superusers: list = ["123456789", "987654321"]
    
    # 调试模式
    debug: bool = False

driver = get_driver()
driver.register_config(Config)
```

### 方式三：NoneBot2 配置

在 `bot.py` 或主配置文件中：

```python
from nonebot import get_driver

driver = get_driver()

# 设置配置
driver.config.dmp_base_url = "https://your-dmp-server.com"
driver.config.dmp_token = "your_dmp_token_here"
driver.config.default_cluster = "your_default_cluster_name"
driver.config.onebot_ws_urls = "ws://127.0.0.1:6700"
driver.config.onebot_access_token = "your_access_token_here"
driver.config.superusers = ["123456789", "987654321"]
driver.config.debug = False
```

## 📋 配置项说明

### DMP API 配置

| 配置项 | 类型 | 必需 | 说明 |
|--------|------|------|------|
| `dmp_base_url` | str | ✅ | DMP 服务器地址 |
| `dmp_token` | str | ✅ | DMP API 访问令牌 |
| `default_cluster` | str | ✅ | 默认集群名称 |

### OneBot 配置

| 配置项 | 类型 | 必需 | 说明 |
|--------|------|------|------|
| `onebot_ws_urls` | str | ✅ | OneBot WebSocket 连接地址 |
| `onebot_access_token` | str | ❌ | OneBot 访问令牌（可选） |

### 用户配置

| 配置项 | 类型 | 必需 | 说明 |
|--------|------|------|------|
| `superusers` | list | ❌ | 超级用户 QQ 号列表 |
| `debug` | bool | ❌ | 调试模式开关 |

## 💾 数据存储

插件使用 `nonebot-plugin-localstore` 管理数据存储：

- **自动创建**: 插件会自动创建专用的数据目录
- **数据隔离**: 每个插件的数据独立存储
- **路径管理**: 自动处理不同操作系统的路径差异

### 存储位置

- **Windows**: `%APPDATA%/nonebot2/data/nonebot_plugin_dst_qq/`
- **Linux/macOS**: `~/.local/share/nonebot2/data/nonebot_plugin_dst_qq/`

## ✅ 配置验证

### 必需配置检查

插件启动时会自动检查以下必需配置：

1. **DMP API 配置**: 确保服务器地址和令牌有效
2. **OneBot 连接**: 验证 WebSocket 连接地址
3. **集群信息**: 验证默认集群是否可用

### 配置错误处理

如果配置无效，插件会：

1. 记录错误日志
2. 显示配置错误信息
3. 阻止插件启动

## 🚨 常见配置错误

### 1. DMP 连接失败

**错误信息**: `Failed to connect to DMP server`

**解决方案**:
- 检查 `DMP_BASE_URL` 是否正确
- 确认 DMP 服务器是否运行
- 验证网络连接

### 2. 令牌无效

**错误信息**: `Invalid DMP token`

**解决方案**:
- 检查 `DMP_TOKEN` 是否正确
- 确认令牌是否过期
- 联系 DMP 管理员

### 3. 集群不存在

**错误信息**: `Cluster not found`

**解决方案**:
- 检查 `DEFAULT_CLUSTER` 名称
- 确认集群是否已创建
- 使用 `dst.help` 查看可用集群

### 4. OneBot 连接失败

**错误信息**: `Failed to connect to OneBot`

**解决方案**:
- 检查 `ONEBOT_WS_URLS` 地址
- 确认 OneBot 服务是否运行
- 验证端口是否开放

## 🔄 配置更新

### 热重载配置

支持配置热重载，修改配置后：

1. 保存配置文件
2. 插件自动检测变化
3. 重新加载配置

### 配置持久化

配置更改会自动保存到：

- 环境变量文件 (`.env`)
- 配置文件 (`config.py`)
- NoneBot2 配置系统

## 📞 获取帮助

如果遇到配置问题：

1. 检查本文档的常见错误部分
2. 查看插件日志输出
3. 使用 `dst.help` 命令获取帮助
4. 在 GitHub Issues 中反馈问题

## 🔒 安全建议

1. **保护敏感信息**:
   - 不要将令牌提交到版本控制
   - 使用环境变量存储敏感配置
   - 定期更新访问令牌

2. **权限控制**:
   - 限制超级用户权限
   - 定期审查用户权限
   - 监控异常操作

3. **网络安全**:
   - 使用 HTTPS 连接
   - 配置防火墙规则
   - 定期安全更新
