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
    text += "Just click the ⭐ button when choosing video quality!\n\n"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 I'm Rich!", callback_data="premium_rich")]
    ])

    await message.answer(text, parse_mode="Markdown", reply_markup=kb)


@payment_router.callback_query(F.data == "premium_rich")
async def premium_rich_callback(callback: CallbackQuery, bot: Bot):
    """Handle 'I'm Rich' button - send invoice for lifetime premium"""
    await callback.answer()

    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title="👑 Lifetime Premium Access",
        description="Unlimited downloads forever! No limits, no restrictions. Be a legend!",
        payload="lifetime_premium",
        currency="XTR",
        prices=[{"label": "Lifetime Premium", "amount": 9999}]
    )


@payment_router.message(Command("refund"))
async def refund_command(message: Message, bot: Bot):
    """Admin command to refund payment by transaction ID"""
    if message.from_user.id != Config.ADMIN_ID:
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Usage: /refund <telegram_payment_charge_id>")
        return

    charge_id = args[1].strip()

    from storage.db import get_payment_by_charge_id
    payment = await get_payment_by_charge_id(charge_id)

    if not payment:
        await message.answer("❌ Payment not found")
        return

    if payment.status == "refunded":
        await message.answer("❌ This payment was already refunded")
        return

    try:
        await bot.refund_star_payment(
            payment.user_id,
            telegram_payment_charge_id=charge_id
        )

        from storage.db import update_payment_status
        await update_payment_status(charge_id, "refunded")

        await message.answer(f"✅ Refunded {payment.amount} {payment.currency} to user {payment.user_id}")
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
                logger.error(f"Invalid payload format: {payload}")
                await message.answer("⚠️ Error: Invalid payment data.")
                # Refund invalid payment
                await bot.refund_star_payment(
                    message.from_user.id,
                    telegram_payment_charge_id=payment.telegram_payment_charge_id
                )
                from storage.db import update_payment_status
                await update_payment_status(payment.telegram_payment_charge_id, "refunded")
                return

            _, url_hash, format_choice = parts

            # Validate format_choice
            if not format_choice.startswith(("youtube_video_", "youtube_audio_")):
                logger.error(f"Invalid format_choice: {format_choice}")
                await message.answer("⚠️ Error: Invalid format data.")
                await bot.refund_star_payment(
                    message.from_user.id,
                    telegram_payment_charge_id=payment.telegram_payment_charge_id
                )
                from storage.db import update_payment_status
                await update_payment_status(payment.telegram_payment_charge_id, "refunded")
                return

            url = get_url(url_hash)
            if not url:
                logger.error(f"URL expired for hash: {url_hash}")
                await message.answer("⚠️ Error: Link expired. Please try again.")
                await bot.refund_star_payment(
                    message.from_user.id,
                    telegram_payment_charge_id=payment.telegram_payment_charge_id
                )
                from storage.db import update_payment_status
                await update_payment_status(payment.telegram_payment_charge_id, "refunded")
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
            await message.answer("❌ Error processing your purchase. Refunding...")
            try:
                await bot.refund_star_payment(
                    message.from_user.id,
                    telegram_payment_charge_id=payment.telegram_payment_charge_id
                )
                from storage.db import update_payment_status
                await update_payment_status(payment.telegram_payment_charge_id, "refunded")
            except Exception as refund_error:
                logger.error(f"Refund failed: {refund_error}")

    elif payload == "lifetime_premium":
        # Grant lifetime premium
        from storage.db.crud import toggle_lifetime_premium
        await toggle_lifetime_premium(user_id=message.from_user.id)

        await message.answer(
            "🎉👑 **Welcome to the Elite Club!**\n\n"
            "You now have **LIFETIME PREMIUM ACCESS**!\n\n"
            "✨ Unlimited downloads\n"
            "🚀 No restrictions\n"
            "🏆 Forever and ever!\n\n"
            "Thank you for your incredible support! 🧡",
            parse_mode="Markdown"
        )

    elif payload == "subscription":
        # Handle subscription implementation
        pass
