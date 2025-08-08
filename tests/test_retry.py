# -*- coding: utf-8 -*-
"""测试重试和退避策略功能。"""
import pytest
import time
import asyncio
from unittest.mock import Mock, patch

from pexels_python.core.retry import (
    RetryConfig,
    retry_on_failure,
    async_retry_on_failure,
    RetryableOperation,
    AsyncRetryableOperation,
)
from pexels_python.core.exceptions import (
    PexelsRateLimitError,
    PexelsServerError,
    PexelsAuthError,
)


class TestRetryConfig:
    """RetryConfig 测试类。"""
    
    def test_default_config(self):
        """测试默认配置。"""
        config = RetryConfig()
        
        assert config.max_retries == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0
        assert config.jitter is True
        assert config.jitter_range == 0.1
        assert PexelsRateLimitError in config.retryable_exceptions
        assert PexelsServerError in config.retryable_exceptions
        assert 429 in config.retryable_status_codes
        assert 500 in config.retryable_status_codes
    
    def test_custom_config(self):
        """测试自定义配置。"""
        config = RetryConfig(
            max_retries=5,
            base_delay=2.0,
            max_delay=120.0,
            exponential_base=3.0,
            jitter=False,
            jitter_range=0.2,
        )
        
        assert config.max_retries == 5
        assert config.base_delay == 2.0
        assert config.max_delay == 120.0
        assert config.exponential_base == 3.0
        assert config.jitter is False
        assert config.jitter_range == 0.2
    
    def test_calculate_delay(self):
        """测试延迟计算。"""
        config = RetryConfig(base_delay=1.0, exponential_base=2.0, jitter=False)
        
        # 测试指数退避
        assert config.calculate_delay(0) == 1.0  # 1.0 * 2^0
        assert config.calculate_delay(1) == 2.0  # 1.0 * 2^1
        assert config.calculate_delay(2) == 4.0  # 1.0 * 2^2
        assert config.calculate_delay(3) == 8.0  # 1.0 * 2^3
    
    def test_calculate_delay_with_max_limit(self):
        """测试最大延迟限制。"""
        config = RetryConfig(base_delay=10.0, max_delay=15.0, jitter=False)
        
        delay = config.calculate_delay(3)  # 10.0 * 2^3 = 80.0，但被限制为 15.0
        assert delay == 15.0
    
    def test_calculate_delay_with_retry_after(self):
        """测试使用 retry_after 的延迟计算。"""
        config = RetryConfig(base_delay=1.0, jitter=False)
        
        # 创建带有 retry_after 的异常
        exception = PexelsRateLimitError(
            429, "Rate limit exceeded", retry_after=30.0
        )
        
        delay = config.calculate_delay(0, exception)
        assert delay == 30.0
    
    def test_calculate_delay_with_jitter(self):
        """测试带抖动的延迟计算。"""
        config = RetryConfig(base_delay=10.0, jitter=True, jitter_range=0.1)
        
        delays = [config.calculate_delay(0) for _ in range(100)]
        
        # 所有延迟应该在 9.0 到 11.0 之间（10.0 ± 10%）
        assert all(9.0 <= delay <= 11.0 for delay in delays)
        # 应该有一些变化（不是所有值都相同）
        assert len(set(delays)) > 1
    
    def test_should_retry_by_exception_type(self):
        """测试基于异常类型的重试判断。"""
        config = RetryConfig(max_retries=3)
        
        # 可重试的异常
        assert config.should_retry(PexelsRateLimitError(429, "Rate limit"), 0) is True
        assert config.should_retry(PexelsServerError(500, "Server error"), 1) is True
        
        # 不可重试的异常
        assert config.should_retry(PexelsAuthError(401, "Unauthorized"), 0) is False
        assert config.should_retry(ValueError("Invalid value"), 0) is False
    
    def test_should_retry_by_status_code(self):
        """测试基于状态码的重试判断。"""
        config = RetryConfig(max_retries=3)
        
        # 可重试的状态码
        rate_limit_error = PexelsRateLimitError(429, "Rate limit")
        server_error = PexelsServerError(502, "Bad gateway")
        
        assert config.should_retry(rate_limit_error, 0) is True
        assert config.should_retry(server_error, 1) is True
        
        # 不可重试的状态码
        auth_error = PexelsAuthError(401, "Unauthorized")
        assert config.should_retry(auth_error, 0) is False
    
    def test_should_retry_max_attempts(self):
        """测试最大重试次数限制。"""
        config = RetryConfig(max_retries=2)
        
        exception = PexelsRateLimitError(429, "Rate limit")
        
        assert config.should_retry(exception, 0) is True
        assert config.should_retry(exception, 1) is True
        assert config.should_retry(exception, 2) is False  # 达到最大重试次数


