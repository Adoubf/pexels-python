# Pexels Python 示例代码

本目录包含了 pexels-python 库的各种使用示例，帮助您快速上手和了解库的功能。

## 准备工作

在运行示例之前，请确保：

1. 已安装依赖：
   ```bash
   poetry install
   ```

2. 设置 Pexels API 密钥：
   ```bash
   export PEXELS_API_KEY="your_pexels_api_key_here"
   ```

   您可以在 [Pexels API](https://www.pexels.com/api/) 页面免费申请 API 密钥。

## 示例文件说明

### 1. `basic_usage.py` - 基础使用
演示同步客户端的基本功能：
- 搜索照片和视频
- 获取精选内容
- 基本错误处理
- API 限流信息查看

```bash
poetry run python examples/basic_usage.py
```

### 2. `async_usage.py` - 异步客户端
演示异步客户端的使用：
- 异步 API 调用
- 并发请求处理
- 异步错误处理
- 上下文管理器使用

```bash
poetry run python examples/async_usage.py
```

### 3. `pagination_example.py` - 分页功能
演示分页迭代器的使用：
- 自动翻页迭代器
- 同步和异步分页
- 分页控制和限制
- 并发分页搜索

```bash
poetry run python examples/pagination_example.py
```

### 4. `retry_and_cache_example.py` - 重试和缓存
演示高级功能：
- 重试策略配置
- 缓存机制使用
- 错误恢复
- 性能优化
- 调试日志

```bash
poetry run python examples/retry_and_cache_example.py
```

## 功能特性展示

### 🔄 自动重试
- 对 429 限流错误自动重试
- 指数退避策略
- 可配置的重试次数和延迟

### 💾 智能缓存
- 内存缓存支持
- Redis 缓存支持
- TTL 过期控制
- LRU 淘汰策略

### 📄 分页迭代
- 自动翻页生成器
- 同步和异步支持
- 灵活的分页控制

### 🚀 异步支持
- 基于 httpx 的异步客户端
- 并发请求处理
- 异步上下文管理

### 📝 美化日志
- Rich 集成的彩色日志
- 详细的请求/响应信息
- 可切换的日志级别

### 🛡️ 异常处理
- 丰富的异常类型
- 详细的错误上下文
- 重试建议

## 注意事项

1. **API 限制**：Pexels API 有请求频率限制，请合理使用。

2. **缓存策略**：在生产环境中，建议使用 Redis 缓存以获得更好的性能。

3. **错误处理**：示例代码包含了基本的错误处理，实际使用时请根据需要完善。

4. **异步使用**：使用异步客户端时，记得在 `async with` 语句中使用以确保资源正确释放。

## 更多信息

- [Pexels API 文档](https://www.pexels.com/api/documentation/)
- [项目 GitHub 仓库](https://github.com/your-username/pexels-python)
- [问题反馈](https://github.com/your-username/pexels-python/issues)