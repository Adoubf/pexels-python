# -*- coding: utf-8 -*-
"""pexels_python.core.retry

重试和退避策略实现。

特性：
- 指数退避算法
- 随机抖动避免雷群效应
- 针对 429 限流的智能重试
- 可配置的重试条件和策略
- 支持同步和异步操作
"""
from __future__ import annotations

import asyncio
import random
import time
from functools import wraps
from typing import Any, Callable, Optional, Type, TypeVar

from ..utils.logging import get_logger, log_retry
from .exceptions import PexelsHttpError, PexelsRateLimitError, PexelsServerError

logger = get_logger(__name__)

T = TypeVar('T')
F = TypeVar('F', bound=Callable[..., Any])


class RetryConfig:
    """重试配置类。
    
    Args:
        max_retries: 最大重试次数，默认 3
        base_delay: 基础延迟时间（秒），默认 1.0
        max_delay: 最大延迟时间（秒），默认 60.0
        exponential_base: 指数退避的底数，默认 2.0
        jitter: 是否添加随机抖动，默认 True
        jitter_range: 抖动范围（0-1），默认 0.1
        retryable_exceptions: 可重试的异常类型
        retryable_status_codes: 可重试的 HTTP 状态码
    """
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        jitter_range: float = 0.1,
        retryable_exceptions: Optional[tuple[Type[Exception], ...]] = None,
        retryable_status_codes: Optional[set[int]] = None,
    ) -> None:
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.jitter_range = jitter_range
        
        # 默认可重试的异常类型
        self.retryable_exceptions = retryable_exceptions or (
            PexelsRateLimitError,
            PexelsServerError,
        )
        
        # 默认可重试的状态码
        self.retryable_status_codes = retryable_status_codes or {
            429,  # Too Many Requests
            500,  # Internal Server Error
            502,  # Bad Gateway
            503,  # Service Unavailable
            504,  # Gateway Timeout
        }
    
    def calculate_delay(self, attempt: int, exception: Optional[Exception] = None) -> float:
        """计算重试延迟时间。
        
        Args:
            attempt: 当前重试次数（从 0 开始）
            exception: 触发重试的异常（可选）
            
        Returns:
            延迟时间（秒）
        """
        # 如果异常包含 retry_after 信息，优先使用
        if isinstance(exception, PexelsHttpError) and exception.retry_after:
            delay = exception.retry_after
        else:
            # 指数退避计算
            delay = self.base_delay * (self.exponential_base ** attempt)
        
        # 限制最大延迟
        delay = min(delay, self.max_delay)
        
        # 添加随机抖动
        if self.jitter:
            jitter_amount = delay * self.jitter_range
            delay += random.uniform(-jitter_amount, jitter_amount)
        
        # 确保延迟不为负数
        return max(0, delay)
    
    def should_retry(self, exception: Exception, attempt: int) -> bool:
        """判断是否应该重试。
        
        Args:
            exception: 发生的异常
            attempt: 当前重试次数（从 0 开始）
            
        Returns:
            是否应该重试
        """
        # 检查重试次数限制
        if attempt >= self.max_retries:
            return False
        
        # 检查异常类型
        if isinstance(exception, self.retryable_exceptions):
            return True
        
        # 检查 HTTP 状态码
        if isinstance(exception, PexelsHttpError):
            return exception.status_code in self.retryable_status_codes
        
        return False


# 默认重试配置
DEFAULT_RETRY_CONFIG = RetryConfig()


