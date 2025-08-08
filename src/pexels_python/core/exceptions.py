# -*- coding: utf-8 -*-
"""pexels_python.core.exceptions

规范且丰富的自定义异常体系。

- PexelsError: 基类
- PexelsHttpError: HTTP 相关错误的基类，包含上下文信息（方法、URL、请求参数、请求 ID、重试建议等）
- 子类：
  - PexelsBadRequestError (400)
  - PexelsAuthError (401/403)
  - PexelsNotFoundError (404)
  - PexelsRateLimitError (429)
  - PexelsServerError (>=500)
  - PexelsApiError: 其他非 2xx 的通用错误（保持向后兼容）

所有异常提供 to_dict() 方法，便于记录日志与序列化。
"""
from __future__ import annotations

from typing import Any, Dict, Mapping, Optional


class PexelsError(Exception):
    """包内所有异常的基类。"""


class PexelsHttpError(PexelsError):
    """HTTP 相关错误的基类，承载丰富上下文信息。

    Attributes:
        status_code: HTTP 状态码
        message: 错误消息（尽可能解析自响应体）
        method: HTTP 方法
        url: 请求的完整 URL
        params: 查询参数（如果有）
        headers: 响应头
        response_body: 原始响应体（字符串形式）
        request_id: 服务器返回的请求标识（X-Request-Id）
        retry_after: 建议的重试秒数（若可用）
    """

    __slots__ = (
        "status_code",
        "message",
        "method",
        "url",
        "params",
        "headers",
        "response_body",
        "request_id",
        "retry_after",
    )

    def __init__(
        self,
        status_code: int,
        message: str,
        *,
        method: str | None = None,
        url: str | None = None,
        params: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, Any]] = None,
        response_body: Optional[str] = None,
        request_id: Optional[str] = None,
        retry_after: Optional[float] = None,
    ) -> None:
        super().__init__(f"HTTP {status_code} 错误: {message}")
        self.status_code = status_code
        self.message = message
        self.method = method or ""
        self.url = url or ""
        self.params = dict(params or {})
        self.headers = dict(headers or {})
        self.response_body = response_body
        self.request_id = request_id
        self.retry_after = retry_after

    def __str__(self) -> str:  # noqa: D401
        base = super().__str__()
        rid = f" request_id={self.request_id}" if self.request_id else ""
        return f"{base}{rid}"

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典，便于日志或上报。"""
        return {
            "status_code": self.status_code,
            "message": self.message,
            "method": self.method,
            "url": self.url,
            "params": dict(self.params or {}),
            "headers": dict(self.headers or {}),
            "response_body": self.response_body,
            "request_id": self.request_id,
            "retry_after": self.retry_after,
        }

    def should_retry(self) -> bool:
        """默认不建议自动重试。子类可覆盖。"""
        return False


class PexelsBadRequestError(PexelsHttpError):
    """参数错误或请求无效（400）。"""


class PexelsAuthError(PexelsHttpError):
    """鉴权失败（401/403）。"""


class PexelsNotFoundError(PexelsHttpError):
    """资源不存在（404）。"""


class PexelsRateLimitError(PexelsHttpError):
    """触发限流（429）。"""

    def should_retry(self) -> bool:  # noqa: D401
        return True


class PexelsServerError(PexelsHttpError):
    """服务器错误（>=500）。"""

    def should_retry(self) -> bool:  # noqa: D401
        return True


class PexelsApiError(PexelsHttpError):
    """通用 API 错误（保持兼容）。"""


def _parse_retry_after(headers: Mapping[str, Any]) -> Optional[float]:
    """从响应头中解析建议的重试等待时间（秒）。

    解析顺序：Retry-After -> X-Ratelimit-Reset
    - Retry-After: 可为秒数字或 HTTP 日期（此处仅处理数字）
    - X-Ratelimit-Reset: 常见为秒数字或时间戳（此处若可转为 float 则返回）
    """
    retry_after = headers.get("Retry-After")
    if retry_after is not None:
        try:
            return float(retry_after)
        except (TypeError, ValueError):
            pass
    reset = headers.get("X-Ratelimit-Reset")
    if reset is not None:
        try:
            return float(reset)
        except (TypeError, ValueError):
            pass
    return None


def build_api_error(
    *,
    status_code: int,
    message: str,
    method: str,
    url: str,
    params: Optional[Mapping[str, Any]],
    headers: Optional[Mapping[str, Any]],
    response_body: Optional[str],
) -> PexelsHttpError:
    """根据状态码构建合适的异常实例。"""
    headers = headers or {}
    request_id = None
    try:
        request_id = headers.get("X-Request-Id")  # type: ignore[assignment]
    except Exception:
        request_id = None
    retry_after = _parse_retry_after(headers)

    if status_code == 400:
        cls = PexelsBadRequestError
    elif status_code in (401, 403):
        cls = PexelsAuthError
    elif status_code == 404:
        cls = PexelsNotFoundError
    elif status_code == 429:
        cls = PexelsRateLimitError
    elif status_code >= 500:
        cls = PexelsServerError
    else:
        cls = PexelsApiError

    return cls(
        status_code,
        message,
        method=method,
        url=url,
        params=params,
        headers=headers,
        response_body=response_body,
        request_id=request_id,
        retry_after=retry_after,
    )