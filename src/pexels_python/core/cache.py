# -*- coding: utf-8 -*-
"""pexels_python.core.cache

缓存机制实现，支持内存缓存和可选的 Redis 缓存。

特性：
- 内存 LRU 缓存（默认）
- 可选的 Redis 分布式缓存
- 自动过期和清理
- 缓存键生成和管理
- 支持同步和异步操作
"""
from __future__ import annotations

import hashlib
import json
import time
from abc import ABC, abstractmethod
from functools import wraps
from typing import Any, Dict, Optional

from ..utils.logging import get_logger

logger = get_logger(__name__)


class CacheBackend(ABC):
    """缓存后端抽象基类。"""
    
    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值。"""
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """设置缓存值。"""
        pass
    
    @abstractmethod
    def delete(self, key: str) -> None:
        """删除缓存值。"""
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """清空所有缓存。"""
        pass


class MemoryCache(CacheBackend):
    """内存缓存实现。
    
    使用字典存储缓存数据，支持 TTL 过期。
    
    Args:
        max_size: 最大缓存条目数，默认 1000
        default_ttl: 默认 TTL（秒），默认 300（5分钟）
    """
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 300) -> None:
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._access_order: list[str] = []
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值。"""
        if key not in self._cache:
            return None
        
        entry = self._cache[key]
        
        # 检查是否过期
        if entry["expires_at"] and time.time() > entry["expires_at"]:
            self.delete(key)
            return None
        
        # 更新访问顺序（LRU）
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)
        
        logger.debug(f"缓存命中: {key}")
        return entry["value"]
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """设置缓存值。"""
        ttl = ttl or self.default_ttl
        expires_at = time.time() + ttl if ttl > 0 else None
        
        # 如果缓存已满，删除最久未使用的条目
        if len(self._cache) >= self.max_size and key not in self._cache:
            self._evict_lru()
        
        self._cache[key] = {
            "value": value,
            "created_at": time.time(),
            "expires_at": expires_at,
        }
        
        # 更新访问顺序
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)
        
        logger.debug(f"缓存设置: {key}, TTL: {ttl}s")
    
    def delete(self, key: str) -> None:
        """删除缓存值。"""
        if key in self._cache:
            del self._cache[key]
        if key in self._access_order:
            self._access_order.remove(key)
        logger.debug(f"缓存删除: {key}")
    
    def clear(self) -> None:
        """清空所有缓存。"""
        self._cache.clear()
        self._access_order.clear()
        logger.debug("缓存已清空")
    
    def _evict_lru(self) -> None:
        """删除最久未使用的缓存条目。"""
        if self._access_order:
            lru_key = self._access_order[0]
            self.delete(lru_key)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息。"""
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "default_ttl": self.default_ttl,
        }


class RedisCache(CacheBackend):
    """Redis 缓存实现。
    
    需要安装 redis 包：pip install redis
    
    Args:
        redis_url: Redis 连接 URL，默认 redis://localhost:6379/0
        key_prefix: 缓存键前缀，默认 pexels_python
        default_ttl: 默认 TTL（秒），默认 300（5分钟）
    """
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        key_prefix: str = "pexels_python",
        default_ttl: int = 300,
    ) -> None:
        try:
            import redis
        except ImportError:
            raise ImportError("Redis 缓存需要安装 redis 包: pip install redis")
        
        self.redis = redis.from_url(redis_url)
        self.key_prefix = key_prefix
        self.default_ttl = default_ttl
        
        # 测试连接
        try:
            self.redis.ping()
            logger.info(f"Redis 缓存已连接: {redis_url}")
        except Exception as e:
            logger.error(f"Redis 连接失败: {e}")
            raise
    
    def _make_key(self, key: str) -> str:
        """生成带前缀的缓存键。"""
        return f"{self.key_prefix}:{key}"
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值。"""
        try:
            redis_key = self._make_key(key)
            data = self.redis.get(redis_key)
            if data is None:
                return None
            
            value = json.loads(data.decode('utf-8'))
            logger.debug(f"Redis 缓存命中: {key}")
            return value
        except Exception as e:
            logger.warning(f"Redis 获取缓存失败: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """设置缓存值。"""
        try:
            redis_key = self._make_key(key)
            data = json.dumps(value, ensure_ascii=False)
            ttl = ttl or self.default_ttl
            
            if ttl > 0:
                self.redis.setex(redis_key, ttl, data)
            else:
                self.redis.set(redis_key, data)
            
            logger.debug(f"Redis 缓存设置: {key}, TTL: {ttl}s")
        except Exception as e:
            logger.warning(f"Redis 设置缓存失败: {e}")
    
    def delete(self, key: str) -> None:
        """删除缓存值。"""
        try:
            redis_key = self._make_key(key)
            self.redis.delete(redis_key)
            logger.debug(f"Redis 缓存删除: {key}")
        except Exception as e:
            logger.warning(f"Redis 删除缓存失败: {e}")
    
    def clear(self) -> None:
        """清空所有缓存。"""
        try:
            pattern = f"{self.key_prefix}:*"
            keys = self.redis.keys(pattern)
            if keys:
                self.redis.delete(*keys)
            logger.debug("Redis 缓存已清空")
        except Exception as e:
            logger.warning(f"Redis 清空缓存失败: {e}")


class CacheManager:
    """缓存管理器。
    
    统一管理缓存操作，支持多种缓存后端。
    
    Args:
        backend: 缓存后端实例
        enabled: 是否启用缓存，默认 True
    """
    
    def __init__(self, backend: CacheBackend, enabled: bool = True) -> None:
        self.backend = backend
        self.enabled = enabled
        self._stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
        }
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值。"""
        if not self.enabled:
            return None
        
        value = self.backend.get(key)
        if value is not None:
            self._stats["hits"] += 1
        else:
            self._stats["misses"] += 1
        
        return value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """设置缓存值。"""
        if not self.enabled:
            return
        
        self.backend.set(key, value, ttl)
        self._stats["sets"] += 1
    
    def delete(self, key: str) -> None:
        """删除缓存值。"""
        if not self.enabled:
            return
        
        self.backend.delete(key)
        self._stats["deletes"] += 1
    
    def clear(self) -> None:
        """清空所有缓存。"""
        if not self.enabled:
            return
        
        self.backend.clear()
    
    def enable(self) -> None:
        """启用缓存。"""
        self.enabled = True
        logger.info("缓存已启用")
    
    def disable(self) -> None:
        """禁用缓存。"""
        self.enabled = False
        logger.info("缓存已禁用")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息。"""
        total_requests = self._stats["hits"] + self._stats["misses"]
        hit_rate = self._stats["hits"] / total_requests if total_requests > 0 else 0
        
        stats = {
            **self._stats,
            "total_requests": total_requests,
            "hit_rate": hit_rate,
            "enabled": self.enabled,
        }
        
        # 添加后端统计信息
        if hasattr(self.backend, "get_stats"):
            stats["backend"] = self.backend.get_stats()
        
        return stats


def generate_cache_key(method: str, endpoint: str, params: Dict[str, Any]) -> str:
    """生成缓存键。
    
    Args:
        method: HTTP 方法
        endpoint: API 端点
        params: 请求参数
        
    Returns:
        缓存键字符串
    """
    # 排序参数以确保一致性
    sorted_params = sorted(params.items()) if params else []
    
    # 创建缓存键数据
    cache_data = {
        "method": method,
        "endpoint": endpoint,
        "params": sorted_params,
    }
    
    # 生成 MD5 哈希
    cache_str = json.dumps(cache_data, sort_keys=True, ensure_ascii=False)
    cache_hash = hashlib.md5(cache_str.encode('utf-8')).hexdigest()
    
    return f"{method}:{endpoint}:{cache_hash}"


def cached_request(
    cache_manager: CacheManager,
    ttl: Optional[int] = None,
    cache_key_func: Optional[callable] = None,
):
    """缓存请求装饰器。
    
    Args:
        cache_manager: 缓存管理器实例
        ttl: 缓存 TTL（秒），None 使用默认值
        cache_key_func: 自定义缓存键生成函数
        
    Example:
        @cached_request(cache_manager, ttl=600)
        def api_method(self, endpoint, params):
            return self._make_request("GET", endpoint, params)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 只缓存 GET 请求
            if len(args) >= 2 and args[1].upper() != "GET":
                return func(*args, **kwargs)
            
            # 生成缓存键
            if cache_key_func:
                cache_key = cache_key_func(*args, **kwargs)
            else:
                # 默认缓存键生成
                method = args[1] if len(args) >= 2 else "GET"
                endpoint = args[2] if len(args) >= 3 else ""
                params = args[3] if len(args) >= 4 else kwargs.get("params", {})
                cache_key = generate_cache_key(method, endpoint, params or {})
            
            # 尝试从缓存获取
            cached_value = cache_manager.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # 执行原函数
            result = func(*args, **kwargs)
            
            # 缓存结果
            cache_manager.set(cache_key, result, ttl)
            
            return result
        
        return wrapper
    return decorator


# 默认缓存管理器
_default_cache_manager: Optional[CacheManager] = None


def get_default_cache_manager() -> CacheManager:
    """获取默认缓存管理器。"""
    global _default_cache_manager
    if _default_cache_manager is None:
        backend = MemoryCache()
        _default_cache_manager = CacheManager(backend)
    return _default_cache_manager


def set_default_cache_manager(cache_manager: CacheManager) -> None:
    """设置默认缓存管理器。"""
    global _default_cache_manager
    _default_cache_manager = cache_manager