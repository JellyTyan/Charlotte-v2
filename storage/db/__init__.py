from .db_manager import DatabaseManager
from .crud import (
    get_user,
    create_user,
    get_user_settings,
    update_user_premium,
    update_user_settings,
    get_chat,
    create_chat,
    get_chat_settings,
    update_chat_settings,
    create_usage_log,
    create_payment_log,
    update_payment_status,
    check_if_user_premium,
    toggle_lifetime_premium,
    ban_user,
    unban_user,
    list_of_banned_users,
    get_global_settings,
    update_global_settings,
)

database_manager = DatabaseManager()
