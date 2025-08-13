# 贡献指南

感谢您对 `nonebot-plugin-dst-qq` 项目的关注！我们欢迎所有形式的贡献。

## 如何贡献

### 报告 Bug

如果您发现了一个 Bug，请：

1. 在 [GitHub Issues](https://github.com/uitok/nonebot-plugin-dst-qq/issues) 中搜索是否已经有人报告过
2. 如果没有，请创建一个新的 Issue
3. 在 Issue 中详细描述：
   - Bug 的具体表现
   - 复现步骤
   - 期望的行为
   - 环境信息（Python 版本、NoneBot2 版本等）

### 提交功能请求

如果您有功能建议，请：

1. 在 Issues 中搜索是否已经有人提出过类似建议
2. 如果没有，请创建一个新的 Issue
3. 详细描述您希望添加的功能和使用场景

### 提交代码

如果您想贡献代码，请：

1. Fork 本仓库
2. 创建您的特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交您的更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开一个 Pull Request

## 开发环境设置

### 环境要求

- Python >= 3.9
- NoneBot2 >= 2.4.0

### 本地开发

```bash
# 克隆仓库
git clone https://github.com/uitok/nonebot-plugin-dst-qq.git
cd nonebot-plugin-dst-qq

# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest

# 代码格式化
black src/
isort src/

# 代码检查
flake8 src/
mypy src/
```

## 代码规范

### Python 代码风格

- 遵循 [PEP 8](https://www.python.org/dev/peps/pep-0008/) 代码风格
- 使用 [Black](https://black.readthedocs.io/) 进行代码格式化
- 使用 [isort](https://pycqa.github.io/isort/) 进行导入排序
- 使用 [flake8](https://flake8.pycqa.org/) 进行代码检查

### 类型注解

- 尽可能使用类型注解
- 使用 [mypy](https://mypy.readthedocs.io/) 进行类型检查

### 文档字符串

- 为所有公共函数和类添加文档字符串
- 使用 Google 风格的文档字符串格式

### 测试

- 为新功能添加测试
- 确保所有测试通过
- 测试覆盖率应保持在合理水平

## 提交信息规范

请使用清晰的提交信息，建议使用以下格式：

```
类型(范围): 简短描述

详细描述（可选）
```

类型包括：
- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `style`: 代码格式调整
- `refactor`: 代码重构
- `test`: 测试相关
- `chore`: 构建过程或辅助工具的变动

## 发布流程

1. 更新版本号（在 `pyproject.toml` 中）
2. 更新 `README.md` 中的更新日志
3. 创建 Git 标签：`git tag v0.x.x`
4. 推送到 GitHub：`git push origin v0.x.x`
5. GitHub Actions 会自动发布到 PyPI

## 联系方式

如果您有任何问题，请：

- 在 [GitHub Issues](https://github.com/uitok/nonebot-plugin-dst-qq/issues) 中提问
- 发送邮件到：ui_101@qq.com

感谢您的贡献！ 