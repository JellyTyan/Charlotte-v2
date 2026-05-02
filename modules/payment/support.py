import logging

from aiogram import Router, F, Bot
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, PreCheckoutQuery, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from states import SupportStates
from storage.db.crud import get_global_settings, create_payment_log

support_router = Router(name="payment_support")
logger = logging.getLogger(__name__)

@support_router.message(Command("support"))
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

@support_router.callback_query(F.data == "view_supporters")
async def view_supporters_callback(callback: CallbackQuery, bot: Bot, db_session: AsyncSession):
    await callback.answer()

    settings = await get_global_settings(db_session)
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

@support_router.callback_query(F.data == "back_to_support")
async def back_to_support_callback(callback: CallbackQuery):
    await callback.answer()
    await callback.message.delete()

@support_router.callback_query(F.data == "support_stars")
async def support_stars_callback(callback: CallbackQuery, bot: Bot):
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

@support_router.callback_query(F.data.startswith("support_"))
async def support_amount_callback(callback: CallbackQuery, bot: Bot, state: FSMContext):
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

@support_router.message(SupportStates.waiting_for_amount)
async def process_custom_amount(message: Message, bot: Bot, state: FSMContext):
    if not message.text:
        return

    try:
        amount = int(message.text.strip())

        if amount < 1 or amount > 100000:
            await message.answer("❌ Amount must be between 1 and 100,000 Stars. Please try again:")
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
        await message.answer("❌ Please enter a valid number between 1 and 100,000:")

@support_router.pre_checkout_query(lambda query: query.invoice_payload.startswith("support_"))
async def support_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)

@support_router.message(F.successful_payment, lambda msg: msg.successful_payment.invoice_payload.startswith("support_"))
async def support_successful_payment(message: Message, db_session: AsyncSession):
    payment = message.successful_payment
    payload = payment.invoice_payload

    logger.info(f"Successful support payment: {payment.total_amount} {payment.currency} from {message.from_user.id}")

    await create_payment_log(
        session=db_session,
        user_id=message.from_user.id,
        amount=payment.total_amount,
        currency=payment.currency,
        payload=payload,
        telegram_payment_charge_id=payment.telegram_payment_charge_id,
        provider_payment_charge_id=payment.provider_payment_charge_id
    )

    await message.answer(
        "🧡🌟 **Thank you so much!**\n\n"
        "Your support means the world and helps keep Charlotte running for everyone!\n\n"
        "You're awesome! 🚀",
        parse_mode="Markdown"
    )
