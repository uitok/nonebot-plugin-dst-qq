"""
Wiki截图工具
基于 nonebot-plugin-htmlrender 和 Playwright 实现的饥荒Wiki页面截图功能
"""

import asyncio
import urllib.parse
from typing import Optional, List

from nonebot import logger


class WikiScreenshotTool:
    """Wiki截图工具"""
    
    def __init__(self):
        pass
    
    def _safe_filename(self, name: str) -> str:
        """将文件名安全化"""
        import re
        return re.sub(r'[\\/*?:"<>|]', "_", name)
    
    async def _get_wiki_html(self, item_name: str) -> Optional[str]:
        """获取Wiki页面的HTML内容，并进行优化处理"""
        try:
            import httpx
            
            # 构建Wiki URL
            encoded_name = urllib.parse.quote(item_name)
            url = f"https://dontstarve.huijiwiki.com/wiki/{encoded_name}"
            
            logger.info(f"正在获取Wiki页面: {url}")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Cache-Control': 'max-age=0'
            }
            
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                # 添加重试机制
                for attempt in range(3):
                    try:
                        if attempt > 0:
                            logger.info(f"重试获取Wiki页面，第{attempt + 1}次尝试")
                            import asyncio
                            await asyncio.sleep(1)  # 等待1秒后重试
                        
                        response = await client.get(url, headers=headers)
                        response.raise_for_status()
                        
                        html_content = response.text
                        
                        # 检查是否获取到有效内容
                        if len(html_content) < 1000:
                            logger.warning(f"获取的HTML内容过短: {len(html_content)} 字符")
                            if attempt < 2:
                                continue
                        
                        # 优化HTML内容 - 移除不需要的元素
                        optimized_html = self._optimize_html_content(html_content)
                        
                        logger.info(f"成功获取Wiki页面，HTML长度: {len(html_content)} 字符")
                        return optimized_html
                        
                    except httpx.HTTPStatusError as e:
                        if e.response.status_code == 403:
                            logger.warning(f"访问被拒绝 (403)，尝试使用不同的User-Agent")
                            # 更换User-Agent
                            headers['User-Agent'] = f'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                            if attempt < 2:
                                continue
                        elif e.response.status_code == 404:
                            logger.error(f"Wiki页面不存在 (404): {url}")
                            return None
                        else:
                            logger.error(f"HTTP错误 {e.response.status_code}: {e}")
                            if attempt < 2:
                                continue
                        raise
                    except Exception as e:
                        logger.warning(f"第{attempt + 1}次尝试失败: {e}")
                        if attempt < 2:
                            continue
                        raise
                
                return None  # 所有重试都失败
                
        except Exception as e:
            logger.error(f"获取Wiki页面HTML失败: {e}")
            return None
    
    def _optimize_html_content(self, html_content: str) -> str:
        """优化HTML内容，移除不需要的元素"""
        try:
            from bs4 import BeautifulSoup
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 移除不需要的元素
            elements_to_remove = [
                # 导航和页面结构
                '#mw-navigation',
                '#mw-head',
                '#mw-page-base', 
                '#mw-head-base',
                '#footer',
                '.mw-notification-area',
                '#siteNotice',
                '.mw-indicators',
                
                # 编辑相关
                '.mw-editsection',
                '.mw-headline .mw-editsection',
                
                # 页面底部
                '.printfooter',
                '#catlinks',
                '.navbox',
                
                # 其他不需要的元素
                '.metadata',
                '#toc',  # 目录（可选）
            ]
            
            for selector in elements_to_remove:
                for element in soup.select(selector):
                    element.decompose()
            
            # 优化图片加载 - 添加懒加载属性
            for img in soup.find_all('img'):
                img['loading'] = 'lazy'
                # 限制图片最大宽度
                if img.get('style'):
                    img['style'] += '; max-width: 600px; height: auto;'
                else:
                    img['style'] = 'max-width: 600px; height: auto;'
            
            # 优化表格显示
            for table in soup.find_all('table'):
                if table.get('style'):
                    table['style'] += '; max-width: 100%; font-size: 12px;'
                else:
                    table['style'] = 'max-width: 100%; font-size: 12px;'
            
            # 添加CSS样式优化显示效果
            style_tag = soup.new_tag('style')
            style_tag.string = """
            body {
                font-family: Arial, sans-serif;
                line-height: 1.6;
                margin: 20px;
                background-color: #f8f9fa;
            }
            .mw-parser-output {
                background-color: white;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            table.infobox {
                float: right;
                margin: 0 0 20px 20px;
                clear: right;
                border: 1px solid #a2a9b1;
                background-color: #f8f9fa;
                max-width: 300px;
            }
            table.infobox th, table.infobox td {
                padding: 4px 8px;
                font-size: 12px;
            }
            h1, h2, h3, h4, h5, h6 {
                color: #000;
                border-bottom: 1px solid #a2a9b1;
                padding-bottom: 4px;
            }
            img {
                max-width: 100%;
                height: auto;
            }
            """
            soup.head.append(style_tag)
            
            return str(soup)
            
        except ImportError:
            logger.warning("BeautifulSoup未安装，使用原始HTML内容")
            return html_content
        except Exception as e:
            logger.warning(f"优化HTML内容失败: {e}, 使用原始内容")
            return html_content
    
    async def _extract_main_content(self, html_content: str) -> str:
        """提取主要内容区域"""
        try:
            from bs4 import BeautifulSoup
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 尝试找到主要内容区域
            content_selectors = [
                '.mw-parser-output',
                '#mw-content-text .mw-parser-output',
                '#mw-content-text',
                '#content .mw-content-ltr',
                '#content'
            ]
            
            main_content = None
            for selector in content_selectors:
                element = soup.select_one(selector)
                if element:
                    main_content = element
                    logger.debug(f"找到主要内容区域: {selector}")
                    break
            
            if main_content:
                # 创建新的HTML文档，只包含主要内容
                new_soup = BeautifulSoup('<!DOCTYPE html><html><head></head><body></body></html>', 'html.parser')
                
                # 复制head中的样式
                if soup.head:
                    for style in soup.head.find_all('style'):
                        new_soup.head.append(style)
                
                # 添加内容
                new_soup.body.append(main_content)
                
                return str(new_soup)
            else:
                logger.warning("未找到主要内容区域，使用完整HTML")
                return html_content
                
        except ImportError:
            logger.warning("BeautifulSoup未安装，无法提取主要内容")
            return html_content
        except Exception as e:
            logger.warning(f"提取主要内容失败: {e}")
            return html_content
    
    async def _extract_infobox(self, html_content: str) -> Optional[str]:
        """提取信息框HTML"""
        try:
            from bs4 import BeautifulSoup
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 尝试找到信息框
            infobox_selectors = [
                'table.infobox',
                'table[class*="infobox"]',
                '.infobox',
                'table.wikitable:first-of-type',
            ]
            
            for selector in infobox_selectors:
                elements = soup.select(selector)
                for element in elements:
                    # 检查是否真的是信息框（通常有float:right样式或在右侧）
                    style = element.get('style', '')
                    classes = ' '.join(element.get('class', []))
                    
                    if ('float:right' in style or 'float: right' in style or 
                        'infobox' in classes.lower()):
                        
                        # 创建新的HTML文档，只包含信息框
                        new_soup = BeautifulSoup('<!DOCTYPE html><html><head></head><body></body></html>', 'html.parser')
                        
                        # 添加样式
                        style_tag = new_soup.new_tag('style')
                        style_tag.string = """
                        body {
                            font-family: Arial, sans-serif;
                            margin: 10px;
                            background-color: #f8f9fa;
                        }
                        table.infobox {
                            border: 1px solid #a2a9b1;
                            background-color: #f8f9fa;
                            margin: 0;
                            width: auto;
                            max-width: 300px;
                        }
                        table.infobox th, table.infobox td {
                            padding: 4px 8px;
                            font-size: 12px;
                            border: 1px solid #a2a9b1;
                        }
                        table.infobox th {
                            background-color: #eaf3ff;
                            font-weight: bold;
                        }
                        img {
                            max-width: 100%;
                            height: auto;
                        }
                        """
                        new_soup.head.append(style_tag)
                        
                        # 添加信息框
                        new_soup.body.append(element)
                        
                        logger.info(f"找到信息框: {selector}")
                        return str(new_soup)
            
            logger.info("未找到信息框")
            return None
            
        except ImportError:
            logger.warning("BeautifulSoup未安装，无法提取信息框")
            return None
        except Exception as e:
            logger.warning(f"提取信息框失败: {e}")
            return None
    
    async def _extract_content_without_infobox(self, html_content: str) -> str:
        """提取正文内容（排除信息框）"""
        try:
            from bs4 import BeautifulSoup
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 移除信息框
            infobox_selectors = [
                'table.infobox',
                'table[class*="infobox"]',
                '.infobox',
            ]
            
            for selector in infobox_selectors:
                for element in soup.select(selector):
                    style = element.get('style', '')
                    classes = ' '.join(element.get('class', []))
                    
                    if ('float:right' in style or 'float: right' in style or 
                        'infobox' in classes.lower()):
                        element.decompose()
            
            # 提取主要内容
            return await self._extract_main_content(str(soup))
            
        except ImportError:
            logger.warning("BeautifulSoup未安装，使用原始HTML")
            return html_content
        except Exception as e:
            logger.warning(f"提取正文内容失败: {e}")
            return html_content
    
    async def screenshot_wiki_page(self, item_name: str) -> Optional[bytes]:
        """截图Wiki页面的主要内容区域"""
        try:
            # 延迟导入 htmlrender
            from nonebot_plugin_htmlrender import get_browser
            
            # 直接使用 playwright 访问页面
            encoded_name = urllib.parse.quote(item_name)
            url = f"https://dontstarve.huijiwiki.com/wiki/{encoded_name}"
            
            logger.info(f"正在截图Wiki页面: {url}")
            
            browser = await get_browser()
            
            # 创建上下文以启用更多反检测功能
            context = await browser.new_context(
                viewport={"width": 1200, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 EdgA/120.0.0.0",
                extra_http_headers={
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Cache-Control': 'max-age=0',
                    'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Microsoft Edge";v="120"',
                    'Sec-Ch-Ua-Mobile': '?0',
                    'Sec-Ch-Ua-Platform': '"Windows"',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-User': '?1',
                    'Upgrade-Insecure-Requests': '1'
                },
                ignore_https_errors=True,
                java_script_enabled=True
            )
            
            page = await context.new_page()
            
            try:
                # 先等待一个随机时间，模拟人类行为
                import random
                await page.wait_for_timeout(random.randint(1000, 3000))
                
                # 访问页面，使用更宽松的加载策略
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                
                # 检测是否遇到五秒盾页面
                shield_detected = False
                try:
                    # 检查常见的五秒盾元素
                    shield_elements = [
                        "text=正在检测环境",
                        "text=Just a moment",
                        "text=Please wait",
                        "text=Checking your browser",
                        "#cf-wrapper",
                        ".cf-browser-verification",
                        "[data-ray]"
                    ]
                    
                    for selector in shield_elements:
                        try:
                            element = await page.wait_for_selector(selector, timeout=2000)
                            if element:
                                shield_detected = True
                                logger.info("检测到五秒盾页面，等待通过...")
                                break
                        except:
                            continue
                    
                    if shield_detected:
                        # 等待五秒盾通过，最多等待15秒
                        logger.info("等待五秒盾验证完成...")
                        for attempt in range(15):
                            await page.wait_for_timeout(1000)
                            # 检查是否已经跳转到实际页面
                            current_url = page.url
                            if "challenge" not in current_url.lower() and "checking" not in current_url.lower():
                                try:
                                    # 尝试找到Wiki内容
                                    await page.wait_for_selector('.mw-parser-output', timeout=2000)
                                    logger.info("五秒盾验证通过，页面加载成功")
                                    break
                                except:
                                    continue
                        else:
                            logger.warning("五秒盾验证超时，继续尝试截图")
                    
                except Exception as e:
                    logger.debug(f"五秒盾检测出错: {e}")
                
                # 等待主要内容加载
                try:
                    await page.wait_for_selector('.mw-parser-output', timeout=15000)
                    logger.info("主要内容加载成功")
                except:
                    logger.warning("等待主要内容加载超时，继续执行")
                
                # 额外等待让页面稳定
                await page.wait_for_timeout(3000)
                
                # 隐藏不需要的元素
                hide_script = """
                // 隐藏导航和页面结构元素
                const hideSelectors = [
                    '#mw-navigation', '#mw-head', '#mw-page-base', '#mw-head-base',
                    '#footer', '.mw-notification-area', '#siteNotice', '.mw-indicators',
                    '.mw-editsection', '.printfooter', '#catlinks', '.navbox'
                ];
                hideSelectors.forEach(selector => {
                    const elements = document.querySelectorAll(selector);
                    elements.forEach(el => el.style.display = 'none');
                });
                
                // 调整body的样式
                document.body.style.paddingTop = '0';
                document.body.style.margin = '0';
                """
                
                await page.evaluate(hide_script)
                await page.wait_for_timeout(1000)
                
                # 尝试找到主要内容区域
                content_selectors = [
                    '.mw-parser-output',
                    '#mw-content-text .mw-parser-output', 
                    '#mw-content-text',
                    '#content'
                ]
                
                element = None
                for selector in content_selectors:
                    try:
                        element = await page.query_selector(selector)
                        if element:
                            logger.info(f"找到内容区域: {selector}")
                            break
                    except:
                        continue
                
                if element:
                    # 截图指定元素
                    screenshot_bytes = await element.screenshot(type="png")
                else:
                    # 整页截图
                    logger.warning("未找到特定内容区域，使用整页截图")
                    screenshot_bytes = await page.screenshot(type="png", full_page=True)
                
                if screenshot_bytes:
                    logger.info(f"Wiki页面截图成功: {item_name}, 大小: {len(screenshot_bytes)} bytes")
                    return screenshot_bytes
                else:
                    logger.warning(f"Wiki页面截图失败: {item_name}")
                    return None
                    
            finally:
                await page.close()
                await context.close()
                
        except Exception as e:
            logger.error(f"截图Wiki页面时出错: {e}")
            return None
    
    async def screenshot_wiki_separate(self, item_name: str) -> dict:
        """分别截图信息栏和正文内容"""
        try:
            # 延迟导入 htmlrender
            from nonebot_plugin_htmlrender import html_to_pic
            
            # 获取HTML内容
            html_content = await self._get_wiki_html(item_name)
            if not html_content:
                return {'infobox': None, 'content': None}
            
            results = {'infobox': None, 'content': None}
            
            # 截图信息框
            logger.info("开始截图信息框")
            infobox_html = await self._extract_infobox(html_content)
            if infobox_html:
                try:
                    infobox_bytes = await html_to_pic(
                        html=infobox_html,
                        viewport={"width": 350, "height": 600},
                        wait=1000,
                        type="png",
                        device_scale_factor=1.0
                    )
                    results['infobox'] = infobox_bytes
                    logger.info("信息框截图成功")
                except Exception as e:
                    logger.warning(f"信息框截图失败: {e}")
            
            # 截图正文内容（不包含信息框）
            logger.info("开始截图正文内容")
            content_html = await self._extract_content_without_infobox(html_content)
            if content_html:
                try:
                    content_bytes = await html_to_pic(
                        html=content_html,
                        viewport={"width": 1200, "height": 800},
                        wait=2000,
                        type="png",
                        device_scale_factor=1.0
                    )
                    results['content'] = content_bytes
                    logger.info("正文内容截图成功")
                except Exception as e:
                    logger.warning(f"正文内容截图失败: {e}")
            
            logger.info(f"分离截图完成 - 信息框: {'成功' if results['infobox'] else '失败'}, 正文: {'成功' if results['content'] else '失败'}")
            return results
            
        except Exception as e:
            logger.error(f"分离截图时出错: {e}")
            return {'infobox': None, 'content': None}
    
    async def screenshot_wiki_sections(self, item_name: str) -> List[bytes]:
        """截图Wiki页面的各个章节（高级功能）"""
        try:
            # 延迟导入 htmlrender
            from nonebot_plugin_htmlrender import html_to_pic
            
            # 获取HTML内容
            html_content = await self._get_wiki_html(item_name)
            if not html_content:
                return []
            
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            screenshots = []
            
            # 截图信息框（如果有）
            infobox_html = await self._extract_infobox(html_content)
            if infobox_html:
                try:
                    infobox_bytes = await html_to_pic(
                        html=infobox_html,
                        viewport={"width": 350, "height": 600},
                        wait=1000,
                        type="png"
                    )
                    if infobox_bytes:
                        screenshots.append(infobox_bytes)
                        logger.info("信息框截图成功")
                except Exception as e:
                    logger.warning(f"信息框截图失败: {e}")
            
            # 获取所有章节标题和内容
            try:
                headings = soup.select('h2, h3')
                logger.info(f"找到 {len(headings)} 个章节")
                
                for i, heading in enumerate(headings):
                    try:
                        title = heading.get_text(strip=True)
                        if not title:
                            continue
                        
                        # 收集该章节的内容
                        section_elements = []
                        section_elements.append(heading)
                        
                        # 获取后续元素直到下一个同级或更高级标题
                        current = heading.next_sibling
                        while current:
                            if hasattr(current, 'name'):
                                if current.name in ['h1', 'h2', 'h3'] and current.name <= heading.name:
                                    break
                                section_elements.append(current)
                            current = current.next_sibling
                        
                        if len(section_elements) > 1:  # 有实际内容
                            # 创建章节HTML
                            section_soup = BeautifulSoup('<!DOCTYPE html><html><head></head><body></body></html>', 'html.parser')
                            
                            # 添加样式
                            style_tag = section_soup.new_tag('style')
                            style_tag.string = """
                            body {
                                font-family: Arial, sans-serif;
                                line-height: 1.6;
                                margin: 20px;
                                background-color: #f8f9fa;
                            }
                            h2, h3, h4 {
                                color: #000;
                                border-bottom: 1px solid #a2a9b1;
                                padding-bottom: 4px;
                            }
                            img {
                                max-width: 100%;
                                height: auto;
                            }
                            """
                            section_soup.head.append(style_tag)
                            
                            # 添加章节内容
                            for element in section_elements:
                                if hasattr(element, 'name'):
                                    section_soup.body.append(element)
                            
                            # 截图章节
                            try:
                                section_bytes = await html_to_pic(
                                    html=str(section_soup),
                                    viewport={"width": 1200, "height": 800},
                                    wait=1500,
                                    type="png"
                                )
                                if section_bytes:
                                    screenshots.append(section_bytes)
                                    logger.info(f"章节 '{title}' 截图成功")
                            except Exception as section_e:
                                logger.warning(f"章节 '{title}' 截图失败: {section_e}")
                                
                    except Exception as section_e:
                        logger.warning(f"处理章节时出错: {section_e}")
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
        # htmlrender 插件会自动管理浏览器资源，无需手动清理
        _wiki_screenshot_tool = None