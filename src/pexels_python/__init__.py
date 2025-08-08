# -*- coding: utf-8 -*-
"""pexels_python

一个轻量的 Pexels API Python 客户端，支持照片与视频的常用接口。

快速开始：
    >>> from pexels_python import PexelsClient
    >>> client = PexelsClient(api_key="YOUR_API_KEY")
    >>> data = client.search_photos("cats", per_page=3)
    >>> print([p["id"] for p in data["photos"]])

本包仅依赖 requests，适合在服务端或脚本中使用。
"""
from __future__ import annotations

__all__ = [
    # 客户端
    "PexelsClient",
    "AsyncPexelsClient",
    # 分页迭代器
    "PaginationIterator",
    "AsyncPaginationIterator",
    "iter_search_photos",
    "iter_curated_photos", 
    "iter_search_videos",
    "iter_popular_videos",
    # 异常
    "PexelsError",
    "PexelsApiError",
    "PexelsAuthError",
    "PexelsRateLimitError",
    "PexelsBadRequestError",
    "PexelsNotFoundError",
    "PexelsServerError",
    # 重试和缓存
    "RetryConfig",
    "retry_on_failure",
    "async_retry_on_failure",
    "CacheManager",
    "MemoryCache",
    "RedisCache",
    # 工具
    "set_debug",
    "set_info",
]

__version__ = "0.1.0"

from .core.client import PexelsClient  # noqa: E402
from .core.async_client import AsyncPexelsClient  # noqa: E402
from .core.pagination import (  # noqa: E402
    PaginationIterator,
    AsyncPaginationIterator,
    iter_search_photos,
    iter_curated_photos,
    iter_search_videos,
    iter_popular_videos,
)
from .core.exceptions import (  # noqa: E402
    PexelsApiError,
    PexelsAuthError,
    PexelsBadRequestError,
    PexelsError,
    PexelsNotFoundError,
    PexelsRateLimitError,
    PexelsServerError,
)
from .core.retry import (  # noqa: E402
    RetryConfig,
    async_retry_on_failure,
    retry_on_failure,
)
from .core.cache import (  # noqa: E402
    CacheManager,
    MemoryCache,
    RedisCache,
)
from .utils.logging import set_debug, set_info  # noqa: E402
