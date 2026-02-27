settings-welcome = Hey! 👋 Here you can tweak everything to your liking. Make yourself at home!
settings-back = 🔙 Back
settings-title = Settings
settings-no-permission = Aww, you don't have permission to change these settings!
settings-saved = Nice! Settings updated successfully! ✨
settings-no-allowed-groups = This setting isn't available for groups, sorry!
settings-no-allowed-dm = This setting isn't for private chats, sorry!

btn-language = Language
btn-title-language = Caption language
btn-blocked-services = Blocked services

btn-send-raw = { $is_enabled ->
    [true] ✅ Send art as File (Best Quality)
    *[false] ❌ Send art as File (Best Quality)
}
btn-send-music-covers = { $is_enabled ->
    [true] ✅ Send Music Covers
    *[false] ❌ Send Music Covers
}
btn-send-reactions = { $is_enabled ->
    [true] ✅ Send Fun Reactions
    *[false] ❌ Send Fun Reactions
}
btn-auto-translate = { $is_enabled ->
    [true] ✅ Auto-translate captions
    *[false] ❌ Auto-translate captions
}
btn-auto-caption = { $is_enabled ->
    [true] ✅ Captions
    *[false] ❌ Captions
}
btn-notifications = { $is_enabled ->
    [true] ✅ Notifications
    *[false] ❌ Notifications
}
btn-allow-playlists = { $is_enabled ->
    [true] ✅ Allow Playlists
    *[false] ❌ Allow Playlists
}

desc-send-raw = I'll send art as uncompressed files so you get the absolute best quality! 🎨
desc-send-music-covers = I'll attach the album art to every song I download for you. 🎵
desc-send-reactions = I'll react with emojis to show you I'm working! ⚡
desc-send-notifications = Disable this to receive media without notification sound. 🔕
desc-auto-caption = I'll automatically verify and add captions to media. 📝
desc-auto-translate-titles = I'll translate video captions to your language automatically! 🌍
desc-allow-playlists = I'll handle full playlists for you (use carefully!). 📂
desc-lossless-mode = I'll try to find Hi-Res songs for you! But I don't promise I'll find it or if it's the right one. 🎧

setting-status-changed = { $is_enabled ->
    [true] Yay! Setting *{ $setting_name }* is now enabled!
    *[false] Got it! Setting *{ $setting_name }* is now disabled!
}

pick-language = Choose your language! 🌍
pick-title-language = Choose language for captions!
language-changed = Awesome! I'll speak *{ $language }* now!
language-updated = Language updated!
title-language-changed = Captions will be in *{ $language }* now!
title-language-updated = Caption language updated!
setting-updated = All set! Updated.
invalid-setting = Oops, that setting looks weird!
error-updating = Oh no, couldn't update that. Try again?
setting-changed = Done! *{ $setting }* is now { $status }!
enabled = enabled
disabled = disabled
enable = Enable
disable = Disable
back = Back
service-status-changed = Service { $service } is now { $status }!
blocked = blocked
unblocked = unblocked
settings-not-found = Hmm, can't find those settings!
no-permission-service = You aren't allowed to touch these settings!
error-service-status = Couldn't update service status. :(
current-status = Current status: { $status }

btn-configure-services = ⚙️ Configure Services
settings-select-service = Select a service to configure:
settings-service-title = ⚙️ **{ $name } Settings**
btn-lossless = { $is_enabled ->
    [true] ✅ LOSSLESS
    *[false] ❌ LOSSLESS
}
btn-service-enabled = { $is_enabled ->
    [true] ✅ Enabled
    *[false] ❌ Enabled
}
