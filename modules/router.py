from aiogram import Router
from middlewares.service_use import ServiceUseMiddleware

service_router = Router()

service_router.message.middleware(ServiceUseMiddleware())
