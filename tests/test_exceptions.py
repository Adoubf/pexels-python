# -*- coding: utf-8 -*-
"""测试异常处理。"""
import pytest

from pexels_python.core.exceptions import (
    PexelsApiError,
    PexelsAuthError,
    PexelsBadRequestError,
    PexelsError,
    PexelsHttpError,
    PexelsNotFoundError,
    PexelsRateLimitError,
    PexelsServerError,
    _parse_retry_after,
    build_api_error,
)


class TestPexelsError:
    """测试基础异常类。"""

    def test_base_exception(self):
        """测试基础异常。"""
        error = PexelsError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, Exception)


class TestPexelsHttpError:
    """测试HTTP异常基类。"""

    def test_basic_creation(self):
        """测试基本创建。"""
        error = PexelsHttpError(
            status_code=400,
            message="Bad request",
            method="GET",
            url="https://api.pexels.com/v1/search",
            params={"query": "test"},
            headers={"X-Request-Id": "123"},
            response_body='{"error": "Bad request"}',
            request_id="123",
            retry_after=60.0
        )
        
        assert error.status_code == 400
        assert error.message == "Bad request"
        assert error.method == "GET"
        assert error.url == "https://api.pexels.com/v1/search"
        assert error.params == {"query": "test"}
        assert error.headers == {"X-Request-Id": "123"}
        assert error.response_body == '{"error": "Bad request"}'
        assert error.request_id == "123"
        assert error.retry_after == 60.0

    def test_string_representation(self):
        """测试字符串表示。"""
        error = PexelsHttpError(
            status_code=404,
            message="Not found",
            request_id="req-123"
        )
        
        expected = "HTTP 404 错误: Not found request_id=req-123"
        assert str(error) == expected

    def test_to_dict(self):
        """测试序列化为字典。"""
        error = PexelsHttpError(
            status_code=500,
            message="Server error",
            method="POST",
            url="https://api.pexels.com/v1/test",
            params={"key": "value"},
            headers={"Content-Type": "application/json"},
            response_body="Internal server error",
            request_id="req-456",
            retry_after=30.0
        )
        
        result = error.to_dict()
        expected = {
            "status_code": 500,
            "message": "Server error",
            "method": "POST",
            "url": "https://api.pexels.com/v1/test",
            "params": {"key": "value"},
            "headers": {"Content-Type": "application/json"},
            "response_body": "Internal server error",
            "request_id": "req-456",
            "retry_after": 30.0
        }
        
        assert result == expected

    def test_should_retry_default(self):
        """测试默认不重试。"""
        error = PexelsHttpError(status_code=400, message="Bad request")
        assert error.should_retry() is False


class TestSpecificErrors:
    """测试具体的异常类型。"""

    def test_bad_request_error(self):
        """测试400错误。"""
        error = PexelsBadRequestError(status_code=400, message="Invalid parameters")
        assert isinstance(error, PexelsHttpError)
        assert error.status_code == 400
        assert error.should_retry() is False

    def test_auth_error(self):
        """测试认证错误。"""
        error = PexelsAuthError(status_code=401, message="Unauthorized")
        assert isinstance(error, PexelsHttpError)
        assert error.status_code == 401
        assert error.should_retry() is False

    def test_not_found_error(self):
        """测试404错误。"""
        error = PexelsNotFoundError(status_code=404, message="Resource not found")
        assert isinstance(error, PexelsHttpError)
        assert error.status_code == 404
        assert error.should_retry() is False

    def test_rate_limit_error(self):
        """测试限流错误。"""
        error = PexelsRateLimitError(status_code=429, message="Rate limit exceeded")
        assert isinstance(error, PexelsHttpError)
        assert error.status_code == 429
        assert error.should_retry() is True

    def test_server_error(self):
        """测试服务器错误。"""
        error = PexelsServerError(status_code=500, message="Internal server error")
        assert isinstance(error, PexelsHttpError)
        assert error.status_code == 500
        assert error.should_retry() is True

    def test_api_error(self):
        """测试通用API错误。"""
        error = PexelsApiError(status_code=418, message="I'm a teapot")
        assert isinstance(error, PexelsHttpError)
        assert error.status_code == 418
        assert error.should_retry() is False


