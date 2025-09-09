# GitHub Actions 工作流说明

本项目包含以下自动化工作流：

## 🧪 测试工作流 (test.yml)

**触发条件:**
- 推送到 `main` 或 `dev` 分支
- 创建针对 `main` 或 `dev` 分支的 Pull Request
- 手动触发

**功能:**
- 在多个 Python 版本 (3.9-3.12) 上运行测试
- 代码风格检查 (flake8, black, isort)
- 类型检查 (mypy)
- 单元测试 (pytest)
- 代码覆盖率上传到 Codecov

## 🚀 发布到 Test PyPI (publish-test-pypi.yml)

**触发条件:**
- 推送以下格式的标签:
  - `v*-dev` (如: `v0.4.6-dev`)
  - `v*-alpha` (如: `v0.4.6-alpha`)
  - `v*-beta` (如: `v0.4.6-beta`)
  - `v*-rc*` (如: `v0.4.6-rc1`)
- 手动触发

**功能:**
- 自动构建 Python 包
- 发布到 Test PyPI
- 创建 GitHub 预发布版本
- 上传构建产物

**使用示例:**
```bash
# 创建开发版本标签
git tag v0.4.6-dev
git push origin v0.4.6-dev
```

## 📦 发布到正式 PyPI (publish-pypi.yml)

**触发条件:**
- 推送正式版本标签格式: `v[数字].[数字].[数字]` (如: `v0.4.6`)
- 手动触发

**功能:**
- 自动构建 Python 包
- 发布到正式 PyPI
- 创建 GitHub 正式发布版本
- 上传构建产物

**使用示例:**
```bash
# 创建正式版本标签
git tag v0.4.6
git push origin v0.4.6
```

## 📋 所需的 GitHub Secrets

在 GitHub 仓库设置中需要配置以下 Secrets：

### Test PyPI 发布 (必需)
- `TEST_PYPI_API_TOKEN`: Test PyPI 的 API Token
  1. 访问 https://test.pypi.org/manage/account/token/
  2. 创建新的 API Token
  3. 复制 token 并添加到 GitHub Secrets

### 正式 PyPI 发布 (必需)
- `PYPI_API_TOKEN`: 正式 PyPI 的 API Token
  1. 访问 https://pypi.org/manage/account/token/
  2. 创建新的 API Token
  3. 复制 token 并添加到 GitHub Secrets

### 自动创建 (无需手动配置)
- `GITHUB_TOKEN`: GitHub 自动提供，用于创建 Release

## 🏷️ 版本标签命名规范

### 开发版本 (发布到 Test PyPI)
- `v0.4.6-dev`: 开发版本
- `v0.4.6-alpha`: Alpha 版本
- `v0.4.6-beta`: Beta 版本
- `v0.4.6-rc1`: Release Candidate 版本

### 正式版本 (发布到 PyPI)
- `v0.4.6`: 正式版本
- `v1.0.0`: 主要版本

## 📝 发布流程

### 开发版本发布
1. 在 `dev` 分支上完成开发
2. 创建开发版本标签: `git tag v0.4.6-dev`
3. 推送标签: `git push origin v0.4.6-dev`
4. GitHub Actions 自动发布到 Test PyPI

### 正式版本发布
1. 将 `dev` 分支合并到 `main`
2. 在 `main` 分支创建正式标签: `git tag v0.4.6`
3. 推送标签: `git push origin v0.4.6`
4. GitHub Actions 自动发布到正式 PyPI

## 🔍 监控和调试

- 在 GitHub 仓库的 "Actions" 标签页可以查看所有工作流运行状态
- 点击具体的工作流运行可以查看详细日志
- 失败的工作流会显示错误信息和堆栈跟踪