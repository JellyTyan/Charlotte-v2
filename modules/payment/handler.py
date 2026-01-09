import logging
import json

from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, PreCheckoutQuery, ContentType, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from core.config import Config
from storage.db.crud import get_user
from utils.url_cache import get_url
from tasks.task_manager import task_manager

from .service import PaymentService

logger = logging.getLogger(__name__)
payment_router = Router()

@payment_router.message(Command("premium"))
async def premium_command(message: Message):
    user = await get_user(message.from_user.id)
    is_premium = user.is_premium if user else False

    text = f"🌟 **Premium Downloads**\n\n"
    text += "You can purchase high-quality YouTube videos (>100MB) for 5 Stars each.\n"
    text += "Just click the ⭐ button when choosing video quality!"

    await message.answer(text, parse_mode="Markdown")


@payment_router.message(Command("refund"))
async def refund_command(message: Message, bot: Bot):
    """Refund last successful payment for user"""
    from storage.db import get_last_payment
    
    payment = await get_last_payment(message.from_user.id)
    
    if not payment:
        await message.answer("❌ No payments found")
        return
    
    if payment.status == "refunded":
        await message.answer("❌ This payment was already refunded")
        return
    
    try:
        await bot.refund_star_payment(
            message.from_user.id,
            telegram_payment_charge_id=payment.telegram_payment_charge_id
        )
        
        from storage.db import update_payment_status
        await update_payment_status(payment.telegram_payment_charge_id, "refunded")
        
        await message.answer(f"✅ Refunded {payment.amount} {payment.currency}")
    except Exception as e:
        logger.error(f"Refund failed: {e}")
        await message.answer(f"❌ Refund failed: {e}")


@payment_router.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)


@payment_router.message(F.successful_payment)
async def successful_payment_handler(message: Message, bot: Bot):
    payment = message.successful_payment
    payload = payment.invoice_payload

    logger.info(f"Successful payment: {payment.total_amount} {payment.currency} from {message.from_user.id}")

    # Log payment to database
    from storage.db import create_payment_log
    await create_payment_log(
        user_id=message.from_user.id,
        amount=payment.total_amount,
        currency=payment.currency,
        payload=payload,
        telegram_payment_charge_id=payment.telegram_payment_charge_id,
        provider_payment_charge_id=payment.provider_payment_charge_id
    )

    if payload.startswith("yt_"):
        # Format: yt_URLHASH_FORMAT
        try:
            parts = payload.split("_", 2)
            if len(parts) < 3:
                await message.answer("⚠️ Error: Invalid payment data.")
                return

            _, url_hash, format_choice = parts
            url = get_url(url_hash)

            if not url:
                await message.answer("⚠️ Error: Link expired. Please try again.")
                return

            await message.answer("✅ Payment received! Starting download...")

            # Import here to avoid circular dep
            from modules.youtube.handler import download_youtube_media

            await task_manager.add_task(
                message.from_user.id,
                download_youtube_media(
                    message,
                    url,
                    format_choice,
                    message.from_user.id,
                    payment.telegram_payment_charge_id
                ),
                message
            )

        except Exception as e:
            logger.error(f"Error processing payment payload: {e}")
            await message.answer("❌ Error processing your purchase. Please contact support.")

    elif payload == "subscription":
        # Handle subscription implementation
        pass
