"""
文字转图片模块
使用nonebot-plugin-htmlrender将文字转换为图片
"""

import base64
from typing import Optional
from pathlib import Path
from nonebot import logger

# 延迟导入htmlrender，避免启动时的依赖问题
_htmlrender_available = None

def _check_htmlrender():
    """检查htmlrender是否可用"""
    global _htmlrender_available
    if _htmlrender_available is None:
        try:
            from nonebot import require
            require("nonebot_plugin_htmlrender")
            from nonebot_plugin_htmlrender import text_to_pic
            _htmlrender_available = True
            logger.success("HTMLRender插件加载成功")
        except Exception as e:
            _htmlrender_available = False
            logger.warning(f"HTMLRender插件不可用，将使用备用方案: {e}")
    return _htmlrender_available

async def convert_text_to_image_async(text: str) -> str:
    """
    异步将文字转换为图片
    
    Args:
        text: 要转换的文字
        
    Returns:
        base64格式的图片数据字符串或原文本
    """
    if not text.strip():
        text = "空消息"
    
    # 检查htmlrender是否可用
    if _check_htmlrender():
        try:
            from nonebot_plugin_htmlrender import text_to_pic
            
            # 使用htmlrender生成图片 - 优化参数减少文件大小
            try:
                pic_bytes = await text_to_pic(
                    text=text,
                    width=600,  # 减少宽度以减小文件大小
                    device_scale_factor=1.0  # 避免高分辨率
                )
            except Exception as e:
                logger.error(f"text_to_pic调用失败: {e}")
                # 尝试使用更基础参数
                pic_bytes = await text_to_pic(text=text)
            
            # 检查图片大小，如果太大就返回文本
            max_image_size = 100 * 1024  # 100KB限制
            if len(pic_bytes) > max_image_size:
                logger.warning(f"图片太大({len(pic_bytes)} bytes > {max_image_size} bytes)，回退到文本模式")
                return text
            
            # 转换为base64
            img_base64 = base64.b64encode(pic_bytes).decode()
            logger.debug(f"HTMLRender生成图片大小: {len(pic_bytes)} bytes, base64长度: {len(img_base64)}")
            
            # OneBot支持的图片格式 - 返回base64字符串让外层处理
            return f"base64://{img_base64}"
            
        except Exception as e:
            logger.error(f"HTMLRender生成图片失败，使用备用方案: {e}")
            return await _fallback_text_to_image(text)
    else:
        return await _fallback_text_to_image(text)

async def _fallback_text_to_image(text: str) -> str:
    """
    备用的PIL图片生成方案
    
    Args:
        text: 要转换的文字
        
    Returns:
        base64格式的图片数据字符串或原文本
    """
    try:
        import io
        import textwrap
        import os
        from PIL import Image, ImageDraw, ImageFont
        
        if not text.strip():
            text = "空消息"
        
        # 字体设置
        font_size = 20
        font_color = "#2c3e50"
        background_color = "#f8f9fa"
        padding = 15
        max_width = 700
        line_spacing = 6
        
        # 加载字体
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/System/Library/Fonts/PingFang.ttc",
            "C:/Windows/Fonts/msyh.ttc",
        ]
        
        font = None
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    font = ImageFont.truetype(font_path, font_size)
                    break
                except Exception:
                    continue
        
        if not font:
            try:
                font = ImageFont.load_default(size=font_size)
            except Exception:
                font = ImageFont.load_default()
        
        # 文本预处理
        lines = []
        for line in text.split('\n'):
            if not line.strip():
                lines.append('')
            else:
                wrapped = textwrap.fill(line, width=50)
                lines.extend(wrapped.split('\n'))
        
        processed_text = '\n'.join(lines)
        
        # 计算尺寸
        text_lines = processed_text.split('\n')
        max_line_width = 0
        total_height = 0
        
        for line in text_lines:
            if hasattr(font, 'getbbox'):
                bbox = font.getbbox(line if line.strip() else 'A')
                line_width = bbox[2] - bbox[0]
                line_height = bbox[3] - bbox[1]
            else:
                # 兼容旧版PIL
                line_width, line_height = font.getsize(line if line.strip() else 'A')
            
            max_line_width = max(max_line_width, line_width)
            total_height += line_height + line_spacing
        
        # 计算图片尺寸
        img_width = min(max_line_width + 2 * padding, max_width)
        img_height = total_height + 2 * padding
        img_width = max(img_width, 200)
        img_height = max(img_height, 100)
        
        # 创建图片
        image = Image.new('RGB', (img_width, img_height), background_color)
        draw = ImageDraw.Draw(image)
        
        # 绘制文本
        y_offset = padding
        for line in text_lines:
            if line.strip():
                draw.text((padding, y_offset), line, font=font, fill=font_color)
            
            if hasattr(font, 'getbbox'):
                bbox = font.getbbox(line if line.strip() else 'A')
                line_height = bbox[3] - bbox[1]
            else:
                _, line_height = font.getsize(line if line.strip() else 'A')
            
            y_offset += line_height + line_spacing
        
        # 转换为base64 - 先尝试JPEG压缩
        buffer = io.BytesIO()
        
        # 转换为RGB（JPEG不支持RGBA）
        if image.mode != 'RGB':
            rgb_image = Image.new('RGB', image.size, background_color)
            rgb_image.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
            image = rgb_image
        
        # 尝试JPEG压缩
        image.save(buffer, format='JPEG', quality=85, optimize=True)
        buffer.seek(0)
        
        # 检查图片大小
        pic_bytes = buffer.getvalue()
        max_image_size = 100 * 1024  # 100KB限制
        
        # 如果JPEG还是太大，尝试更低质量
        if len(pic_bytes) > max_image_size:
            buffer = io.BytesIO()
            image.save(buffer, format='JPEG', quality=60, optimize=True)
            buffer.seek(0)
            pic_bytes = buffer.getvalue()
            
            # 如果还是太大，返回文本
            if len(pic_bytes) > max_image_size:
                logger.warning(f"PIL图片太大({len(pic_bytes)} bytes > {max_image_size} bytes)，回退到文本模式")
                return text
        
        img_base64 = base64.b64encode(pic_bytes).decode()
        logger.debug(f"PIL生成图片大小: {len(pic_bytes)} bytes, base64长度: {len(img_base64)}")
        
        # OneBot支持的图片格式 - 返回base64字符串让外层处理
        return f"base64://{img_base64}"
        
    except Exception as e:
        logger.error(f"备用图片生成失败: {e}")
        # 如果PIL也失败，返回纯文本
        return text

def convert_text_to_image(text: str) -> str:
    """
    同步包装器，用于向后兼容
    
    Args:
        text: 要转换的文字
        
    Returns:
        base64格式的图片数据字符串或原文本
    """
    import asyncio
    
    try:
        # 尝试在现有事件循环中运行
        loop = asyncio.get_running_loop()
        # 如果已有事件循环，创建任务
        task = asyncio.create_task(convert_text_to_image_async(text))
        return asyncio.run_coroutine_threadsafe(task, loop).result(timeout=10)
    except RuntimeError:
        # 没有运行的事件循环，创建新的
        return asyncio.run(convert_text_to_image_async(text))
    except Exception as e:
        logger.error(f"图片生成失败: {e}")
        return text