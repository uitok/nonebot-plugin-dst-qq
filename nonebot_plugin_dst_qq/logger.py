"""
结构化日志系统 - 提供统一的日志格式和上下文信息
"""

import logging
import json
import time
from typing import Dict, Any, Optional, Union
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, asdict
from functools import wraps
import traceback
import asyncio


class LogLevel(Enum):
    """日志级别枚举"""
    DEBUG = "DEBUG"
    INFO = "INFO" 
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogCategory(Enum):
    """日志分类枚举"""
    API = "api"           # API请求相关
    COMMAND = "command"   # 命令处理相关
    MESSAGE = "message"   # 消息互通相关
    CACHE = "cache"       # 缓存操作相关
    DATABASE = "database" # 数据库操作相关
    SYSTEM = "system"     # 系统级别操作
    SECURITY = "security" # 安全相关
    PERFORMANCE = "performance" # 性能监控
    USER = "user"         # 用户操作相关


@dataclass
class LogContext:
    """日志上下文信息"""
    timestamp: str
    level: str
    category: str
    module: str
    function: str
    message: str
    extra: Dict[str, Any] = None
    user_id: Optional[str] = None
    cluster_name: Optional[str] = None
    world_name: Optional[str] = None
    request_id: Optional[str] = None
    duration: Optional[float] = None
    error: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        data = asdict(self)
        # 移除空值
        return {k: v for k, v in data.items() if v is not None}


