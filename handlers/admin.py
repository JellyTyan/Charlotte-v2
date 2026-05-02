import logging
import datetime
import asyncio
from typing import Optional

from aiogram import types, Bot
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import (
    InaccessibleMessage,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    FSInputFile,
    ReplyKeyboardRemove
)
from aiogram.exceptions import TelegramRetryAfter, TelegramForbiddenError, TelegramBadRequest
from fluentogram import TranslatorHub, TranslatorRunner
from sqlalchemy.ext.asyncio import AsyncSession

from storage.db.crud import (
    get_user_counts,
    get_top_services,
    get_status_stats,
    toggle_lifetime_premium,
    get_premium_and_donation_stats,
    ban_user,
    unban_user,
    list_of_banned_users,
    get_global_settings,
    update_global_settings,
    get_list_user_ids,
    get_news_subscribers_ids,
    get_all_chat_ids,
    get_db_overview_stats,
    get_cache_counts_by_service
)
from states import NewsSpamGroup
from utils import escape_markdown

from aiogram import Router
from middlewares.admin_check import AdminMiddleware

logger = logging.getLogger(__name__)

admin_router = Router()
admin_router.message.middleware(AdminMiddleware())
admin_router.callback_query.middleware(AdminMiddleware())

class AdminStates(StatesGroup):
    waiting_for_user_id = State()
    waiting_for_user_id_ban = State()
    waiting_for_user_id_pardon = State()

# === Keyboards ===
statistic_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👯 Global Stats", callback_data="admin_panel_statistic"),
            InlineKeyboardButton(text="📈 Top Services", callback_data="statistic_top_services"),
        ],
        [
            InlineKeyboardButton(text="😔 User Premium stats", callback_data="statistic_premium_stats"),
            InlineKeyboardButton(text="📊 Service Stats", callback_data="statistic_service_usage"),
        ],
        [
            InlineKeyboardButton(text="🗑 Clean Old Stats", callback_data="statistic_clean_old"),
            InlineKeyboardButton(text="🔙 Back", callback_data="admin_panel_back"),
        ],
    ])

panel_kb = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="✡ Premium", callback_data="admin_panel_premium"),
        InlineKeyboardButton(text="📈 Statistic", callback_data="admin_panel_statistic"),
    ],
    [
        InlineKeyboardButton(text="😔 Ban List", callback_data="admin_panel_banlist"),
        InlineKeyboardButton(text="🐀 Bot Settings", callback_data="admin_panel_bot_settings"),
    ],
    [
        InlineKeyboardButton(text="📝 Get Logs", callback_data="admin_panel_get_logs"),
        InlineKeyboardButton(text="📰 News spam", callback_data="admin_panel_news"),
    ],
])

# === Main page ===
@admin_router.message(Command("admin_panel"))
async def admin_panel(message: types.Message, state: FSMContext) -> None:
    await state.update_data(current_admin_screen=None)

    await message.answer(
        (
            "Hey, Jelly! Here's your buttons to play with\n"
        ),
        parse_mode=ParseMode.HTML,
        reply_markup=panel_kb,
    )

@admin_router.callback_query(lambda c: c.data == "admin_panel_back")
async def settings_back(callback: CallbackQuery, state: FSMContext):
    await state.update_data(current_admin_screen="main")

    text = ("Hey, Jelly! Here's your buttons to play with\n")

    if isinstance(callback.message, types.InaccessibleMessage) or callback.message is None:
        if callback.bot is None:
            return
        await callback.bot.send_message(callback.from_user.id, text,
            parse_mode=ParseMode.HTML,
            reply_markup=panel_kb,)
    else:
        await callback.message.edit_text(text,
            parse_mode=ParseMode.HTML,
            reply_markup=panel_kb,
        )
    await callback.answer()

