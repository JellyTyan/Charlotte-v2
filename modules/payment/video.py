import logging
import asyncio

from aiogram import Router, F, Bot
from aiogram.types import LabeledPrice, Message, PreCheckoutQuery
from sqlalchemy.ext.asyncio import AsyncSession

from storage.db.crud import create_payment_log, update_payment_status
from utils.url_cache import get_url

video_payment_router = Router(name="payment_video")
logger = logging.getLogger(__name__)

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

@video_payment_router.pre_checkout_query(lambda query: query.invoice_payload.startswith("yt_"))
async def video_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    # Verify hash is still in cache before taking payment
    payload = pre_checkout_query.invoice_payload
    parts = payload.split("_")
    if len(parts) >= 5:
        url_hash = parts[1]
        url = get_url(url_hash)
        if not url:
            await pre_checkout_query.answer(ok=False, error_message="Link expired. Please request the download again.")
            return
            
    await pre_checkout_query.answer(ok=True)

@video_payment_router.message(F.successful_payment, lambda msg: msg.successful_payment.invoice_payload.startswith("yt_"))
async def video_successful_payment(message: Message, bot: Bot, db_session: AsyncSession):
    payment = message.successful_payment
    payload = payment.invoice_payload

    logger.info(f"Successful video payment: {payment.total_amount} {payment.currency} from {message.from_user.id}")

    await create_payment_log(
        session=db_session,
        user_id=message.from_user.id,
        amount=payment.total_amount,
        currency=payment.currency,
        payload=payload,
        telegram_payment_charge_id=payment.telegram_payment_charge_id,
        provider_payment_charge_id=payment.provider_payment_charge_id
    )

    try:
        parts = payload.split("_")
        if len(parts) < 5:
            logger.error(f"Invalid payload format: {payload}")
            await message.answer("⚠️ Error: Invalid payment data.")
            await bot.refund_star_payment(
                message.from_user.id,
                telegram_payment_charge_id=payment.telegram_payment_charge_id
            )
            await update_payment_status(db_session, payment.telegram_payment_charge_id, "refunded")
            return

        url_hash = parts[1]
        resolution = parts[-1]
        format_choice = "_".join(parts[2:-1])

        if not format_choice.startswith(("youtube_video_", "youtube_audio_")):
            logger.error(f"Invalid format_choice: {format_choice}")
            await message.answer("⚠️ Error: Invalid format data.")
            await bot.refund_star_payment(
                message.from_user.id,
                telegram_payment_charge_id=payment.telegram_payment_charge_id
            )
            await update_payment_status(db_session, payment.telegram_payment_charge_id, "refunded")
            return

        url = get_url(url_hash)
        if not url:
            logger.error(f"URL expired for hash: {url_hash}")
            await message.answer("⚠️ Error: Link expired. Please try again.")
            await bot.refund_star_payment(
                message.from_user.id,
                telegram_payment_charge_id=payment.telegram_payment_charge_id
            )
            await update_payment_status(db_session, payment.telegram_payment_charge_id, "refunded")
            return

        await message.answer("✅ Thank you for supporting Charlotte! Starting download...")

        from modules.services.youtube.handler import process_youtube_download
        
        asyncio.create_task(process_youtube_download(
            message=message,
            url=url,
            format_choice=format_choice,
            resolution=resolution,
            user_id=message.from_user.id,
            db_session=db_session,
            payment_charge_id=payment.telegram_payment_charge_id
        ))

    except Exception as e:
        logger.error(f"Error processing payment payload: {e}")
        await message.answer("❌ Error processing your request. Refunding...")
        try:
            await bot.refund_star_payment(
                message.from_user.id,
                telegram_payment_charge_id=payment.telegram_payment_charge_id
            )
            await update_payment_status(db_session, payment.telegram_payment_charge_id, "refunded")
        except Exception as refund_error:
            logger.error(f"Refund failed: {refund_error}")