# -*- coding: utf-8 -*-
"""pexels_python.core.client

Pexels API 客户端的核心实现。

特性：
- 支持照片和视频的搜索、精选/热门、单个获取
- 自动处理限流信息
- 丰富的错误处理和重试机制
- 可配置的请求超时和重试策略
- 详细的日志记录
"""
from __future__ import annotations

import time
from typing import Any, Dict, Mapping, Optional
from urllib.parse import urljoin

import requests

from ..utils.logging import get_logger, log_api_call
from .exceptions import build_api_error
from .retry import retry_on_failure, RetryConfig
from .pagination import PaginationIterator

class PexelsClient:
    """Pexels API 客户端。
    
    提供照片和视频的搜索、精选、获取等功能。
    
    Args:
        api_key: Pexels API 密钥
        base_url: API 基础 URL，默认为官方地址
        timeout: 请求超时时间（秒），默认 30 秒
        max_retries: 最大重试次数，默认 3 次
        retry_delay: 重试延迟（秒），默认 1 秒
    
    Example:
        >>> client = PexelsClient(api_key="YOUR_API_KEY")
        >>> photos = client.search_photos("cats", per_page=5)
        >>> print(len(photos["photos"]))
    """
    
    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://api.pexels.com/v1/",
        timeout: float = 30.0,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/") + "/"
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # 会话复用连接池
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": api_key,
            "User-Agent": "pexels-python/0.1.0",
        })
        
        # 配置连接池
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10,
            pool_maxsize=20,
            max_retries=0  # 我们自己处理重试
        )
        self._session.mount('https://', adapter)
        self._session.mount('http://', adapter)
        
        # 最近一次请求的限流信息
        self.last_rate_limit: Dict[str, Any] = {}
        
        # 重试配置
        self._retry_config = RetryConfig(
            max_retries=max_retries,
            base_delay=retry_delay,
        )
        
        # 日志器
        self._logger = get_logger(__name__)
    
    def __enter__(self) -> "PexelsClient":
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
    
    def close(self) -> None:
        """关闭会话，释放连接池资源。"""
        if hasattr(self, "_session"):
            self._session.close()
    
    @retry_on_failure()
    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """发起 HTTP 请求的核心方法。
        
        Args:
            method: HTTP 方法
            endpoint: API 端点
            params: 查询参数
            
        Returns:
            解析后的 JSON 响应
            
        Raises:
            PexelsHttpError: 各种 HTTP 错误
        """
        url = urljoin(self.base_url, endpoint)
        params = params or {}
        
        # 移除空值参数
        params = {k: v for k, v in params.items() if v is not None}
        
        start_time = time.time()
        
        try:
            response = self._session.request(
                method=method,
                url=url,
                params=params,
                timeout=self.timeout,
            )
            
            duration_ms = (time.time() - start_time) * 1000
            
            # 更新限流信息
            self._update_rate_limit_info(response.headers)
            
            # 记录请求日志
            log_api_call(self._logger, method, url, response.status_code, duration_ms)
            
            if response.ok:
                return response.json()
            
            # 构建错误信息
            error_message = self._extract_error_message(response)
            error = build_api_error(
                status_code=response.status_code,
                message=error_message,
                method=method,
                url=url,
                params=params,
                headers=dict(response.headers),
                response_body=response.text,
            )
            
            raise error
            
        except requests.exceptions.RequestException as e:
            raise build_api_error(
                status_code=0,
                message=f"网络请求失败: {e}",
                method=method,
                url=url,
                params=params,
                headers={},
                response_body=None,
            )
    
    def _extract_error_message(self, response: requests.Response) -> str:
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
    
    def search_photos(
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
        """搜索照片。
        
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
        return self._make_request("GET", "search", params)
    
    def curated_photos(
        self,
        *,
        page: int = 1,
        per_page: int = 15,
    ) -> Dict[str, Any]:
        """获取精选照片。
        
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
        return self._make_request("GET", "curated", params)
    
    def get_photo(self, photo_id: int) -> Dict[str, Any]:
        """根据 ID 获取单张照片。
        
        Args:
            photo_id: 照片 ID
            
        Returns:
            照片详情字典
        """
        return self._make_request("GET", f"photos/{photo_id}")
    
    # 视频相关方法
    
    def search_videos(
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
        """搜索视频。
        
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
        return self._make_request("GET", "videos/search", params)
    
    def popular_videos(
        self,
        *,
        min_width: Optional[int] = None,
        min_height: Optional[int] = None,
        min_duration: Optional[int] = None,
        max_duration: Optional[int] = None,
        page: int = 1,
        per_page: int = 15,
    ) -> Dict[str, Any]:
        """获取热门视频。
        
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
        return self._make_request("GET", "videos/popular", params)
    
    def get_video(self, video_id: int) -> Dict[str, Any]:
        """根据 ID 获取单个视频。
        
        Args:
            video_id: 视频 ID
            
        Returns:
            视频详情字典
        """
        return self._make_request("GET", f"videos/videos/{video_id}")
    
    # 分页迭代器方法
    
    def iter_search_photos(
        self,
        query: str,
        *,
        per_page: int = 15,
        max_pages: Optional[int] = None,
        **kwargs: Any,
    ) -> "PaginationIterator":
        """创建照片搜索的分页迭代器。
        
        Args:
            query: 搜索关键词
            per_page: 每页数量，默认 15
            max_pages: 最大页数，None 表示无限制
            **kwargs: 传递给 search_photos 的其他参数
            
        Returns:
            分页迭代器实例
            
        Example:
            >>> client = PexelsClient(api_key="YOUR_API_KEY")
            >>> for photo in client.iter_search_photos("cats", max_pages=3):
            ...     print(photo["id"])
        """
        
        return PaginationIterator(
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
    ) -> "PaginationIterator":
        """创建精选照片的分页迭代器。
        
        Args:
            per_page: 每页数量，默认 15
            max_pages: 最大页数，None 表示无限制
            **kwargs: 传递给 curated_photos 的其他参数
            
        Returns:
            分页迭代器实例
        """
        
        return PaginationIterator(
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
    ) -> "PaginationIterator":
        """创建视频搜索的分页迭代器。
        
        Args:
            query: 搜索关键词
            per_page: 每页数量，默认 15
            max_pages: 最大页数，None 表示无限制
            **kwargs: 传递给 search_videos 的其他参数
            
        Returns:
            分页迭代器实例
        """
        
        return PaginationIterator(
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
    ) -> "PaginationIterator":
        """创建热门视频的分页迭代器。
        
        Args:
            per_page: 每页数量，默认 15
            max_pages: 最大页数，None 表示无限制
            **kwargs: 传递给 popular_videos 的其他参数
            
        Returns:
            分页迭代器实例
        """
        
        return PaginationIterator(
            self,
            "popular_videos",
            per_page=per_page,
            max_pages=max_pages,
            **kwargs,
        )