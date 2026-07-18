from aiogram import Bot, types


async def set_default_commands(bot: Bot) -> None:
    await bot.set_my_commands(
        [
            types.BotCommand(command="start", description="🌸 Start work with me"),
            types.BotCommand(command="help", description="🐾 My commands"),
            types.BotCommand(command="settings", description="🎀 Settings"),
            types.BotCommand(command="sponsor", description="🫶 Sponsorship"),
            types.BotCommand(command="support", description="❤️‍🔥 Support project"),
            types.BotCommand(command="cancel", description="🔮 Cancel task"),
        ]
    )
