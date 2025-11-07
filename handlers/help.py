from aiogram import types
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.i18n import gettext as _

from core.loader import dp


@dp.message(Command("help"))
async def help_command(message: types.Message, state: FSMContext) -> None:
    user = message.from_user
    if user is None:
        return

    await message.answer(
            "<b>Hey, {name}! I'm here to help you</b>\n\n"
            "Here are the main commands:\n"
            "  /start – Start using the bot\n"
            "  /help – Show this help message\n"
            "  /settings – Bot settings\n"
            "  /support – Support my creator\n\n"
            "I can download media from a wide range of platforms.\n"
            "Here's what I support:\n\n"
            "<b>Music Platforms</b>\n"
            "  - Spotify\n"
            "  - Apple Music\n"
            "  - SoundCloud\n"
            "    I’ll fetch the music, with title, artist, and cover.\n\n"
            "<b>Video Platforms</b>\n"
            "  - YouTube – Videos, Shorts, or just audio (up to 50 MB)\n"
            "  - TikTok – Videos and images\n"
            "  - BiliBili – Full video support (with limitations)\n"
            "  - Instagram – Reels and posts\n"
            "  - Twitter – Videos and images\n"
            "  - Reddit – Media from posts\n\n"
            "<b>Art Platforms</b>\n"
            "  - Pixiv – I can download illustrations for you\n\n"
            "  - Pinterest – I can download all media for you\n"
            "Just send a link — and I’ll take care of the rest.",
        parse_mode=ParseMode.HTML,
    )
