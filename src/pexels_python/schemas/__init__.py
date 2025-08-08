# -*- coding: utf-8 -*-
"""类型模式导出。仅用于类型提示，运行时不做强校验。"""
from .common import Photo, PhotoSrc, Video, VideoFile, VideoPicture, VideoUser
from .photos import CuratedPhotosResponse, SearchPhotosResponse
from .videos import PopularVideosResponse, SearchVideosResponse

__all__ = [
    # 通用
    "Photo",
    "PhotoSrc",
    "Video",
    "VideoFile",
    "VideoPicture",
    "VideoUser",
    # 照片
    "SearchPhotosResponse",
    "CuratedPhotosResponse",
    # 视频
    "SearchVideosResponse",
    "PopularVideosResponse",
]
