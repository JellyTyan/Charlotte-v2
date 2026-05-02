from typing import Any

from pydantic import BaseModel, Field

class CacheItemMetadata(BaseModel):
    file_id: str | None = None
    raw_file_id: str | None = None
    cover: str | None = None
    media_type: str | None = None
    duration: int | None = None
    width: int | None = None
    height: int | None = None
    is_blurred: bool | None = None

class CacheMetadata(BaseModel):
    title: str | None = None
    description: str | None = None
    author: str | None = None
    duration: int | None = None
    cover: str | None = None
    full_cover: str | None = None
    width: int | None = None
    height: int | None = None
    is_blurred: bool | None = None
    items: list[CacheItemMetadata] = Field(default_factory=list)

class MediaCacheDTO(BaseModel):
    cache_key: str
    telegram_file_id: str | None = None
    telegram_document_file_id: str | None = None
    media_type: str
    platform: str
    data: CacheMetadata = Field(default_factory=CacheMetadata)