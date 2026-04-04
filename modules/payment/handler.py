import logging

from aiogram import Router, F, Bot
from aiogram.enums import ParseMode, parse_mode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, PreCheckoutQuery, ContentType, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from core.config import Config
from storage.db.crud import get_user
from utils.url_cache import get_url
from tasks.task_manager import task_manager
from states import SupportStates

from .service import PaymentService

logger = logging.getLogger(__name__)
payment_router = Router()

@payment_router.message(Command("support"))
async def support_command(message: Message):
    text = (
        "🧡 **Support Charlotte**\n\n"
        "Charlotte is a non-commercial project made by people for people! "
        "I created this bot to help everyone save and share content without restrictions.\n\n"
        "💻 **About hosting costs:**\n"
        "Running Charlotte costs around €12/month for servers, and I cover all expenses from my own pocket. "
        "This bot will always remain free and open for everyone!\n\n"
        "💚 **How you can help:**\n"
        "• Tell your friends about Charlotte\n"
        "• Share the bot in your communities\n"
        "• Leave a small tip to help with hosting costs\n\n"
        "Every bit of support helps keep Charlotte running! Thank you for being part of this community! 🌟"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="☕ Buy Me a Coffee", url="https://buymeacoffee.com/jellytyan"),
            InlineKeyboardButton(text="⭐ Support via Stars", callback_data="support_stars")
        ],
        [
            InlineKeyboardButton(text="💝 Our Supporters", callback_data="view_supporters")
        ]
    ])

    await message.answer(text, parse_mode="Markdown", reply_markup=kb)


@payment_router.callback_query(F.data == "view_supporters")
async def view_supporters_callback(callback: CallbackQuery, bot: Bot):
    """Show list of supporters"""
    await callback.answer()

    from storage.db.crud import get_global_settings
    settings = await get_global_settings()
    supporters = settings.get("supporters", [])

    if not supporters:
        text = "💝 <b>Our Supporters</b>\n\nBe the first to support Charlotte and see your name here!"
    else:
        text = "💝 <b>Our Supporters</b>\n\nThank you to these amazing people who help keep Charlotte running:\n\n"
        for supporter in supporters:
            text += f"• {supporter}\n"
        text += "\n🧡 Your support means everything!"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Back", callback_data="back_to_support")]
    ])

    await bot.send_message(
        callback.from_user.id,
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=kb
    )


@payment_router.callback_query(F.data == "back_to_support")
async def back_to_support_callback(callback: CallbackQuery):
    """Go back to support menu"""
    await callback.answer()
    await callback.message.delete()


@payment_router.message(Command("add_supporter"))
async def add_supporter_command(message: Message):
    """Admin command to add supporter to the list"""
    if message.from_user.id != Config.ADMIN_ID:
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Usage: /add_supporter <name>")
        return

    supporter_name = args[1].strip()

    from storage.db.crud import get_global_settings, update_global_settings
    settings = await get_global_settings()
    supporters = settings.get("supporters", [])

    if supporter_name in supporters:
        await message.answer(f"⚠️ {supporter_name} is already in the supporters list.")
        return

    supporters.append(supporter_name)
    await update_global_settings("supporters", supporters)

    await message.answer(f"✅ Added {supporter_name} to supporters list!")


@payment_router.message(Command("remove_supporter"))
async def remove_supporter_command(message: Message):
    """Admin command to remove supporter from the list"""
    if message.from_user.id != Config.ADMIN_ID:
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Usage: /remove_supporter <name>")
        return

    supporter_name = args[1].strip()

    from storage.db.crud import get_global_settings, update_global_settings
    settings = await get_global_settings()
    supporters = settings.get("supporters", [])

    if supporter_name not in supporters:
        await message.answer(f"⚠️ {supporter_name} is not in the supporters list.")
        return

    supporters.remove(supporter_name)
    await update_global_settings("supporters", supporters)

    await message.answer(f"✅ Removed {supporter_name} from supporters list!")


