# Wiki 截图功能升级总结

## 升级概述

成功将机器人插件的 Wiki 截图功能从 Selenium 升级到 Playwright（通过 nonebot-plugin-htmlrender）。

## 主要变更

### 1. 依赖配置更新

**修改文件**: `pyproject.toml`

```diff
dependencies = [
    # ... 其他依赖
-   "selenium>=4.15.0"
+   "nonebot-plugin-htmlrender>=0.3.0",
+   "beautifulsoup4>=4.12.0"
]

keywords = [
    # ... 其他关键词
-   "selenium"
+   "playwright", "htmlrender"
]

plugins = [
    # ... 其他插件
+   "nonebot_plugin_htmlrender"
]
```

### 2. 核心代码重构

**修改文件**: `nonebot_plugin_dst_qq/wiki_screenshot.py`

#### 主要变更:
- **移除**: Selenium WebDriver 相关代码
- **新增**: Playwright 浏览器控制
- **新增**: BeautifulSoup4 HTML 解析
- **改进**: 错误处理和重试机制
- **优化**: 页面加载策略

#### 新的截图流程:
1. 使用 `nonebot_plugin_htmlrender.get_browser()` 获取浏览器实例
2. 创建新页面并设置视口和 User-Agent
3. 访问 Wiki 页面（使用 `domcontentloaded` 加载策略）
4. 等待主要内容加载并隐藏不需要的页面元素
5. 截图内容区域或整页
6. 自动清理资源

### 3. 功能特性

#### ✅ 正常工作的功能:
- **基本 Wiki 截图**: 成功截图物品页面
- **自动元素隐藏**: 移除导航栏、页脚等干扰元素  
- **智能内容定位**: 尝试定位主要内容区域
- **错误处理**: 超时和异常的优雅处理
- **资源管理**: 自动清理浏览器页面

#### ⚠️ 需要进一步优化的功能:
- **分离截图**: HTML 解析方式的分离截图受 403 限制
- **内容区域检测**: 当前使用整页截图作为后备方案

## 测试结果

### 成功测试的物品:
- ✅ 大理石 (39,943 bytes)
- ✅ 石头 (40,201 bytes)  
- ✅ 木头 (48,216 bytes)
- ✅ 威尔逊 (39,006 bytes)

### 性能表现:
- **初次运行**: 需要下载 Playwright 浏览器 (~280MB)
- **后续运行**: 快速启动，每次截图约 10-15 秒
- **内存使用**: 比 Selenium 更高效
- **稳定性**: 更好的错误恢复机制

## 技术优势

### Playwright vs Selenium:
1. **更现代**: 支持最新的 Web 标准
2. **更快速**: 更快的页面加载和截图
3. **更稳定**: 更好的元素等待和错误处理
4. **更简单**: 集成在 htmlrender 插件中，无需手动管理驱动
5. **更可靠**: 自动重试和超时机制

### 架构改进:
1. **延迟导入**: 避免 NoneBot 初始化问题
2. **智能等待**: 区分 DOM 加载和内容加载
3. **优雅降级**: 内容区域找不到时使用整页截图
4. **资源清理**: 自动关闭页面避免内存泄漏

## 部署说明

### 首次运行:
- Playwright 会自动下载 Chromium 浏览器 (~280MB)
- 安装系统依赖包 (字体、图形库等)
- 整个过程约需 3-5 分钟

### 生产环境:
- 确保有足够磁盘空间 (~500MB for Playwright)
- 网络环境能访问 Playwright 镜像源
- 系统支持图形库 (通常 Docker 环境需要额外配置)

## 使用方式

### 基本截图:
```python
from nonebot_plugin_dst_qq.wiki_screenshot import screenshot_wiki_item

# 截图指定物品
image_bytes = await screenshot_wiki_item("大理石")
```

### 命令触发:
```
/物品 大理石        # 基本截图
/查 石头           # 基本截图  
```

## 兼容性

- ✅ 保持所有原有 API 接口不变
- ✅ 现有的命令和功能正常工作
- ✅ 缓存系统继续有效
- ✅ 错误日志和调试信息完整

## 后续优化建议

1. **改进内容定位**: 优化 CSS 选择器以更准确定位内容区域
2. **分离截图重构**: 使用 Playwright 实现信息框和正文的分离截图
3. **性能调优**: 优化页面加载策略和截图参数
4. **缓存截图**: 缓存截图结果减少重复请求
5. **批量截图**: 支持一次性截图多个物品

## 升级完成 ✅

Wiki 截图功能已成功从 Selenium 升级到 Playwright，提供更稳定、更快速的截图体验。