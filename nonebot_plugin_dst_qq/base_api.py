"""
基础API客户端类 - 统一HTTP请求处理和错误处理机制
"""

import httpx
from typing import Dict, Any, Optional, Union
from abc import ABC, abstractmethod
import asyncio
from dataclasses import dataclass
from enum import Enum
# 导入配置
from .config import Config
from nonebot import logger

class HTTPMethod(Enum):
    """HTTP请求方法枚举"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"

@dataclass
class APIResponse:
    """API响应数据类"""
    code: int
    data: Any = None
    message: str = ""
    success: bool = False
    
    def __post_init__(self):
        """初始化后处理"""
        self.success = self.code == 200 or self.code == 0

class APIError(Exception):
    """API错误基类"""
    def __init__(self, code: int, message: str, response: Optional[httpx.Response] = None):
        self.code = code
        self.message = message
        self.response = response
        super().__init__(f"API错误 {code}: {message}")

class BaseAPI(ABC):
    """
    基础API客户端类
    
    提供统一的HTTP请求处理、错误处理、重试机制和日志记录
    """
    
    def __init__(self, config: Config, service_name: str = "API"):
        """
        初始化基础API客户端
        
        Args:
            config: 插件配置对象
            service_name: 服务名称，用于日志记录
        """
        self.config = config
        self.service_name = service_name
        self.base_url = config.dmp.base_url
        self.token = config.dmp.token
        
        # 基础请求头
        self._base_headers = {
            "Authorization": self.token,
            "Content-Type": "application/json",
            "User-Agent": f"NoneBot-DST-Plugin/{service_name}"
        }
        
        # 请求配置
        self.timeout = getattr(config, 'api_timeout', 30.0)
        self.max_retries = getattr(config, 'api_max_retries', 3)
        self.retry_delay = getattr(config, 'api_retry_delay', 1.0)
        
        # 验证配置
        self._validate_config()
    
    def _validate_config(self) -> None:
        """验证配置参数"""
        if not self.base_url:
            raise ValueError(f"{self.service_name}: base_url 不能为空")
        if not self.token:
            logger.warning(f"[{self.service_name}] Token未设置，某些API可能无法访问")
    
    def _merge_headers(self, custom_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """
        合并请求头
        
        Args:
            custom_headers: 自定义请求头
            
        Returns:
            合并后的请求头
        """
        headers = self._base_headers.copy()
        if custom_headers:
            headers.update(custom_headers)
        return headers
    
    def _build_url(self, endpoint: str) -> str:
        """
        构建完整的API URL
        
        Args:
            endpoint: API端点
            
        Returns:
            完整的API URL
        """
        if endpoint.startswith('http'):
            return endpoint
        
        base = self.base_url.rstrip('/')
        endpoint = endpoint.lstrip('/')
        return f"{base}/{endpoint}"
    
    async def _handle_response(self, response: httpx.Response) -> APIResponse:
        """
        处理HTTP响应
        
        Args:
            response: HTTP响应对象
            
        Returns:
            标准化的API响应对象
        """
        try:
            # 尝试解析JSON响应
            data = response.json()
            
            # 标准化响应格式
            if isinstance(data, dict):
                code = data.get("code", response.status_code)
                message = data.get("message", data.get("msg", ""))
                response_data = data.get("data", data)
            else:
                code = response.status_code
                message = ""
                response_data = data
            
            return APIResponse(
                code=code,
                data=response_data,
                message=message
            )
            
        except (ValueError, TypeError):
            # 如果不是JSON响应，返回文本内容
            return APIResponse(
                code=response.status_code,
                data=response.text,
                message=f"非JSON响应: {response.status_code}"
            )
    
    def _handle_http_error(self, error: httpx.HTTPStatusError) -> APIResponse:
        """
        处理HTTP状态错误
        
        Args:
            error: HTTP状态错误
            
        Returns:
            错误响应对象
        """
        status_code = error.response.status_code
        
        error_messages = {
            400: "请求参数错误",
            401: "Token认证失败，请检查token是否有效",
            403: "权限不足",
            404: "API接口不存在",
            429: "请求频率过高，请稍后重试",
            500: "服务器内部错误",
            502: "网关错误",
            503: "服务不可用",
            504: "网关超时"
        }
        
        message = error_messages.get(status_code, f"HTTP错误: {status_code}")
        
        logger.error(f"[{self.service_name}] HTTP错误: {status_code} - {message}")
        
        return APIResponse(
            code=status_code,
            message=message
        )
    
    def _handle_request_error(self, error: httpx.RequestError) -> APIResponse:
        """
        处理请求错误
        
        Args:
            error: 请求错误
            
        Returns:
            错误响应对象
        """
        if isinstance(error, httpx.TimeoutException):
            message = "请求超时，请稍后重试"
            code = 408
        elif isinstance(error, httpx.ConnectError):
            message = "无法连接到服务器，请检查网络连接"
            code = 503
        else:
            message = f"网络请求错误: {str(error)}"
            code = 500
        
        logger.error(f"[{self.service_name}] 请求错误: {message} - {error}")
        
        return APIResponse(
            code=code,
            message=message
        )
    
    async def _make_request_with_retry(
        self,
        method: HTTPMethod,
        url: str,
        **kwargs
    ) -> APIResponse:
        """
        带重试机制的HTTP请求
        
        Args:
            method: HTTP方法
            url: 请求URL
            **kwargs: 其他请求参数
            
        Returns:
            API响应对象
        """
        last_error = None
        
        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    # 发送请求
                    if method == HTTPMethod.GET:
                        response = await client.get(url, **kwargs)
                    elif method == HTTPMethod.POST:
                        response = await client.post(url, **kwargs)
                    elif method == HTTPMethod.PUT:
                        response = await client.put(url, **kwargs)
                    elif method == HTTPMethod.DELETE:
                        response = await client.delete(url, **kwargs)
                    elif method == HTTPMethod.PATCH:
                        response = await client.patch(url, **kwargs)
                    else:
                        raise ValueError(f"不支持的HTTP方法: {method}")
                    
                    # 检查HTTP状态码
                    response.raise_for_status()
                    
                    # 处理响应
                    result = await self._handle_response(response)
                    
                    if attempt > 0:
                        logger.info(f"[{self.service_name}] 重试成功 (第{attempt}次) - {method.value} {url}")
                    
                    return result
                    
            except httpx.HTTPStatusError as e:
                # HTTP状态错误通常不需要重试
                return self._handle_http_error(e)
                
            except httpx.RequestError as e:
                last_error = e
                
                if attempt < self.max_retries:
                    delay = self.retry_delay * (2 ** attempt)  # 指数退避
                    logger.warning(f"[{self.service_name}] 请求失败，{delay}秒后重试 (第{attempt + 1}次/共{self.max_retries}次) - {e}")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"[{self.service_name}] 请求失败，已达到最大重试次数 - {e}")
            
            except Exception as e:
                logger.error(f"[{self.service_name}] 未知错误 - {e}")
                return APIResponse(
                    code=500,
                    message=f"未知错误: {str(e)}"
                )
        
        # 所有重试都失败了
        if last_error:
            return self._handle_request_error(last_error)
        
        return APIResponse(
            code=500,
            message="请求失败，已达到最大重试次数"
        )
    
    async def request(
        self,
        method: Union[HTTPMethod, str],
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> APIResponse:
        """
        发送HTTP请求的统一入口
        
        Args:
            method: HTTP方法
            endpoint: API端点
            params: URL参数
            json_data: JSON请求体
            data: 表单数据
            headers: 自定义请求头
            **kwargs: 其他请求参数
            
        Returns:
            API响应对象
        """
        # 转换方法类型
        if isinstance(method, str):
            method = HTTPMethod(method.upper())
        
        # 构建URL
        url = self._build_url(endpoint)
        
        # 合并请求头
        merged_headers = self._merge_headers(headers)
        
        # 准备请求参数
        request_kwargs = {
            "headers": merged_headers,
            **kwargs
        }
        
        if params:
            request_kwargs["params"] = params
        if json_data:
            request_kwargs["json"] = json_data
        if data:
            request_kwargs["data"] = data
        
        # 记录请求日志
        logger.debug(f"[{self.service_name}] API请求: {method.value} {url}")
        
        # 发送请求
        return await self._make_request_with_retry(method, url, **request_kwargs)
    
    async def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> APIResponse:
        """GET请求的便捷方法"""
        return await self.request(HTTPMethod.GET, endpoint, params=params, **kwargs)
    
    async def post(
        self,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> APIResponse:
        """POST请求的便捷方法"""
        return await self.request(HTTPMethod.POST, endpoint, json_data=json_data, data=data, **kwargs)
    
    async def put(
        self,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> APIResponse:
        """PUT请求的便捷方法"""
        return await self.request(HTTPMethod.PUT, endpoint, json_data=json_data, **kwargs)
    
    async def delete(
        self,
        endpoint: str,
        **kwargs
    ) -> APIResponse:
        """DELETE请求的便捷方法"""
        return await self.request(HTTPMethod.DELETE, endpoint, **kwargs)
    
    # 抽象方法，子类需要实现
    @abstractmethod
    async def get_available_clusters(self) -> APIResponse:
        """获取可用集群列表 - 子类必须实现"""
        pass
    
    async def get_first_available_cluster(self) -> Optional[str]:
        """
        获取第一个可用的集群名称
        
        Returns:
            集群名称或None
        """
        try:
            response = await self.get_available_clusters()
            if response.success and response.data:
                clusters = response.data
                if isinstance(clusters, list) and clusters:
                    first_cluster = clusters[0]
                    if isinstance(first_cluster, dict):
                        return first_cluster.get("clusterName")
                    else:
                        return str(first_cluster)
            return None
        except Exception as e:
            logger.error(f"[{self.service_name}] 获取集群列表失败: {e}")
            return None
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(service_name='{self.service_name}', base_url='{self.base_url}')"
