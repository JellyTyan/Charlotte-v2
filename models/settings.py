from typing import List

from pydantic import BaseModel, Field, ConfigDict

class ProfileSettings(BaseModel):
    language: str = "en"
    title_language: str = "en"
    notifications: bool = True
    reactions: bool = False
    negativity: bool = False
    news_spam: bool = False
    bot_sign: bool = True



class MediaSettings(BaseModel):
    caption: bool = False
    translate_caption: bool = False

class MediaSettingsExtra(MediaSettings):
    raw: bool = False

class MusicSettings(BaseModel):
    send_covers: bool = False

class MusicSettingsExtra(MusicSettings):
    lossless: bool = False


class YoutubeSettings(MediaSettings):
    simple: bool = True
    ui_mode: str = "simple"


class ServicesSettings(BaseModel):
    youtube: YoutubeSettings = YoutubeSettings()
    tiktok: MediaSettings = MediaSettings()
    instagram: MediaSettings = MediaSettings()
    twitter: MediaSettingsExtra = MediaSettingsExtra()
    pinterest: MediaSettingsExtra = MediaSettingsExtra()
    pixiv: MediaSettingsExtra = MediaSettingsExtra()
    reddit: MediaSettings = MediaSettings()

    spotify: MusicSettingsExtra = MusicSettingsExtra()
    deezer: MusicSettingsExtra = MusicSettingsExtra()
    applemusic: MusicSettingsExtra = MusicSettingsExtra()
    ytmusic: MusicSettings = MusicSettings()
    soundcloud: MusicSettings = MusicSettings()


class ExperimentalSettings(BaseModel):
    ephemeral_messages: bool = False


class UserSettingsJson(BaseModel):
    model_config = ConfigDict(extra="ignore")
    version: int = 1
    profile: ProfileSettings = ProfileSettings()
    services: ServicesSettings = ServicesSettings()
    experimental: ExperimentalSettings = ExperimentalSettings()


class ChatProfileSettings(BaseModel):
    language: str = "en"
    title_language: str = "en"
    notifications: bool = True
    reactions: bool = True
    negativity: bool = False
    allow_playlists: bool = True
    allow_nsfw: bool = False
    blocked_services: set[str] = Field(default_factory=set)
    banned_users: set[int] = Field(default_factory=set)
    news_spam: bool = False
    bot_sign: bool = True


class ChatServicesSettings(BaseModel):
    preferred_services: List[str] = []
    blocked_services: List[str] = []

    youtube: MediaSettings = MediaSettings()
    tiktok: MediaSettings = MediaSettings()
    instagram: MediaSettings = MediaSettings()
    twitter: MediaSettingsExtra = MediaSettingsExtra()
    pinterest: MediaSettingsExtra = MediaSettingsExtra()
    pixiv: MediaSettingsExtra = MediaSettingsExtra()
    reddit: MediaSettings = MediaSettings()

    spotify: MusicSettingsExtra = MusicSettingsExtra()
    deezer: MusicSettingsExtra = MusicSettingsExtra()
    applemusic: MusicSettingsExtra = MusicSettingsExtra()
    ytmusic: MusicSettings = MusicSettings()
    soundcloud: MusicSettings = MusicSettings()


class ChatSettingsJson(BaseModel):
    model_config = ConfigDict(extra="ignore")
    version: int = 1
    profile: ChatProfileSettings = ChatProfileSettings()
    services: ChatServicesSettings = ChatServicesSettings()
