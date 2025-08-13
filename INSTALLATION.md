# nonebot-plugin-dst-qq 完整安装教程

本教程将指导您完成 `nonebot-plugin-dst-qq` 插件的完整部署流程，包括 DMP 饥荒管理平台、NapCatQQ 协议端和 NoneBot2 机器人的配置。

## 🎯 系统要求

- Python >= 3.9
- 稳定的网络连接

## 🎮 第一步：部署 DMP 饥荒管理平台

### 1.1 了解 DMP

DMP (饥荒管理平台) 是一个帮助你更好地管理饥荒专用服务器的平台。

**主要功能：**
- 🏠 **多房间管理**：支持多房间、多世界管理，提供清晰明了的配置选项
- 📋 **日志查看**：包含世界日志、聊天日志、请求日志、运行日志
- 👥 **玩家信息**：快速查看玩家信息，支持一键添加管理员、白名单、黑名单
- 🔐 **用户体系**：多个账号登录，不同账号拥有不同权限，由管理员统一配置
- 💾 **自动备份**：在设定的时间自动备份存档，并提供一键恢复功能
- ⚙️ **可视化配置**：像游戏中一样，随心所欲的配置世界和模组


### 1.2 安装 DMP

**安装方式：**
- **一键安装**：运行 `run.sh` 脚本即可一键安装和使用
- **Docker 部署**：支持 Docker 部署，多个环境互不干涉

