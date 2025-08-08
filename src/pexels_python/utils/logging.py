# -*- coding: utf-8 -*-
"""基于 Rich + logging 的美化日志系统。

特性：
- 集成 Rich 的美化输出，支持彩色、样式、图标等
- 动态切换日志级别（debug/info）
- 统一的日志格式与样式
- 自动处理控制台宽度与截断
"""
from __future__ import annotations

import logging
import sys
from typing import Optional

try:
    from rich.console import Console
    from rich.logging import RichHandler
    HAS_RICH = True
except ImportError:
    HAS_RICH = False


# 全局控制台实例与日志级别
_console: Optional["Console"] = None
_current_level = logging.INFO


def _get_console() -> "Console":
    """获取全局 Rich Console 实例。"""
    global _console
    if _console is None:
        if HAS_RICH:
            _console = Console(stderr=True, force_terminal=True)
        else:
            # 降级：伪造一个简单的 Console
            class FakeConsole:
                def print(self, *args, **kwargs):
                    print(*args, file=sys.stderr)
            _console = FakeConsole()  # type: ignore
    return _console


def _setup_rich_handler() -> logging.Handler:
    """创建 Rich 处理器，如果 Rich 不可用则降级为标准处理器。"""
    if HAS_RICH:
        return RichHandler(
            console=_get_console(),
            show_time=True,
            show_path=True,
            markup=True,
            rich_tracebacks=True,
            tracebacks_width=120,
            tracebacks_show_locals=False,
        )
    else:
        # 降级：标准流处理器
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
        )
        return handler


def get_logger(name: str) -> logging.Logger:
    """获取指定名称的美化日志器。
    
    Args:
        name: 日志器名称，通常使用 __name__
    
    Returns:
        配置好的 Logger 实例
    """
    logger = logging.getLogger(name)
    
    # 避免重复添加处理器
    if not logger.handlers:
        handler = _setup_rich_handler()
        handler.setLevel(_current_level)
        logger.addHandler(handler)
        logger.setLevel(_current_level)
        logger.propagate = False
    
    return logger


def set_debug() -> None:
    """全局设置为调试级别，显示详细的请求/响应信息。"""
    global _current_level
    _current_level = logging.DEBUG
    
    # 更新已存在的所有 pexels_python 相关日志器
    for name in list(logging.Logger.manager.loggerDict.keys()):
        if name.startswith("pexels_python"):
            logger = logging.getLogger(name)
            logger.setLevel(logging.DEBUG)
            for handler in logger.handlers:
                handler.setLevel(logging.DEBUG)


def set_info() -> None:
    """全局设置为信息级别，仅显示重要信息。"""
    global _current_level
    _current_level = logging.INFO
    
    # 更新已存在的所有 pexels_python 相关日志器
    for name in list(logging.Logger.manager.loggerDict.keys()):
        if name.startswith("pexels_python"):
            logger = logging.getLogger(name)
            logger.setLevel(logging.INFO)
            for handler in logger.handlers:
                handler.setLevel(logging.INFO)


def log_api_call(logger: logging.Logger, method: str, url: str, status_code: int, duration_ms: float) -> None:
    """记录 API 调用日志（带样式）。"""
    if HAS_RICH:
        # 使用 Rich 样式
        if status_code < 300:
            status_style = "green"
            emoji = "✅"
        elif status_code < 400:
            status_style = "yellow"
            emoji = "⚠️"
        else:
            status_style = "red"
            emoji = "❌"
        
        logger.info(
            f"{emoji} [{status_style}]{method}[/] {url} -> [{status_style}]{status_code}[/] ({duration_ms:.1f}ms)",
            extra={"markup": True}
        )
    else:
        # 降级：纯文本
        emoji = "✓" if status_code < 400 else "✗"
        logger.info(f"{emoji} {method} {url} -> {status_code} ({duration_ms:.1f}ms)")


def log_retry(logger: logging.Logger, attempt: int, max_retries: int, delay: float, reason: str) -> None:
    """记录重试日志（带样式）。"""
    if HAS_RICH:
        logger.warning(
            f"🔄 重试 [{attempt}/{max_retries}] 将在 [yellow]{delay:.1f}s[/] 后执行，原因: {reason}",
            extra={"markup": True}
        )
    else:
        logger.warning(f"↻ 重试 [{attempt}/{max_retries}] 将在 {delay:.1f}s 后执行，原因: {reason}")