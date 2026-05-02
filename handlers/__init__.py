from aiogram import Router
from . import start, help, settings, cancel
from .admin import admin_router

user_router = Router()
user_router.include_router(start.router)
user_router.include_router(help.router)
user_router.include_router(settings.router)
user_router.include_router(cancel.router)
