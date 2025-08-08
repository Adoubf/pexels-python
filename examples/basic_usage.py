#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""基础使用示例。

演示 pexels-python 的基本功能：
- 同步客户端的基本使用
- 搜索照片和视频
- 获取精选内容
- 错误处理
"""
import os
from pexels_python import PexelsClient, PexelsApiError


def main():
    """主函数。"""
    # 从环境变量获取API密钥
    api_key = os.getenv("PEXELS_API_KEY")
    if not api_key:
        print("❌ 请设置环境变量 PEXELS_API_KEY")
        print("   export PEXELS_API_KEY='your_api_key_here'")
        return
    
    # 创建客户端
    client = PexelsClient(api_key=api_key)
    
    try:
        print("🔍 搜索照片...")
        # 搜索照片
        photos = client.search_photos("nature", per_page=5)
        print(f"   找到 {photos['total_results']} 张照片，显示前 {len(photos['photos'])} 张")
        
        for i, photo in enumerate(photos["photos"][:3], 1):
            print(f"   {i}. {photo['alt']} (ID: {photo['id']})")
            print(f"      摄影师: {photo['photographer']}")
            print(f"      尺寸: {photo['width']}x{photo['height']}")
            print()
        
        print("📸 获取精选照片...")
        # 获取精选照片
        curated = client.curated_photos(per_page=3)
        print(f"   获取到 {len(curated['photos'])} 张精选照片")
        
        print("🎥 搜索视频...")
        # 搜索视频
        videos = client.search_videos("ocean", per_page=3)
        print(f"   找到 {videos['total_results']} 个视频，显示前 {len(videos['videos'])} 个")
        
        for i, video in enumerate(videos["videos"], 1):
            print(f"   {i}. 时长: {video['duration']}秒 (ID: {video['id']})")
            print(f"      尺寸: {video['width']}x{video['height']}")
        
        print("\n📊 API限流信息:")
        if client.last_rate_limit:
            print(f"   剩余请求: {client.last_rate_limit.get('remaining', 'N/A')}")
            print(f"   限制总数: {client.last_rate_limit.get('limit', 'N/A')}")
            print(f"   重置时间: {client.last_rate_limit.get('reset', 'N/A')}")
        
    except PexelsApiError as e:
        print(f"❌ API错误: {e}")
        print(f"   状态码: {e.status_code}")
        if e.request_id:
            print(f"   请求ID: {e.request_id}")


if __name__ == "__main__":
    main()