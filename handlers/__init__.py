from aiogram import Router
from . import start, help, settings, cancel, common, saves, chat_moderation, report
from .admin import admin_router

user_router = Router()
user_router.include_router(start.router)
user_router.include_router(help.router)
user_router.include_router(settings.router)
user_router.include_router(chat_moderation.router)
user_router.include_router(cancel.router)
user_router.include_router(common.router)
user_router.include_router(saves.router)
user_router.include_router(report.router)