# === Statistic ===
@admin_router.callback_query(lambda c: c.data == "admin_panel_statistic")
async def admin_panel_stats(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    data = await state.get_data()
    if data.get("current_admin_screen") == "statistics":
        await callback.answer("Nothing happened!", cache_time=1)
        return

    await state.update_data(current_admin_screen="statistics")

    user_count = await get_user_counts(db_session)
    status_stats = await get_status_stats(db_session)
    db_overview = await get_db_overview_stats(db_session)

    total_requests = status_stats['complete'] + status_stats['error']
    success_rate = (status_stats['complete'] / total_requests * 100) if total_requests > 0 else 0

    total_users = db_overview['total_users']
    total_chats = db_overview['total_chats']
    inactive_users = db_overview['inactive_users']
    inactive_users_pct = (inactive_users / total_users * 100) if total_users > 0 else 0

    text = (
        "📊 <b>Global Statistics</b>\n\n"
        "<b>🗄 Database</b>\n"
        f"  👤 Users: <b>{total_users:,}</b>\n"
        f"  └ Inactive (30d+): {inactive_users:,} ({inactive_users_pct:.1f}%)\n"
        f"  💬 Chats: <b>{total_chats:,}</b>\n\n"
        "<b>👥 Active Users:</b>\n"
        f"  Today: {user_count['today']}\n"
        f"  Yesterday: {user_count['yesterday']}\n"
        f"  This week: {user_count['week']}\n"
        f"  This month: {user_count['month']}\n\n"
        "<b>📥 Total Requests:</b> {total}\n"
        f"  ✅ Successful: {status_stats['complete']} ({success_rate:.1f}%)\n"
        f"  ❌ Failed: {status_stats['error']} ({100-success_rate:.1f}%)\n\n"
        "<b>💾 Media Cache:</b>\n"
        f"  📦 Total cached: <b>{db_overview.get('total_cached', 0):,}</b> files\n"
    ).format(total=total_requests)

    if isinstance(callback.message, types.InaccessibleMessage) or callback.message is None:
        if callback.bot is None:
            return
        await callback.bot.send_message(callback.from_user.id, text,
            parse_mode=ParseMode.HTML,
            reply_markup=statistic_kb,)
    else:
        await callback.message.edit_text(text,
            parse_mode=ParseMode.HTML,
            reply_markup=statistic_kb,
        )
    await callback.answer()

@admin_router.callback_query(lambda c: c.data == "statistic_top_services")
async def admin_panel_top_services(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    data = await state.get_data()
    if data.get("current_admin_screen") == "top_services":
        await callback.answer("Nothing happened!", cache_time=1)
        return

    await state.update_data(current_admin_screen="top_services")

    text = "🏆 <b>Top Services (All Time)</b>\n\n"
    top_services = await get_top_services(db_session)

    medals = ["🥇", "🥈", "🥉"]
    for idx, (service, count) in enumerate(top_services):
        medal = medals[idx] if idx < 3 else f"{idx + 1}."
        text += f"{medal} <b>{service}</b>: {count}\n"

    if isinstance(callback.message, types.InaccessibleMessage) or callback.message is None:
        if callback.bot is None:
            return
        await callback.bot.send_message(callback.from_user.id, text,
            parse_mode=ParseMode.HTML,
            reply_markup=statistic_kb,)
    else:
        await callback.message.edit_text(text,
            parse_mode=ParseMode.HTML,
            reply_markup=statistic_kb,
        )
    await callback.answer()

@admin_router.callback_query(lambda c: c.data == "statistic_premium_stats")
async def admin_panel_prem_stats(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    data = await state.get_data()
    if data.get("current_admin_screen") == "premium_stats":
        await callback.answer("Nothing happened!", cache_time=1)
        return

    await state.update_data(current_admin_screen="premium_stats")

    stats = await get_premium_and_donation_stats(db_session)
    text = (
        "⭐ <b>Premium Statistics</b>\n\n"
        f"👑 Total premium users: {stats['total_premium_users']}\n"
        f"⭐ Total stars donated: {stats['total_stars_donated']}\n"
    )

    if isinstance(callback.message, types.InaccessibleMessage) or callback.message is None:
        if callback.bot is None:
            return
        await callback.bot.send_message(callback.from_user.id, text,
            parse_mode=ParseMode.HTML,
            reply_markup=statistic_kb,)
    else:
        await callback.message.edit_text(text,
            parse_mode=ParseMode.HTML,
            reply_markup=statistic_kb,
        )
    await callback.answer()

# === Premium panel ===
@admin_router.callback_query(lambda c: c.data == "admin_panel_premium")
async def admin_panel_premium(callback: CallbackQuery, state: FSMContext):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🦐 Toggle premium", callback_data="admin_panel_toggle_premium"),
            InlineKeyboardButton(text="🍄 Toggle whom lifetime", callback_data="admin_panel_toggle_lifetime_premium"),
        ],
        [
            InlineKeyboardButton(text="🔙 Back", callback_data="admin_panel_back"),
        ]
    ])

    text = ("Premium. When Charlotte turned paid?")

    if isinstance(callback.message, types.InaccessibleMessage) or callback.message is None:
        if callback.bot is None:
            return
        await callback.bot.send_message(callback.from_user.id, text,
            parse_mode=ParseMode.HTML,
            reply_markup=kb,)
    else:
        await callback.message.edit_text(text,
            parse_mode=ParseMode.HTML,
            reply_markup=kb,
        )
    await callback.answer()

