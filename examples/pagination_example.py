#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""分页迭代器使用示例。

演示 pexels-python 的分页功能：
- 自动翻页迭代器
- 同步和异步分页
- 分页控制和限制
"""
import asyncio
import os
from pexels_python import (
    PexelsClient, 
    AsyncPexelsClient,
    iter_search_photos,
    iter_curated_photos,
    PaginationIterator,
    AsyncPaginationIterator
)


def sync_pagination_example():
    """同步分页示例。"""
    api_key = os.getenv("PEXELS_API_KEY")
    if not api_key:
        print("❌ 请设置环境变量 PEXELS_API_KEY")
        return
    
    client = PexelsClient(api_key=api_key)
    
    print("🔄 同步分页示例")
    print("=" * 50)
    
    # 使用便捷函数进行分页搜索
    print("1. 使用便捷函数搜索照片 (最多获取20张):")
    count = 0
    for photo in iter_search_photos(client, "sunset", per_page=5, max_items=20):
        count += 1
        print(f"   {count}. {photo['alt']} by {photo['photographer']}")
        if count >= 10:  # 只显示前10张
            break
    
    print(f"\n   实际获取了 {count} 张照片")
    
    # 使用分页迭代器类
    print("\n2. 使用分页迭代器类:")
    iterator = PaginationIterator(
        client=client,
        endpoint="search_photos",
        query="nature",
        per_page=3,
        max_pages=3
    )
    
    page_count = 0
    total_items = 0
    for page in iterator:
        page_count += 1
        items = page.get("photos", [])
        total_items += len(items)
        print(f"   第 {page_count} 页: {len(items)} 张照片")
        
        # 显示前几张照片的信息
        for i, photo in enumerate(items[:2], 1):
            print(f"     {i}. ID: {photo['id']}, 摄影师: {photo['photographer']}")
    
    print(f"\n   总计: {page_count} 页, {total_items} 张照片")
    
    # 精选照片分页
    print("\n3. 精选照片分页:")
    count = 0
    for photo in iter_curated_photos(client, per_page=5, max_items=15):
        count += 1
        print(f"   {count}. {photo['photographer']} - {photo['width']}x{photo['height']}")
        if count >= 8:
            break


async def async_pagination_example():
    """异步分页示例。"""
    api_key = os.getenv("PEXELS_API_KEY")
    if not api_key:
        print("❌ 请设置环境变量 PEXELS_API_KEY")
        return
    
    async with AsyncPexelsClient(api_key=api_key) as client:
        print("\n🚀 异步分页示例")
        print("=" * 50)
        
        # 异步分页迭代器
        print("1. 异步搜索视频:")
        iterator = AsyncPaginationIterator(
            client=client,
            endpoint="search_videos",
            query="ocean",
            per_page=3,
            max_pages=2
        )
        
        page_count = 0
        total_items = 0
        async for page in iterator:
            page_count += 1
            items = page.get("videos", [])
            total_items += len(items)
            print(f"   第 {page_count} 页: {len(items)} 个视频")
            
            for i, video in enumerate(items, 1):
                print(f"     {i}. 时长: {video['duration']}秒, 尺寸: {video['width']}x{video['height']}")
        
        print(f"\n   总计: {page_count} 页, {total_items} 个视频")
        
        # 并发分页搜索
        print("\n2. 并发分页搜索:")
        topics = ["cats", "dogs"]
        tasks = []
        
        for topic in topics:
            iterator = AsyncPaginationIterator(
                client=client,
                endpoint="search_photos",
                query=topic,
                per_page=5,
                max_pages=2
            )
            tasks.append(collect_pages(iterator, topic))
        
        results = await asyncio.gather(*tasks)
        for topic, count in results:
            print(f"   {topic}: {count} 张照片")


async def collect_pages(iterator: AsyncPaginationIterator, topic: str) -> tuple[str, int]:
    """收集分页数据。"""
    total_count = 0
    async for page in iterator:
        photos = page.get("photos", [])
        total_count += len(photos)
    return topic, total_count


def main():
    """主函数。"""
    # 同步分页示例
    sync_pagination_example()
    
    # 异步分页示例
    asyncio.run(async_pagination_example())


if __name__ == "__main__":
    main()