@payment_router.message(Command("list_supporters"))
async def list_supporters_command(message: Message):
    """Admin command to list all supporters"""
    if message.from_user.id != Config.ADMIN_ID:
        return

    from storage.db.crud import get_global_settings
    settings = await get_global_settings()
    supporters = settings.get("supporters", [])

    if not supporters:
        await message.answer("💝 No supporters yet.")
        return

    text = "💝 <b>Supporters List:</b>\n\n"
    for idx, supporter in enumerate(supporters, 1):
        text += f"{idx}. {supporter}\n"

    await message.answer(text, parse_mode=ParseMode.HTML)

@payment_router.callback_query(F.data == "support_stars")
async def support_stars_callback(callback: CallbackQuery, bot: Bot):
    """Handle Stars support button"""
    await callback.answer()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⭐ 10 Stars", callback_data="support_10"),
            InlineKeyboardButton(text="⭐ 50 Stars", callback_data="support_50")
        ],
        [
            InlineKeyboardButton(text="⭐ 100 Stars", callback_data="support_100"),
            InlineKeyboardButton(text="⭐ Custom", callback_data="support_custom")
        ]
    ])

    await bot.send_message(
        callback.from_user.id,
        "🌟 Choose support amount:\n\nYour support helps keep Charlotte running!",
        reply_markup=kb
    )


@payment_router.callback_query(F.data.startswith("support_"))
async def support_amount_callback(callback: CallbackQuery, bot: Bot, state: FSMContext):
    """Handle support amount selection"""
    await callback.answer()

    if callback.data == "support_custom":
        await bot.send_message(
            callback.from_user.id,
            "💸 Please enter the amount of Stars you'd like to donate (1-100000):"
        )
        await state.set_state(SupportStates.waiting_for_amount)
        return

    amount_map = {
        "support_10": 10,
        "support_50": 50,
        "support_100": 100
    }

    amount = amount_map.get(callback.data, 10)

    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title="🧡 Support Charlotte",
        description=f"Thank you for supporting this free project! Your {amount} Stars help keep the bot running.",
        payload=f"support_{amount}",
        currency="XTR",
        prices=[{"label": "Support", "amount": amount}]
    )


@payment_router.message(SupportStates.waiting_for_amount)
async def process_custom_amount(message: Message, bot: Bot, state: FSMContext):
    """Process custom support amount input"""
    if not message.text:
        return

    try:
        amount = int(message.text.strip())

        if amount < 1 or amount > 100000:
            await message.answer(
                "❌ Amount must be between 1 and 100,000 Stars. Please try again:"
            )
            return

        await state.clear()

        await bot.send_invoice(
            chat_id=message.from_user.id,
            title="🧡 Support Charlotte",
            description=f"Thank you for supporting this free project! Your {amount} Stars help keep the bot running.",
            payload=f"support_{amount}",
            currency="XTR",
            prices=[{"label": "Support", "amount": amount}]
        )

    except ValueError:
        await message.answer(
            "❌ Please enter a valid number between 1 and 100,000:"
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

            await message.answer("✅ Thank you for supporting Charlotte! Starting download...")

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
            await message.answer("❌ Error processing your request. Refunding...")
            try:
                await bot.refund_star_payment(
                    message.from_user.id,
                    telegram_payment_charge_id=payment.telegram_payment_charge_id
                )
                from storage.db import update_payment_status
                await update_payment_status(payment.telegram_payment_charge_id, "refunded")
            except Exception as refund_error:
                logger.error(f"Refund failed: {refund_error}")

    elif payload.startswith("support_"):
        # Handle support donations
        await message.answer(
            "🧡🌟 **Thank you so much!**\n\n"
            "Your support means the world and helps keep Charlotte running for everyone!\n\n"
            "You're awesome! 🚀",
            parse_mode="Markdown"
        )

    elif payload == "subscription":
        # Handle subscription implementation
        pass