@admin_router.callback_query(lambda c: c.data == "admin_panel_toggle_premium")
async def admin_toggle_premium(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔙 Back", callback_data="admin_panel_back"),
        ]
    ])

    premium_status = await toggle_lifetime_premium(session=db_session, user_id=callback.from_user.id)

    text = (f"Changed premium status to `{premium_status}`")

    if isinstance(callback.message, types.InaccessibleMessage) or callback.message is None:
        if callback.bot is None:
            return
        await callback.bot.send_message(callback.from_user.id, text,
            parse_mode=ParseMode.HTML,
            reply_markup=kb,)
    else:
        await callback.message.edit_text(text,
            parse_mode=ParseMode.HTML,
            reply_markup=kb,
        )
    await callback.answer()

@admin_router.callback_query(lambda c: c.data == "admin_panel_toggle_lifetime_premium")
async def handle_toggle_lifetime_premium_callback(callback: CallbackQuery, state: FSMContext):
    text = ("🆔 Please send the user ID:")

    if isinstance(callback.message, types.InaccessibleMessage) or callback.message is None:
        if callback.bot is None:
            return
        await callback.bot.send_message(callback.from_user.id, text,
            parse_mode=ParseMode.HTML,
        )
    else:
        await callback.message.edit_text(text,
            parse_mode=ParseMode.HTML,
        )
    await state.set_state(AdminStates.waiting_for_user_id)
    await callback.answer()

@admin_router.message(AdminStates.waiting_for_user_id)
async def process_user_id(message: types.Message, state: FSMContext, db_session: AsyncSession, i18n: TranslatorRunner):
    message_text = message.text
    if message_text is None:
        return
    user_id_text = message_text.strip()

    if not user_id_text.isdigit():
        await message.answer("❌ Invalid user ID. Please send only numbers.")
        return

    user_id = int(user_id_text)

    premium_status = await toggle_lifetime_premium(session=db_session, user_id=user_id)

    await message.answer(
        (
            f"Changed premium status to `{premium_status}`"
        ),
        parse_mode=ParseMode.HTML,
    )

    # Send notification to user if premium was granted
    if premium_status and message.bot:
        try:
            await message.bot.send_message(user_id, i18n.get("premium-granted"))
        except Exception as e:
            import logging
            logging.error(f"Failed to send premium notification to user {user_id}: {e}")

    await state.clear()

# === Ban panel ===
@admin_router.callback_query(lambda c: c.data == "admin_panel_banlist")
async def admin_panel_banlist(callback: CallbackQuery, state: FSMContext):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🚫 Ban user", callback_data="ban_panel_ban_user"),
            InlineKeyboardButton(text="🤭 Pardon user", callback_data="ban_panel_pardon_user"),
        ],
        [
            InlineKeyboardButton(text="🐒 Ban List", callback_data="ban_panel_list"),
            InlineKeyboardButton(text="🔙 Back", callback_data="admin_panel_back"),
        ]
    ])

    text = "🚫 Ban Management Panel\n\nChoose what to do:"

    if isinstance(callback.message, types.InaccessibleMessage) or callback.message is None:
        if callback.bot is None:
            return
        await callback.bot.send_message(callback.from_user.id, text,
            parse_mode=ParseMode.HTML,
            reply_markup=kb,)
    else:
        await callback.message.edit_text(text,
            parse_mode=ParseMode.HTML,
            reply_markup=kb,
        )
    await callback.answer()

@admin_router.callback_query(lambda c: c.data == "ban_panel_list")
async def ban_panel_list(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔙 Back", callback_data="admin_panel_banlist"),
        ]
    ])

    text = "Banned users:\n"
    banned_users = await list_of_banned_users(db_session)
    for user in banned_users:
        text += f"{user.user_id}\n"

    if isinstance(callback.message, types.InaccessibleMessage) or callback.message is None:
        if callback.bot is None:
            return
        await callback.bot.send_message(callback.from_user.id, text,
            parse_mode=ParseMode.HTML,
            reply_markup=kb,)
    else:
        await callback.message.edit_text(text,
            parse_mode=ParseMode.HTML,
            reply_markup=kb,
        )
    await callback.answer()

