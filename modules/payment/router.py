from aiogram import Router
from .admin import admin_router
from .support import support_router
from .sponsor import sponsor_router
from .video import video_payment_router

payment_router = Router(name="payment")

payment_router.include_routers(
    admin_router,
    support_router,
    sponsor_router,
    video_payment_router
)