from aiogram import Router
from middlewares.service_use import ServiceUseMiddleware
from middlewares.service_block import ServiceBlockMiddleware
from middlewares.reaction import ReactionMiddleware

from .youtube.handler import youtube_router
from .ytmusic.handler import ytmusic_router
from .twitter.handler import twitter_router
from .twitch.handler import twitch_router
from .tiktok.handler import tiktok_router
from .spotify.handler import spotify_router
from .soundcloud.handler import soundcloud_router
from .reddit.handler import reddit_router
from .pixiv.handler import pixiv_router
from .pinterest.handler import pinterest_router
from .nicovideo.handler import nicovideo_router
from .instagram.handler import insta_router
from .deezer.handler import deezer_router
from .bluesky.handler import bluesky_router
from.apple_music.handler import apple_router

service_router = Router()

service_router.message.middleware(ServiceUseMiddleware())
service_router.message.middleware(ServiceBlockMiddleware())
service_router.message.middleware(ReactionMiddleware())

service_router.include_router(youtube_router)
service_router.include_router(ytmusic_router)
service_router.include_router(twitter_router)
service_router.include_router(twitch_router)
service_router.include_router(tiktok_router)
service_router.include_router(spotify_router)
service_router.include_router(soundcloud_router)
service_router.include_router(reddit_router)
service_router.include_router(pixiv_router)
service_router.include_router(pinterest_router)
service_router.include_router(nicovideo_router)
service_router.include_router(insta_router)
service_router.include_router(deezer_router)
service_router.include_router(bluesky_router)
service_router.include_router(apple_router)