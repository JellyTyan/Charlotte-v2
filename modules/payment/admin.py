import logging
from aiogram import Router, Bot
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from storage.db.crud import get_global_settings, update_global_settings, get_payment_by_charge_id, update_payment_status

admin_router = Router(name="payment_admin")
logger = logging.getLogger(__name__)

@admin_router.message(Command("add_supporter"))
async def add_supporter_command(message: Message, db_session: AsyncSession):
    if message.from_user.id != settings.ADMIN_ID:
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Usage: /add_supporter <name>")
        return

    supporter_name = args[1].strip()

    settings = await get_global_settings(db_session)
    supporters = settings.get("supporters", [])

    if supporter_name in supporters:
        await message.answer(f"⚠️ {supporter_name} is already in the supporters list.")
        return

    supporters.append(supporter_name)
    await update_global_settings(db_session, "supporters", supporters)

    await message.answer(f"✅ Added {supporter_name} to supporters list!")

@admin_router.message(Command("remove_supporter"))
async def remove_supporter_command(message: Message, db_session: AsyncSession):
    if message.from_user.id != settings.ADMIN_ID:
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Usage: /remove_supporter <name>")
        return

    supporter_name = args[1].strip()

    settings = await get_global_settings(db_session)
    supporters = settings.get("supporters", [])

    if supporter_name not in supporters:
        await message.answer(f"⚠️ {supporter_name} is not in the supporters list.")
        return

    supporters.remove(supporter_name)
    await update_global_settings(db_session, "supporters", supporters)

    await message.answer(f"✅ Removed {supporter_name} from supporters list!")

@admin_router.message(Command("list_supporters"))
async def list_supporters_command(message: Message, db_session: AsyncSession):
    if message.from_user.id != settings.ADMIN_ID:
        return

    settings = await get_global_settings(db_session)
    supporters = settings.get("supporters", [])

    if not supporters:
        await message.answer("💝 No supporters yet.")
        return

    text = "💝 <b>Supporters List:</b>\n\n"
    for idx, supporter in enumerate(supporters, 1):
        text += f"{idx}. {supporter}\n"

    await message.answer(text, parse_mode=ParseMode.HTML)

@admin_router.message(Command("refund"))
async def refund_command(message: Message, bot: Bot, db_session: AsyncSession):
    if message.from_user.id != settings.ADMIN_ID:
        return

    args = message.text.split()
    if len(args) < 2:
        await message.answer(
            "Usage:\n"
            "• `/refund <telegram_payment_charge_id>` (if payment exists in database)\n"
            "• `/refund <telegram_payment_charge_id> <user_id>` (if payment not found in database)",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    charge_id = args[1].strip()
    user_id = None
    if len(args) >= 3:
        try:
            user_id = int(args[2].strip())
        except ValueError:
            await message.answer("❌ User ID must be an integer.")
            return

    payment = await get_payment_by_charge_id(db_session, charge_id)

    if not payment:
        if not user_id:
            await message.answer(
                "❌ Payment not found in database.\n"
                "To attempt a refund for a payment not in the database, please specify the User ID:\n"
                "Usage: `/refund <telegram_payment_charge_id> <user_id>`",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        try:
            await bot.refund_star_payment(
                user_id=user_id,
                telegram_payment_charge_id=charge_id
            )
            await message.answer(
                f"✅ Successfully refunded payment <code>{charge_id}</code> to user <code>{user_id}</code> (directly, bypassed DB)",
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            logger.error(f"Direct refund failed: {e}")
            await message.answer(f"❌ Refund failed: {e}")
        return

    if payment.status == "refunded":
        await message.answer("❌ This payment was already refunded")
        return

    try:
        await bot.refund_star_payment(
            payment.user_id,
            telegram_payment_charge_id=charge_id
        )

        await update_payment_status(db_session, charge_id, "refunded")

        await message.answer(f"✅ Refunded {payment.amount} {payment.currency} to user {payment.user_id}")
    except Exception as e:
        logger.error(f"Refund failed: {e}")
        await message.answer(f"❌ Refund failed: {e}")
