from aiogram import Bot, types


async def set_default_commands(bot: Bot) -> None:
    await bot.set_my_commands(
        [
            types.BotCommand(command="start", description="🌸 Start work with me"),
            types.BotCommand(command="help", description="🐾 My commands"),
            types.BotCommand(command="settings", description="🎀 Settings"),
            types.BotCommand(command="saves", description="📚 My media library"),
            types.BotCommand(command="copy", description="📋 Copy media to clipboard (1h)"),
            types.BotCommand(command="report", description="🚨 Report an issue with content"),
            types.BotCommand(command="support", description="❤️‍🔥 Support project"),
            types.BotCommand(command="cancel", description="🔮 Cancel task"),
        ]
    )
