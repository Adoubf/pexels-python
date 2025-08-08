# pexels-python

一个功能完整、高性能的 Pexels API Python 客户端库。

## ✨ 特性

- 🔄 **自动重试机制**：对 429 限流错误自动重试，支持指数退避策略
- 🚀 **异步支持**：基于 httpx 的异步客户端，支持并发请求
- 📄 **分页迭代器**：自动翻页生成器，轻松处理大量数据
- 💾 **智能缓存**：支持内存和 Redis 缓存，提升性能
- 🛡️ **丰富异常**：详细的异常类型和错误上下文信息
- 📝 **美化日志**：集成 Rich 的彩色日志输出
- 🎯 **类型注解**：完整的类型提示支持
- 🧪 **完善测试**：高覆盖率的测试套件

## 📦 安装

使用 Poetry 管理：

```bash
poetry add pexels-python
```

或本地开发：

```bash
poetry install
```

## 🚀 快速开始

### 基础使用

```python
from pexels_python import PexelsClient

client = PexelsClient(api_key="YOUR_PEXELS_API_KEY")

# 搜索照片
photos = client.search_photos("cats", per_page=5)
print(f"找到 {photos['total_results']} 张照片")

# 精选照片
curated = client.curated_photos(per_page=5)
print(f"获取 {len(curated['photos'])} 张精选照片")

# 搜索视频
videos = client.search_videos("nature", per_page=5)
print(f"找到 {len(videos['videos'])} 个视频")
```

### 异步使用

```python
import asyncio
from pexels_python import AsyncPexelsClient

async def main():
    async with AsyncPexelsClient(api_key="YOUR_API_KEY") as client:
        # 并发搜索
        photos_task = client.search_photos("mountains", per_page=5)
        videos_task = client.search_videos("ocean", per_page=5)
        
        photos, videos = await asyncio.gather(photos_task, videos_task)
        print(f"照片: {len(photos['photos'])}, 视频: {len(videos['videos'])}")

asyncio.run(main())
```

### 分页迭代

```python
from pexels_python import iter_search_photos

# 自动翻页获取所有结果
for photo in iter_search_photos(client, "sunset", per_page=10, max_items=100):
    print(f"照片 ID: {photo['id']}, 摄影师: {photo['photographer']}")
```

### 重试和缓存

```python
from pexels_python import PexelsClient, RetryConfig, CacheManager

# 配置重试策略
retry_config = RetryConfig(
    max_retries=3,
    base_delay=1.0,
    exponential_base=2.0
)

# 配置缓存
cache_manager = CacheManager.create_memory_cache(
    max_size=100,
    ttl=300  # 5分钟
)

client = PexelsClient(
    api_key="YOUR_API_KEY",
    retry_config=retry_config,
    cache_manager=cache_manager
)
```

## 🛡️ 错误处理

本库提供了丰富的异常类型：

```python
from pexels_python import (
    PexelsClient, 
    PexelsAuthError,
    PexelsRateLimitError, 
    PexelsBadRequestError,
    PexelsNotFoundError,
    PexelsServerError
)

client = PexelsClient(api_key="YOUR_API_KEY")

try:
    photos = client.search_photos("test")
except PexelsAuthError as e:
    print(f"认证失败: {e.message}")
except PexelsRateLimitError as e:
    print(f"限流错误，建议等待 {e.retry_after} 秒")
except PexelsBadRequestError as e:
    print(f"请求参数错误: {e.message}")
except PexelsNotFoundError as e:
    print(f"资源不存在: {e.message}")
except PexelsServerError as e:
    print(f"服务器错误: {e.message}")
```

## 📝 日志配置

```python
from pexels_python import set_debug, set_info

# 启用调试日志，显示详细的请求/响应信息
set_debug()

# 设置为信息级别
set_info()
```

## 📚 示例代码

查看 `examples/` 目录获取更多示例：

- `basic_usage.py` - 基础功能演示
- `async_usage.py` - 异步客户端使用
- `pagination_example.py` - 分页功能演示
- `retry_and_cache_example.py` - 重试和缓存功能

运行示例：

```bash
# 设置 API 密钥
export PEXELS_API_KEY="your_api_key_here"

# 运行基础示例
poetry run python examples/basic_usage.py

# 运行异步示例
poetry run python examples/async_usage.py
```

## 🧪 测试

运行测试套件：

```bash
# 运行所有测试
poetry run python -m pytest tests/ -v

# 运行特定测试
poetry run python -m pytest tests/test_client.py -v

# 运行异步测试
poetry run python -m pytest tests/test_async_client.py -v
```

## 📖 API 文档

### 主要类

- `PexelsClient` - 同步客户端
- `AsyncPexelsClient` - 异步客户端
- `PaginationIterator` - 分页迭代器
- `RetryConfig` - 重试配置
- `CacheManager` - 缓存管理器

### 主要方法

**照片相关：**
- `search_photos(query, ...)` - 搜索照片
- `curated_photos(...)` - 获取精选照片
- `get_photo(photo_id)` - 获取单张照片

**视频相关：**
- `search_videos(query, ...)` - 搜索视频
- `popular_videos(...)` - 获取热门视频
- `get_video(video_id)` - 获取单个视频

**分页迭代器：**
- `iter_search_photos(...)` - 照片搜索迭代器
- `iter_curated_photos(...)` - 精选照片迭代器
- `iter_search_videos(...)` - 视频搜索迭代器
- `iter_popular_videos(...)` - 热门视频迭代器

## 🔧 配置选项

### 重试配置

```python
RetryConfig(
    max_retries=3,        # 最大重试次数
    base_delay=1.0,       # 基础延迟（秒）
    max_delay=60.0,       # 最大延迟（秒）
    exponential_base=2.0, # 指数退避基数
    jitter=True           # 是否添加随机抖动
)
```

### 缓存配置

```python
# 内存缓存
CacheManager.create_memory_cache(
    max_size=100,  # 最大缓存项数
    ttl=300        # 生存时间（秒）
)

# Redis 缓存
CacheManager.create_redis_cache(
    host="localhost",
    port=6379,
    db=0,
    ttl=300
)
```

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可

MIT License
