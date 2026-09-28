settings-welcome = Hallo! Hier kannst du alles nach deinen Wünschen anpassen, mach es dir gemütlich.
settings-back = 🔙 Zurück
settings-title = Einstellungen
settings-no-permission = Huch, du hast keine Berechtigung, diese Einstellungen zu ändern.
settings-saved = Einstellungen aktualisiert! ✨
settings-no-allowed-groups = Diese Einstellung ist in Gruppen nicht verfügbar, tut mir leid.
settings-no-allowed-dm = Diese Einstellung kann nicht im privaten Chat geändert werden.

btn-language = Sprache
btn-title-language = Beschriftungen
btn-blocked-services = Dienste-Sperrliste

btn-send-raw = { $is_enabled ->
    [true] 🟢 Als Datei
    *[false] ⚪ Als Datei
}
btn-send-music-covers = { $is_enabled ->
    [true] 🟢 Cover
    *[false] ⚪ Cover
}
btn-send-reactions = { $is_enabled ->
    [true] 🟢 Reaktionen
    *[false] ⚪ Reaktionen
}
btn-negativity = { $is_enabled ->
    [true] 🟢 Frech-Modus
    *[false] ⚪ Frech-Modus
}
btn-auto-translate = { $is_enabled ->
    [true] 🟢 Übersetzen
    *[false] ⚪ Übersetzen
}
btn-auto-caption = { $is_enabled ->
    [true] 🟢 Beschriftung
    *[false] ⚪ Beschriftung
}
btn-notifications = { $is_enabled ->
    [true] 🟢 Benachrichtigungen
    *[false] ⚪ Benachrichtigungen
}
btn-allow-playlists = { $is_enabled ->
    [true] 🟢 Playlists
    *[false] ⚪ Playlists
}
btn-allow-nsfw = { $is_enabled ->
    [true] 🟢 NSFW
    *[false] ⚪ NSFW
}

desc-send-raw = Ich sende Medien als Dateien — so bleibt die beste Qualität erhalten.
desc-send-music-covers = Hänge Albumcover an jeden Track an.
desc-send-reactions = Ich setze Emoji-Reaktionen, damit du den Fortschritt sehen kannst.
desc-negativity-mode = Ich verwende etwas frechere Emojis bei den Reaktionen.
desc-send-notifications = Deaktiviere dies, wenn du Medien lautlos erhalten möchtest.
desc-auto-caption = Ich prüfe und füge automatisch Beschreibungen zu Medien hinzu.
desc-auto-translate-titles = Übersetze Videobeschreibungen in deine Sprache.
desc-allow-playlists = Ganze Playlists herunterladen — sei vorsichtig damit.
desc-allow-nsfw = NSFW-Inhalte in diesem Chat erlauben.
desc-lossless-mode = Ich versuche, eine Hi-Res-Version des Tracks zu finden. Keine Garantie.

setting-status-changed = { $is_enabled ->
    [true] *{ $setting_name }* aktiviert!
    *[false] *{ $setting_name }* deaktiviert.
}

pick-language = Sprache wählen 🌍
pick-title-language = Sprache für Beschriftungen wählen
language-changed = Ich spreche jetzt *{ $language }*!
language-updated = Sprache aktualisiert.
title-language-changed = Beschriftungen sind jetzt auf *{ $language }*.
title-language-updated = Sprache der Beschriftungen aktualisiert.
setting-updated = Erledigt, aktualisiert.
invalid-setting = Hmm, diese Einstellung kenne ich nicht.
error-updating = Konnte nicht aktualisiert werden, tut mir leid. Versuchen wir es nochmal?
enabled = aktiviert
disabled = deaktiviert
enable = Aktivieren
disable = Deaktivieren
back = Zurück
service-status-changed = Dienst { $service } ist jetzt { $status }.
blocked = gesperrt
unblocked = entsperrt
settings-not-found = Konnte diese Einstellungen nicht finden.
no-permission-service = Du darfst diese Einstellungen nicht ändern.
error-service-status = Status des Dienstes konnte nicht aktualisiert werden, sorry.
current-status = Aktueller Status: { $status }

