settings-welcome = Hey! 👋 Hier kannst du alles nach deinem Geschmack anpassen. Fühl dich wie zuhause!
settings-back = 🔙 Zurück
settings-title = Einstellungen
settings-no-permission = Aww, du hast keine Berechtigung, diese Einstellungen zu ändern!
settings-saved = Super! Einstellungen aktualisiert! ✨
settings-no-allowed-groups = Diese Einstellung gibt's nicht für Gruppen, sorry!
settings-no-allowed-dm = Diese Einstellung ist nicht für Privatchats, sorry!

btn-language = Sprache
btn-title-language = Beschreibungssprache
btn-blocked-services = Blockierte Dienste

btn-send-raw = { $is_enabled ->
    [true] ✅ Art als Datei (Beste Qualität)
    *[false] ❌ Art als Datei (Beste Qualität)
}
btn-send-music-covers = { $is_enabled ->
    [true] ✅ Musik-Cover
    *[false] ❌ Musik-Cover
}
btn-send-reactions = { $is_enabled ->
    [true] ✅ Lustige Reaktionen
    *[false] ❌ Lustige Reaktionen
}
btn-auto-translate = { $is_enabled ->
    [true] ✅ Beschreibungen übersetzen
    *[false] ❌ Beschreibungen übersetzen
}
btn-auto-caption = { $is_enabled ->
    [true] ✅ Captions
    *[false] ❌ Captions
}
btn-notifications = { $is_enabled ->
    [true] ✅ Benachrichtigungen
    *[false] ❌ Benachrichtigungen
}
btn-allow-playlists = { $is_enabled ->
    [true] ✅ Playlists erlauben
    *[false] ❌ Playlists erlauben
}

desc-send-raw = Ich sende Arts als unkomprimierte Dateien für die absolut beste Qualität! 🎨
desc-send-music-covers = Ich hänge das Album-Cover an jeden Song an. 🎵
desc-send-reactions = Ich reagiere mit Emojis, damit du siehst, dass ich arbeite! ⚡
desc-send-notifications = Deaktivieren, um Medien ohne Benachrichtigungston zu empfangen. 🔕
desc-auto-caption = Ich überprüfe und füge automatisch Beschreibungen hinzu. 📝
desc-auto-translate-titles = Ich übersetze Videobeschreibungen automatisch in deine Sprache! 🌍
desc-allow-playlists = Ich lade ganze Playlists herunter (vorsichtig nutzen!). 📂
desc-lossless-mode = Ich werde versuchen, Hi-Res-Songs für dich zu finden! Aber ich verspreche nicht, dass ich sie finde oder ob es die richtigen sind. 🎧

setting-status-changed = { $is_enabled ->
    [true] Yay! Einstellung *{ $setting_name }* ist jetzt an!
    *[false] Alles klar! Einstellung *{ $setting_name }* ist jetzt aus!
}

pick-language = Wähle deine Sprache! 🌍
pick-title-language = Wähle die Sprache für Beschreibungen!
language-changed = Klasse! Ich spreche jetzt *{ $language }*!
language-updated = Sprache aktualisiert!
title-language-changed = Beschreibungen sind jetzt auf *{ $language }*!
title-language-updated = Beschreibungssprache aktualisiert!
setting-updated = Erledigt! Aktualisiert.
invalid-setting = Hoppla, das sieht komisch aus!
error-updating = Oh nein, konnte das nicht aktualisieren. Noch mal versuchen?
setting-changed = Fertig! *{ $setting }* ist jetzt { $status }!
enabled = aktiviert
disabled = deaktiviert
enable = Aktivieren
disable = Deaktivieren
back = Zurück
service-status-changed = Dienst { $service } ist jetzt { $status }!
blocked = blockiert
unblocked = entblockt
settings-not-found = Hmm, finde die Einstellungen nicht!
no-permission-service = Du darfst diese Einstellungen nicht anfassen!
error-service-status = Konnte den Dienst-Status nicht aktualisieren. :(
current-status = Aktueller Status: { $status }

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
