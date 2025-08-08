# -*- coding: utf-8 -*-
"""公共类型与工具（仅类型声明）。

为开发者提供静态类型支持，运行时并不强制转换。
"""
from __future__ import annotations

from typing import TypedDict


class PhotoSrc(TypedDict, total=False):
    original: str
    large2x: str
    large: str
    medium: str
    small: str
    portrait: str
    landscape: str
    tiny: str


class Photo(TypedDict):
    id: int
    width: int
    height: int
    url: str
    photographer: str
    photographer_url: str
    photographer_id: int
    avg_color: str
    src: PhotoSrc
    liked: bool
    alt: str


class VideoUser(TypedDict):
    id: int
    name: str
    url: str


class VideoFile(TypedDict, total=False):
    id: int
    quality: str  # e.g. hd | sd | hls
    file_type: str  # e.g. video/mp4
    width: int
    height: int
    fps: float | int
    link: str


class VideoPicture(TypedDict):
    id: int
    nr: int
    picture: str


class Video(TypedDict):
    id: int
    width: int
    height: int
    url: str
    image: str
    duration: int
    user: VideoUser
    video_files: list[VideoFile]
    video_pictures: list[VideoPicture]