btn-configure-services = ⚙️ Dienste konfigurieren
settings-select-service = Wähle einen Dienst zur Konfiguration:
settings-service-title = **{ $name } Einstellungen**
btn-lossless = { $is_enabled ->
    [true] 🟢 LOSSLESS
    *[false] ⚪ LOSSLESS
}
btn-service-enabled = { $is_enabled ->
    [true] 🟢 Dienst
    *[false] ⚪ Dienst
}

btn-news-spam = { $is_enabled ->
    [true] 🟢 Rundschreiben
    *[false] ⚪ Rundschreiben
}
desc-news-spam = Erlaube mir, dir Neuigkeiten und Updates zu senden.

btn-bot-sign = { $is_enabled ->
    [true] 🟢 Bot Ad 🧡
    *[false] ⚪ Bot Ad 🧡
}
desc-bot-sign = Signatur „Charlotte 🧡“ zu Medien hinzufügen. Deaktivieren ist kostenlos.

btn-simple-mode = { $is_enabled ->
    [true] 🟢 Einfacher Modus
    *[false] ⚪ Einfacher Modus
}
desc-simple =
    Einfaches YouTube-Interface:
    Ein — nur zwei Buttons (Video oder Audio), Download in bester Qualität bis 100 MB (bis 1 GB für Sponsoren).
    Aus — Auflösungswahl, Video zuschneiden (für Sponsoren).

btn-youtube-ui-mode = YouTube-Interface
yt-ui-mode-simple = Einfach
yt-ui-mode-balance = Ausgewogen
yt-ui-mode-advanced = Erweitert
desc-youtube-ui-mode =
    Wähle deinen Download-Stil für YouTube:

    • Einfach — 2 Buttons (Video / Audio), Download mit einem Klick.
    • Ausgewogen — Buttons bester Qualitäten mit einem Klick + Zugang zu erweiterten Einstellungen.
    • Erweitert — freie Wahl der Qualität, Audiospur und Video zuschneiden (Trim).

btn-experimental = 🧪 Neue Funktionen
desc-experimental-features =
    Experimentelle Funktionen funktionieren nur in neueren offiziellen Telegram-Apps und können sich in älteren oder Drittanbieter-Clients instabil verhalten.

btn-ephemeral-messages = { $is_enabled ->
    [true] 🟢 Vergängliche Nachrichten
    *[false] ⚪ Vergängliche Nachrichten
}
desc-ephemeral-messages = Servicenachrichten in Gruppen als vergängliche Nachrichten senden, die nur für dich sichtbar sind. Wenn aus — normale Nachrichten mit automatischer Löschung.
btn-chat-banned-users = 🚫 Chat-Sperrliste
desc-chat-banned-users = Benutzer verwalten, die in diesem Chat gesperrt sind.
cban-usage = Gib die Benutzer-ID an oder antworte auf eine Nachricht: <code>/cban &lt;user_id&gt;</code>
cban-cannot-ban-self = Du kannst dich nicht selbst sperren.
cban-cannot-ban-admin = Chat-Administratoren können nicht gesperrt werden.
cban-cannot-ban-bot = Der Bot kann nicht gesperrt werden.
cban-success = Benutzer <code>{ $user_id }</code> wurde in diesem Chat gesperrt.
cban-already-banned = Benutzer <code>{ $user_id }</code> ist in diesem Chat bereits gesperrt.
cunban-usage = Gib die Benutzer-ID an oder antworte auf eine Nachricht: <code>/cunban &lt;user_id&gt;</code>
cunban-not-banned = Benutzer <code>{ $user_id }</code> ist in diesem Chat nicht gesperrt.
cunban-success = Benutzer <code>{ $user_id }</code> wurde in diesem Chat entsperrt.
cbanlist-empty = Keine gesperrten Benutzer in diesem Chat.
cbanlist-title = <b>Chat-Sperrliste:</b>
btn-unban-user = ❌ Entsperren { $user_id }
