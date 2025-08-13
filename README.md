# nonebot-plugin-dst-qq

[![PyPI](https://img.shields.io/pypi/v/nonebot-plugin-dst-qq)](https://pypi.org/project/nonebot-plugin-dst-qq/)
[![Python](https://img.shields.io/pypi/pyversions/nonebot-plugin-dst-qq)](https://pypi.org/pypi/nonebot-plugin-dst-qq/)
[![License](https://img.shields.io/pypi/l/nonebot-plugin-dst-qq)](https://pypi.org/project/nonebot-plugin-dst-qq/)

基于 NoneBot2 和 Alconna 的饥荒管理平台 (DMP) QQ 机器人插件，支持游戏信息查询、命令执行和消息互通功能。

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

### 🚀 Alconna 特性
- **Alconna 命令系统**: 使用强大的 Alconna 命令解析器，支持智能参数解析和类型检查
- **智能集群选择**: 自动获取可用集群，智能选择第一个可用集群
- **中英文支持**: 支持中英文命令，方便不同用户使用
- **参数类型检查**: 自动类型转换和验证，智能参数解析，友好的错误提示
- **可选参数支持**: 使用方括号 `[]` 表示可选参数，使用尖括号 `<>` 表示必需参数

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

#### 5. 聊天管理模块

##### 5.1 获取聊天历史
- **接口**: `GET /home/chat`
- **描述**: 获取指定世界的聊天历史
- **参数**: `clusterName` (集群名称), `worldName` (世界名称), `lines` (行数)
- **认证**: 需要Token

##### 5.2 获取聊天统计
- **接口**: `GET /home/chat/stats`
- **描述**: 获取聊天统计信息
- **参数**: `clusterName` (集群名称)
- **认证**: 需要Token

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
- [DMP](https://github.com/miracleEverywhere/dst-management-platform-api) - 饥荒管理平台

## 📞 联系方式

- 作者：uitok
- 邮箱：ui_101@qq.com
- 项目主页：[https://github.com/uitok/nonebot-plugin-dst-qq](https://github.com/uitok/nonebot-plugin-dst-qq)

---

如果这个项目对您有帮助，请给个 ⭐️ 支持一下！
