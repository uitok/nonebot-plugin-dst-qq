# DMP 饥荒管理平台机器人

基于 NoneBot2 和 Alconna 的饥荒管理平台 (DMP) QQ 机器人插件，支持游戏信息查询、命令执行和消息互通功能。

## ✨ 特性

- 🚀 **Alconna 命令系统**: 使用强大的 Alconna 命令解析器，支持智能参数解析和类型检查
- 🌍 **游戏信息查询**: 获取世界信息、房间信息、系统状态、在线玩家等
- 🔧 **管理员功能**: 备份管理、命令执行、世界回档、重置等高级功能
- 💬 **消息互通**: 游戏内消息与QQ消息实时互通
- 🌐 **多集群支持**: 支持多个游戏集群的管理
- 🎯 **中英文支持**: 支持中英文命令，方便不同用户使用
- 🔍 **智能集群选择**: 自动获取可用集群，智能选择第一个可用集群

## 🛠️ 安装

### 环境要求

- Python 3.9+
- NoneBot2 2.0+

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置

创建 `.env` 文件并配置以下环境变量：

```env
# DMP 服务器配置
DMP_BASE_URL=http://your-dmp-server:port/v1
DMP_TOKEN=your-jwt-token
DEFAULT_CLUSTER=cx

# OneBot 配置
ONEBOT_WS_URLS=["ws://your-onebot-server:port"]
ONEBOT_ACCESS_TOKEN=your-access-token

# 超级用户配置
SUPERUSERS=["你的QQ号"]
```

## 📚 使用说明

### 基础命令

| 命令 | 英文别名 | 功能 | 参数 |
|------|----------|------|------|
| `世界 [集群]` | `world [集群]` | 获取世界信息 | 集群名称（可选，自动选择） |
| `房间 [集群]` | `room [集群]` | 获取房间信息 | 集群名称（可选，自动选择） |
| `系统` | `sys` | 获取系统信息 | 无 |
| `玩家 [集群]` | `players [集群]` | 获取在线玩家列表 | 集群名称（可选，自动选择） |
| `直连 [集群]` | `connection [集群]` | 获取服务器直连信息 | 集群名称（可选，自动选择） |
| `菜单` | `help` | 显示帮助信息 | 无 |

### 管理员命令

| 命令 | 英文别名 | 功能 | 参数 |
|------|----------|------|------|
| `管理命令` | `admin` | 显示管理员功能菜单 | 无 |
| `查看备份` | `backup` | 获取备份文件列表 | 自动选择集群 |
| `创建备份` | `createbackup` | 手动创建备份 | 自动选择集群 |
| `执行命令 <命令>` | `exec <命令>` | 执行游戏命令 | 命令内容 |
| `回滚世界 <天数>` | `rollback <天数>` | 回档指定天数 | 天数（1-5） |
| `重置世界 [世界]` | `reset [世界]` | 重置世界 | 世界名称（可选，默认Master） |
| `聊天历史 [世界] [行数]` | `chathistory [世界] [行数]` | 获取聊天历史 | 世界名称（可选）、行数（可选，默认50） |
| `聊天统计` | `chatstats` | 获取聊天历史统计信息 | 自动选择集群 |

### 消息互通功能

| 命令 | 英文别名 | 功能 | 参数 |
|------|----------|------|------|
| `消息互通` | `exchange` | 开启游戏内消息与QQ消息互通 | 无 |
| `关闭互通` | `closeexchange` | 关闭消息互通功能 | 无 |
| `互通状态` | `exchangestatus` | 查看当前互通状态 | 无 |
| `最新消息 [世界] [数量]` | `latestmessages [世界] [数量]` | 获取游戏内最新消息 | 世界名称（可选）、数量（可选，默认10） |

## 🔧 Alconna 特性

### 参数类型检查
- 自动类型转换和验证
- 智能参数解析
- 友好的错误提示

### 可选参数支持
- 使用方括号 `[]` 表示可选参数
- 使用尖括号 `<>` 表示必需参数
- 支持默认值设置

### 命令别名
- 中英文命令完全对应
- 支持多种调用方式
- 统一的参数处理

## 🌐 DMP API 接口文档

### 基础信息

**基础URL**: `http://your-server:port/v1`

**认证方式**: 大部分API需要JWT Token认证，在请求头中添加 `Authorization: <token>`

### 主要接口

#### 1. 认证模块 (Auth)

##### 1.1 用户登录
- **接口**: `POST /login`
- **描述**: 用户登录获取JWT Token
- **请求体**:
```json
{
  "loginForm": {
    "username": "用户名",
    "password": "密码"
  }
}
```

##### 1.2 获取用户信息
- **接口**: `GET /userinfo`
- **描述**: 获取当前登录用户信息
- **认证**: 需要Token

#### 2. 游戏管理模块

##### 2.1 获取世界信息
- **接口**: `GET /home/world`
- **描述**: 获取指定集群的世界信息
- **参数**: `clusterName` (集群名称)
- **认证**: 需要Token

