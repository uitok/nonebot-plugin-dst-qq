# GitHub 推送准备指南

## 📋 推送前检查清单

### ✅ 项目结构检查
- [x] 项目命名符合规范：`nonebot-plugin-dst-qq`
- [x] 模块命名符合规范：`nonebot_plugin_dst_qq`
- [x] 使用 `src/` 布局
- [x] 包含必要的配置文件：`pyproject.toml`、`README.md`、`LICENSE`

### ✅ 插件元数据检查
- [x] `__plugin_meta__` 正确填写
- [x] 包含所有必需字段：name、description、usage、type、homepage、config、supported_adapters
- [x] type 设置为 "application"
- [x] homepage URL 正确

### ✅ 依赖配置检查
- [x] 正确添加 `nonebot2>=2.4.0` 依赖
- [x] 添加适配器依赖 `nonebot-adapter-onebot>=2.4.0`
- [x] 没有错误添加 `nonebot` 依赖
- [x] 其他依赖版本合理

### ✅ 文档检查
- [x] README.md 内容完整
- [x] 包含功能介绍、安装方法、配置说明、使用方法
- [x] 更新日志详细
- [x] 贡献指南完整

### ✅ 自动化配置
- [x] GitHub Actions 工作流配置
- [x] 测试工作流
- [x] 发布工作流
- [x] .gitignore 文件

## 🚀 GitHub 推送步骤

### 1. 初始化 Git 仓库（如果还没有）

```bash
git init
git add .
git commit -m "feat: 初始版本发布

- 基于 NoneBot2 的饥荒管理平台 QQ 机器人插件
- 支持游戏信息查询、命令执行和消息互通功能
- 符合 NoneBot 插件发布规范"
```

### 2. 创建 GitHub 仓库

1. 访问 [GitHub](https://github.com)
2. 点击 "New repository"
3. 仓库名称：`nonebot-plugin-dst-qq`
4. 描述：`基于 NoneBot2 的饥荒管理平台 (DMP) QQ 机器人插件`
5. 选择 Public
6. 不要初始化 README（因为已经有了）
7. 点击 "Create repository"

### 3. 推送代码到 GitHub

```bash
# 添加远程仓库
git remote add origin https://github.com/uitok/nonebot-plugin-dst-qq.git

# 推送主分支
git branch -M main
git push -u origin main
```

### 4. 设置 GitHub Secrets（用于自动发布）

1. 在 GitHub 仓库页面，点击 "Settings"
2. 点击左侧 "Secrets and variables" → "Actions"
3. 点击 "New repository secret"
4. 名称：`PYPI_API_TOKEN`
5. 值：您的 PyPI API Token

### 5. 创建发布标签

```bash
# 创建标签
git tag v0.2.4

# 推送标签
git push origin v0.2.4
```

## 📦 PyPI 发布准备

### 1. 注册 PyPI 账户

1. 访问 [PyPI](https://pypi.org)
2. 注册账户
3. 启用双因素认证

### 2. 创建 API Token

1. 在 PyPI 账户设置中创建 API Token
2. 选择 "Entire account (all projects)"
3. 复制 Token 并保存到 GitHub Secrets

### 3. 测试构建

```bash
# 安装构建工具
pip install build twine

# 构建包
python -m build

# 检查构建结果
ls dist/
```

### 4. 测试上传（可选）

```bash
# 上传到测试 PyPI
twine upload --repository testpypi dist/*

# 测试安装
pip install --index-url https://test.pypi.org/simple/ nonebot-plugin-dst-qq
```

## 🏪 NoneBot 商店发布

### 1. 发布到 PyPI

推送标签后，GitHub Actions 会自动发布到 PyPI。

### 2. 提交商店申请

1. 访问 [NoneBot 商店](https://nonebot.dev/store)
2. 切换到插件页签
3. 点击 "发布插件"
4. 填写插件信息：
   - 插件名称：nonebot-plugin-dst-qq
   - 插件描述：基于 NoneBot2 的饥荒管理平台 (DMP) QQ 机器人插件
   - 插件分类：application
   - 支持的适配器：OneBot V11
   - 项目主页：https://github.com/uitok/nonebot-plugin-dst-qq
   - 插件配置项：DMP_BASE_URL, DMP_TOKEN, DEFAULT_CLUSTER

### 3. 等待审核

- NoneFlow Bot 会自动检查插件
- 维护者会进行代码审查
- 审核通过后会自动合并到商店

## 🔧 后续维护

### 版本更新流程

1. 更新 `pyproject.toml` 中的版本号
2. 更新 `CHANGELOG.md`
3. 更新 `README.md` 中的更新日志
4. 提交代码并推送
5. 创建新标签：`git tag v0.x.x`
6. 推送标签：`git push origin v0.x.x`

### 自动化发布

推送标签后，GitHub Actions 会自动：
1. 构建 Python 包
2. 发布到 PyPI
3. 运行测试

## 📞 联系方式

如有问题，请联系：
- 邮箱：ui_101@qq.com
- GitHub Issues：https://github.com/uitok/nonebot-plugin-dst-qq/issues 