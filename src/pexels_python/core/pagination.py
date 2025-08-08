# -*- coding: utf-8 -*-
"""pexels_python.core.pagination

分页迭代器实现，支持自动翻页和数据生成。

特性：
- 自动处理分页逻辑
- 支持照片和视频的分页迭代
- 内置重试和错误处理
- 可配置的批次大小和最大页数
"""
from __future__ import annotations

from typing import Any, Dict, Generator, Iterator, Optional, TYPE_CHECKING

from ..utils.logging import get_logger

if TYPE_CHECKING:
    from .client import PexelsClient
    from .async_client import AsyncPexelsClient

logger = get_logger(__name__)


class PaginationIterator:
    """分页迭代器基类。
    
    自动处理 Pexels API 的分页逻辑，支持照片和视频的迭代。
    
    Args:
        client: Pexels 客户端实例
        method_name: 要调用的客户端方法名
        per_page: 每页数量，默认 15
        max_pages: 最大页数，None 表示无限制
        start_page: 起始页码，默认 1
        **kwargs: 传递给 API 方法的其他参数
    
    Example:
        >>> client = PexelsClient(api_key="YOUR_API_KEY")
        >>> iterator = PaginationIterator(client, "search_photos", query="cats")
        >>> for photo in iterator:
        ...     print(photo["id"])
    """
    
    def __init__(
        self,
        client: "PexelsClient",
        method_name: str,
        *,
        per_page: int = 15,
        max_pages: Optional[int] = None,
        start_page: int = 1,
        **kwargs: Any,
    ) -> None:
        self.client = client
        self.method_name = method_name
        self.per_page = per_page
        self.max_pages = max_pages
        self.start_page = start_page
        self.kwargs = kwargs
        
        # 状态跟踪
        self.current_page = start_page
        self.total_results: Optional[int] = None
        self.pages_fetched = 0
        self.items_yielded = 0
        
        # 获取客户端方法
        self.method = getattr(client, method_name)
        if not callable(self.method):
            raise ValueError(f"方法 {method_name} 不存在或不可调用")
    
    def __iter__(self) -> Iterator[Dict[str, Any]]:
        """返回迭代器自身。"""
        return self
    
    def __next__(self) -> Dict[str, Any]:
        """获取下一个项目。"""
        try:
            return next(self._item_generator())
        except StopIteration:
            raise
    
    def _item_generator(self) -> Generator[Dict[str, Any], None, None]:
        """内部项目生成器。"""
        while True:
            # 检查是否达到最大页数限制
            if self.max_pages and self.pages_fetched >= self.max_pages:
                logger.debug(f"达到最大页数限制: {self.max_pages}")
                break
            
            try:
                # 获取当前页数据
                response = self._fetch_page(self.current_page)
                self.pages_fetched += 1
                
                # 更新总结果数（如果可用）
                if "total_results" in response and self.total_results is None:
                    self.total_results = response["total_results"]
                
                # 确定数据键名（photos 或 videos）
                data_key = self._get_data_key(response)
                items = response.get(data_key, [])
                
                if not items:
                    logger.debug(f"第 {self.current_page} 页没有数据")
                    break
                
                # 生成当前页的所有项目
                for item in items:
                    yield item
                    self.items_yielded += 1
                
                # 检查是否有下一页
                if not self._has_next_page(response):
                    logger.debug("没有更多页面")
                    break
                
                self.current_page += 1
                
            except Exception as e:
                logger.error(f"获取第 {self.current_page} 页时出错: {e}")
                raise
    
    def _fetch_page(self, page: int) -> Dict[str, Any]:
        """获取指定页的数据。"""
        params = {
            **self.kwargs,
            "page": page,
            "per_page": self.per_page,
        }
        
        logger.debug(f"获取第 {page} 页数据，参数: {params}")
        
        return self.method(**params)
    
    def _get_data_key(self, response: Dict[str, Any]) -> str:
        """确定响应中的数据键名。"""
        if "photos" in response:
            return "photos"
        elif "videos" in response:
            return "videos"
        else:
            raise ValueError(f"响应中未找到 photos 或 videos 键: {list(response.keys())}")
    
    def _has_next_page(self, response: Dict[str, Any]) -> bool:
        """检查是否有下一页。"""
        # 方法1: 检查 next_page 字段
        if "next_page" in response and response["next_page"]:
            return True
        
        # 方法2: 检查当前页项目数量
        data_key = self._get_data_key(response)
        items = response.get(data_key, [])
        if len(items) < self.per_page:
            return False
        
        # 方法3: 检查总结果数（如果可用）
        if self.total_results is not None:
            expected_total_pages = (self.total_results + self.per_page - 1) // self.per_page
            return self.current_page < expected_total_pages
        
        # 默认假设有下一页（会在下次请求时验证）
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """获取迭代统计信息。"""
        return {
            "current_page": self.current_page,
            "pages_fetched": self.pages_fetched,
            "items_yielded": self.items_yielded,
            "total_results": self.total_results,
            "per_page": self.per_page,
            "max_pages": self.max_pages,
        }


