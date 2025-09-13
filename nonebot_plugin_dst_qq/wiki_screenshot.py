"""
Wiki截图工具
基于Selenium实现的饥荒Wiki页面截图功能
"""

import asyncio
import io
import re
import time
from typing import Optional, List
import urllib.parse

from nonebot import logger
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException


class WikiScreenshotTool:
    """Wiki截图工具"""
    
    def __init__(self):
        self.driver = None
        self._driver_lock = asyncio.Lock()
        
    async def _get_driver(self):
        """获取WebDriver实例"""
        if self.driver is None:
            await self._init_driver()
        return self.driver
    
    async def _init_driver(self):
        """初始化WebDriver"""
        try:
            options = Options()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--disable-extensions')
            options.add_argument('--disable-plugins')
            options.add_argument('--disable-images')  # 禁用图片加载以提高速度
            options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            
            # 设置页面加载策略
            options.page_load_strategy = 'eager'
            
            # 在事件循环中运行WebDriver初始化
            loop = asyncio.get_event_loop()
            self.driver = await loop.run_in_executor(None, lambda: webdriver.Chrome(options=options))
            
            # 设置超时时间
            self.driver.implicitly_wait(10)
            self.driver.set_page_load_timeout(30)
            
            logger.info("WebDriver初始化成功")
            
        except Exception as e:
            logger.error(f"WebDriver初始化失败: {e}")
            self.driver = None
            raise
    
    async def close_driver(self):
        """关闭WebDriver"""
        if self.driver:
            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, lambda: self.driver.quit())
                logger.info("WebDriver已关闭")
            except Exception as e:
                logger.error(f"关闭WebDriver时出错: {e}")
            finally:
                self.driver = None
    
    def _safe_filename(self, name: str) -> str:
        """将文件名安全化"""
        return re.sub(r'[\\/*?:"<>|]', "_", name)
    
    async def _hide_unwanted_elements(self, driver):
        """隐藏不需要的页面元素"""
        try:
            loop = asyncio.get_event_loop()
            
            # 隐藏的元素选择器列表
            hide_selectors = [
                "#siteNotice",  # 网站通知
                ".mw-notification-area",  # 通知区域
                "#mw-navigation",  # 导航区域
                "#mw-page-base",  # 页面基础
                "#mw-head-base",  # 头部基础
                "#mw-head",  # 页面头部
                "#footer",  # 页面底部
                ".navbox",  # 导航框
                ".metadata",  # 元数据
                ".mw-editsection",  # 编辑链接
                "#toc",  # 目录（可选，根据需要）
            ]
            
            hide_script = """
            var selectors = arguments[0];
            selectors.forEach(function(selector) {
                var elements = document.querySelectorAll(selector);
                elements.forEach(function(el) {
                    el.style.display = 'none';
                });
            });
            """
            
            await loop.run_in_executor(None, lambda: driver.execute_script(hide_script, hide_selectors))
            logger.debug("已隐藏不需要的页面元素")
            
        except Exception as e:
            logger.warning(f"隐藏页面元素时出错: {e}")
    
    async def _hide_navigation_elements(self, driver):
        """隐藏导航相关元素（用于整页截图）"""
        try:
            loop = asyncio.get_event_loop()
            
            hide_script = """
            // 隐藏顶部导航和头部
            var topElements = [
                '#mw-navigation', '#mw-head', '#mw-page-base', '#mw-head-base',
                '.mw-notification-area', '#siteNotice', '.mw-indicators'
            ];
            topElements.forEach(function(selector) {
                var elements = document.querySelectorAll(selector);
                elements.forEach(function(el) {
                    el.style.display = 'none';
                });
            });
            
            // 隐藏底部
            var bottomElements = ['#footer', '.navbox', '#catlinks'];
            bottomElements.forEach(function(selector) {
                var elements = document.querySelectorAll(selector);
                elements.forEach(function(el) {
                    el.style.display = 'none';
                });
            });
            
            // 调整body的padding和margin
            document.body.style.paddingTop = '0';
            document.body.style.margin = '0';
            """
            
            await loop.run_in_executor(None, lambda: driver.execute_script(hide_script))
            logger.debug("已隐藏导航元素")
            
        except Exception as e:
            logger.warning(f"隐藏导航元素时出错: {e}")
    
    async def _optimize_content_display(self, driver):
        """优化内容显示"""
        try:
            loop = asyncio.get_event_loop()
            
            optimize_script = """
            // 移除或优化一些元素
            var optimizeSelectors = [
                '.mw-editsection',  // 编辑链接
                '.mw-headline .mw-editsection',  // 标题中的编辑链接
                '.printfooter',  // 打印页脚
                '.catlinks',  // 分类链接
            ];
            
            optimizeSelectors.forEach(function(selector) {
                var elements = document.querySelectorAll(selector);
                elements.forEach(function(el) {
                    el.style.display = 'none';
                });
            });
            
            // 优化表格显示
            var tables = document.querySelectorAll('table');
            tables.forEach(function(table) {
                table.style.maxWidth = '100%';
                table.style.fontSize = '12px';
            });
            
            // 优化图片显示
            var images = document.querySelectorAll('.mw-parser-output img');
            images.forEach(function(img) {
                if (img.width > 600) {
                    img.style.maxWidth = '600px';
                    img.style.height = 'auto';
                }
            });
            """
            
            await loop.run_in_executor(None, lambda: driver.execute_script(optimize_script))
            logger.debug("已优化内容显示")
            
        except Exception as e:
            logger.warning(f"优化内容显示时出错: {e}")
    
    async def _wait_for_page_load(self, driver):
        """等待页面加载完成"""
        try:
            loop = asyncio.get_event_loop()
            wait = WebDriverWait(driver, 15)
            
            # 等待页面基本结构加载
            try:
                wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                logger.debug("页面body已加载")
            except TimeoutException:
                logger.warning("等待页面body加载超时")
            
            # 等待主要内容区域加载
            content_loaded = False
            for selector in [".mw-parser-output", "#mw-content-text", "#content"]:
                try:
                    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                    logger.debug(f"内容区域已加载: {selector}")
                    content_loaded = True
                    break
                except TimeoutException:
                    continue
            
            if not content_loaded:
                logger.warning("未能检测到内容区域加载完成，继续执行")
            
            # 等待页面完全加载（通过JavaScript）
            try:
                wait.until(lambda driver: driver.execute_script("return document.readyState") == "complete")
                logger.debug("页面完全加载完成")
            except TimeoutException:
                logger.warning("等待页面完全加载超时")
            
        except Exception as e:
            logger.warning(f"等待页面加载时出错: {e}")
    
    async def screenshot_wiki_page(self, item_name: str) -> Optional[bytes]:
        """截图Wiki页面的主要内容区域"""
        async with self._driver_lock:
            try:
                driver = await self._get_driver()
                if not driver:
                    return None
                
                # 构建Wiki URL
                encoded_name = urllib.parse.quote(item_name)
                url = f"https://dontstarve.huijiwiki.com/wiki/{encoded_name}"
                
                logger.info(f"正在访问Wiki页面: {url}")
                
                # 在事件循环中访问页面
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, lambda: driver.get(url))
                
                # 等待页面加载完成
                await self._wait_for_page_load(driver)
                await asyncio.sleep(3)  # 额外等待以确保所有内容加载
                
                # 尝试找到并截图主要内容区域
                screenshot_bytes = await self._screenshot_main_content(driver)
                
                if screenshot_bytes:
                    logger.info(f"Wiki页面截图成功: {item_name}, 大小: {len(screenshot_bytes)} bytes")
                    return screenshot_bytes
                else:
                    logger.warning(f"Wiki页面截图失败: {item_name}")
                    return None
                    
            except Exception as e:
                logger.error(f"截图Wiki页面时出错: {e}")
                return None
    
    async def _screenshot_main_content(self, driver) -> Optional[bytes]:
        """截图主要内容区域"""
        try:
            loop = asyncio.get_event_loop()
            
            # 等待页面完全加载
            wait = WebDriverWait(driver, 10)
            
            # 尝试等待页面关键元素加载完成
            try:
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".mw-parser-output")))
            except TimeoutException:
                logger.warning("等待页面加载超时，继续尝试截图")
            
            # 隐藏不需要的元素（导航栏、侧边栏等）
            await self._hide_unwanted_elements(driver)
            
            # 尝试多种选择器来找到主要内容区域，优先级从高到低
            content_selectors = [
                ".mw-parser-output",  # MediaWiki解析器输出区域（最精确）
                "#mw-content-text .mw-parser-output",  # 确保在内容文本区域内的解析器输出
                "#mw-content-text",  # MediaWiki内容文本区域
                "#content .mw-content-ltr",  # 左到右内容区域
                "#content",  # 主内容区域
            ]
            
            element = None
            selected_selector = None
            for selector in content_selectors:
                try:
                    element = driver.find_element(By.CSS_SELECTOR, selector)
                    if element and element.is_displayed():
                        # 检查元素是否有实际内容
                        if element.size['height'] > 100 and element.size['width'] > 100:
                            logger.info(f"找到合适的内容区域: {selector}")
                            selected_selector = selector
                            break
                        else:
                            logger.debug(f"元素尺寸过小，跳过: {selector}")
                            element = None
                except NoSuchElementException:
                    continue
            
            if not element:
                logger.warning("未找到合适的内容区域，使用整页截图")
                # 隐藏页面顶部和底部的导航元素
                await self._hide_navigation_elements(driver)
                await asyncio.sleep(1)
                # 整页截图
                screenshot_bytes = await loop.run_in_executor(None, lambda: driver.get_screenshot_as_png())
                return screenshot_bytes
            
            # 滚动到元素顶部
            await loop.run_in_executor(None, lambda: driver.execute_script(
                "arguments[0].scrollIntoView({block: 'start', behavior: 'smooth'});", 
                element))
            await asyncio.sleep(2)  # 等待滚动完成
            
            # 如果是整个内容区域，尝试优化显示
            if selected_selector in [".mw-parser-output", "#mw-content-text .mw-parser-output"]:
                # 移除或隐藏一些不需要的内容
                await self._optimize_content_display(driver)
                await asyncio.sleep(1)
            
            # 截图指定元素
            screenshot_bytes = await loop.run_in_executor(None, lambda: element.screenshot_as_png())
            
            # 检查截图是否有效
            if screenshot_bytes and len(screenshot_bytes) > 1000:  # 至少1KB
                return screenshot_bytes
            else:
                logger.warning("截图尺寸过小，可能截图失败")
                return None
            
        except Exception as e:
            logger.error(f"截图主要内容区域时出错: {e}")
            # 尝试整页截图作为fallback
            try:
                loop = asyncio.get_event_loop()
                # 隐藏导航元素后截图
                await self._hide_navigation_elements(driver)
                await asyncio.sleep(1)
                screenshot_bytes = await loop.run_in_executor(None, lambda: driver.get_screenshot_as_png())
                return screenshot_bytes
            except Exception as fallback_e:
                logger.error(f"fallback截图也失败: {fallback_e}")
                return None
    
    async def _get_adaptive_screenshot_size(self, driver, element) -> tuple:
        """获取自适应截图尺寸"""
        try:
            loop = asyncio.get_event_loop()
            
            # 获取元素的实际内容大小
            size_script = """
            var element = arguments[0];
            var rect = element.getBoundingClientRect();
            var scrollHeight = element.scrollHeight;
            var scrollWidth = element.scrollWidth;
            var clientHeight = element.clientHeight;
            var clientWidth = element.clientWidth;
            
            return {
                scrollHeight: scrollHeight,
                scrollWidth: scrollWidth,
                clientHeight: clientHeight,
                clientWidth: clientWidth,
                rectHeight: rect.height,
                rectWidth: rect.width
            };
            """
            
            size_info = await loop.run_in_executor(None, lambda: driver.execute_script(size_script, element))
            
            # 计算适当的尺寸
            width = max(size_info['scrollWidth'], size_info['clientWidth'], 800)
            height = max(size_info['scrollHeight'], size_info['clientHeight'])
            
            # 限制最大尺寸以避免截图过大
            max_width = 1200
            max_height = 2000
            
            if width > max_width:
                width = max_width
            if height > max_height:
                height = max_height
                
            logger.debug(f"自适应截图尺寸: {width}x{height}")
            return (int(width), int(height))
            
        except Exception as e:
            logger.warning(f"获取自适应尺寸失败: {e}")
            return (800, 600)  # 默认尺寸
    
    async def _screenshot_infobox(self, driver) -> Optional[bytes]:
        """单独截图信息框"""
        try:
            loop = asyncio.get_event_loop()
            
            # 尝试多种信息框选择器
            infobox_selectors = [
                "table.infobox",
                "table[class*='infobox']",
                ".infobox",
                "table.wikitable:first-of-type",
                "table[style*='float:right']",
                "table[align='right']"
            ]
            
            infobox = None
            for selector in infobox_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed() and element.size['height'] > 100:
                            # 检查是否真的是信息框（通常包含图片或位于右侧）
                            style = element.get_attribute('style') or ''
                            if 'float:right' in style or 'float: right' in style:
                                infobox = element
                                logger.info(f"找到信息框: {selector}")
                                break
                    if infobox:
                        break
                except NoSuchElementException:
                    continue
            
            if not infobox:
                logger.info("未找到信息框")
                return None
            
            # 滚动到信息框
            await loop.run_in_executor(None, lambda: driver.execute_script(
                "arguments[0].scrollIntoView({block: 'start', behavior: 'instant'});",
                infobox))
            await asyncio.sleep(1)
            
            # 获取自适应尺寸
            width, height = await self._get_adaptive_screenshot_size(driver, infobox)
            
            # 截图信息框
            screenshot_bytes = await loop.run_in_executor(None, lambda: infobox.screenshot_as_png())
            
            if screenshot_bytes and len(screenshot_bytes) > 1000:
                logger.info(f"信息框截图成功，尺寸: {len(screenshot_bytes)} bytes")
                return screenshot_bytes
            else:
                logger.warning("信息框截图失败或尺寸过小")
                return None
                
        except Exception as e:
            logger.warning(f"截图信息框时出错: {e}")
            return None
    
    async def _screenshot_main_content_without_infobox(self, driver) -> Optional[bytes]:
        """截图正文内容（排除信息框）"""
        try:
            loop = asyncio.get_event_loop()
            
            # 隐藏信息框
            hide_infobox_script = """
            var infoboxSelectors = [
                'table.infobox',
                'table[class*="infobox"]',
                '.infobox',
                'table[style*="float:right"]',
                'table[align="right"]'
            ];
            
            infoboxSelectors.forEach(function(selector) {
                var elements = document.querySelectorAll(selector);
                elements.forEach(function(el) {
                    var style = el.getAttribute('style') || '';
                    if (style.includes('float:right') || style.includes('float: right')) {
                        el.style.display = 'none';
                    }
                });
            });
            """
            
            await loop.run_in_executor(None, lambda: driver.execute_script(hide_infobox_script))
            
            # 等待DOM更新
            await asyncio.sleep(1)
            
            # 寻找主要内容区域
            content_selectors = [
                ".mw-parser-output",
                "#mw-content-text .mw-parser-output",
                "#mw-content-text"
            ]
            
            element = None
            for selector in content_selectors:
                try:
                    element = driver.find_element(By.CSS_SELECTOR, selector)
                    if element and element.is_displayed() and element.size['height'] > 100:
                        logger.info(f"找到正文内容区域: {selector}")
                        break
                except NoSuchElementException:
                    continue
            
            if not element:
                logger.warning("未找到正文内容区域")
                return None
            
            # 优化内容显示
            await self._optimize_content_display(driver)
            
            # 滚动到内容开始
            await loop.run_in_executor(None, lambda: driver.execute_script(
                "arguments[0].scrollIntoView({block: 'start', behavior: 'instant'});",
                element))
            await asyncio.sleep(1)
            
            # 获取自适应尺寸
            width, height = await self._get_adaptive_screenshot_size(driver, element)
            
            # 截图正文内容
            screenshot_bytes = await loop.run_in_executor(None, lambda: element.screenshot_as_png())
            
            if screenshot_bytes and len(screenshot_bytes) > 1000:
                logger.info(f"正文内容截图成功，尺寸: {len(screenshot_bytes)} bytes")
                return screenshot_bytes
            else:
                logger.warning("正文内容截图失败或尺寸过小")
                return None
                
        except Exception as e:
            logger.warning(f"截图正文内容时出错: {e}")
            return None
    
    async def screenshot_wiki_separate(self, item_name: str) -> dict:
        """分别截图信息栏和正文内容"""
        async with self._driver_lock:
            try:
                driver = await self._get_driver()
                if not driver:
                    return {'infobox': None, 'content': None}
                
                # 构建Wiki URL
                encoded_name = urllib.parse.quote(item_name)
                url = f"https://dontstarve.huijiwiki.com/wiki/{encoded_name}"
                
                logger.info(f"正在访问Wiki页面进行分离截图: {url}")
                
                # 访问页面
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, lambda: driver.get(url))
                
                # 等待页面加载完成
                await self._wait_for_page_load(driver)
                await asyncio.sleep(3)
                
                # 隐藏不需要的元素
                await self._hide_unwanted_elements(driver)
                
                results = {'infobox': None, 'content': None}
                
                # 截图信息框
                logger.info("开始截图信息框")
                infobox_bytes = await self._screenshot_infobox(driver)
                results['infobox'] = infobox_bytes
                
                # 重新加载页面以获取完整内容
                await loop.run_in_executor(None, lambda: driver.get(url))
                await self._wait_for_page_load(driver)
                await asyncio.sleep(2)
                await self._hide_unwanted_elements(driver)
                
                # 截图正文内容（不包含信息框）
                logger.info("开始截图正文内容")
                content_bytes = await self._screenshot_main_content_without_infobox(driver)
                results['content'] = content_bytes
                
                logger.info(f"分离截图完成 - 信息框: {'成功' if results['infobox'] else '失败'}, 正文: {'成功' if results['content'] else '失败'}")
                return results
                
            except Exception as e:
                logger.error(f"分离截图时出错: {e}")
                return {'infobox': None, 'content': None}
    
    async def screenshot_wiki_sections(self, item_name: str) -> List[bytes]:
        """截图Wiki页面的各个章节（高级功能）"""
        async with self._driver_lock:
            try:
                driver = await self._get_driver()
                if not driver:
                    return []
                
                # 构建Wiki URL
                encoded_name = urllib.parse.quote(item_name)
                url = f"https://dontstarve.huijiwiki.com/wiki/{encoded_name}"
                
                logger.info(f"正在访问Wiki页面进行分节截图: {url}")
                
                # 访问页面
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, lambda: driver.get(url))
                await asyncio.sleep(3)
                
                screenshots = []
                
                # 截图信息框（如果有）
                try:
                    infobox = driver.find_element(By.XPATH, "//table[contains(@class,'infobox')]")
                    if infobox and infobox.is_displayed():
                        screenshot_bytes = await loop.run_in_executor(None, lambda: infobox.screenshot_as_png())
                        screenshots.append(screenshot_bytes)
                        logger.info("信息框截图成功")
                except NoSuchElementException:
                    logger.info("未找到信息框")
                
                # 获取所有章节标题
                try:
                    headings = driver.find_elements(By.XPATH, "//span[@id]/ancestor::h2")
                    logger.info(f"找到 {len(headings)} 个章节")
                    
                    for i, heading in enumerate(headings):
                        try:
                            title = heading.text.strip()
                            if not title:
                                continue
                                
                            # 滚动到标题
                            await loop.run_in_executor(None, lambda: driver.execute_script("arguments[0].scrollIntoView();", heading))
                            await asyncio.sleep(1)
                            
                            # 尝试截图该章节的内容
                            # 这是一个简化实现，实际可能需要更复杂的逻辑来确定章节边界
                            section_element = heading.find_element(By.XPATH, "./following-sibling::*[1]")
                            if section_element and section_element.is_displayed():
                                screenshot_bytes = await loop.run_in_executor(None, lambda: section_element.screenshot_as_png())
                                screenshots.append(screenshot_bytes)
                                logger.info(f"章节 '{title}' 截图成功")
                                
                        except Exception as section_e:
                            logger.warning(f"章节截图失败: {section_e}")
                            continue
                
                except Exception as e:
                    logger.warning(f"获取章节时出错: {e}")
                
                return screenshots
                
            except Exception as e:
                logger.error(f"分节截图时出错: {e}")
                return []


# 全局实例
_wiki_screenshot_tool = None

async def get_wiki_screenshot_tool():
    """获取Wiki截图工具实例"""
    global _wiki_screenshot_tool
    if _wiki_screenshot_tool is None:
        _wiki_screenshot_tool = WikiScreenshotTool()
    return _wiki_screenshot_tool

async def screenshot_wiki_item(item_name: str) -> Optional[bytes]:
    """截图指定物品的Wiki页面"""
    try:
        tool = await get_wiki_screenshot_tool()
        return await tool.screenshot_wiki_page(item_name)
    except Exception as e:
        logger.error(f"截图Wiki物品失败: {e}")
        return None

async def screenshot_wiki_item_separate(item_name: str) -> dict:
    """分别截图指定物品的信息栏和正文内容"""
    try:
        tool = await get_wiki_screenshot_tool()
        return await tool.screenshot_wiki_separate(item_name)
    except Exception as e:
        logger.error(f"分离截图Wiki物品失败: {e}")
        return {'infobox': None, 'content': None}

async def cleanup_screenshot_tool():
    """清理截图工具资源"""
    global _wiki_screenshot_tool
    if _wiki_screenshot_tool:
        await _wiki_screenshot_tool.close_driver()
        _wiki_screenshot_tool = None