> 📖 **详细部署文档请参考**：[DMP 官方文档](https://miraclesses.top/)

请根据官方文档完成 DMP 的部署，确保能够正常访问 DMP 的 Web 界面并获取以下信息：
- DMP 服务器地址和端口
- JWT 认证令牌
- 集群名称

## 🤖 第二步：部署 NapCatQQ

### 2.1 了解 NapCatQQ

[NapCatQQ](https://napneko.github.io/) 是一个现代化的基于 NTQQ 的 Bot 协议端实现。

**核心特性：**
- 🚀 **开箱即用**：多种部署方式，快捷部署于 Windows/Linux/MacOS 等主流 x64 架构平台
- 💖 **内存轻量**：天生无头，不依赖框架加载，不依赖 Electron，内存占用低至 50~100 MB
- 🔧 **适配快速**：采取 Core/Adapter 架构，支持多种 Bot 协议，快速迁移

### 2.2 下载和配置 NapCatQQ

1. **下载 NapCatQQ**
   - 访问 [NapCatQQ 官网](https://napneko.github.io/)
   - 下载适合您系统的版本

2. **基础配置**
   - 按照官方文档完成基础配置

3. **开启 WebSocket 正向服务器**
   - 在 NapCatQQ 配置中启用 WebSocket 服务器
   - 设置监听地址：`127.0.0.1`
   - 设置端口：`6700`（默认）
   - 生成并记录访问令牌（Access Token）

> 📖 **详细配置请参考**：[NapCatQQ 官方文档](https://napneko.github.io/)

## 🐍 第三步：部署 NoneBot2

### 3.1 安装 nb-cli 脚手架

根据 [NoneBot2 快速上手文档](https://nonebot.dev/docs/quick-start)：

```bash
# 1. 安装 pipx（如果尚未安装）
python -m pip install --user pipx
python -m pipx ensurepath

# 2. 安装脚手架
pipx install nb-cli
```

> ⚠️ **注意**：如果出现"open a new terminal"或"re-login"提示，请关闭当前终端并重新打开。

### 3.2 创建 NoneBot2 项目

```bash
# 创建项目
nb create
```

在交互式配置中选择(使用鼠标点击即可选中该选项)：

1. **项目模板**：选择 `bootstrap`（初学者或用户）
2. **项目名称**：例如 `dst-bot`
3. **适配器**：选择 `OneBot V11`
4. **驱动器**：选择 `HTTPX(HTTPX驱动`和`websockets(websockets驱动器)`
5. **立即安装依赖**：选择 `Yes`
6. **创建虚拟环境**：选择 `no`
7. **内置插件**：可以选择 `echo` 用于测试

### 3.3 安装 nonebot-plugin-dst-qq 插件

```bash
# 进入项目目录
cd dst-bot

# 安装插件
pip install nonebot-plugin-dst-qq
```

### 3.4 配置插件

编辑项目根目录下的 `pyproject.toml` 文件，在 `[tool.nonebot]` 部分添加：

```toml
[tool.nonebot]
plugins = ["nonebot_plugin_dst_qq"]
```

### 3.5 配置环境变量

将本项目的 `.env.example` 文件复制到机器人项目根目录，并重命名为 `.env`：

```bash
# 复制环境变量模板
cp .env.example .env
```

编辑 `.env` 文件，配置以下必需的环境变量：

```env
# NoneBot2 配置
DRIVER=~httpx+~websockets
SUPERUSERS=["你的QQ号"]

# OneBot 适配器配置（NapCatQQ WebSocket）
ONEBOT_WS_URLS=["ws://127.0.0.1:6700"]
ONEBOT_ACCESS_TOKEN=你的NapCatQQ访问令牌

# DMP 服务器配置（必需）
DMP_BASE_URL=http://你的DMP服务器地址:端口/v1
DMP_TOKEN=你的DMP_JWT令牌
DEFAULT_CLUSTER=你的集群名称
```

**配置说明：**
- `SUPERUSERS`：管理员的 QQ 号列表，用于执行管理员命令
- `ONEBOT_WS_URLS`：NapCatQQ 的 WebSocket 服务器地址
- `ONEBOT_ACCESS_TOKEN`：NapCatQQ 的访问令牌
- `DMP_BASE_URL`：DMP 服务器的 API 地址，格式为 `http://地址:端口/v1`
- `DMP_TOKEN`：DMP 的 JWT 认证令牌
- `DEFAULT_CLUSTER`：默认的饥荒集群名称

## 🚀 第四步：运行机器人

### 4.1 启动机器人

```bash
# 在项目根目录运行
nb run
```

如果一切配置正确，您应该看到类似以下的输出：
```
08-06 15:30:00 [INFO] nonebot | NoneBot is initializing...
08-06 15:30:00 [INFO] nonebot | Current Env: prod
08-06 15:30:00 [INFO] nonebot | Loaded adapter: OneBot V11
08-06 15:30:00 [INFO] nonebot | Loaded plugin: nonebot_plugin_dst_qq
08-06 15:30:00 [INFO] nonebot | NoneBot is running...
```

### 4.2 测试机器人

机器人启动后，您可以在 QQ 中测试以下命令：

#### 基础查询命令
| 命令 | 别名 | 功能 |
|------|------|------|
| `/世界` | `/world` | 获取世界信息 |
| `/房间` | `/room` | 获取房间信息 |
| `/系统` | `/sys` | 获取系统信息 |
| `/玩家` | `/players` | 获取在线玩家列表 |
| `/直连` | `/connection` | 获取服务器直连信息 |
| `/菜单` | `/help` | 显示帮助信息 |

#### 管理员命令
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

#### 消息互通功能
| 命令 | 功能 |
|------|------|
| `消息互通` | 开启游戏内消息与QQ消息互通 |
| `关闭互通` | 关闭消息互通功能 |
| `互通状态` | 查看当前互通状态 |
| `最新消息` | 获取游戏内最新消息 |

## 🔧 故障排除

### 常见问题及解决方案

#### 1. 插件无法加载
**症状**：启动时提示插件加载失败
**解决方案**：
- 检查 `pyproject.toml` 中的插件配置是否正确
- 确认插件已正确安装：`pip list | grep nonebot-plugin-dst-qq`
- 检查 Python 版本是否 >= 3.9

#### 2. 连接 NapCatQQ 失败
**症状**：启动时提示 WebSocket 连接失败
**解决方案**：
- 确认 NapCatQQ 已启动并开启 WebSocket 服务器
- 检查 `.env` 中的 `ONEBOT_WS_URLS` 地址是否正确
- 验证 `ONEBOT_ACCESS_TOKEN` 是否与 NapCatQQ 配置一致
- 检查防火墙是否阻止了连接

#### 3. DMP API 连接失败
**症状**：执行命令时提示 DMP 连接错误
**解决方案**：
- 确认 DMP 服务器正常运行
- 检查 `.env` 中的 `DMP_BASE_URL` 地址是否正确
- 验证 `DMP_TOKEN` 是否有效且未过期
- 确认 `DEFAULT_CLUSTER` 名称存在

#### 4. 权限不足
**症状**：无法执行管理员命令
**解决方案**：
- 确认您的 QQ 号在 `SUPERUSERS` 列表中
- 检查 DMP 中的用户权限配置
- 确认 JWT 令牌有足够的权限

#### 5. 消息互通不工作
**症状**：QQ 消息无法与游戏内消息互通
**解决方案**：
- 确认已执行 `消息互通` 命令开启功能
- 检查 DMP 的消息互通功能是否正常
- 验证网络连接是否稳定

### 调试技巧

1. **启用调试模式**：在 `.env` 中设置 `DEBUG=true`
2. **查看详细日志**：观察控制台输出的错误信息
3. **测试连接**：使用 `curl` 或浏览器测试 DMP API 连接
4. **检查网络**：确认各服务之间的网络连通性

## 📞 获取帮助

### 官方资源
- **项目主页**：[https://github.com/uitok/nonebot-plugin-dst-qq](https://github.com/uitok/nonebot-plugin-dst-qq)
- **问题反馈**：[GitHub Issues](https://github.com/uitok/nonebot-plugin-dst-qq/issues)
- **DMP 文档**：[https://miraclesses.top/](https://miraclesses.top/)
- **NapCatQQ 文档**：[https://napneko.github.io/](https://napneko.github.io/)
- **NoneBot2 文档**：[https://nonebot.dev/docs/quick-start](https://nonebot.dev/docs/quick-start)

### 社区支持
- **NoneBot2 社区**：[NoneBot 论坛](https://forum.nonebot.dev/)
- **DMP 社区**：参考 DMP 官方文档中的社区信息
- **NapCatQQ 社区**：参考 NapCatQQ 官方文档中的社区信息

## 📝 更新日志

### 当前版本：`0.2.5`

**主要修复：**
- ✅ 修复了插件打包问题，确保包含所有 Python 模块文件
- ✅ 优化了插件加载机制，使用 `require()` 函数
- ✅ 改进了错误处理和用户反馈
- ✅ 统一了配置获取方式
- ✅ 更新了项目结构，符合 NoneBot2 插件发布规范

**技术改进：**
- 🔧 重构插件加载机制
- 🛠️ 简化相对导入逻辑
- 📦 优化依赖注入和配置管理
- 🎯 提升插件稳定性和用户体验

---

🎉 **恭喜！** 现在您已经成功部署了完整的饥荒管理机器人系统。机器人将帮助您更方便地管理饥荒服务器，实现游戏内外的无缝连接。

如果您在使用过程中遇到任何问题，请随时在 [GitHub Issues](https://github.com/uitok/nonebot-plugin-dst-qq/issues) 中反馈，我们会尽快为您解决！ 