@admin_router.callback_query(lambda c: c.data == "ban_panel_ban_user")
async def handle_ban_user_callback(callback: CallbackQuery, state: FSMContext):
    text = ("🆔 Please send the user ID:")

    if isinstance(callback.message, types.InaccessibleMessage) or callback.message is None:
        if callback.bot is None:
            return
        await callback.bot.send_message(callback.from_user.id, text)
    else:
        await callback.message.edit_text(text)
    await state.set_state(AdminStates.waiting_for_user_id_ban)
    await callback.answer()

@admin_router.callback_query(lambda c: c.data == "ban_panel_pardon_user")
async def handle_pardon_user_callback(callback: CallbackQuery, state: FSMContext):
    text = ("🆔 Please send the user ID:")

    if isinstance(callback.message, types.InaccessibleMessage) or callback.message is None:
        if callback.bot is None:
            return
        await callback.bot.send_message(callback.from_user.id, text)
    else:
        await callback.message.edit_text(text)
    await state.set_state(AdminStates.waiting_for_user_id_pardon)
    await callback.answer()

@admin_router.message(AdminStates.waiting_for_user_id_ban)
async def process_ban(message: types.Message, state: FSMContext, db_session: AsyncSession):
    message_text = message.text
    if message_text is None:
        return
    user_id_text = message_text.strip()

    if not user_id_text.isdigit():
        await message.answer("❌ Invalid user ID. Please send only numbers.")
        return

    user_id = int(user_id_text)

    await ban_user(session=db_session, user_id=user_id)

    await message.answer(
        (
            f"Banned user ID: `{user_id}`"
        ),
        parse_mode=ParseMode.HTML,
    )
    await state.clear()

@admin_router.message(AdminStates.waiting_for_user_id_pardon)
async def process_pardon(message: types.Message, state: FSMContext, db_session: AsyncSession):
    message_text = message.text
    if message_text is None:
        return
    user_id_text = message_text.strip()

    if not user_id_text.isdigit():
        await message.answer("❌ Invalid user ID. Please send only numbers.")
        return

    user_id = int(user_id_text)

    await unban_user(session=db_session, user_id=user_id)

    await message.answer(
        (
            f"Pardon user ID: `{user_id}`"
        ),
        parse_mode=ParseMode.HTML,
    )
    await state.clear()

# === Get logs button ===
@admin_router.callback_query(lambda c: c.data == "admin_panel_get_logs")
async def admin_panel_get_logs(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    message = callback.message
    if message is None:
        return
    if not isinstance(message, InaccessibleMessage):
        await message.delete()
    await message.bot.send_document(
        chat_id=message.chat.id,
        document=FSInputFile("logs/charlotte.log"),
        caption="Here's your logs"
    )

# === Spam news button ===
@admin_router.callback_query(lambda c: c.data == "admin_panel_news")
async def admin_panel_news(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(NewsSpamGroup.news_spam)
    text = "Send a message with the news"

    if isinstance(callback.message, types.InaccessibleMessage) or callback.message is None:
        if callback.bot is None:
            return
        await callback.bot.send_message(callback.from_user.id, text)
    else:
        await callback.message.edit_text(text)

@admin_router.message(NewsSpamGroup.news_spam)
async def proccess_spam_news(message: types.Message, state: FSMContext) -> None:
    escaped_text = escape_markdown(str(message.text))
    text = "Are you sure you want to send such a message?\n" f"> {escaped_text}"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="To subscribers", callback_data="news_spam_subscribers"),
            InlineKeyboardButton(text="Force to all", callback_data="news_spam_force_all"),
        ],
        [
            InlineKeyboardButton(text="Cancel", callback_data="news_spam_decline"),
        ]
    ])

    await state.update_data(message_text=escaped_text)
    await state.set_state(NewsSpamGroup.accept_news_spam)
    await message.answer(
        text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN_V2
    )

