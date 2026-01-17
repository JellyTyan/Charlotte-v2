from aiogram import types
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import InaccessibleMessage, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, FSInputFile, message
from typing import Optional
from states import NewsSpamGroup
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
    update_global_settings
)
from storage.db.crud_statistics import get_service_stats, get_user_stats
# from utils.register_services import SERVICES

from core.loader import dp
from core.config import Config

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
@dp.message(Command("admin_panel"))
async def admin_panel(message: types.Message, state: FSMContext) -> None:
    user = message.from_user
    if user is None:
        return

    config: Optional[Config] = dp.workflow_data.get("config")
    if not config:
        return
    ADMIN_ID = config.ADMIN_ID

    if message.chat.id != ADMIN_ID or user.id != ADMIN_ID:
        return

    await state.update_data(current_admin_screen=None)

    await message.answer(
        (
            "Hey, Jelly! Here's your buttons to play with\n"
        ),
        parse_mode=ParseMode.HTML,
        reply_markup=panel_kb,
    )

@dp.callback_query(lambda c: c.data == "admin_panel_back")
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
@dp.callback_query(lambda c: c.data == "admin_panel_statistic")
async def admin_panel_stats(callback: CallbackQuery, state: FSMContext):
    config: Optional[Config] = dp.workflow_data.get("config")
    if not config:
        return
    ADMIN_ID = config.ADMIN_ID
    if callback.from_user.id != ADMIN_ID:
        return

    data = await state.get_data()
    if data.get("current_admin_screen") == "statistics":
        await callback.answer("Nothing happened!", cache_time=1)
        return

    await state.update_data(current_admin_screen="statistics")

    user_count = await get_user_counts()
    status_stats = await get_status_stats()
    
    total_requests = status_stats['complete'] + status_stats['error']
    success_rate = (status_stats['complete'] / total_requests * 100) if total_requests > 0 else 0

    text = (
        "📊 <b>Global Statistics</b>\n\n"
        "<b>👥 Active Users:</b>\n"
        f"  Today: {user_count['today']}\n"
        f"  Yesterday: {user_count['yesterday']}\n"
        f"  This week: {user_count['week']}\n"
        f"  This month: {user_count['month']}\n\n"
        "<b>📥 Total Requests:</b> {total}\n"
        f"  ✅ Successful: {status_stats['complete']} ({success_rate:.1f}%)\n"
        f"  ❌ Failed: {status_stats['error']} ({100-success_rate:.1f}%)\n"
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

@dp.callback_query(lambda c: c.data == "statistic_top_services")
async def admin_panel_top_services(callback: CallbackQuery, state: FSMContext):
    config: Optional[Config] = dp.workflow_data.get("config")
    if not config:
        return
    ADMIN_ID = config.ADMIN_ID
    if callback.from_user.id != ADMIN_ID:
        return

    data = await state.get_data()
    if data.get("current_admin_screen") == "top_services":
        await callback.answer("Nothing happened!", cache_time=1)
        return

    await state.update_data(current_admin_screen="top_services")

    text = "🏆 <b>Top Services (All Time)</b>\n\n"
    top_services = await get_top_services()
    
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

@dp.callback_query(lambda c: c.data == "statistic_premium_stats")
async def admin_panel_prem_stats(callback: CallbackQuery, state: FSMContext):
    config: Optional[Config] = dp.workflow_data.get("config")
    if not config:
        return
    ADMIN_ID = config.ADMIN_ID
    if callback.from_user.id != ADMIN_ID:
        return

    data = await state.get_data()
    if data.get("current_admin_screen") == "premium_stats":
        await callback.answer("Nothing happened!", cache_time=1)
        return

    await state.update_data(current_admin_screen="premium_stats")

    stats = await get_premium_and_donation_stats()
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
@dp.callback_query(lambda c: c.data == "admin_panel_premium")
async def admin_panel_premium(callback: CallbackQuery, state: FSMContext):
    config: Optional[Config] = dp.workflow_data.get("config")
    if not config:
        return
    ADMIN_ID = config.ADMIN_ID
    if callback.from_user.id != ADMIN_ID:
        return

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

@dp.callback_query(lambda c: c.data == "admin_panel_toggle_premium")
async def admin_toggle_premium(callback: CallbackQuery, state: FSMContext):
    config: Optional[Config] = dp.workflow_data.get("config")
    if not config:
        return
    ADMIN_ID = config.ADMIN_ID
    if callback.from_user.id != ADMIN_ID:
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔙 Back", callback_data="admin_panel_back"),
        ]
    ])

    premium_status = await toggle_lifetime_premium(user_id=callback.from_user.id)

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

