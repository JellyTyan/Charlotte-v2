from aiogram import Bot
from aiogram.types import LabeledPrice

class PaymentService:
    @staticmethod
    async def create_single_download_invoice(chat_id: int, payload: str, provider_token: str = ""):
        return {
            "chat_id": chat_id,
            "title": "🚀 Support Heavy Download",
            "description": "This large file (>100MB) requires extra server resources. Your support helps keep Charlotte running for everyone!",
            "payload": payload,
            "provider_token": provider_token,
            "currency": "XTR",
            "prices": [LabeledPrice(label="Support Download", amount=5)],
            "start_parameter": "support-download"
        }
