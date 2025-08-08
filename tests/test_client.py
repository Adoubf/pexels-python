# -*- coding: utf-8 -*-
"""测试同步客户端功能。"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import requests

from pexels_python import PexelsClient
from pexels_python.core.exceptions import (
    PexelsApiError,
    PexelsAuthError,
    PexelsRateLimitError,
)


class TestPexelsClient:
    """PexelsClient 测试类。"""
    
    @pytest.fixture
    def client(self):
        """创建测试客户端。"""
        return PexelsClient(api_key="test_api_key")
    
    @pytest.fixture
    def mock_response(self):
        """创建模拟响应。"""
        response = Mock()
        response.ok = True
        response.status_code = 200
        response.headers = {
            "X-Ratelimit-Limit": "200",
            "X-Ratelimit-Remaining": "199",
            "X-Ratelimit-Reset": "3600",
        }
        response.json.return_value = {
            "photos": [
                {
                    "id": 123456,
                    "width": 1920,
                    "height": 1080,
                    "url": "https://example.com/photo",
                    "photographer": "Test Photographer",
                    "photographer_url": "https://example.com/photographer",
                    "photographer_id": 789,
                    "avg_color": "#FFFFFF",
                    "src": {
                        "original": "https://example.com/original.jpg",
                        "large": "https://example.com/large.jpg",
                        "medium": "https://example.com/medium.jpg",
                        "small": "https://example.com/small.jpg",
                    },
                    "liked": False,
                    "alt": "Test photo",
                }
            ],
            "total_results": 1000,
            "page": 1,
            "per_page": 15,
        }
        return response
    
    def test_client_initialization(self, client):
        """测试客户端初始化。"""
        assert client.api_key == "test_api_key"
        assert client.base_url == "https://api.pexels.com/v1/"
        assert client.timeout == 30.0
        assert client.max_retries == 3
        assert client.retry_delay == 1.0
        assert isinstance(client.last_rate_limit, dict)
    
    def test_context_manager(self):
        """测试上下文管理器。"""
        with PexelsClient(api_key="test") as client:
            assert client.api_key == "test"
        # 确保 close 被调用
        assert hasattr(client, "_session")
    
    @patch('requests.Session.request')
    def test_search_photos_success(self, mock_request, client, mock_response):
        """测试搜索照片成功。"""
        mock_request.return_value = mock_response
        
        result = client.search_photos("cats", per_page=5)
        
        assert "photos" in result
        assert len(result["photos"]) == 1
        assert result["total_results"] == 1000
        assert result["page"] == 1
        assert result["per_page"] == 15
        
        # 验证请求参数
        mock_request.assert_called_once()
        args, kwargs = mock_request.call_args
        assert kwargs["params"]["query"] == "cats"
        assert kwargs["params"]["per_page"] == 5
    
    @patch('requests.Session.request')
    def test_curated_photos_success(self, mock_request, client, mock_response):
        """测试获取精选照片成功。"""
        mock_request.return_value = mock_response
        
        result = client.curated_photos(per_page=10)
        
        assert "photos" in result
        mock_request.assert_called_once()
        args, kwargs = mock_request.call_args
        assert kwargs["params"]["per_page"] == 10
    
    @patch('requests.Session.request')
    def test_get_photo_success(self, mock_request, client):
        """测试获取单张照片成功。"""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.json.return_value = {
            "id": 123456,
            "width": 1920,
            "height": 1080,
            "url": "https://example.com/photo",
            "photographer": "Test Photographer",
        }
        mock_request.return_value = mock_response
        
        result = client.get_photo(123456)
        
        assert result["id"] == 123456
        assert result["photographer"] == "Test Photographer"
    
    @patch('requests.Session.request')
    def test_search_videos_success(self, mock_request, client):
        """测试搜索视频成功。"""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.json.return_value = {
            "videos": [
                {
                    "id": 789012,
                    "width": 1920,
                    "height": 1080,
                    "url": "https://example.com/video",
                    "duration": 30,
                    "user": {
                        "id": 123,
                        "name": "Test User",
                        "url": "https://example.com/user",
                    },
                    "video_files": [],
                    "video_pictures": [],
                }
            ],
            "total_results": 500,
            "page": 1,
            "per_page": 15,
        }
        mock_request.return_value = mock_response
        
        result = client.search_videos("nature", per_page=5)
        
        assert "videos" in result
        assert len(result["videos"]) == 1
        assert result["total_results"] == 500
    
    @patch('requests.Session.request')
    def test_rate_limit_info_update(self, mock_request, client, mock_response):
        """测试限流信息更新。"""
        mock_request.return_value = mock_response
        
        client.search_photos("test")
        
        assert client.last_rate_limit["limit"] == "200"
        assert client.last_rate_limit["remaining"] == "199"
        assert client.last_rate_limit["reset"] == "3600"
    
    @patch('requests.Session.request')
    def test_auth_error(self, mock_request, client):
        """测试认证错误。"""
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 401
        mock_response.headers = {}
        mock_response.text = "Unauthorized"
        mock_response.json.return_value = {"error": "Invalid API key"}
        mock_request.return_value = mock_response
        
        with pytest.raises(PexelsAuthError) as exc_info:
            client.search_photos("test")
        
        assert exc_info.value.status_code == 401
        assert "Invalid API key" in exc_info.value.message
    
    @patch('requests.Session.request')
    def test_rate_limit_error(self, mock_request, client):
        """测试限流错误。"""
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "60"}
        mock_response.text = "Too Many Requests"
        mock_response.json.return_value = {"error": "Rate limit exceeded"}
        mock_request.return_value = mock_response
        
        with pytest.raises(PexelsRateLimitError) as exc_info:
            client.search_photos("test")
        
        assert exc_info.value.status_code == 429
        assert exc_info.value.retry_after == 60.0
        assert exc_info.value.should_retry() is True
    
    @patch('requests.Session.request')
    def test_network_error(self, mock_request, client):
        """测试网络错误。"""
        mock_request.side_effect = requests.exceptions.ConnectionError("Network error")
        
        with pytest.raises(PexelsApiError) as exc_info:
            client.search_photos("test")
        
        assert exc_info.value.status_code == 0
        assert "网络请求失败" in exc_info.value.message
    
    def test_pagination_iterator_creation(self, client):
        """测试分页迭代器创建。"""
        iterator = client.iter_search_photos("cats", max_pages=3)
        
        assert iterator.method_name == "search_photos"
        assert iterator.per_page == 15
        assert iterator.max_pages == 3
        assert iterator.kwargs["query"] == "cats"
    
    @patch('requests.Session.request')
    def test_pagination_iterator_usage(self, mock_request, client):
        """测试分页迭代器使用。"""
        # 模拟多页响应
        responses = []
        for page in range(1, 4):
            response = Mock()
            response.ok = True
            response.status_code = 200
            response.headers = {}
            response.json.return_value = {
                "photos": [{"id": i + (page - 1) * 2} for i in range(1, 3)],
                "page": page,
                "per_page": 2,
                "total_results": 6,
            }
            responses.append(response)
        
        mock_request.side_effect = responses
        
        iterator = client.iter_search_photos("test", per_page=2, max_pages=3)
        photos = list(iterator)
        
        assert len(photos) == 6
        assert photos[0]["id"] == 1
        assert photos[-1]["id"] == 6
        assert mock_request.call_count == 3
    
    def test_empty_params_filtering(self, client):
        """测试空参数过滤。"""
        with patch('requests.Session.request') as mock_request:
            mock_response = Mock()
            mock_response.ok = True
            mock_response.status_code = 200
            mock_response.headers = {}
            mock_response.json.return_value = {"photos": []}
            mock_request.return_value = mock_response
            
            client.search_photos("test", orientation=None, size="", color=None)
            
            args, kwargs = mock_request.call_args
            params = kwargs["params"]
            
            # 空值应该被过滤掉
            assert "orientation" not in params
            assert "size" not in params
            assert "color" not in params
            assert params["query"] == "test"