class TestRetryDecorator:
    """重试装饰器测试类。"""
    
    def test_retry_success_on_first_attempt(self):
        """测试第一次尝试成功。"""
        call_count = 0
        
        @retry_on_failure(max_retries=3)
        def test_function():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = test_function()
        
        assert result == "success"
        assert call_count == 1
    
    def test_retry_success_after_failures(self):
        """测试失败后重试成功。"""
        call_count = 0
        
        @retry_on_failure(max_retries=3, base_delay=0.01)  # 快速重试用于测试
        def test_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise PexelsRateLimitError(429, "Rate limit")
            return "success"
        
        result = test_function()
        
        assert result == "success"
        assert call_count == 3
    
    def test_retry_exhausted(self):
        """测试重试次数耗尽。"""
        call_count = 0
        
        @retry_on_failure(max_retries=2, base_delay=0.01)
        def test_function():
            nonlocal call_count
            call_count += 1
            raise PexelsRateLimitError(429, "Rate limit")
        
        with pytest.raises(PexelsRateLimitError):
            test_function()
        
        assert call_count == 3  # 1 次初始调用 + 2 次重试
    
    def test_retry_non_retryable_exception(self):
        """测试不可重试的异常。"""
        call_count = 0
        
        @retry_on_failure(max_retries=3)
        def test_function():
            nonlocal call_count
            call_count += 1
            raise PexelsAuthError(401, "Unauthorized")
        
        with pytest.raises(PexelsAuthError):
            test_function()
        
        assert call_count == 1  # 不应该重试
    
    @patch('time.sleep')
    def test_retry_delay(self, mock_sleep):
        """测试重试延迟。"""
        call_count = 0
        
        @retry_on_failure(max_retries=2, base_delay=1.0)
        def test_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise PexelsServerError(500, "Server error")
            return "success"
        
        result = test_function()
        
        assert result == "success"
        assert call_count == 3
        assert mock_sleep.call_count == 2  # 2 次重试延迟
    
    def test_retry_with_custom_config(self):
        """测试自定义重试配置。"""
        config = RetryConfig(max_retries=1, base_delay=0.01)
        call_count = 0
        
        @retry_on_failure(config)
        def test_function():
            nonlocal call_count
            call_count += 1
            raise PexelsRateLimitError(429, "Rate limit")
        
        with pytest.raises(PexelsRateLimitError):
            test_function()
        
        assert call_count == 2  # 1 次初始调用 + 1 次重试


class TestAsyncRetryDecorator:
    """异步重试装饰器测试类。"""
    
    @pytest.mark.asyncio
    async def test_async_retry_success_on_first_attempt(self):
        """测试异步第一次尝试成功。"""
        call_count = 0
        
        @async_retry_on_failure(max_retries=3)
        async def test_function():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = await test_function()
        
        assert result == "success"
        assert call_count == 1
    
    @pytest.mark.asyncio
    async def test_async_retry_success_after_failures(self):
        """测试异步失败后重试成功。"""
        call_count = 0
        
        @async_retry_on_failure(max_retries=3, base_delay=0.01)
        async def test_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise PexelsRateLimitError(429, "Rate limit")
            return "success"
        
        result = await test_function()
        
        assert result == "success"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_async_retry_exhausted(self):
        """测试异步重试次数耗尽。"""
        call_count = 0
        
        @async_retry_on_failure(max_retries=2, base_delay=0.01)
        async def test_function():
            nonlocal call_count
            call_count += 1
            raise PexelsRateLimitError(429, "Rate limit")
        
        with pytest.raises(PexelsRateLimitError):
            await test_function()
        
        assert call_count == 3  # 1 次初始调用 + 2 次重试


class TestRetryableOperation:
    """RetryableOperation 测试类。"""
    
    def test_retryable_operation_success(self):
        """测试可重试操作成功。"""
        call_count = 0
        
        with RetryableOperation(RetryConfig(max_retries=3, base_delay=0.01)) as retry:
            while retry.should_continue():
                call_count += 1
                if call_count < 3:
                    retry.failure(PexelsRateLimitError(429, "Rate limit"))
                else:
                    retry.success("success")
        
        assert retry.result == "success"
        assert call_count == 3
    
    def test_retryable_operation_failure(self):
        """测试可重试操作失败。"""
        call_count = 0
        
        with pytest.raises(PexelsRateLimitError):
            with RetryableOperation(RetryConfig(max_retries=2, base_delay=0.01)) as retry:
                while retry.should_continue():
                    call_count += 1
                    retry.failure(PexelsRateLimitError(429, "Rate limit"))
        
        assert call_count == 3  # 1 次初始调用 + 2 次重试
    
    def test_retryable_operation_non_retryable(self):
        """测试不可重试操作。"""
        call_count = 0
        
        with pytest.raises(PexelsAuthError):
            with RetryableOperation(RetryConfig(max_retries=3)) as retry:
                while retry.should_continue():
                    call_count += 1
                    retry.failure(PexelsAuthError(401, "Unauthorized"))
        
        assert call_count == 1  # 不应该重试


class TestAsyncRetryableOperation:
    """AsyncRetryableOperation 测试类。"""
    
    @pytest.mark.asyncio
    async def test_async_retryable_operation_success(self):
        """测试异步可重试操作成功。"""
        call_count = 0
        
        async with AsyncRetryableOperation(RetryConfig(max_retries=3, base_delay=0.01)) as retry:
            while await retry.should_continue():
                call_count += 1
                if call_count < 3:
                    retry.failure(PexelsRateLimitError(429, "Rate limit"))
                else:
                    retry.success("success")
        
        assert retry.result == "success"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_async_retryable_operation_failure(self):
        """测试异步可重试操作失败。"""
        call_count = 0
        
        with pytest.raises(PexelsRateLimitError):
            async with AsyncRetryableOperation(RetryConfig(max_retries=2, base_delay=0.01)) as retry:
                while await retry.should_continue():
                    call_count += 1
                    retry.failure(PexelsRateLimitError(429, "Rate limit"))
        
        assert call_count == 3  # 1 次初始调用 + 2 次重试