class AsyncPaginationIterator:
    """异步分页迭代器。
    
    异步版本的分页迭代器，用于 AsyncPexelsClient。
    """
    
    def __init__(
        self,
        client: "AsyncPexelsClient",
        method_name: str,
        *,
        per_page: int = 15,
        max_pages: Optional[int] = None,
        start_page: int = 1,
        **kwargs: Any,
    ) -> None:
        self.client = client
        self.method_name = method_name
        self.per_page = per_page
        self.max_pages = max_pages
        self.start_page = start_page
        self.kwargs = kwargs
        
        # 状态跟踪
        self.current_page = start_page
        self.total_results: Optional[int] = None
        self.pages_fetched = 0
        self.items_yielded = 0
        
        # 获取客户端方法
        self.method = getattr(client, method_name)
        if not callable(self.method):
            raise ValueError(f"方法 {method_name} 不存在或不可调用")
    
    def __aiter__(self):
        """返回异步迭代器自身。"""
        return self
    
    async def __anext__(self) -> Dict[str, Any]:
        """获取下一个项目（异步）。"""
        if not hasattr(self, '_generator'):
            self._generator = self._item_generator()
        
        try:
            return await self._generator.__anext__()
        except StopAsyncIteration:
            raise
    
    async def _item_generator(self):
        """内部异步项目生成器。"""
        while True:
            # 检查是否达到最大页数限制
            if self.max_pages and self.pages_fetched >= self.max_pages:
                logger.debug(f"达到最大页数限制: {self.max_pages}")
                break
            
            try:
                # 获取当前页数据
                response = await self._fetch_page(self.current_page)
                self.pages_fetched += 1
                
                # 更新总结果数（如果可用）
                if "total_results" in response and self.total_results is None:
                    self.total_results = response["total_results"]
                
                # 确定数据键名（photos 或 videos）
                data_key = self._get_data_key(response)
                items = response.get(data_key, [])
                
                if not items:
                    logger.debug(f"第 {self.current_page} 页没有数据")
                    break
                
                # 生成当前页的所有项目
                for item in items:
                    yield item
                    self.items_yielded += 1
                
                # 检查是否有下一页
                if not self._has_next_page(response):
                    logger.debug("没有更多页面")
                    break
                
                self.current_page += 1
                
            except Exception as e:
                logger.error(f"获取第 {self.current_page} 页时出错: {e}")
                raise
    
    async def _fetch_page(self, page: int) -> Dict[str, Any]:
        """获取指定页的数据（异步）。"""
        params = {
            **self.kwargs,
            "page": page,
            "per_page": self.per_page,
        }
        
        logger.debug(f"获取第 {page} 页数据，参数: {params}")
        
        return await self.method(**params)
    
    def _get_data_key(self, response: Dict[str, Any]) -> str:
        """确定响应中的数据键名。"""
        if "photos" in response:
            return "photos"
        elif "videos" in response:
            return "videos"
        else:
            raise ValueError(f"响应中未找到 photos 或 videos 键: {list(response.keys())}")
    
    def _has_next_page(self, response: Dict[str, Any]) -> bool:
        """检查是否有下一页。"""
        # 方法1: 检查 next_page 字段
        if "next_page" in response and response["next_page"]:
            return True
        
        # 方法2: 检查当前页项目数量
        data_key = self._get_data_key(response)
        items = response.get(data_key, [])
        if len(items) < self.per_page:
            return False
        
        # 方法3: 检查总结果数（如果可用）
        if self.total_results is not None:
            expected_total_pages = (self.total_results + self.per_page - 1) // self.per_page
            return self.current_page < expected_total_pages
        
        # 默认假设有下一页（会在下次请求时验证）
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """获取迭代统计信息。"""
        return {
            "current_page": self.current_page,
            "pages_fetched": self.pages_fetched,
            "items_yielded": self.items_yielded,
            "total_results": self.total_results,
            "per_page": self.per_page,
            "max_pages": self.max_pages,
        }


# 便捷函数
def iter_search_photos(
    client: "PexelsClient",
    query: str,
    *,
    per_page: int = 15,
    max_pages: Optional[int] = None,
    **kwargs: Any,
) -> PaginationIterator:
    """创建照片搜索的分页迭代器。"""
    return PaginationIterator(
        client,
        "search_photos",
        query=query,
        per_page=per_page,
        max_pages=max_pages,
        **kwargs,
    )


def iter_curated_photos(
    client: "PexelsClient",
    *,
    per_page: int = 15,
    max_pages: Optional[int] = None,
    **kwargs: Any,
) -> PaginationIterator:
    """创建精选照片的分页迭代器。"""
    return PaginationIterator(
        client,
        "curated_photos",
        per_page=per_page,
        max_pages=max_pages,
        **kwargs,
    )


def iter_search_videos(
    client: "PexelsClient",
    query: str,
    *,
    per_page: int = 15,
    max_pages: Optional[int] = None,
    **kwargs: Any,
) -> PaginationIterator:
    """创建视频搜索的分页迭代器。"""
    return PaginationIterator(
        client,
        "search_videos",
        query=query,
        per_page=per_page,
        max_pages=max_pages,
        **kwargs,
    )


def iter_popular_videos(
    client: "PexelsClient",
    *,
    per_page: int = 15,
    max_pages: Optional[int] = None,
    **kwargs: Any,
) -> PaginationIterator:
    """创建热门视频的分页迭代器。"""
    return PaginationIterator(
        client,
        "popular_videos",
        per_page=per_page,
        max_pages=max_pages,
        **kwargs,
    )