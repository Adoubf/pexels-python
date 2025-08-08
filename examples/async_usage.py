#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""异步客户端使用示例。

演示 pexels-python 的异步功能：
- 异步客户端的基本使用
- 并发请求
- 异步错误处理
"""
import asyncio
import os
from pexels_python import AsyncPexelsClient, PexelsApiError


async def search_multiple_topics(client: AsyncPexelsClient, topics: list[str]):
    """并发搜索多个主题。"""
    print(f"🔍 并发搜索 {len(topics)} 个主题...")
    
    # 创建并发任务
    tasks = [
        client.search_photos(topic, per_page=3)
        for topic in topics
    ]
    
    # 等待所有任务完成
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # 处理结果
    for topic, result in zip(topics, results):
        if isinstance(result, Exception):
            print(f"   ❌ {topic}: {result}")
        else:
            print(f"   ✅ {topic}: {result['total_results']} 张照片")


async def main():
    """主函数。"""
    # 从环境变量获取API密钥
    api_key = os.getenv("PEXELS_API_KEY")

    if not api_key:
        print("❌ 请设置环境变量 PEXELS_API_KEY")
        print("   export PEXELS_API_KEY='your_api_key_here'")
        return
    
    # 创建异步客户端
    async with AsyncPexelsClient(api_key=api_key) as client:
        try:
            # 基本搜索
            print("📸 异步搜索照片...")
            photos = await client.search_photos("mountains", per_page=5)
            print(f"   找到 {photos['total_results']} 张照片")
            print(f"找到第一张图片：{photos['photos'][0]['alt']} by {photos['photos'][0]['photographer']}. image:{photos['photos'][0]['src']}")

            # 并发搜索多个主题
            topics = ["cats", "dogs", "birds", "flowers"]
            await search_multiple_topics(client, topics)
            
            # 获取精选内容
            print("\n🌟 获取精选内容...")
            curated_task = client.curated_photos(per_page=3)
            popular_task = client.popular_videos(per_page=3)
            
            curated, popular = await asyncio.gather(curated_task, popular_task)
            
            print(f"   精选照片: {len(curated['photos'])} 张")
            print(f"   热门视频: {len(popular['videos'])} 个")
            
            # 获取特定资源
            print("\n🎯 获取特定资源...")
            try:
                photo = await client.get_photo(2014422)
                print(f"   照片详情: {photo['alt']} by {photo['photographer']}")
            except PexelsApiError as e:
                print(f"   获取照片失败: {e}")
            
            print("\n📊 API限流信息:")
            if client.last_rate_limit:
                print(f"   剩余请求: {client.last_rate_limit.get('remaining', 'N/A')}")
                print(f"   限制总数: {client.last_rate_limit.get('limit', 'N/A')}")
        
        except PexelsApiError as e:
            print(f"❌ API错误: {e}")
            print(f"   状态码: {e.status_code}")


if __name__ == "__main__":
    asyncio.run(main())