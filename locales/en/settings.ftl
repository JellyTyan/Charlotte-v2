settings-welcome = Welcome! Here are your personal settings. Feel free to customize them as you like!
settings-back = 🔙 Back
settings-title = Settings
settings-no-permission = You don't have permission to edit these settings!
settings-saved = Setting updated!
settings-no-allowed-groups = This setting is not available for groups!
settings-no-allowed-dm = This setting is not available for private chats!

btn-language = Language
btn-title-language = Title language
btn-blocked-services = Blocked services

btn-send-raw = { $is_enabled ->
    [true] ✅ Send art raw
    *[false] ❌ Send art raw
}
btn-send-music-covers = { $is_enabled ->
    [true] ✅ Send Music Covers
    *[false] ❌ Send Music Covers
}
btn-send-reactions = { $is_enabled ->
    [true] ✅ Send reactions
    *[false] ❌ Send reactions
}
btn-auto-translate = { $is_enabled ->
    [true] ✅ Auto translate titles
    *[false] ❌ Auto translate titles
}
btn-auto-caption = { $is_enabled ->
    [true] ✅ Auto caption
    *[false] ❌ Auto caption
}
btn-notifications = { $is_enabled ->
    [true] ✅ Send a notification
    *[false] ❌ Send a notification
}
btn-allow-playlists = { $is_enabled ->
    [true] ✅ Allow playlists
    *[false] ❌ Allow playlists
}

desc-send-raw = Send the uncompressed version of art images after the usual preview, so you can get the best quality.
desc-send-music-covers = Send music album covers along with audio files.
desc-send-reactions = Send reaction emojis when processing media.
desc-send-notifications = Control whether a sound notification is sent when media is delivered.
desc-auto-caption = Automatically add captions to media.
desc-auto-translate-titles = Automatically translate media titles to your language.
desc-allow-playlists = Allow downloading and processing of playlists.

setting-status-changed = { $is_enabled ->
    [true] Setting *{ $setting_name }* has been enabled!
    *[false] Setting *{ $setting_name }* has been disabled!
}

pick-language = Pick a language!
pick-title-language = Pick a title language!
language-changed = Language has been changed to *{ $language }*!
language-updated = Language updated!
title-language-changed = Title language has been changed to *{ $language }*!
title-language-updated = Title language updated!
setting-updated = Setting updated!
invalid-setting = Invalid setting!
error-updating = Error updating setting!
setting-changed = Setting *{ $setting }* has been { $status }!
enabled = enabled
disabled = disabled
enable = Enable
disable = Disable
back = Back
service-status-changed = Service { $service } { $status }!
blocked = blocked
unblocked = unblocked
settings-not-found = Settings not found!
no-permission-service = You don't have permission to edit these settings!
error-service-status = Error updating service status!
