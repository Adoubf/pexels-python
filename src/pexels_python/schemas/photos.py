# -*- coding: utf-8 -*-
"""照片相关的响应模式（类型声明）。"""
from __future__ import annotations

from typing import NotRequired, TypedDict

from .common import Photo


class SearchPhotosResponse(TypedDict, total=False):
    total_results: int
    page: int
    per_page: int
    photos: list[Photo]
    next_page: NotRequired[str]
    prev_page: NotRequired[str]


class CuratedPhotosResponse(TypedDict, total=False):
    page: int
    per_page: int
    photos: list[Photo]
    next_page: NotRequired[str]
    prev_page: NotRequired[str]
