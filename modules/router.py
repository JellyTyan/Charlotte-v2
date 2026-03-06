from aiogram import Router
from middlewares.service_use import ServiceUseMiddleware
from middlewares.service_block import ServiceBlockMiddleware

service_router = Router()

service_router.message.middleware(ServiceUseMiddleware())
service_router.message.middleware(ServiceBlockMiddleware())