def retry_on_failure(
    config: Optional[RetryConfig] = None,
    *,
    max_retries: Optional[int] = None,
    base_delay: Optional[float] = None,
) -> Callable[[F], F]:
    """重试装饰器（同步版本）。
    
    Args:
        config: 重试配置，如果为 None 则使用默认配置
        max_retries: 最大重试次数（覆盖配置）
        base_delay: 基础延迟时间（覆盖配置）
        
    Example:
        @retry_on_failure(max_retries=5)
        def api_call():
            # 可能失败的 API 调用
            pass
    """
    retry_config = config or DEFAULT_RETRY_CONFIG
    
    # 允许通过参数覆盖配置
    if max_retries is not None:
        retry_config = RetryConfig(
            max_retries=max_retries,
            base_delay=base_delay or retry_config.base_delay,
            max_delay=retry_config.max_delay,
            exponential_base=retry_config.exponential_base,
            jitter=retry_config.jitter,
            jitter_range=retry_config.jitter_range,
            retryable_exceptions=retry_config.retryable_exceptions,
            retryable_status_codes=retry_config.retryable_status_codes,
        )
    
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None
            
            for attempt in range(retry_config.max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    # 检查是否应该重试
                    if not retry_config.should_retry(e, attempt):
                        raise
                    
                    # 计算延迟时间
                    delay = retry_config.calculate_delay(attempt, e)
                    
                    # 记录重试日志
                    reason = getattr(e, 'message', str(e))
                    log_retry(logger, attempt + 1, retry_config.max_retries, delay, reason)
                    
                    # 等待后重试
                    time.sleep(delay)
            
            # 如果所有重试都失败，抛出最后一个异常
            raise last_exception
        
        return wrapper  # type: ignore
    
    return decorator


def async_retry_on_failure(
    config: Optional[RetryConfig] = None,
    *,
    max_retries: Optional[int] = None,
    base_delay: Optional[float] = None,
) -> Callable[[F], F]:
    """异步重试装饰器。
    
    Args:
        config: 重试配置，如果为 None 则使用默认配置
        max_retries: 最大重试次数（覆盖配置）
        base_delay: 基础延迟时间（覆盖配置）
        
    Example:
        @async_retry_on_failure(max_retries=5)
        async def async_api_call():
            # 可能失败的异步 API 调用
            pass
    """
    retry_config = config or DEFAULT_RETRY_CONFIG
    
    # 允许通过参数覆盖配置
    if max_retries is not None:
        retry_config = RetryConfig(
            max_retries=max_retries,
            base_delay=base_delay or retry_config.base_delay,
            max_delay=retry_config.max_delay,
            exponential_base=retry_config.exponential_base,
            jitter=retry_config.jitter,
            jitter_range=retry_config.jitter_range,
            retryable_exceptions=retry_config.retryable_exceptions,
            retryable_status_codes=retry_config.retryable_status_codes,
        )
    
    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None
            
            for attempt in range(retry_config.max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    # 检查是否应该重试
                    if not retry_config.should_retry(e, attempt):
                        raise
                    
                    # 计算延迟时间
                    delay = retry_config.calculate_delay(attempt, e)
                    
                    # 记录重试日志
                    reason = getattr(e, 'message', str(e))
                    log_retry(logger, attempt + 1, retry_config.max_retries, delay, reason)
                    
                    # 异步等待后重试
                    await asyncio.sleep(delay)
            
            # 如果所有重试都失败，抛出最后一个异常
            raise last_exception
        
        return wrapper  # type: ignore
    
    return decorator


class RetryableOperation:
    """可重试操作的上下文管理器。
    
    提供更灵活的重试控制，支持手动重试逻辑。
    
    Example:
        with RetryableOperation(max_retries=3) as retry:
            while retry.should_continue():
                try:
                    result = api_call()
                    retry.success(result)
                except Exception as e:
                    retry.failure(e)
    """
    
    def __init__(self, config: Optional[RetryConfig] = None) -> None:
        self.config = config or DEFAULT_RETRY_CONFIG
        self.attempt = 0
        self.last_exception: Optional[Exception] = None
        self.result: Any = None
        self._success = False
    
    def __enter__(self) -> "RetryableOperation":
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        # 如果没有成功且有异常，重新抛出
        if not self._success and self.last_exception:
            raise self.last_exception
    
    def should_continue(self) -> bool:
        """检查是否应该继续尝试。"""
        if self._success:
            return False
        
        if self.attempt == 0:
            self.attempt += 1
            return True
        
        if self.last_exception and self.config.should_retry(self.last_exception, self.attempt - 1):
            delay = self.config.calculate_delay(self.attempt - 1, self.last_exception)
            
            # 记录重试日志
            reason = getattr(self.last_exception, 'message', str(self.last_exception))
            log_retry(logger, self.attempt, self.config.max_retries, delay, reason)
            
            # 等待后继续
            time.sleep(delay)
            self.attempt += 1
            return True
        
        return False
    
    def success(self, result: Any) -> None:
        """标记操作成功。"""
        self.result = result
        self._success = True
    
    def failure(self, exception: Exception) -> None:
        """标记操作失败。"""
        self.last_exception = exception


class AsyncRetryableOperation:
    """异步可重试操作的上下文管理器。"""
    
    def __init__(self, config: Optional[RetryConfig] = None) -> None:
        self.config = config or DEFAULT_RETRY_CONFIG
        self.attempt = 0
        self.last_exception: Optional[Exception] = None
        self.result: Any = None
        self._success = False
    
    async def __aenter__(self) -> "AsyncRetryableOperation":
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        # 如果没有成功且有异常，重新抛出
        if not self._success and self.last_exception:
            raise self.last_exception
    
    async def should_continue(self) -> bool:
        """检查是否应该继续尝试（异步）。"""
        if self._success:
            return False
        
        if self.attempt == 0:
            self.attempt += 1
            return True
        
        if self.last_exception and self.config.should_retry(self.last_exception, self.attempt - 1):
            delay = self.config.calculate_delay(self.attempt - 1, self.last_exception)
            
            # 记录重试日志
            reason = getattr(self.last_exception, 'message', str(self.last_exception))
            log_retry(logger, self.attempt, self.config.max_retries, delay, reason)
            
            # 异步等待后继续
            await asyncio.sleep(delay)
            self.attempt += 1
            return True
        
        return False
    
    def success(self, result: Any) -> None:
        """标记操作成功。"""
        self.result = result
        self._success = True
    
    def failure(self, exception: Exception) -> None:
        """标记操作失败。"""
        self.last_exception = exception