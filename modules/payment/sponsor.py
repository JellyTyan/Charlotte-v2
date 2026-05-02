import logging

from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, PreCheckoutQuery, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from storage.db.crud import create_payment_log, grant_sponsorship, get_global_settings, update_global_settings

sponsor_router = Router(name="payment_sponsor")
logger = logging.getLogger(__name__)

@sponsor_router.message(Command("sponsor", "premium"))
async def sponsor_command(message: Message):
    text = (
        "🌟 **Become a Charlotte Sponsor!**\n\n"
        "Unlock Sponsor features for 30 days while helping keep the project alive.\n\n"
        "💎 **Sponsor Benefits:**\n"
        "- Download YT video in high quality\n"
        "- Trim Youtube Video\n"
        "- NSFW content unlocked\n"
        "- Your name gets added to the `/support` wall!\n"
        "- Access to priority download queues\n\n"
        "⭐ Support Charlotte with 100 Stars to become a Sponsor for 30 days!"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ Become Sponsor (100 Stars)", callback_data="sponsor_100")]
    ])

    await message.answer(text, parse_mode="Markdown", reply_markup=kb)

@sponsor_router.callback_query(F.data == "sponsor_100")
async def sponsor_checkout_callback(callback: CallbackQuery, bot: Bot):
    await callback.answer()
    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title="🌟 Charlotte Sponsorship",
        description="Become a sponsor for 30 days! Unlock premium features and get your name on the supporters wall.",
        payload="sponsor_100",
        currency="XTR",
        prices=[{"label": "Sponsorship (30 Days)", "amount": 100}]
    )

@sponsor_router.pre_checkout_query(lambda query: query.invoice_payload == "sponsor_100")
async def sponsor_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)

@sponsor_router.message(F.successful_payment, lambda msg: msg.successful_payment.invoice_payload == "sponsor_100")
async def sponsor_successful_payment(message: Message, db_session: AsyncSession):
    payment = message.successful_payment
    
    logger.info(f"Successful sponsorship payment from {message.from_user.id}")

    await create_payment_log(
        session=db_session,
        user_id=message.from_user.id,
        amount=payment.total_amount,
        currency=payment.currency,
        payload=payment.invoice_payload,
        telegram_payment_charge_id=payment.telegram_payment_charge_id,
        provider_payment_charge_id=payment.provider_payment_charge_id
    )

    # Grant 30 days of premium and add 100 stars donated
    await grant_sponsorship(db_session, message.from_user.id, days=30, stars_donated=100)

    # Add to supporters list
    name = message.from_user.full_name or message.from_user.username or str(message.from_user.id)
    settings = await get_global_settings(db_session)
    supporters = settings.get("supporters", [])
    
    if name not in supporters:
        supporters.append(name)
        await update_global_settings(db_session, "supporters", supporters)

    await message.answer(
        "🎉 **Congratulations!**\n\n"
        "You are now a Charlotte Sponsor! You've unlocked Premium features for 30 days, "
        "and your name has been added to our supporters wall.\n\n"
        "Thank you so much for your support! 💖",
        parse_mode="Markdown"
    )