class TestRetryAfterParsing:
    """测试重试时间解析。"""

    def test_parse_retry_after_header(self):
        """测试解析Retry-After头。"""
        headers = {"Retry-After": "60"}
        result = _parse_retry_after(headers)
        assert result == 60.0

    def test_parse_ratelimit_reset_header(self):
        """测试解析X-Ratelimit-Reset头。"""
        headers = {"X-Ratelimit-Reset": "120"}
        result = _parse_retry_after(headers)
        assert result == 120.0

    def test_retry_after_priority(self):
        """测试Retry-After优先级更高。"""
        headers = {
            "Retry-After": "60",
            "X-Ratelimit-Reset": "120"
        }
        result = _parse_retry_after(headers)
        assert result == 60.0

    def test_invalid_values(self):
        """测试无效值处理。"""
        headers = {"Retry-After": "invalid"}
        result = _parse_retry_after(headers)
        assert result is None

    def test_no_headers(self):
        """测试无相关头部。"""
        headers = {"Content-Type": "application/json"}
        result = _parse_retry_after(headers)
        assert result is None


class TestBuildApiError:
    """测试异常构建函数。"""

    def test_build_400_error(self):
        """测试构建400错误。"""
        error = build_api_error(
            status_code=400,
            message="Bad request",
            method="GET",
            url="https://api.pexels.com/v1/search",
            params={"query": "test"},
            headers={"X-Request-Id": "123"},
            response_body='{"error": "Bad request"}'
        )
        
        assert isinstance(error, PexelsBadRequestError)
        assert error.status_code == 400
        assert error.request_id == "123"

    def test_build_401_error(self):
        """测试构建401错误。"""
        error = build_api_error(
            status_code=401,
            message="Unauthorized",
            method="GET",
            url="https://api.pexels.com/v1/search",
            params=None,
            headers=None,
            response_body=None
        )
        
        assert isinstance(error, PexelsAuthError)
        assert error.status_code == 401

    def test_build_403_error(self):
        """测试构建403错误。"""
        error = build_api_error(
            status_code=403,
            message="Forbidden",
            method="GET",
            url="https://api.pexels.com/v1/search",
            params=None,
            headers=None,
            response_body=None
        )
        
        assert isinstance(error, PexelsAuthError)
        assert error.status_code == 403

    def test_build_404_error(self):
        """测试构建404错误。"""
        error = build_api_error(
            status_code=404,
            message="Not found",
            method="GET",
            url="https://api.pexels.com/v1/photos/123",
            params=None,
            headers=None,
            response_body=None
        )
        
        assert isinstance(error, PexelsNotFoundError)
        assert error.status_code == 404

    def test_build_429_error(self):
        """测试构建429错误。"""
        error = build_api_error(
            status_code=429,
            message="Rate limit exceeded",
            method="GET",
            url="https://api.pexels.com/v1/search",
            params=None,
            headers={"Retry-After": "60"},
            response_body=None
        )
        
        assert isinstance(error, PexelsRateLimitError)
        assert error.status_code == 429
        assert error.retry_after == 60.0

    def test_build_500_error(self):
        """测试构建500错误。"""
        error = build_api_error(
            status_code=500,
            message="Internal server error",
            method="GET",
            url="https://api.pexels.com/v1/search",
            params=None,
            headers=None,
            response_body=None
        )
        
        assert isinstance(error, PexelsServerError)
        assert error.status_code == 500

    def test_build_generic_error(self):
        """测试构建通用错误。"""
        error = build_api_error(
            status_code=418,
            message="I'm a teapot",
            method="GET",
            url="https://api.pexels.com/v1/search",
            params=None,
            headers=None,
            response_body=None
        )
        
        assert isinstance(error, PexelsApiError)
        assert error.status_code == 418