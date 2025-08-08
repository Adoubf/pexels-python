# -*- coding: utf-8 -*-
"""测试分页迭代器功能。"""
import pytest
from unittest.mock import Mock, patch

from pexels_python.core.pagination import (
    PaginationIterator,
    iter_search_photos,
    iter_curated_photos,
    iter_search_videos,
    iter_popular_videos,
)
from pexels_python import PexelsClient


class TestPaginationIterator:
    """PaginationIterator 测试类。"""
    
    @pytest.fixture
    def client(self):
        """创建测试客户端。"""
        return PexelsClient(api_key="test_api_key")
    
    @pytest.fixture
    def mock_responses(self):
        """创建模拟多页响应。"""
        responses = []
        for page in range(1, 4):
            response = {
                "photos": [
                    {"id": i + (page - 1) * 3, "url": f"photo_{i + (page - 1) * 3}"}
                    for i in range(1, 4)
                ],
                "page": page,
                "per_page": 3,
                "total_results": 9,
            }
            if page < 3:
                response["next_page"] = f"https://api.pexels.com/v1/search?page={page + 1}"
            responses.append(response)
        return responses
    
    def test_iterator_initialization(self, client):
        """测试迭代器初始化。"""
        iterator = PaginationIterator(
            client,
            "search_photos",
            query="cats",
            per_page=10,
            max_pages=5,
        )
        
        assert iterator.client == client
        assert iterator.method_name == "search_photos"
        assert iterator.per_page == 10
        assert iterator.max_pages == 5
        assert iterator.kwargs["query"] == "cats"
        assert iterator.current_page == 1
        assert iterator.pages_fetched == 0
        assert iterator.items_yielded == 0
    
    def test_iterator_invalid_method(self, client):
        """测试无效方法名。"""
        with pytest.raises(ValueError, match="方法 invalid_method 不存在或不可调用"):
            PaginationIterator(client, "invalid_method")
    
    def test_iterator_basic_usage(self, client, mock_responses):
        """测试基本迭代功能。"""
        with patch.object(client, 'search_photos', side_effect=mock_responses):
            iterator = PaginationIterator(
                client,
                "search_photos",
                query="test",
                per_page=3,
                max_pages=3,
            )
            
            items = list(iterator)
            
            assert len(items) == 9
            assert items[0]["id"] == 1
            assert items[-1]["id"] == 9
            assert iterator.pages_fetched == 3
            assert iterator.items_yielded == 9
    
    def test_iterator_max_pages_limit(self, client, mock_responses):
        """测试最大页数限制。"""
        with patch.object(client, 'search_photos', side_effect=mock_responses):
            iterator = PaginationIterator(
                client,
                "search_photos",
                query="test",
                per_page=3,
                max_pages=2,  # 限制为 2 页
            )
            
            items = list(iterator)
            
            assert len(items) == 6  # 只有 2 页的数据
            assert iterator.pages_fetched == 2
            assert iterator.items_yielded == 6
    
    def test_iterator_empty_response(self, client):
        """测试空响应处理。"""
        empty_response = {
            "photos": [],
            "page": 1,
            "per_page": 15,
            "total_results": 0,
        }
        
        with patch.object(client, 'search_photos', return_value=empty_response):
            iterator = PaginationIterator(client, "search_photos", query="test")
            
            items = list(iterator)
            
            assert len(items) == 0
            assert iterator.pages_fetched == 1
            assert iterator.items_yielded == 0
    
    def test_iterator_partial_page(self, client):
        """测试不完整页面处理。"""
        responses = [
            {
                "photos": [{"id": 1}, {"id": 2}],  # 只有 2 个项目，少于 per_page
                "page": 1,
                "per_page": 5,
                "total_results": 2,
            }
        ]
        
        with patch.object(client, 'search_photos', side_effect=responses):
            iterator = PaginationIterator(client, "search_photos", query="test", per_page=5)
            
            items = list(iterator)
            
            assert len(items) == 2
            assert iterator.pages_fetched == 1
    
    def test_iterator_stats(self, client, mock_responses):
        """测试统计信息。"""
        with patch.object(client, 'search_photos', side_effect=mock_responses):
            iterator = PaginationIterator(
                client,
                "search_photos",
                query="test",
                per_page=3,
                max_pages=2,
            )
            
            # 消费一些项目
            items = []
            for i, item in enumerate(iterator):
                items.append(item)
                if i >= 4:  # 获取前 5 个项目
                    break
            
            stats = iterator.get_stats()
            
            assert stats["current_page"] == 2
            assert stats["pages_fetched"] == 2
            assert stats["items_yielded"] == 5
            assert stats["total_results"] == 9
            assert stats["per_page"] == 3
            assert stats["max_pages"] == 2
    
    def test_iterator_data_key_detection(self, client):
        """测试数据键检测。"""
        # 测试视频响应
        video_response = {
            "videos": [{"id": 1}, {"id": 2}],
            "page": 1,
            "per_page": 15,
        }
        
        with patch.object(client, 'search_videos', return_value=video_response):
            iterator = PaginationIterator(client, "search_videos", query="test")
            
            items = list(iterator)
            
            assert len(items) == 2
            assert items[0]["id"] == 1
    
    def test_iterator_error_handling(self, client):
        """测试错误处理。"""
        with patch.object(client, 'search_photos', side_effect=Exception("API Error")):
            iterator = PaginationIterator(client, "search_photos", query="test")
            
            with pytest.raises(Exception, match="API Error"):
                list(iterator)
    
    def test_convenience_functions(self, client):
        """测试便捷函数。"""
        # 测试 iter_search_photos
        iterator = iter_search_photos(client, "cats", per_page=10, max_pages=3)
        assert iterator.method_name == "search_photos"
        assert iterator.kwargs["query"] == "cats"
        assert iterator.per_page == 10
        assert iterator.max_pages == 3
        
        # 测试 iter_curated_photos
        iterator = iter_curated_photos(client, per_page=20)
        assert iterator.method_name == "curated_photos"
        assert iterator.per_page == 20
        
        # 测试 iter_search_videos
        iterator = iter_search_videos(client, "nature", per_page=5)
        assert iterator.method_name == "search_videos"
        assert iterator.kwargs["query"] == "nature"
        assert iterator.per_page == 5
        
        # 测试 iter_popular_videos
        iterator = iter_popular_videos(client, per_page=15)
        assert iterator.method_name == "popular_videos"
        assert iterator.per_page == 15
    
    def test_iterator_next_page_detection(self, client):
        """测试下一页检测逻辑。"""
        responses = [
            {
                "photos": [{"id": 1}, {"id": 2}, {"id": 3}],
                "page": 1,
                "per_page": 3,
                "total_results": 6,
                "next_page": "https://api.pexels.com/v1/search?page=2",
            },
            {
                "photos": [{"id": 4}, {"id": 5}, {"id": 6}],
                "page": 2,
                "per_page": 3,
                "total_results": 6,
                # 没有 next_page，表示最后一页
            },
        ]
        
        with patch.object(client, 'search_photos', side_effect=responses):
            iterator = PaginationIterator(client, "search_photos", query="test", per_page=3)
            
            items = list(iterator)
            
            assert len(items) == 6
            assert iterator.pages_fetched == 2
    
    def test_iterator_total_results_calculation(self, client):
        """测试总结果数计算。"""
        responses = [
            {
                "photos": [{"id": 1}, {"id": 2}],
                "page": 1,
                "per_page": 2,
                "total_results": 5,
            },
            {
                "photos": [{"id": 3}, {"id": 4}],
                "page": 2,
                "per_page": 2,
                "total_results": 5,
            },
            {
                "photos": [{"id": 5}],  # 最后一页只有 1 个项目
                "page": 3,
                "per_page": 2,
                "total_results": 5,
            },
        ]
        
        with patch.object(client, 'search_photos', side_effect=responses):
            iterator = PaginationIterator(client, "search_photos", query="test", per_page=2)
            
            items = list(iterator)
            
            assert len(items) == 5
            assert iterator.total_results == 5
            assert iterator.pages_fetched == 3