class StructuredLogger:
    """结构化日志记录器"""
    
    def __init__(self, name: str, enable_json: bool = False):
        """
        初始化结构化日志记录器
        
        Args:
            name: 记录器名称
            enable_json: 是否启用JSON格式输出
        """
        self.logger = logging.getLogger(name)
        self.enable_json = enable_json
        self.module_name = name
        
        # 设置默认格式化器（如果还没有处理器）
        if not self.logger.handlers:
            self._setup_default_handler()
    
    def _setup_default_handler(self):
        """设置默认处理器"""
        handler = logging.StreamHandler()
        
        if self.enable_json:
            formatter = JsonFormatter()
        else:
            formatter = StructuredFormatter()
            
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    def _create_context(
        self,
        level: LogLevel,
        category: LogCategory,
        message: str,
        function_name: str = None,
        **kwargs
    ) -> LogContext:
        """创建日志上下文"""
        import inspect
        
        # 获取调用函数信息
        if function_name is None:
            frame = inspect.currentframe()
            try:
                # 向上查找调用栈，跳过内部方法
                caller_frame = frame.f_back.f_back
                function_name = caller_frame.f_code.co_name
            finally:
                del frame
        
        return LogContext(
            timestamp=datetime.now().isoformat(),
            level=level.value,
            category=category.value,
            module=self.module_name,
            function=function_name or "unknown",
            message=message,
            **kwargs
        )
    
    def _log(self, context: LogContext):
        """内部日志记录方法"""
        level = getattr(logging, context.level)
        
        if self.enable_json:
            # JSON格式
            self.logger.log(level, json.dumps(context.to_dict(), ensure_ascii=False, indent=None))
        else:
            # 结构化文本格式
            extra_info = ""
            if context.extra:
                extra_parts = []
                for key, value in context.extra.items():
                    extra_parts.append(f"{key}={value}")
                extra_info = f" [{', '.join(extra_parts)}]" if extra_parts else ""
            
            # 构建上下文信息
            ctx_parts = []
            if context.user_id:
                ctx_parts.append(f"user:{context.user_id}")
            if context.cluster_name:
                ctx_parts.append(f"cluster:{context.cluster_name}")
            if context.world_name:
                ctx_parts.append(f"world:{context.world_name}")
            if context.request_id:
                ctx_parts.append(f"req:{context.request_id}")
            if context.duration is not None:
                ctx_parts.append(f"duration:{context.duration:.3f}s")
            
            ctx_info = f" <{', '.join(ctx_parts)}>" if ctx_parts else ""
            
            # 错误信息
            error_info = ""
            if context.error:
                error_info = f" ERROR: {context.error.get('message', '')} ({context.error.get('type', '')})"
            
            log_message = f"[{context.category.upper()}] {context.function}() - {context.message}{ctx_info}{extra_info}{error_info}"
            
            self.logger.log(level, log_message)
    
    def debug(
        self,
        message: str,
        category: LogCategory = LogCategory.SYSTEM,
        **kwargs
    ):
        """记录调试日志"""
        context = self._create_context(LogLevel.DEBUG, category, message, **kwargs)
        self._log(context)
    
    def info(
        self,
        message: str,
        category: LogCategory = LogCategory.SYSTEM,
        **kwargs
    ):
        """记录信息日志"""
        context = self._create_context(LogLevel.INFO, category, message, **kwargs)
        self._log(context)
    
    def warning(
        self,
        message: str,
        category: LogCategory = LogCategory.SYSTEM,
        **kwargs
    ):
        """记录警告日志"""
        context = self._create_context(LogLevel.WARNING, category, message, **kwargs)
        self._log(context)
    
    def error(
        self,
        message: str,
        category: LogCategory = LogCategory.SYSTEM,
        error: Exception = None,
        **kwargs
    ):
        """记录错误日志"""
        error_info = None
        if error:
            error_info = {
                "type": type(error).__name__,
                "message": str(error),
                "traceback": traceback.format_exc() if error else None
            }
        
        context = self._create_context(
            LogLevel.ERROR,
            category,
            message,
            error=error_info,
            **kwargs
        )
        self._log(context)
    
    def critical(
        self,
        message: str,
        category: LogCategory = LogCategory.SYSTEM,
        error: Exception = None,
        **kwargs
    ):
        """记录严重错误日志"""
        error_info = None
        if error:
            error_info = {
                "type": type(error).__name__,
                "message": str(error),
                "traceback": traceback.format_exc() if error else None
            }
        
        context = self._create_context(
            LogLevel.CRITICAL,
            category,
            message,
            error=error_info,
            **kwargs
        )
        self._log(context)
    
    def api_request(
        self,
        method: str,
        url: str,
        status_code: int = None,
        duration: float = None,
        **kwargs
    ):
        """记录API请求日志"""
        message = f"{method.upper()} {url}"
        if status_code:
            message += f" -> {status_code}"
        
        level = LogLevel.INFO
        if status_code and status_code >= 400:
            level = LogLevel.ERROR if status_code >= 500 else LogLevel.WARNING
        
        context = self._create_context(
            level,
            LogCategory.API,
            message,
            duration=duration,
            extra={"method": method, "url": url, "status_code": status_code},
            **kwargs
        )
        self._log(context)
    
    def command_execution(
        self,
        command: str,
        user_id: str = None,
        success: bool = True,
        duration: float = None,
        **kwargs
    ):
        """记录命令执行日志"""
        message = f"执行命令: {command}"
        if not success:
            message += " (失败)"
        
        context = self._create_context(
            LogLevel.INFO if success else LogLevel.ERROR,
            LogCategory.COMMAND,
            message,
            user_id=user_id,
            duration=duration,
            extra={"command": command, "success": success},
            **kwargs
        )
        self._log(context)
    
    def message_sync(
        self,
        action: str,
        count: int = None,
        cluster_name: str = None,
        world_name: str = None,
        **kwargs
    ):
        """记录消息同步日志"""
        message = f"消息同步: {action}"
        if count is not None:
            message += f" (数量: {count})"
        
        context = self._create_context(
            LogLevel.INFO,
            LogCategory.MESSAGE,
            message,
            cluster_name=cluster_name,
            world_name=world_name,
            extra={"action": action, "count": count},
            **kwargs
        )
        self._log(context)
    
    def cache_operation(
        self,
        operation: str,
        cache_key: str = None,
        hit: bool = None,
        **kwargs
    ):
        """记录缓存操作日志"""
        message = f"缓存{operation}"
        if cache_key:
            message += f": {cache_key}"
        if hit is not None:
            message += f" ({'命中' if hit else '未命中'})"
        
        context = self._create_context(
            LogLevel.DEBUG,
            LogCategory.CACHE,
            message,
            extra={"operation": operation, "cache_key": cache_key, "hit": hit},
            **kwargs
        )
        self._log(context)
    
    def performance_metric(
        self,
        metric_name: str,
        value: Union[int, float],
        unit: str = "",
        **kwargs
    ):
        """记录性能指标日志"""
        message = f"性能指标 {metric_name}: {value}{unit}"
        
        context = self._create_context(
            LogLevel.INFO,
            LogCategory.PERFORMANCE,
            message,
            extra={"metric_name": metric_name, "value": value, "unit": unit},
            **kwargs
        )
        self._log(context)