@dp.callback_query(lambda c: c.data == "admin_panel_toggle_lifetime_premium")
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

@dp.message(AdminStates.waiting_for_user_id)
async def process_user_id(message: types.Message, state: FSMContext):
    message_text = message.text
    if message_text is None:
        return
    user_id_text = message_text.strip()

    if not user_id_text.isdigit():
        await message.answer("❌ Invalid user ID. Please send only numbers.")
        return

    user_id = int(user_id_text)

    premium_status = await toggle_lifetime_premium(user_id=user_id)

    await message.answer(
        (
            f"Changed premium status to `{premium_status}`"
        ),
        parse_mode=ParseMode.HTML,
    )
    
    # Send notification to user if premium was granted
    if premium_status and message.bot:
        try:
            from storage.db.crud import get_user_settings
            settings = await get_user_settings(user_id)
            lang = settings.lang if settings else "en"
            
            hub = dp.workflow_data.get("_translator_hub")
            if hub:
                i18n = hub.get_translator_by_locale(lang)
                await message.bot.send_message(
                    user_id,
                    i18n.premium.granted()
                )
        except Exception as e:
            import logging
            logging.error(f"Failed to send premium notification to user {user_id}: {e}")
    
    await state.clear()

# === Ban panel ===
@dp.callback_query(lambda c: c.data == "admin_panel_banlist")
async def admin_panel_banlist(callback: CallbackQuery, state: FSMContext):
    config: Optional[Config] = dp.workflow_data.get("config")
    if not config:
        return
    ADMIN_ID = config.ADMIN_ID
    if callback.from_user.id != ADMIN_ID:
        return

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

    text = ("🚫 Ban Management Panel\n\nChoose what to do:")

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

@dp.callback_query(lambda c: c.data == "ban_panel_list")
async def ban_panel_list(callback: CallbackQuery, state: FSMContext):
    config: Optional[Config] = dp.workflow_data.get("config")
    if not config:
        return
    ADMIN_ID = config.ADMIN_ID

    if callback.from_user.id != ADMIN_ID:
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔙 Back", callback_data="admin_panel_banlist"),
        ]
    ])

    text = "Banned users:\n"
    banned_users = await list_of_banned_users()
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

@dp.callback_query(lambda c: c.data == "ban_panel_ban_user")
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

@dp.callback_query(lambda c: c.data == "ban_panel_pardon_user")
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

@dp.message(AdminStates.waiting_for_user_id_ban)
async def process_ban(message: types.Message, state: FSMContext):
    message_text = message.text
    if message_text is None:
        return
    user_id_text = message_text.strip()

    if not user_id_text.isdigit():
        await message.answer("❌ Invalid user ID. Please send only numbers.")
        return

    user_id = int(user_id_text)

    await ban_user(user_id=user_id)

    await message.answer(
        (
            f"Banned user ID: `{user_id}`"
        ),
        parse_mode=ParseMode.HTML,
    )
    await state.clear()

@dp.message(AdminStates.waiting_for_user_id_pardon)
async def process_pardon(message: types.Message, state: FSMContext):
    message_text = message.text
    if message_text is None:
        return
    user_id_text = message_text.strip()

    if not user_id_text.isdigit():
        await message.answer("❌ Invalid user ID. Please send only numbers.")
        return

    user_id = int(user_id_text)

    await unban_user(user_id=user_id)

    await message.answer(
        (
            f"Pardon user ID: `{user_id}`"
        ),
        parse_mode=ParseMode.HTML,
    )
    await state.clear()

# === Get logs button ===
@dp.callback_query(lambda c: c.data == "admin_panel_get_logs")
async def admin_panel_get_logs(callback: CallbackQuery, state: FSMContext):
    config: Optional[Config] = dp.workflow_data.get("config")
    if not config:
        return
    ADMIN_ID = config.ADMIN_ID

    if callback.from_user.id != ADMIN_ID:
        return

    await callback.answer()
    message = callback.message
    if message is None:
        return
    bot = message.bot
    if bot is None:
        return
    if not isinstance(message, InaccessibleMessage):
        await message.delete()
    await bot.send_document(
        chat_id=message.chat.id,
        document=FSInputFile("logs/charlotte.log"),
        caption="Here's your logs"
    )

