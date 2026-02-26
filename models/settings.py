from pydantic import BaseModel, Field
from typing import List


class ProfileSettings(BaseModel):
    language: str = "en"
    title_language: str = "en"
    notifications: bool = True
    reactions: bool = False


class MediaSettings(BaseModel):
    caption: bool = False
    translate_caption: bool = False
    raw: bool = False


class MusicSettings(BaseModel):
    send_covers: bool = False
    lossless: bool = False


class ServicesSettings(BaseModel):
    youtube: MediaSettings = MediaSettings()
    tiktok: MediaSettings = MediaSettings()
    instagram: MediaSettings = MediaSettings()
    twitter: MediaSettings = MediaSettings()
    pinterest: MediaSettings = MediaSettings()
    pixiv: MediaSettings = MediaSettings()
    reddit: MediaSettings = MediaSettings()

    spotify: MusicSettings = MusicSettings()
    deezer: MusicSettings = MusicSettings()
    apple_music: MusicSettings = MusicSettings()
    youtube_music: MusicSettings = MusicSettings()
    soundcloud: MusicSettings = MusicSettings()


class UserSettingsJson(BaseModel):
    version: int = 1
    profile: ProfileSettings = ProfileSettings()
    services: ServicesSettings = ServicesSettings()


class ChatProfileSettings(BaseModel):
    language: str = "en"
    title_language: str = "en"
    notifications: bool = True
    reactions: bool = True
    allow_playlists: bool = True
    blocked_services: set[str] = Field(default_factory=set)


class ChatServicesSettings(BaseModel):
    preferred_services: List[str] = []
    blocked_services: List[str] = []

    youtube: MediaSettings = MediaSettings()
    tiktok: MediaSettings = MediaSettings()
    instagram: MediaSettings = MediaSettings()
    twitter: MediaSettings = MediaSettings()
    pinterest: MediaSettings = MediaSettings()
    pixiv: MediaSettings = MediaSettings()
    reddit: MediaSettings = MediaSettings()

    spotify: MusicSettings = MusicSettings()
    deezer: MusicSettings = MusicSettings()
    apple_music: MusicSettings = MusicSettings()
    youtube_music: MusicSettings = MusicSettings()
    soundcloud: MusicSettings = MusicSettings()


class ChatSettingsJson(BaseModel):
    version: int = 1
    profile: ChatProfileSettings = ChatProfileSettings()
    services: ChatServicesSettings = ChatServicesSettings()