class JsonFormatter(logging.Formatter):
    """JSON格式化器"""
    
    def format(self, record):
        try:
            # 如果消息已经是JSON字符串，直接返回
            message = record.getMessage()
            if isinstance(message, str):
                # 验证是否为有效JSON
                json.loads(message)
                return message
            else:
                # 如果不是字符串，转换为JSON
                return json.dumps(message, ensure_ascii=False, indent=None)
        except (json.JSONDecodeError, ValueError, TypeError):
            # 如果不是JSON，返回原始消息
            return str(record.getMessage())


class StructuredFormatter(logging.Formatter):
    """结构化文本格式化器"""
    
    def format(self, record):
        # 添加时间戳
        formatted_time = self.formatTime(record, datefmt='%Y-%m-%d %H:%M:%S')
        return f"{formatted_time} | {record.levelname:8} | {record.getMessage()}"


def get_logger(name: str, enable_json: bool = False) -> StructuredLogger:
    """
    获取结构化日志记录器
    
    Args:
        name: 记录器名称，通常使用 __name__
        enable_json: 是否启用JSON格式输出
        
    Returns:
        结构化日志记录器实例
    """
    return StructuredLogger(name, enable_json)


def log_execution_time(category: LogCategory = LogCategory.PERFORMANCE):
    """
    装饰器：记录函数执行时间
    
    Args:
        category: 日志分类
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                logger.performance_metric(
                    f"{func.__name__}_execution_time",
                    duration,
                    "s",
                    function_name=func.__name__
                )
                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.error(
                    f"函数执行失败: {func.__name__}",
                    category=category,
                    error=e,
                    duration=duration,
                    function_name=func.__name__
                )
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                logger.performance_metric(
                    f"{func.__name__}_execution_time",
                    duration,
                    "s",
                    function_name=func.__name__
                )
                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.error(
                    f"函数执行失败: {func.__name__}",
                    category=category,
                    error=e,
                    duration=duration,
                    function_name=func.__name__
                )
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


def log_api_call(func):
    """
    装饰器：记录API调用
    """
    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        logger = get_logger(self.__class__.__module__)
        start_time = time.time()
        
        # 提取方法和URL信息
        method = getattr(self, '_current_method', 'UNKNOWN')
        url = getattr(self, '_current_url', 'unknown')
        
        try:
            result = await func(self, *args, **kwargs)
            duration = time.time() - start_time
            
            # 从结果中提取状态码
            status_code = None
            if hasattr(result, 'code'):
                status_code = result.code
            
            logger.api_request(
                method=method,
                url=url,
                status_code=status_code,
                duration=duration,
                function_name=func.__name__
            )
            
            return result
        except Exception as e:
            duration = time.time() - start_time
            logger.api_request(
                method=method,
                url=url,
                status_code=500,
                duration=duration,
                function_name=func.__name__
            )
            logger.error(
                f"API调用失败: {method} {url}",
                category=LogCategory.API,
                error=e,
                function_name=func.__name__
            )
            raise
    
    return wrapper
