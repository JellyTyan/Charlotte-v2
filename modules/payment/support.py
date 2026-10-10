import datetime
import logging

from aiogram import Router, F, Bot
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message,
    PreCheckoutQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)
from sqlalchemy.ext.asyncio import AsyncSession
from fluentogram import TranslatorRunner

from states import SupportStates
from storage.db.crud import (
    get_global_settings,
    update_global_settings,
    create_payment_log,
    get_user,
    add_donation_stars,
)
from utils.effects import answer_with_effect, EFFECT_FIREWORKS
from utils.text_utils import escape_html

support_router = Router(name="payment_support")
logger = logging.getLogger(__name__)


@support_router.message(Command("support"))
async def support_command(message: Message, db_session: AsyncSession, i18n: TranslatorRunner):
    user = await get_user(db_session, message.from_user.id)

    # Format dynamic status display
    progress = (user.stars_donated or 0) % 100 if user else 0
    if user and user.is_lifetime_premium:
        status_text = "\n\n" + i18n.support.status.lifetime()
    elif user and user.is_premium and user.premium_ends:
        date_str = user.premium_ends.strftime("%d.%m.%Y")
        status_text = "\n\n" + i18n.support.status.active(date=date_str, progress=progress)
    else:
        status_text = "\n\n" + i18n.support.status.progress(progress=progress)

    text = i18n.support.text(status=status_text)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=i18n.support.btn.sponsor(), callback_data="support_100")
        ],
        [
            InlineKeyboardButton(text=i18n.support.stars.fifty(), callback_data="support_50"),
            InlineKeyboardButton(text=i18n.support.stars.ten(), callback_data="support_10"),
        ],
        [
            InlineKeyboardButton(text=i18n.support.stars.custom(), callback_data="support_custom"),
            InlineKeyboardButton(text=i18n.support.btn.coffee(), url="https://buymeacoffee.com/jellytyan"),
        ],
        [
            InlineKeyboardButton(text=i18n.support.btn.supporters(), callback_data="view_supporters")
        ]
    ])

    await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=kb)


@support_router.callback_query(F.data == "view_supporters")
async def view_supporters_callback(callback: CallbackQuery, bot: Bot, db_session: AsyncSession, i18n: TranslatorRunner):
    await callback.answer()

    settings = await get_global_settings(db_session)
    supporters = settings.get("supporters", [])

    if not supporters:
        text = i18n.support.wall.empty()
    else:
        supporters_list = "\n".join(f"• {escape_html(s)}" for s in supporters)
        text = i18n.support.wall.text(supporters=supporters_list)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=i18n.support.btn.back(), callback_data="back_to_support")]
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


@support_router.callback_query(F.data.startswith("support_"))
async def support_amount_callback(callback: CallbackQuery, bot: Bot, state: FSMContext, i18n: TranslatorRunner):
    await callback.answer()

    if callback.data == "support_custom":
        await bot.send_message(
            callback.from_user.id,
            i18n.support.custom.prompt()
        )
        await state.set_state(SupportStates.waiting_for_amount)
        return

    amount_map = {
        "support_10": 10,
        "support_50": 50,
        "support_100": 100,
    }

    amount = amount_map.get(callback.data, 100)

    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title=i18n.support.invoice.title(amount=amount),
        description=i18n.support.invoice.desc(amount=amount),
        payload=f"support_{amount}",
        currency="XTR",
        prices=[{"label": "Support", "amount": amount}]
    )


@support_router.message(SupportStates.waiting_for_amount)
async def process_custom_amount(message: Message, bot: Bot, state: FSMContext, i18n: TranslatorRunner):
    if not message.text:
        return

    try:
        amount = int(message.text.strip())

        if amount < 1 or amount > 100000:
            await message.answer(i18n.support.invalid.amount())
            return

        await state.clear()

        await bot.send_invoice(
            chat_id=message.from_user.id,
            title=i18n.support.invoice.title(amount=amount),
            description=i18n.support.invoice.desc(amount=amount),
            payload=f"support_{amount}",
            currency="XTR",
            prices=[{"label": "Support", "amount": amount}]
        )

    except ValueError:
        await message.answer(i18n.support.invalid.number())


@support_router.pre_checkout_query(lambda query: query.invoice_payload.startswith("support_") or query.invoice_payload.startswith("sponsor_"))
async def support_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)


@support_router.message(F.successful_payment, lambda msg: msg.successful_payment.invoice_payload.startswith("support_") or msg.successful_payment.invoice_payload.startswith("sponsor_"))
async def support_successful_payment(message: Message, db_session: AsyncSession, i18n: TranslatorRunner):
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

    stars = payment.total_amount
    earned_months, progress, new_end = await add_donation_stars(
        session=db_session,
        user_id=message.from_user.id,
        stars=stars
    )

    # Add to supporters list
    name = message.from_user.full_name or message.from_user.username or str(message.from_user.id)
    settings = await get_global_settings(db_session)
    supporters = settings.get("supporters", [])
    if name not in supporters:
        supporters.append(name)
        await update_global_settings(db_session, "supporters", supporters)

    user = await get_user(db_session, message.from_user.id)
    if user and user.is_lifetime_premium:
        success_text = i18n.support.success.tip(stars=stars, progress=progress)
    elif earned_months > 0 and new_end:
        date_str = new_end.strftime("%d.%m.%Y")
        days = earned_months * 30
        success_text = i18n.support.success.sponsor(stars=stars, days=days, date=date_str)
    else:
        success_text = i18n.support.success.tip(stars=stars, progress=progress)

    await answer_with_effect(
        message,
        success_text,
        effect_id=EFFECT_FIREWORKS,
        parse_mode=ParseMode.HTML
    )