@admin_router.callback_query(lambda c: c.data in ["news_spam_subscribers", "news_spam_force_all"])
async def process_spam_news_to_chats(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession) -> None:
    data = await state.get_data()
    chat_id = callback.from_user.id
    message_text = data.get("message_text", "")

    await callback.answer("Mailing list started", reply_markup=ReplyKeyboardRemove())
    await state.clear()

    start_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total_chat = 0
    success_send = 0
    error_send = 0

    if callback.data == "news_spam_subscribers":
        user_ids = await get_news_subscribers_ids(db_session)
    else:
        user_ids = await get_list_user_ids(db_session)
        chat_ids = await get_all_chat_ids(db_session)
        user_ids.extend(chat_ids)


    for user_id in user_ids:
        if user_id == chat_id:
            continue

        if await send_message_safe(callback.bot, user_id, message_text):
            success_send += 1
        else:
            error_send += 1

        await asyncio.sleep(0.05)

    end_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    done_message = (
        "The mailing has been completed\n"
        "Beginning at {start_time}\n"
        "Ended at {end_time}\n"
        "Number of chats: {total_chat}\n"
        "Successfully sent: {sucсess_send}\n"
        "Erros: {error_send}"
    ).format(
        start_time=start_time,
        end_time=end_time,
        total_chat=total_chat,
        sucсess_send=success_send,
        error_send=error_send,
    )

    await callback.bot.send_message(chat_id=chat_id, text=done_message)

async def send_message_safe(bot: Bot, user_id: int, text: str) -> bool:
    """
    Функция отправки сообщения с обработкой ошибок и ретраями.
    Возвращает True, если отправлено успешно, иначе False.
    """
    try:
        await bot.send_message(chat_id=user_id, text=text, parse_mode=ParseMode.MARKDOWN_V2)
        return True

    except TelegramRetryAfter as e:
        # Если словили лимит, ждем указанное время и пробуем снова (рекурсия)
        logger.warning(f"Rate limit hit for user {user_id}, waiting {e.retry_after}s")
        await asyncio.sleep(e.retry_after)
        return await send_message_safe(bot, user_id, text)

    except TelegramForbiddenError:
        # Пользователь заблокировал бота
        return False

    except TelegramBadRequest as e:
        # Ошибка запроса (например, чат не найден)
        logger.debug(f"Bad request for user {user_id}: {e}")
        return False

    except Exception as e:
        # Любая другая непредвиденная ошибка
        logger.error(f"Unexpected error sending message to {user_id}: {e}")
        return False

@admin_router.callback_query(lambda c: c.data == "news_spam_decline")
async def decline_spam_news(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.delete()
    await state.clear()
    await callback.answer()

# === Settings panel ===
@admin_router.callback_query(lambda c: c.data == "admin_panel_bot_settings")
async def admin_panel_bot_settings(callback: CallbackQuery, state: FSMContext):
    text = (
        "Here's my settings"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🚫 Block Services", callback_data="settings_panel_block_services"),
        ],
        [
            InlineKeyboardButton(text="🔙 Back", callback_data="admin_panel_back"),
        ]
    ])

    if isinstance(callback.message, types.InaccessibleMessage) or callback.message is None:
        if callback.bot is None:
            return
        await callback.bot.send_message(callback.from_user.id, text,
            parse_mode=ParseMode.HTML,
            reply_markup=kb,)
    else:
        await callback.message.edit_text(text,
            parse_mode=ParseMode.HTML,
            reply_markup=kb,
        )
    await callback.answer()

# @dp.callback_query(lambda c: c.data == "settings_panel_block_services")
# async def blocked_services_menu(callback: CallbackQuery):
#     settings = await get_global_settings()
#     blocked_services = settings.get("blocked_services", [])

#     available_services = list(SERVICES.keys())
#     keyboards = []

#     for service in available_services:
#         is_blocked = service.lower() in blocked_services
#         icon = "🚫" if is_blocked else "✅"
#         keyboards.append([
#             InlineKeyboardButton(
#                 text=f"{icon} {service}",
#                 callback_data=f"global_service_toggle_{service}"
#             )
#         ])

#     keyboards.append([InlineKeyboardButton(text="🔙 Back", callback_data="admin_panel_back")])

#     kb = InlineKeyboardMarkup(inline_keyboard=keyboards)
#     blocked_count = len(blocked_services)

#     text = (
#         f"**Blocked Services Management**\n\n"
#         f"Currently blocked: {blocked_count} services\n\n"
#         f"Tap a service to toggle its status."
#     )

#     await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)
#     await callback.answer()