# === Spam news button ===
@dp.callback_query(lambda c: c.data == "admin_panel_news")
async def admin_panel_news(callback: CallbackQuery, state: FSMContext):
    config: Optional[Config] = dp.workflow_data.get("config")
    if not config:
        return
    ADMIN_ID = config.ADMIN_ID

    if callback.from_user.id != ADMIN_ID:
        return

    await callback.answer()
    await state.set_state(NewsSpamGroup.news_spam)
    text = ("Send a message with the news")

    if isinstance(callback.message, types.InaccessibleMessage) or callback.message is None:
        if callback.bot is None:
            return
        await callback.bot.send_message(callback.from_user.id, text)
    else:
        await callback.message.edit_text(text)

# === Settings panel ===
@dp.callback_query(lambda c: c.data == "admin_panel_bot_settings")
async def admin_panel_bot_settings(callback: CallbackQuery, state: FSMContext):
    config: Optional[Config] = dp.workflow_data.get("config")
    if not config:
        return
    ADMIN_ID = config.ADMIN_ID

    if callback.from_user.id != ADMIN_ID:
        return

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


@dp.callback_query(lambda c: c.data.startswith("global_service_toggle_"))
async def toggle_service(callback: CallbackQuery):
    data = callback.data
    if data is None:
        return
    service = data.replace("global_service_toggle_", "")
    service = service.lower()
    settings = await get_global_settings()
    blocked_services = settings.get("blocked_services", [])

    if service in blocked_services:
        blocked_services.remove(service)
    else:
        blocked_services.append(service)

    await update_global_settings("blocked_services", blocked_services)
    # await blocked_services_menu(callback)


# === Service Statistics ===
@dp.callback_query(lambda c: c.data == "statistic_service_usage")
async def admin_panel_service_usage(callback: CallbackQuery, state: FSMContext):
    config: Optional[Config] = dp.workflow_data.get("config")
    if not config or callback.from_user.id != config.ADMIN_ID:
        return

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
                func.sum(case((Statistics.status == 'failed', 1), else_=0)).label('failed')
            )
            .where(Statistics.event_time >= since)
            .group_by(Statistics.service_name)
            .order_by(func.count(Statistics.event_id).desc())
        )
        
        stats = result.all()

    text = "📊 <b>Service Usage (Last 30 days)</b>\n\n"
    total_all = 0
    success_all = 0
    failed_all = 0
    
    for service, total, success, failed in stats:
        success_rate = (success / total * 100) if total > 0 else 0
        text += f"<b>{service}</b>\n"
        text += f"  Total: {total}\n"
        text += f"  ✅ Success: {success} ({success_rate:.1f}%)\n"
        text += f"  ❌ Failed: {failed}\n\n"
        total_all += total
        success_all += success
        failed_all += failed
    
    overall_rate = (success_all / total_all * 100) if total_all > 0 else 0
    text += f"<b>━━━━━━━━━━━━━━━</b>\n"
    text += f"<b>Total Downloads:</b> {total_all}\n"
    text += f"<b>Overall Success Rate:</b> {overall_rate:.1f}%"

    if isinstance(callback.message, InaccessibleMessage) or callback.message is None:
        if callback.bot:
            await callback.bot.send_message(callback.from_user.id, text, parse_mode=ParseMode.HTML, reply_markup=statistic_kb)
    else:
        await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=statistic_kb)
    await callback.answer()


@dp.callback_query(lambda c: c.data == "statistic_clean_old")
async def admin_panel_clean_stats(callback: CallbackQuery, state: FSMContext):
    config: Optional[Config] = dp.workflow_data.get("config")
    if not config or callback.from_user.id != config.ADMIN_ID:
        return

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


@dp.callback_query(lambda c: c.data.startswith("clean_stats_"))
async def admin_clean_stats_confirm(callback: CallbackQuery, state: FSMContext):
    config: Optional[Config] = dp.workflow_data.get("config")
    if not config or callback.from_user.id != config.ADMIN_ID:
        return

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
