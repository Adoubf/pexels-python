# -*- coding: utf-8 -*-
"""测试异步客户端功能。"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

from pexels_python import AsyncPexelsClient
from pexels_python.core.exceptions import (
    PexelsApiError,
    PexelsAuthError,
    PexelsRateLimitError,
)


@pytest.mark.skipif(not HTTPX_AVAILABLE, reason="httpx not available")
class TestAsyncPexelsClient:
    """AsyncPexelsClient 测试类。"""
    
    @pytest.fixture
    def client(self):
        """创建测试异步客户端。"""
        return AsyncPexelsClient(api_key="test_api_key")
    
    @pytest.fixture
    def mock_response(self):
        """创建模拟异步响应。"""
        response = Mock()
        response.is_success = True
        response.status_code = 200
        response.url = "https://api.pexels.com/v1/search"
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
        """测试异步客户端初始化。"""
        assert client.api_key == "test_api_key"
        assert client.base_url == "https://api.pexels.com/v1/"
        assert client.timeout == 30.0
        assert client.max_retries == 3
        assert client.retry_delay == 1.0
        assert isinstance(client.last_rate_limit, dict)
    
    @pytest.mark.asyncio
    async def test_context_manager(self):
        """测试异步上下文管理器。"""
        async with AsyncPexelsClient(api_key="test") as client:
            assert client.api_key == "test"
            # 客户端应该在上下文中被初始化
            await client._ensure_client()
            assert client._client is not None
    
    @pytest.mark.asyncio
    async def test_search_photos_success(self, client, mock_response):
        """测试异步搜索照片成功。"""
        with patch.object(client, '_ensure_client') as mock_ensure:
            mock_client = AsyncMock()
            mock_client.request.return_value = mock_response
            mock_ensure.return_value = mock_client
            
            result = await client.search_photos("cats", per_page=5)
            
            assert "photos" in result
            assert len(result["photos"]) == 1
            assert result["total_results"] == 1000
            assert result["page"] == 1
            assert result["per_page"] == 15
            
            # 验证请求参数
            mock_client.request.assert_called_once()
            args, kwargs = mock_client.request.call_args
            assert kwargs["params"]["query"] == "cats"
            assert kwargs["params"]["per_page"] == 5
    
    @pytest.mark.asyncio
    async def test_curated_photos_success(self, client, mock_response):
        """测试异步获取精选照片成功。"""
        with patch.object(client, '_ensure_client') as mock_ensure:
            mock_client = AsyncMock()
            mock_client.request.return_value = mock_response
            mock_ensure.return_value = mock_client
            
            result = await client.curated_photos(per_page=10)
            
            assert "photos" in result
            mock_client.request.assert_called_once()
            args, kwargs = mock_client.request.call_args
            assert kwargs["params"]["per_page"] == 10
    
    @pytest.mark.asyncio
    async def test_get_photo_success(self, client):
        """测试异步获取单张照片成功。"""
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.status_code = 200
        mock_response.url = "https://api.pexels.com/v1/photos/123456"
        mock_response.headers = {}
        mock_response.json.return_value = {
            "id": 123456,
            "width": 1920,
            "height": 1080,
            "url": "https://example.com/photo",
            "photographer": "Test Photographer",
        }
        
        with patch.object(client, '_ensure_client') as mock_ensure:
            mock_client = AsyncMock()
            mock_client.request.return_value = mock_response
            mock_ensure.return_value = mock_client
            
            result = await client.get_photo(123456)
            
            assert result["id"] == 123456
            assert result["photographer"] == "Test Photographer"
    
    @pytest.mark.asyncio
    async def test_search_videos_success(self, client):
        """测试异步搜索视频成功。"""
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.status_code = 200
        mock_response.url = "https://api.pexels.com/v1/videos/search"
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
        
        with patch.object(client, '_ensure_client') as mock_ensure:
            mock_client = AsyncMock()
            mock_client.request.return_value = mock_response
            mock_ensure.return_value = mock_client
            
            result = await client.search_videos("nature", per_page=5)
            
            assert "videos" in result
            assert len(result["videos"]) == 1
            assert result["total_results"] == 500
    
    @pytest.mark.asyncio
    async def test_rate_limit_info_update(self, client, mock_response):
        """测试异步限流信息更新。"""
        with patch.object(client, '_ensure_client') as mock_ensure:
            mock_client = AsyncMock()
            mock_client.request.return_value = mock_response
            mock_ensure.return_value = mock_client
            
            await client.search_photos("test")
            
            assert client.last_rate_limit["limit"] == "200"
            assert client.last_rate_limit["remaining"] == "199"
            assert client.last_rate_limit["reset"] == "3600"
    
    @pytest.mark.asyncio
    async def test_auth_error(self, client):
        """测试异步认证错误。"""
        mock_response = Mock()
        mock_response.is_success = False
        mock_response.status_code = 401
        mock_response.url = "https://api.pexels.com/v1/search"
        mock_response.headers = {}
        mock_response.text = "Unauthorized"
        mock_response.json.return_value = {"error": "Invalid API key"}
        
        with patch.object(client, '_ensure_client') as mock_ensure:
            mock_client = AsyncMock()
            mock_client.request.return_value = mock_response
            mock_ensure.return_value = mock_client
            
            with pytest.raises(PexelsAuthError) as exc_info:
                await client.search_photos("test")
            
            assert exc_info.value.status_code == 401
            assert "Invalid API key" in exc_info.value.message
    
    @pytest.mark.asyncio
    async def test_rate_limit_error(self, client):
        """测试异步限流错误。"""
        mock_response = Mock()
        mock_response.is_success = False
        mock_response.status_code = 429
        mock_response.url = "https://api.pexels.com/v1/search"
        mock_response.headers = {"Retry-After": "60"}
        mock_response.text = "Too Many Requests"
        mock_response.json.return_value = {"error": "Rate limit exceeded"}
        
        with patch.object(client, '_ensure_client') as mock_ensure:
            mock_client = AsyncMock()
            mock_client.request.return_value = mock_response
            mock_ensure.return_value = mock_client
            
            with pytest.raises(PexelsRateLimitError) as exc_info:
                await client.search_photos("test")
            
            assert exc_info.value.status_code == 429
            assert exc_info.value.retry_after == 60.0
            assert exc_info.value.should_retry() is True
    
    @pytest.mark.asyncio
    async def test_network_error(self, client):
        """测试异步网络错误。"""
        with patch.object(client, '_ensure_client') as mock_ensure:
            mock_client = AsyncMock()
            mock_client.request.side_effect = httpx.RequestError("Network error")
            mock_ensure.return_value = mock_client
            
            with pytest.raises(PexelsApiError) as exc_info:
                await client.search_photos("test")
            
            assert exc_info.value.status_code == 0
            assert "网络请求失败" in exc_info.value.message
    
    def test_async_pagination_iterator_creation(self, client):
        """测试异步分页迭代器创建。"""
        iterator = client.iter_search_photos("cats", max_pages=3)
        
        assert iterator.method_name == "search_photos"
        assert iterator.per_page == 15
        assert iterator.max_pages == 3
        assert iterator.kwargs["query"] == "cats"
    
    @pytest.mark.asyncio
    async def test_async_pagination_iterator_usage(self, client):
        """测试异步分页迭代器使用。"""
        # 模拟多页响应
        responses = []
        for page in range(1, 4):
            response = Mock()
            response.is_success = True
            response.status_code = 200
            response.url = f"https://api.pexels.com/v1/search?page={page}"
            response.headers = {}
            response.json.return_value = {
                "photos": [{"id": i + (page - 1) * 2} for i in range(1, 3)],
                "page": page,
                "per_page": 2,
                "total_results": 6,
            }
            responses.append(response)
        
        with patch.object(client, '_ensure_client') as mock_ensure:
            mock_client = AsyncMock()
            mock_client.request.side_effect = responses
            mock_ensure.return_value = mock_client
            
            iterator = client.iter_search_photos("test", per_page=2, max_pages=3)
            photos = []
            async for photo in iterator:
                photos.append(photo)
            
            assert len(photos) == 6
            assert photos[0]["id"] == 1
            assert photos[-1]["id"] == 6
            assert mock_client.request.call_count == 3
    
    @pytest.mark.asyncio
    async def test_empty_params_filtering(self, client):
        """测试异步空参数过滤。"""
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.status_code = 200
        mock_response.url = "https://api.pexels.com/v1/search"
        mock_response.headers = {}
        mock_response.json.return_value = {"photos": []}
        
        with patch.object(client, '_ensure_client') as mock_ensure:
            mock_client = AsyncMock()
            mock_client.request.return_value = mock_response
            mock_ensure.return_value = mock_client
            
            await client.search_photos("test", orientation=None, size="", color=None)
            
            args, kwargs = mock_client.request.call_args
            params = kwargs["params"]
            
            # 空值应该被过滤掉
            assert "orientation" not in params
            assert "size" not in params
            assert "color" not in params
            assert params["query"] == "test"