@admin_router.callback_query(lambda c: c.data.startswith("global_service_toggle_"))
async def toggle_service(callback: CallbackQuery, db_session: AsyncSession):
    data = callback.data
    if data is None:
        return
    service = data.replace("global_service_toggle_", "")
    service = service.lower()
    settings = await get_global_settings(db_session)
    blocked_services = settings.get("blocked_services", [])

    if service in blocked_services:
        blocked_services.remove(service)
    else:
        blocked_services.append(service)

    await update_global_settings(db_session,"blocked_services", blocked_services)
    # await blocked_services_menu(callback)


# === Service Statistics ===
@admin_router.callback_query(lambda c: c.data == "statistic_service_usage")
async def admin_panel_service_usage(callback: CallbackQuery, state: FSMContext):

    from storage.db import database_manager
    from sqlalchemy import select, func, case
    from storage.db.models import Statistics
    import datetime

    async with database_manager.async_session() as session:
        since = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=30)

        result = await session.execute(
            select(
                Statistics.service_name,
                func.count(Statistics.event_id).label('total'),
                func.sum(case((Statistics.status == 'success', 1), else_=0)).label('success'),
                func.sum(case((Statistics.status == 'failed', 1), else_=0)).label('failed'),
                func.count(func.distinct(Statistics.user_id)).label('unique_users')
            )
            .where(Statistics.event_time >= since)
            .group_by(Statistics.service_name)
            .order_by(func.count(Statistics.event_id).desc())
        )

        stats = result.all()
        cache_counts = await get_cache_counts_by_service(session)

    text = "📊 <b>Service Usage (Last 30 days)</b>\n\n"
    total_all = 0
    success_all = 0
    failed_all = 0

    for service, total, success, failed, unique_users in stats:
        success_rate = (success / total * 100) if total > 0 else 0
        text += f"<b>{service}</b>\n"
        text += f"  👥 Users: {unique_users}\n"
        text += f"  Total requests: {total}\n"
        text += f"  ✅ Success: {success} ({success_rate:.1f}%)\n"
        text += f"  ❌ Failed: {failed}\n"
        text += f"  📦 Cached files: {cache_counts.get(service, 0)}\n\n"
        total_all += total
        success_all += success
        failed_all += failed

    overall_rate = (success_all / total_all * 100) if total_all > 0 else 0
    text += "<b>━━━━━━━━━━━━━━━</b>\n"
    text += f"<b>Total Downloads:</b> {total_all}\n"
    text += f"<b>Overall Success Rate:</b> {overall_rate:.1f}%"

    if isinstance(callback.message, InaccessibleMessage) or callback.message is None:
        if callback.bot:
            await callback.bot.send_message(callback.from_user.id, text, parse_mode=ParseMode.HTML, reply_markup=statistic_kb)
    else:
        await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=statistic_kb)
    await callback.answer()


@admin_router.callback_query(lambda c: c.data == "statistic_clean_old")
async def admin_panel_clean_stats(callback: CallbackQuery, state: FSMContext):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🗑 Clean 30+ days", callback_data="clean_stats_30"),
            InlineKeyboardButton(text="🗑 Clean 60+ days", callback_data="clean_stats_60"),
        ],
        [
            InlineKeyboardButton(text="🗑 Clean 90+ days", callback_data="clean_stats_90"),
            InlineKeyboardButton(text="🔙 Back", callback_data="admin_panel_statistic"),
        ]
    ])

    text = "⚠️ <b>Clean Old Statistics</b>\n\nSelect period to clean:"

    if isinstance(callback.message, InaccessibleMessage) or callback.message is None:
        if callback.bot:
            await callback.bot.send_message(callback.from_user.id, text, parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    await callback.answer()


@admin_router.callback_query(lambda c: c.data.startswith("clean_stats_"))
async def admin_clean_stats_confirm(callback: CallbackQuery, state: FSMContext):
    days = int(callback.data.split("_")[-1])

    from storage.db import database_manager
    from sqlalchemy import delete
    from storage.db.models import Statistics
    import datetime

    async with database_manager.async_session() as session:
        cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)
        result = await session.execute(
            delete(Statistics).where(Statistics.event_time < cutoff)
        )
        await session.commit()
        deleted = result.rowcount

    text = f"✅ Cleaned {deleted} records older than {days} days"

    if isinstance(callback.message, InaccessibleMessage) or callback.message is None:
        if callback.bot:
            await callback.bot.send_message(callback.from_user.id, text, parse_mode=ParseMode.HTML, reply_markup=statistic_kb)
    else:
        await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=statistic_kb)
    await callback.answer()
