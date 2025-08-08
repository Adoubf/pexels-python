# -*- coding: utf-8 -*-
"""pexels_python.core.async_client

基于 httpx 的异步 Pexels API 客户端实现。

特性：
- 完全异步的 HTTP 请求
- 连接池复用和管理
- 自动重试和退避策略
- 与同步客户端相同的 API 接口
- 支持异步上下文管理器
"""
from __future__ import annotations


import time
from typing import Any, Dict, Mapping, Optional

try:
    import httpx
except ImportError:
    raise ImportError(
        "httpx 是异步客户端的必需依赖。请安装: pip install httpx"
    )

from ..utils.logging import get_logger, log_api_call
from .exceptions import build_api_error
from .retry import async_retry_on_failure, RetryConfig
from .pagination import AsyncPaginationIterator

logger = get_logger(__name__)


class AsyncPexelsClient:
    """异步 Pexels API 客户端。
    
    基于 httpx 实现的异步版本，提供与同步客户端相同的功能。
    
    Args:
        api_key: Pexels API 密钥
        base_url: API 基础 URL，默认为官方地址
        timeout: 请求超时时间（秒），默认 30 秒
        max_retries: 最大重试次数，默认 3 次
        retry_delay: 重试延迟（秒），默认 1 秒
        max_connections: 最大连接数，默认 20
        max_keepalive_connections: 最大保持连接数，默认 5
        
    Example:
        >>> async with AsyncPexelsClient(api_key="YOUR_API_KEY") as client:
        ...     photos = await client.search_photos("cats", per_page=5)
        ...     print(len(photos["photos"]))
    """
    
    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://api.pexels.com/v1/",
        timeout: float = 30.0,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        max_connections: int = 20,
        max_keepalive_connections: int = 5,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/") + "/"
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # 配置 httpx 客户端
        self._client_config = {
            "base_url": self.base_url,
            "timeout": httpx.Timeout(timeout),
            "limits": httpx.Limits(
                max_connections=max_connections,
                max_keepalive_connections=max_keepalive_connections,
            ),
            "headers": {
                "Authorization": api_key,
                "User-Agent": "pexels-python-async/0.1.0",
            },
        }
        
        self._client: Optional[httpx.AsyncClient] = None
        
        # 最近一次请求的限流信息
        self.last_rate_limit: Dict[str, Any] = {}
        
        # 重试配置
        self._retry_config = RetryConfig(
            max_retries=max_retries,
            base_delay=retry_delay,
        )
        
        # 日志器
        self._logger = get_logger(__name__)
    
    async def __aenter__(self) -> "AsyncPexelsClient":
        """异步上下文管理器入口。"""
        await self._ensure_client()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """异步上下文管理器出口。"""
        await self.close()
    
    async def _ensure_client(self) -> httpx.AsyncClient:
        """确保 httpx 客户端已初始化。"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(**self._client_config)
        return self._client
    
    async def close(self) -> None:
        """关闭客户端，释放连接池资源。"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
    
    @async_retry_on_failure()
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """发起异步 HTTP 请求的核心方法。
        
        Args:
            method: HTTP 方法
            endpoint: API 端点
            params: 查询参数
            
        Returns:
            解析后的 JSON 响应
            
        Raises:
            PexelsHttpError: 各种 HTTP 错误
        """
        client = await self._ensure_client()
        params = params or {}
        
        # 移除空值参数
        params = {k: v for k, v in params.items() if v is not None}
        
        start_time = time.time()
        
        try:
            response = await client.request(
                method=method,
                url=endpoint,
                params=params,
            )
            
            duration_ms = (time.time() - start_time) * 1000
            
            # 更新限流信息
            self._update_rate_limit_info(response.headers)
            
            # 记录请求日志
            log_api_call(self._logger, method, str(response.url), response.status_code, duration_ms)
            
            if response.is_success:
                return response.json()
            
            # 构建错误信息
            error_message = await self._extract_error_message(response)
            error = build_api_error(
                status_code=response.status_code,
                message=error_message,
                method=method,
                url=str(response.url),
                params=params,
                headers=dict(response.headers),
                response_body=response.text,
            )
            
            raise error
            
        except httpx.RequestError as e:
            raise build_api_error(
                status_code=0,
                message=f"网络请求失败: {e}",
                method=method,
                url=endpoint,
                params=params,
                headers={},
                response_body=None,
            )
    
    async def _extract_error_message(self, response: httpx.Response) -> str:
        """从响应中提取错误信息。"""
        try:
            data = response.json()
            if isinstance(data, dict):
                return data.get("error", f"HTTP {response.status_code}")
        except Exception:
            pass
        return f"HTTP {response.status_code}"
    
    def _update_rate_limit_info(self, headers: Mapping[str, str]) -> None:
        """更新限流信息。"""
        self.last_rate_limit = {
            "limit": headers.get("X-Ratelimit-Limit"),
            "remaining": headers.get("X-Ratelimit-Remaining"),
            "reset": headers.get("X-Ratelimit-Reset"),
        }
    
    # 照片相关方法
    
    async def search_photos(
        self,
        query: str,
        *,
        orientation: Optional[str] = None,
        size: Optional[str] = None,
        color: Optional[str] = None,
        locale: Optional[str] = None,
        page: int = 1,
        per_page: int = 15,
    ) -> Dict[str, Any]:
        """异步搜索照片。
        
        Args:
            query: 搜索关键词
            orientation: 方向 (landscape, portrait, square)
            size: 尺寸 (large, medium, small)
            color: 颜色 (red, orange, yellow, green, turquoise, blue, violet, pink, brown, black, gray, white)
            locale: 语言地区代码
            page: 页码，从 1 开始
            per_page: 每页数量，1-80
            
        Returns:
            搜索结果字典
        """
        params = {
            "query": query,
            "orientation": orientation,
            "size": size,
            "color": color,
            "locale": locale,
            "page": page,
            "per_page": per_page,
        }
        return await self._make_request("GET", "search", params)
    
    async def curated_photos(
        self,
        *,
        page: int = 1,
        per_page: int = 15,
    ) -> Dict[str, Any]:
        """异步获取精选照片。
        
        Args:
            page: 页码，从 1 开始
            per_page: 每页数量，1-80
            
        Returns:
            精选照片字典
        """
        params = {
            "page": page,
            "per_page": per_page,
        }
        return await self._make_request("GET", "curated", params)
    
    async def get_photo(self, photo_id: int) -> Dict[str, Any]:
        """异步根据 ID 获取单张照片。
        
        Args:
            photo_id: 照片 ID
            
        Returns:
            照片详情字典
        """
        return await self._make_request("GET", f"photos/{photo_id}")
    
    # 视频相关方法
    
    async def search_videos(
        self,
        query: str,
        *,
        orientation: Optional[str] = None,
        size: Optional[str] = None,
        locale: Optional[str] = None,
        page: int = 1,
        per_page: int = 15,
        min_width: Optional[int] = None,
        min_height: Optional[int] = None,
        max_width: Optional[int] = None,
        max_height: Optional[int] = None,
        min_duration: Optional[int] = None,
        max_duration: Optional[int] = None,
    ) -> Dict[str, Any]:
        """异步搜索视频。
        
        Args:
            query: 搜索关键词
            orientation: 方向 (landscape, portrait, square)
            size: 尺寸 (large, medium, small)
            locale: 语言地区代码
            page: 页码，从 1 开始
            per_page: 每页数量，1-80
            min_width: 最小宽度
            min_height: 最小高度
            max_width: 最大宽度
            max_height: 最大高度
            min_duration: 最小时长（秒）
            max_duration: 最大时长（秒）
            
        Returns:
            搜索结果字典
        """
        params = {
            "query": query,
            "orientation": orientation,
            "size": size,
            "locale": locale,
            "page": page,
            "per_page": per_page,
            "min_width": min_width,
            "min_height": min_height,
            "max_width": max_width,
            "max_height": max_height,
            "min_duration": min_duration,
            "max_duration": max_duration,
        }
        return await self._make_request("GET", "videos/search", params)
    
    async def popular_videos(
        self,
        *,
        min_width: Optional[int] = None,
        min_height: Optional[int] = None,
        min_duration: Optional[int] = None,
        max_duration: Optional[int] = None,
        page: int = 1,
        per_page: int = 15,
    ) -> Dict[str, Any]:
        """异步获取热门视频。
        
        Args:
            min_width: 最小宽度
            min_height: 最小高度
            min_duration: 最小时长（秒）
            max_duration: 最大时长（秒）
            page: 页码，从 1 开始
            per_page: 每页数量，1-80
            
        Returns:
            热门视频字典
        """
        params = {
            "min_width": min_width,
            "min_height": min_height,
            "min_duration": min_duration,
            "max_duration": max_duration,
            "page": page,
            "per_page": per_page,
        }
        return await self._make_request("GET", "videos/popular", params)
    
    async def get_video(self, video_id: int) -> Dict[str, Any]:
        """异步根据 ID 获取单个视频。
        
        Args:
            video_id: 视频 ID
            
        Returns:
            视频详情字典
        """
        return await self._make_request("GET", f"videos/videos/{video_id}")
    
    # 分页迭代器方法
    
    def iter_search_photos(
        self,
        query: str,
        *,
        per_page: int = 15,
        max_pages: Optional[int] = None,
        **kwargs: Any,
    ) -> "AsyncPaginationIterator":
        """创建照片搜索的异步分页迭代器。"""
        
        return AsyncPaginationIterator(
            self,
            "search_photos",
            query=query,
            per_page=per_page,
            max_pages=max_pages,
            **kwargs,
        )
    
    def iter_curated_photos(
        self,
        *,
        per_page: int = 15,
        max_pages: Optional[int] = None,
        **kwargs: Any,
    ) -> "AsyncPaginationIterator":
        """创建精选照片的异步分页迭代器。"""
        
        return AsyncPaginationIterator(
            self,
            "curated_photos",
            per_page=per_page,
            max_pages=max_pages,
            **kwargs,
        )
    
    def iter_search_videos(
        self,
        query: str,
        *,
        per_page: int = 15,
        max_pages: Optional[int] = None,
        **kwargs: Any,
    ) -> "AsyncPaginationIterator":
        """创建视频搜索的异步分页迭代器。"""
        
        return AsyncPaginationIterator(
            self,
            "search_videos",
            query=query,
            per_page=per_page,
            max_pages=max_pages,
            **kwargs,
        )
    
    def iter_popular_videos(
        self,
        *,
        per_page: int = 15,
        max_pages: Optional[int] = None,
        **kwargs: Any,
    ) -> "AsyncPaginationIterator":
        """创建热门视频的异步分页迭代器。"""
        
        return AsyncPaginationIterator(
            self,
            "popular_videos",
            per_page=per_page,
            max_pages=max_pages,
            **kwargs,
        )