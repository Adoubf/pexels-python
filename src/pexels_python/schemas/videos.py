# -*- coding: utf-8 -*-
"""视频相关的响应模式（类型声明）。"""
from __future__ import annotations

from typing import NotRequired, TypedDict

from .common import Video


class SearchVideosResponse(TypedDict, total=False):
    total_results: int
    page: int
    per_page: int
    url: NotRequired[str]
    videos: list[Video]
    next_page: NotRequired[str]


class PopularVideosResponse(TypedDict, total=False):
    page: int
    per_page: int
    videos: list[Video]
    url: NotRequired[str]
    next_page: NotRequired[str]
