# -*- coding: utf-8 -*-
"""测试缓存功能。"""
import time
from unittest.mock import Mock, patch

import pytest

from pexels_python.core.cache import CacheManager, MemoryCache, RedisCache


class TestMemoryCache:
    """测试内存缓存。"""

    def test_basic_operations(self):
        """测试基本的缓存操作。"""
        cache = MemoryCache(max_size=100)
        
        # 测试设置和获取
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        
        # 测试不存在的键
        assert cache.get("nonexistent") is None
        
        # 测试删除
        cache.delete("key1")
        assert cache.get("key1") is None

    def test_ttl_expiration(self):
        """测试TTL过期。"""
        cache = MemoryCache(max_size=100)
        
        cache.set("key1", "value1", ttl=0.1)  # 100ms TTL
        assert cache.get("key1") == "value1"
        
        # 等待过期
        time.sleep(0.2)
        assert cache.get("key1") is None

    def test_max_size_limit(self):
        """测试最大容量限制。"""
        cache = MemoryCache(max_size=2)
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")  # 应该触发LRU淘汰
        
        # key1应该被淘汰
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"

    def test_clear(self):
        """测试清空缓存。"""
        cache = MemoryCache(max_size=100)
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        cache.clear()
        
        assert cache.get("key1") is None
        assert cache.get("key2") is None


class TestRedisCache:
    """测试Redis缓存。"""

    @patch('pexels_python.core.cache.redis.Redis')
    def test_basic_operations(self, mock_redis_class):
        """测试基本的缓存操作。"""
        mock_redis = Mock()
        mock_redis_class.return_value = mock_redis
        
        cache = RedisCache(host="localhost", port=6379, db=0, ttl=60)
        
        # 测试设置
        cache.set("key1", "value1")
        mock_redis.setex.assert_called_once_with("key1", 60, '"value1"')
        
        # 测试获取
        mock_redis.get.return_value = b'"value1"'
        result = cache.get("key1")
        assert result == "value1"
        mock_redis.get.assert_called_once_with("key1")
        
        # 测试删除
        cache.delete("key1")
        mock_redis.delete.assert_called_once_with("key1")

    @patch('pexels_python.core.cache.redis.Redis')
    def test_get_nonexistent(self, mock_redis_class):
        """测试获取不存在的键。"""
        mock_redis = Mock()
        mock_redis_class.return_value = mock_redis
        mock_redis.get.return_value = None
        
        cache = RedisCache(host="localhost", port=6379, db=0, ttl=60)
        
        result = cache.get("nonexistent")
        assert result is None

    @patch('pexels_python.core.cache.redis.Redis')
    def test_connection_error_fallback(self, mock_redis_class):
        """测试连接错误时的降级处理。"""
        mock_redis = Mock()
        mock_redis_class.return_value = mock_redis
        mock_redis.get.side_effect = Exception("Connection failed")
        
        cache = RedisCache(host="localhost", port=6379, db=0, ttl=60)
        
        # 连接失败时应该返回None而不是抛出异常
        result = cache.get("key1")
        assert result is None


class TestCacheManager:
    """测试缓存管理器。"""

    def test_memory_cache_manager(self):
        """测试内存缓存管理器。"""
        manager = CacheManager(MemoryCache(max_size=100))
        
        manager.set("key1", {"data": "value1"})
        result = manager.get("key1")
        assert result == {"data": "value1"}

    @patch('pexels_python.core.cache.redis.Redis')
    def test_redis_cache_manager(self, mock_redis_class):
        """测试Redis缓存管理器。"""
        mock_redis = Mock()
        mock_redis_class.return_value = mock_redis
        
        manager = CacheManager(RedisCache(
            redis_url="redis://localhost:6379/0", default_ttl=60
        ))
        
        manager.set("key1", {"data": "value1"})
        mock_redis.setex.assert_called_once()

    def test_cache_key_generation(self):
        """测试缓存键生成。"""
        from pexels_python.core.cache import generate_cache_key
        manager = CacheManager(MemoryCache(max_size=100))
        
        # 测试不同参数生成不同的键
        key1 = generate_cache_key("GET", "search_photos", {"query": "cats", "per_page": 10})
        key2 = generate_cache_key("GET", "search_photos", {"query": "dogs", "per_page": 10})
        key3 = generate_cache_key("GET", "search_photos", {"query": "cats", "per_page": 20})
        
        assert key1 != key2
        assert key1 != key3
        assert key2 != key3
        
        # 测试相同参数生成相同的键
        key4 = generate_cache_key("GET", "search_photos", {"query": "cats", "per_page": 10})
        assert key1 == key4