##### 2.2 获取房间信息
- **接口**: `GET /home/room`
- **描述**: 获取指定集群的房间信息
- **参数**: `clusterName` (集群名称)
- **认证**: 需要Token

##### 2.3 获取在线玩家
- **接口**: `GET /home/players`
- **描述**: 获取指定集群的在线玩家列表
- **参数**: `clusterName` (集群名称)
- **认证**: 需要Token

##### 2.4 获取系统信息
- **接口**: `GET /home/sys`
- **描述**: 获取系统状态信息
- **认证**: 需要Token

#### 3. 备份管理模块

##### 3.1 获取备份列表
- **接口**: `GET /tools/backup`
- **描述**: 获取备份文件列表
- **参数**: `clusterName` (集群名称)
- **认证**: 需要Token

##### 3.2 创建备份
- **接口**: `POST /backup/create`
- **描述**: 手动创建备份
- **参数**: `clusterName` (集群名称)
- **认证**: 需要Token

#### 4. 命令执行模块

##### 4.1 执行游戏命令
- **接口**: `POST /home/exec`
- **描述**: 在游戏内执行控制台命令
- **请求体**:
```json
{
  "type": "console",
  "extraData": "命令内容",
  "clusterName": "集群名称",
  "worldName": "世界名称"
}
```

##### 4.2 回档管理
- **接口**: `POST /home/exec`
- **描述**: 执行指定集群的回档操作
- **请求体**:
```json
{
  "type": "rollback",
  "extraData": 天数,
  "clusterName": "集群名称",
  "worldName": ""
}
```

#### 5. 世界管理模块

##### 5.1 重置世界
- **接口**: `POST /world/reset`
- **描述**: 重置指定世界
- **请求体**:
```json
{
  "clusterName": "集群名称",
  "worldName": "世界名称"
}
```

##### 5.2 获取聊天历史
- **接口**: `GET /chat/history`
- **描述**: 获取游戏内聊天历史
- **参数**: `clusterName` (集群名称), `worldName` (世界名称，可选), `lines` (行数，默认50)
- **认证**: 需要Token

#### 6. 集群管理模块

##### 6.1 获取可用集群
- **接口**: `GET /setting/clusters`
- **描述**: 获取所有可用的集群列表
- **认证**: 需要Token

## 📁 项目结构

```
src/plugins/nonebot_plugin_dst_qq/
├── __init__.py          # 主插件文件
├── config.py            # 配置管理
├── database.py          # 数据库操作
└── plugins/             # 子插件目录
    ├── dmp_api.py       # 基础API功能
    ├── dmp_advanced.py  # 高级管理功能
    └── message_exchange.py # 消息互通功能
```

## 🚀 启动

```bash
nb run
```

## 📝 开发说明

### 添加新命令

1. 在相应的子插件文件中定义 Alconna 命令
2. 实现命令处理函数
3. 在 `register_handlers()` 函数中注册命令

示例：

```python
from alconna import Alconna, Args

# 定义命令
my_cmd = Alconna(
    "我的命令",
    Args["param", str, "默认值"],
    help_text="命令说明"
)

# 实现处理函数
async def handle_my_cmd(bot: Bot, event: Event):
    # 处理逻辑
    pass

# 注册命令
my_cmd.on(handle_my_cmd)
```

### 权限控制

使用 `SUPERUSER` 权限装饰器控制管理员命令：

```python
from nonebot.permission import SUPERUSER

# 只有超级用户才能使用的命令
admin_matcher = on_alconna(admin_cmd, priority=1, permission=SUPERUSER)
```

### 智能集群选择

机器人会自动获取可用集群并选择第一个：

```python
async def get_first_available_cluster(self) -> str:
    """获取第一个可用的集群名称"""
    clusters_result = await self.get_available_clusters()
    if clusters_result.get("code") == 200:
        clusters = clusters_result.get("data", [])
        if clusters:
            cluster_name = clusters[0].get("clusterName", "")
            return cluster_name
    return None
```

## 🔧 故障排除

### 常见问题

1. **权限不足错误**
   - 确保你的QQ号在 `SUPERUSERS` 配置中
   - 检查DMP Token是否有效

2. **集群资源不存在**
   - 机器人会自动选择可用集群
   - 检查DMP服务器是否正常运行

3. **命令无法匹配**
   - 确保命令格式正确
   - 检查Alconna命令定义

### 调试模式

启用调试模式查看详细日志：

```env
NONEBOT_DEBUG=true
NONEBOT_LOG_LEVEL=DEBUG
```

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

### 贡献指南

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📄 许可证

MIT License

## 🙏 致谢

- [NoneBot2](https://github.com/nonebot/nonebot2) - 机器人框架
- [Alconna](https://github.com/ArcletProject/Alconna) - 命令解析器
- [DMP](https://github.com/your-dmp-repo) - 饥荒管理平台
