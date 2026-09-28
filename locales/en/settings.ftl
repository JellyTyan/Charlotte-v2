settings-welcome = Hey! You can customize everything here, make yourself at home.
settings-back = 🔙 Back
settings-title = Settings
settings-no-permission = Oops, you don't have permission to change these settings.
settings-saved = Updated settings! ✨
settings-no-allowed-groups = This setting isn't available in groups, sorry.
settings-no-allowed-dm = This setting can't be changed in private chat.

btn-language = Language
btn-title-language = Captions
btn-blocked-services = Service blocklist

btn-send-raw = { $is_enabled ->
    [true] 🟢 As file
    *[false] ⚪ As file
}
btn-send-music-covers = { $is_enabled ->
    [true] 🟢 Covers
    *[false] ⚪ Covers
}
btn-send-reactions = { $is_enabled ->
    [true] 🟢 Reactions
    *[false] ⚪ Reactions
}
btn-negativity = { $is_enabled ->
    [true] 🟢 Cheeky mode
    *[false] ⚪ Cheeky mode
}
btn-auto-translate = { $is_enabled ->
    [true] 🟢 Translate
    *[false] ⚪ Translate
}
btn-auto-caption = { $is_enabled ->
    [true] 🟢 Captions
    *[false] ⚪ Captions
}
btn-notifications = { $is_enabled ->
    [true] 🟢 Notifications
    *[false] ⚪ Notifications
}
btn-allow-playlists = { $is_enabled ->
    [true] 🟢 Playlists
    *[false] ⚪ Playlists
}
btn-allow-nsfw = { $is_enabled ->
    [true] 🟢 NSFW
    *[false] ⚪ NSFW
}

desc-send-raw = I'll send media as files — that preserves the highest quality.
desc-send-music-covers = Attach album art to each track.
desc-send-reactions = I'll add emoji reactions so you can follow the progress.
desc-negativity-mode = I'll use slightly cheekier emoji reactions.
desc-send-notifications = Turn off if you'd like to receive media silently.
desc-auto-caption = I'll automatically check and add descriptions to media.
desc-auto-translate-titles = Translate video descriptions into your language.
desc-allow-playlists = Download whole playlists — careful with this one.
desc-allow-nsfw = Allow NSFW content in this chat.
desc-lossless-mode = I'll try to find a Hi-Res version of the track. No guarantees, though.

setting-status-changed = { $is_enabled ->
    [true] Enabled *{ $setting_name }*!
    *[false] Disabled *{ $setting_name }*.
}

pick-language = Choose language 🌍
pick-title-language = Choose caption language
language-changed = Now speaking *{ $language }*!
language-updated = Language updated.
title-language-changed = Captions will now be in *{ $language }*.
title-language-updated = Caption language updated.
setting-updated = Done, updated.
invalid-setting = Hmm, I don't recognize that setting.
error-updating = Couldn't update that, sorry. Want to try again?
enabled = enabled
disabled = disabled
enable = Enable
disable = Disable
back = Back
service-status-changed = Service { $service } is now { $status }.
blocked = blocked
unblocked = unblocked
settings-not-found = Couldn't find those settings.
no-permission-service = You aren't allowed to change these settings.
error-service-status = Couldn't update service status, sorry.
current-status = Current status: { $status }

btn-configure-services = ⚙️ Service settings
settings-select-service = Choose a service to configure:
settings-service-title = **{ $name } Settings**
btn-lossless = { $is_enabled ->
    [true] 🟢 LOSSLESS
    *[false] ⚪ LOSSLESS
}
btn-service-enabled = { $is_enabled ->
    [true] 🟢 Service
    *[false] ⚪ Service
}

btn-news-spam = { $is_enabled ->
    [true] 🟢 Broadcast
    *[false] ⚪ Broadcast
}
desc-news-spam = Allow sending you news and updates.

btn-bot-sign = { $is_enabled ->
    [true] 🟢 Bot Ad 🧡
    *[false] ⚪ Bot Ad 🧡
}
desc-bot-sign = Add "Charlotte 🧡" watermark to media. Disabling is completely free.

btn-simple-mode = { $is_enabled ->
    [true] 🟢 Simple mode
    *[false] ⚪ Simple mode
}
desc-simple =
    Simple YouTube interface:
    On — only two buttons (Video or Audio), downloads in best quality up to 100 MB (up to 1 GB for Sponsors).
    Off — quality picker and video trimming (for Sponsors).

btn-youtube-ui-mode = YouTube interface
yt-ui-mode-simple = Simple
yt-ui-mode-balance = Balanced
yt-ui-mode-advanced = Advanced
desc-youtube-ui-mode =
    Choose your YouTube download style:

    • Simple — 2 buttons (Video / Audio), one-click download.
    • Balanced — top quality buttons in one click + access to advanced settings.
    • Advanced — pick any quality, audio track, and video trimming (Trim).

btn-experimental = 🧪 New features
desc-experimental-features =
    Experimental features work only in recent official Telegram apps and might behave unpredictably in older or third-party clients.

btn-ephemeral-messages = { $is_enabled ->
    [true] 🟢 Ephemeral messages
    *[false] ⚪ Ephemeral messages
}
desc-ephemeral-messages = Send service notifications in groups as ephemeral messages visible only to you. When off, I send regular auto-deleting messages.

btn-chat-banned-users = 🚫 Ban list
desc-chat-banned-users = Manage users banned from using the bot in this chat.
cban-usage = Specify user ID or reply to a message: <code>/cban &lt;user_id&gt;</code>
cban-cannot-ban-self = You cannot ban yourself.
cban-cannot-ban-admin = You cannot ban chat administrators.
cban-cannot-ban-bot = You cannot ban the bot.
cban-success = User <code>{ $user_id }</code> has been banned in this chat.
cban-already-banned = User <code>{ $user_id }</code> is already banned in this chat.
cunban-usage = Specify user ID or reply to a message: <code>/cunban &lt;user_id&gt;</code>
cunban-not-banned = User <code>{ $user_id }</code> is not banned in this chat.
cunban-success = User <code>{ $user_id }</code> has been unbanned in this chat.
cbanlist-empty = No banned users in this chat.
cbanlist-title = <b>Chat ban list:</b>
btn-unban-user = ❌ Unban { $user_id }
