"""
文字转图片模块
使用PIL库将文字转换为图片
"""

import io
import base64
from PIL import Image, ImageDraw, ImageFont
from typing import Optional, Tuple
import textwrap
import os
from pathlib import Path

class TextToImage:
    """文字转图片转换器"""
    
    def __init__(
        self,
        font_size: int = 24,
        font_color: str = "#000000",
        background_color: str = "#FFFFFF",
        padding: int = 20,
        max_width: int = 800,
        line_spacing: int = 8
    ):
        """
        初始化文字转图片转换器
        
        Args:
            font_size: 字体大小
            font_color: 字体颜色
            background_color: 背景色
            padding: 内边距
            max_width: 最大宽度
            line_spacing: 行间距
        """
        self.font_size = font_size
        self.font_color = font_color
        self.background_color = background_color
        self.padding = padding
        self.max_width = max_width
        self.line_spacing = line_spacing
        
        # 尝试加载字体
        self.font = self._load_font()
    
    def _load_font(self) -> ImageFont.FreeTypeFont:
        """加载字体文件"""
        # 常见的中文字体路径
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/System/Library/Fonts/PingFang.ttc",
            "/System/Library/Fonts/STHeiti Light.ttc",
            "C:/Windows/Fonts/msyh.ttc",
            "C:/Windows/Fonts/simsun.ttc",
        ]
        
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    return ImageFont.truetype(font_path, self.font_size)
                except Exception:
                    continue
        
        # 如果没有找到字体文件，使用默认字体
        try:
            return ImageFont.load_default(size=self.font_size)
        except Exception:
            return ImageFont.load_default()
    
    def _calculate_text_size(self, text: str) -> Tuple[int, int]:
        """计算文本的尺寸"""
        lines = text.split('\n')
        max_line_width = 0
        total_height = 0
        
        for line in lines:
            # 对长行进行换行处理
            wrapped_lines = textwrap.fill(line, width=50).split('\n')
            for wrapped_line in wrapped_lines:
                bbox = self.font.getbbox(wrapped_line)
                line_width = bbox[2] - bbox[0]
                line_height = bbox[3] - bbox[1]
                
                max_line_width = max(max_line_width, line_width)
                total_height += line_height + self.line_spacing
        
        return max_line_width, total_height
    
    def text_to_image(self, text: str) -> str:
        """
        将文字转换为base64编码的图片
        
        Args:
            text: 要转换的文字
            
        Returns:
            base64编码的图片数据
        """
        if not text.strip():
            text = "空消息"
        
        # 预处理文本，进行自动换行
        lines = []
        for line in text.split('\n'):
            if not line.strip():
                lines.append('')
            else:
                # 自动换行，每50个字符换一行
                wrapped = textwrap.fill(line, width=50)
                lines.extend(wrapped.split('\n'))
        
        processed_text = '\n'.join(lines)
        
        # 计算文本尺寸
        text_width, text_height = self._calculate_text_size(processed_text)
        
        # 计算图片尺寸
        img_width = min(text_width + 2 * self.padding, self.max_width)
        img_height = text_height + 2 * self.padding
        
        # 确保最小尺寸
        img_width = max(img_width, 200)
        img_height = max(img_height, 100)
        
        # 创建图片
        image = Image.new('RGB', (img_width, img_height), self.background_color)
        draw = ImageDraw.Draw(image)
        
        # 绘制文本
        y_offset = self.padding
        for line in processed_text.split('\n'):
            if line.strip():
                draw.text(
                    (self.padding, y_offset), 
                    line, 
                    font=self.font, 
                    fill=self.font_color
                )
            
            # 计算行高
            bbox = self.font.getbbox(line if line.strip() else 'A')
            line_height = bbox[3] - bbox[1]
            y_offset += line_height + self.line_spacing
        
        # 转换为base64
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        buffer.seek(0)
        
        img_base64 = base64.b64encode(buffer.getvalue()).decode()
        return f"base64://{img_base64}"


# 全局实例
_text_to_image = TextToImage(
    font_size=20,
    font_color="#2c3e50",
    background_color="#f8f9fa",
    padding=15,
    max_width=700,
    line_spacing=6
)

def convert_text_to_image(text: str) -> str:
    """
    将文字转换为图片的便捷函数
    
    Args:
        text: 要转换的文字
        
    Returns:
        base64编码的图片数据，格式为 "base64://..."
    """
    return _text_to_image.text_to_image(text)