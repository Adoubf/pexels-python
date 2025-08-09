# 📸 pexels-python

[![🇨🇳 中文](https://img.shields.io/badge/lang-中文-red.svg)](README.md)
[![🇺🇸 English](https://img.shields.io/badge/lang-English-blue.svg)](README.en.md)

> A **feature-complete, high-performance Pexels API client** for Python. Ships with sync & async clients, automatic retries, caching, and pagination utilities.

[![PyPI](https://img.shields.io/pypi/v/pexels-python?color=blue)](https://pypi.org/project/pexels-python/)
[![Python Version](https://img.shields.io/pypi/pyversions/pexels-python.svg)](https://pypi.org/project/pexels-python/)
[![License](https://img.shields.io/github/license/Adoubf/pexels-python)](LICENSE)

---

## 📑 Table of Contents
- [✨ Features](#-features)
- [📊 Flow: Pexels API Calls](#-flow-pexels-api-calls)
- [📦 Installation](#-installation)
- [🚀 Quick Start](#-quick-start)
- [🛡️ Error Handling](#️-error-handling)
- [📝 Logging](#-logging)
- [📚 Examples](#-examples)
- [🧪 Tests](#-tests)
- [📖 API Reference](#-api-reference)
- [🔧 Configuration](#-configuration)
- [🤝 Contributing](#-contributing)
- [📄 License](#-license)

---

## ✨ Features

- 🔄 **Automatic retries** on HTTP 429 with exponential backoff
- 🚀 **Async-ready** via `httpx`, supports concurrent requests
- 📄 **Pagination iterators** to seamlessly traverse large result sets
- 💾 **Smart caching** with in-memory and Redis backends
- 🛡️ **Rich exceptions** with detailed context
- 📝 **Pretty logs** powered by `Rich`
- 🎯 **Type hints** across the public API
- 🧪 **Solid tests** with high coverage

---

## 📊 Flow: Pexels API Calls

```mermaid
flowchart LR
    A[Your Code] -->|Build request| B[PexelsClient / AsyncPexelsClient]
    B -->|Check cache| C[CacheManager]
    C -->|Hit| D[Return cached data]
    C -->|Miss| E[HTTP request to Pexels API]
    E -->|200 OK| F[Parse JSON]
    E -->|429 Rate Limit| G[RetryConfig: exponential backoff]
    F --> H[Update cache]
    H --> I[Return to caller]
    G --> E
````

> The client checks cache first. On a miss, it calls the Pexels API and updates cache on success.
> Rate-limited (429)? It retries with exponential backoff (optional jitter).

---

## 📦 Installation

**Poetry:**

```bash
poetry add pexels-python
```

**pip:**

```bash
pip install pexels-python
```

**Local dev:**

```bash
poetry install
```

---

## 🚀 Quick Start

### Sync

```python
from pexels_python import PexelsClient

client = PexelsClient(api_key="YOUR_PEXELS_API_KEY")

photos = client.search_photos("cats", per_page=5)
print(f"total results = {photos['total_results']}")

curated = client.curated_photos(per_page=5)
print(f"curated photos = {len(curated['photos'])}")

videos = client.search_videos("nature", per_page=5)
print(f"videos = {len(videos['videos'])}")
```

### Async

```python
import asyncio
from pexels_python import AsyncPexelsClient

async def main():
    async with AsyncPexelsClient(api_key="YOUR_API_KEY") as client:
        photos_task = client.search_photos("mountains", per_page=5)
        videos_task = client.search_videos("ocean", per_page=5)
        photos, videos = await asyncio.gather(photos_task, videos_task)
        print(f"photos: {len(photos['photos'])}, videos: {len(videos['videos'])}")

asyncio.run(main())
```

### Pagination

```python
from pexels_python import iter_search_photos

for photo in iter_search_photos(client, "sunset", per_page=10, max_items=100):
    print(f"id={photo['id']}, photographer={photo['photographer']}")
```

### Retries & Cache

```python
from pexels_python import PexelsClient, RetryConfig, CacheManager

retry = RetryConfig(max_retries=3, base_delay=1.0, exponential_base=2.0)
cache = CacheManager.create_memory_cache(max_size=100, ttl=300)

client = PexelsClient(
    api_key="YOUR_API_KEY",
    retry_config=retry,
    cache_manager=cache
)
```

---

## 🛡️ Error Handling

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
    client.search_photos("test")
except PexelsAuthError as e:
    print(f"auth failed: {e.message}")
except PexelsRateLimitError as e:
    print(f"rate limited, wait {e.retry_after} seconds")
except PexelsBadRequestError as e:
    print(f"bad request: {e.message}")
except PexelsNotFoundError as e:
    print(f"not found: {e.message}")
except PexelsServerError as e:
    print(f"server error: {e.message}")
```

---

## 📝 Logging

```python
from pexels_python import set_debug, set_info

set_debug()  # verbose request/response logs
set_info()   # info level
```

---

## 📚 Examples

See `examples/`:

* `basic_usage.py` — basics
* `async_usage.py` — async client
* `pagination_example.py` — pagination
* `retry_and_cache_example.py` — retries & cache

Run:

```bash
export PEXELS_API_KEY="your_api_key_here"
poetry run python examples/basic_usage.py
poetry run python examples/async_usage.py
```

---

## 🧪 Tests

```bash
poetry run python -m pytest tests/ -v
poetry run python -m pytest tests/test_client.py -v
poetry run python -m pytest tests/test_async_client.py -v
```

---

## 📖 API Reference

**Core classes:**

* `PexelsClient` — sync client
* `AsyncPexelsClient` — async client
* `PaginationIterator` — pagination
* `RetryConfig` — retries
* `CacheManager` — caching

**Key methods (subset):**

* `search_photos(query, ...)`, `curated_photos(...)`, `get_photo(photo_id)`
* `search_videos(query, ...)`, `popular_videos(...)`, `get_video(video_id)`
* `iter_search_photos(...)`, `iter_curated_photos(...)`
* `iter_search_videos(...)`, `iter_popular_videos(...)`

---

## 🔧 Configuration

### Retry

```python
RetryConfig(
    max_retries=3,
    base_delay=1.0,
    max_delay=60.0,
    exponential_base=2.0,
    jitter=True
)
```

### Cache

```python
CacheManager.create_memory_cache(max_size=100, ttl=300)
CacheManager.create_redis_cache(host="localhost", port=6379, db=0, ttl=300)
```

---

## 🤝 Contributing

Issues and PRs are welcome!

---

## 📄 License

[MIT License](LICENSE)