#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""重试和缓存功能示例。

演示 pexels-python 的高级功能：
- 重试策略配置
- 缓存机制使用
- 错误处理和恢复
"""
import asyncio
import os
import time
from pexels_python import (
    PexelsClient,
    AsyncPexelsClient, 
    RetryConfig,
    CacheManager,
    PexelsRateLimitError,
    set_debug
)


def retry_example():
    """重试功能示例。"""
    api_key = os.getenv("PEXELS_API_KEY")
    if not api_key:
        print("❌ 请设置环境变量 PEXELS_API_KEY")
        return
    
    print("🔄 重试功能示例")
    print("=" * 50)
    
    # 配置重试策略
    retry_config = RetryConfig(
        max_retries=3,
        base_delay=1.0,
        max_delay=10.0,
        exponential_base=2.0,
        jitter=True
    )
    
    # 创建带重试配置的客户端
    client = PexelsClient(
        api_key=api_key,
        retry_config=retry_config
    )
    
    print("1. 正常请求 (应该成功):")
    try:
        photos = client.search_photos("test", per_page=1)
        print(f"   ✅ 成功获取 {len(photos['photos'])} 张照片")
    except Exception as e:
        print(f"   ❌ 请求失败: {e}")
    
    print("\n2. 重试配置信息:")
    print(f"   最大重试次数: {retry_config.max_retries}")
    print(f"   基础延迟: {retry_config.base_delay}秒")
    print(f"   最大延迟: {retry_config.max_delay}秒")
    print(f"   指数退避基数: {retry_config.exponential_base}")
    print(f"   随机抖动: {retry_config.jitter}")


def cache_example():
    """缓存功能示例。"""
    api_key = os.getenv("PEXELS_API_KEY")
    if not api_key:
        print("❌ 请设置环境变量 PEXELS_API_KEY")
        return
    
    print("\n💾 缓存功能示例")
    print("=" * 50)
    
    # 创建内存缓存管理器
    cache_manager = CacheManager.create_memory_cache(
        max_size=100,
        ttl=300  # 5分钟TTL
    )
    
    # 创建带缓存的客户端
    client = PexelsClient(
        api_key=api_key,
        cache_manager=cache_manager
    )
    
    print("1. 第一次请求 (会缓存结果):")
    start_time = time.time()
    photos1 = client.search_photos("mountains", per_page=3)
    duration1 = time.time() - start_time
    print(f"   ✅ 获取 {len(photos1['photos'])} 张照片，耗时: {duration1:.2f}秒")
    
    print("\n2. 第二次相同请求 (从缓存获取):")
    start_time = time.time()
    photos2 = client.search_photos("mountains", per_page=3)
    duration2 = time.time() - start_time
    print(f"   ✅ 获取 {len(photos2['photos'])} 张照片，耗时: {duration2:.2f}秒")
    
    print(f"\n   缓存效果: 第二次请求快了 {duration1/duration2:.1f}x")
    
    # 验证结果一致性
    if photos1['photos'][0]['id'] == photos2['photos'][0]['id']:
        print("   ✅ 缓存数据一致性验证通过")
    else:
        print("   ❌ 缓存数据不一致")
    
    print("\n3. 缓存统计:")
    print(f"   缓存大小: {len(cache_manager._cache._data)} 项")


async def async_retry_cache_example():
    """异步重试和缓存示例。"""
    api_key = os.getenv("PEXELS_API_KEY")
    if not api_key:
        print("❌ 请设置环境变量 PEXELS_API_KEY")
        return
    
    print("\n🚀 异步重试和缓存示例")
    print("=" * 50)
    
    # 配置重试和缓存
    retry_config = RetryConfig(max_retries=2, base_delay=0.5)
    cache_manager = CacheManager.create_memory_cache(max_size=50, ttl=180)
    
    async with AsyncPexelsClient(
        api_key=api_key,
        retry_config=retry_config,
        cache_manager=cache_manager
    ) as client:
        
        print("1. 并发请求测试 (带缓存和重试):")
        topics = ["nature", "technology", "food"]
        
        # 第一轮请求
        print("   第一轮请求:")
        start_time = time.time()
        tasks1 = [client.search_photos(topic, per_page=2) for topic in topics]
        results1 = await asyncio.gather(*tasks1)
        duration1 = time.time() - start_time
        
        for topic, result in zip(topics, results1):
            print(f"     {topic}: {len(result['photos'])} 张照片")
        print(f"   总耗时: {duration1:.2f}秒")
        
        # 第二轮相同请求 (应该从缓存获取)
        print("\n   第二轮相同请求 (缓存):")
        start_time = time.time()
        tasks2 = [client.search_photos(topic, per_page=2) for topic in topics]
        results2 = await asyncio.gather(*tasks2)
        duration2 = time.time() - start_time
        
        for topic, result in zip(topics, results2):
            print(f"     {topic}: {len(result['photos'])} 张照片")
        print(f"   总耗时: {duration2:.2f}秒")
        print(f"   缓存加速: {duration1/duration2:.1f}x")


def logging_example():
    """日志功能示例。"""
    print("\n📝 日志功能示例")
    print("=" * 50)
    
    # 启用调试日志
    set_debug()
    print("1. 已启用调试日志，后续请求将显示详细信息")
    
    api_key = os.getenv("PEXELS_API_KEY")
    if not api_key:
        print("❌ 请设置环境变量 PEXELS_API_KEY")
        return
    
    client = PexelsClient(api_key=api_key)
    
    print("\n2. 执行一个请求 (观察日志输出):")
    try:
        photos = client.search_photos("debug_test", per_page=1)
        print(f"   ✅ 请求成功，获取 {len(photos['photos'])} 张照片")
    except Exception as e:
        print(f"   ❌ 请求失败: {e}")


def main():
    """主函数。"""
    # 重试示例
    retry_example()
    
    # 缓存示例
    cache_example()
    
    # 异步重试和缓存示例
    asyncio.run(async_retry_cache_example())
    
    # 日志示例
    logging_example()


if __name__ == "__main__":
    main()