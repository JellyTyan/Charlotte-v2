from aiogram import Bot
from aiogram.types import LabeledPrice

class PaymentService:
    @staticmethod
    async def create_single_download_invoice(chat_id: int, payload: str, provider_token: str = ""):
        return {
            "chat_id": chat_id,
            "title": "Premium Download",
            "description": "Unlock high-quality download (>100MB) for this video.",
            "payload": payload,
            "provider_token": provider_token,
            "currency": "XTR",
            "prices": [LabeledPrice(label="Premium Video", amount=5)],
            "start_parameter": "premium-download"
        }
