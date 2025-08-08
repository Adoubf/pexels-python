# -*- coding: utf-8 -*-
"""测试日志系统。"""
import logging
from unittest.mock import Mock, patch

import pytest

from pexels_python.utils.logging import (
    get_logger,
    log_api_call,
    log_retry,
    set_debug,
    set_info,
)


class TestLoggingSetup:
    """测试日志设置。"""

    def test_get_logger(self):
        """测试获取日志器。"""
        logger = get_logger("test_logger")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_logger"

    def test_logger_singleton(self):
        """测试日志器单例行为。"""
        logger1 = get_logger("test_singleton")
        logger2 = get_logger("test_singleton")
        assert logger1 is logger2

    def test_set_debug_level(self):
        """测试设置调试级别。"""
        logger = get_logger("pexels_python.test_debug")
        
        set_debug()
        assert logger.level == logging.DEBUG
        
        # 检查处理器级别
        for handler in logger.handlers:
            assert handler.level == logging.DEBUG

    def test_set_info_level(self):
        """测试设置信息级别。"""
        logger = get_logger("pexels_python.test_info")
        
        set_info()
        assert logger.level == logging.INFO
        
        # 检查处理器级别
        for handler in logger.handlers:
            assert handler.level == logging.INFO


class TestLogFormatting:
    """测试日志格式化。"""

    @patch('pexels_python.utils.logging.HAS_RICH', True)
    def test_log_api_call_success_with_rich(self):
        """测试成功API调用日志（Rich版本）。"""
        logger = Mock()
        
        log_api_call(logger, "GET", "https://api.pexels.com/v1/search", 200, 150.5)
        
        logger.info.assert_called_once()
        call_args = logger.info.call_args
        message = call_args[0][0]
        
        assert "✅" in message
        assert "GET" in message
        assert "200" in message
        assert "150.5ms" in message

    @patch('pexels_python.utils.logging.HAS_RICH', True)
    def test_log_api_call_client_error_with_rich(self):
        """测试客户端错误API调用日志（Rich版本）。"""
        logger = Mock()
        
        log_api_call(logger, "GET", "https://api.pexels.com/v1/search", 400, 50.0)
        
        logger.info.assert_called_once()
        call_args = logger.info.call_args
        message = call_args[0][0]
        
        assert "❌" in message
        assert "GET" in message
        assert "400" in message
        assert "50.0ms" in message

    @patch('pexels_python.utils.logging.HAS_RICH', True)
    def test_log_api_call_redirect_with_rich(self):
        """测试重定向API调用日志（Rich版本）。"""
        logger = Mock()
        
        log_api_call(logger, "GET", "https://api.pexels.com/v1/search", 301, 25.0)
        
        logger.info.assert_called_once()
        call_args = logger.info.call_args
        message = call_args[0][0]
        
        assert "⚠️" in message
        assert "GET" in message
        assert "301" in message
        assert "25.0ms" in message

    @patch('pexels_python.utils.logging.HAS_RICH', False)
    def test_log_api_call_without_rich(self):
        """测试API调用日志（无Rich版本）。"""
        logger = Mock()
        
        log_api_call(logger, "GET", "https://api.pexels.com/v1/search", 200, 100.0)
        
        logger.info.assert_called_once()
        call_args = logger.info.call_args
        message = call_args[0][0]
        
        assert "✓" in message
        assert "GET" in message
        assert "200" in message
        assert "100.0ms" in message

    @patch('pexels_python.utils.logging.HAS_RICH', True)
    def test_log_retry_with_rich(self):
        """测试重试日志（Rich版本）。"""
        logger = Mock()
        
        log_retry(logger, 2, 3, 5.0, "Rate limit exceeded")
        
        logger.warning.assert_called_once()
        call_args = logger.warning.call_args
        message = call_args[0][0]
        
        assert "🔄" in message
        assert "[2/3]" in message
        assert "5.0s" in message
        assert "Rate limit exceeded" in message

    @patch('pexels_python.utils.logging.HAS_RICH', False)
    def test_log_retry_without_rich(self):
        """测试重试日志（无Rich版本）。"""
        logger = Mock()
        
        log_retry(logger, 1, 2, 3.0, "Server error")
        
        logger.warning.assert_called_once()
        call_args = logger.warning.call_args
        message = call_args[0][0]
        
        assert "↻" in message
        assert "[1/2]" in message
        assert "3.0s" in message
        assert "Server error" in message


class TestRichIntegration:
    """测试Rich集成。"""

    @patch('pexels_python.utils.logging.HAS_RICH', True)
    @patch('pexels_python.utils.logging.Console')
    @patch('pexels_python.utils.logging.RichHandler')
    def test_rich_handler_setup(self, mock_rich_handler, mock_console):
        """测试Rich处理器设置。"""
        from pexels_python.utils.logging import _setup_rich_handler
        
        mock_console_instance = Mock()
        mock_console.return_value = mock_console_instance
        
        handler = _setup_rich_handler()
        
        mock_rich_handler.assert_called_once()
        call_kwargs = mock_rich_handler.call_args[1]
        
        assert call_kwargs['show_time'] is True
        assert call_kwargs['show_path'] is True
        assert call_kwargs['markup'] is True
        assert call_kwargs['rich_tracebacks'] is True

    @patch('pexels_python.utils.logging.HAS_RICH', False)
    def test_fallback_handler_setup(self):
        """测试降级处理器设置。"""
        from pexels_python.utils.logging import _setup_rich_handler
        
        handler = _setup_rich_handler()
        
        assert isinstance(handler, logging.StreamHandler)
        assert handler.formatter is not None