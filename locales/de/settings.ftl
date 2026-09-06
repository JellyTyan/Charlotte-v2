settings-welcome = Hey! 👋 Hier kannst du alles nach deinem Geschmack anpassen. Fühl dich wie zuhause!
settings-back = 🔙 Zurück
settings-title = Einstellungen
settings-no-permission = Aww, du hast keine Berechtigung, diese Einstellungen zu ändern!
settings-saved = Super! Einstellungen aktualisiert! ✨
settings-no-allowed-groups = Diese Einstellung gibt's nicht für Gruppen, sorry!
settings-no-allowed-dm = Diese Einstellung ist nicht für Privatchats, sorry!

btn-language = Sprache
btn-title-language = Beschreibungen
btn-blocked-services = Blockierte Dienste

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
    [true] 🟢 Negativität
    *[false] ⚪ Negativität
}
btn-auto-translate = { $is_enabled ->
    [true] 🟢 Übersetzung
    *[false] ⚪ Übersetzung
}
btn-auto-caption = { $is_enabled ->
    [true] 🟢 Beschreibungen
    *[false] ⚪ Beschreibungen
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

desc-send-raw = Ich werde Medien als Dateien für die beste Qualität senden! 🎨
desc-send-music-covers = Ich hänge das Album-Cover an jeden Song an. 🎵
desc-send-reactions = Ich reagiere mit Emojis, damit du siehst, dass ich arbeite! ⚡
desc-negativity-mode = Ich werde einige toxische Emojis verwenden! 😈
desc-send-notifications = Deaktivieren, um Medien ohne Benachrichtigungston zu empfangen. 🔕
desc-auto-caption = Ich überprüfe und füge automatisch Beschreibungen hinzu. 📝
desc-auto-translate-titles = Ich übersetze Videobeschreibungen automatisch in deine Sprache! 🌍
desc-allow-playlists = Ich lade ganze Playlists herunter (vorsichtig nutzen!). 📂
desc-allow-nsfw = NSFW-Inhalte in diesem Chat erlauben. 🔞
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
    [true] 🟢 LOSSLESS
    *[false] ⚪ LOSSLESS
}
btn-service-enabled = { $is_enabled ->
    [true] 🟢 Dienst
    *[false] ⚪ Dienst
}

btn-news-spam = { $is_enabled ->
    [true] 🟢 News
    *[false] ⚪ News
}
desc-news-spam = Erlaube dem Bot, dir Neuigkeiten und Updates zu senden! 📰

btn-bot-sign = { $is_enabled ->
    [true] 🟢 Bot Ad 🧡
    *[false] ⚪ Bot Ad 🧡
}
desc-bot-sign = Signatur „Charlotte 🧡“ an heruntergeladene Medien anhängen. Das Deaktivieren ist völlig kostenlos! ✨

btn-simple-mode = { $is_enabled ->
    [true] 🟢 Einfacher Modus
    *[false] ⚪ Einfacher Modus
}
desc-simple =
    Einfache YouTube-Benutzeroberfläche:
    Aktiviert — nur zwei Schaltflächen (Video oder Audio), Downloads in maximaler Qualität bis zu 100 MB (bis zu 1 GB für Sponsoren).
    Deaktiviert — Qualität wählen, Videos zuschneiden (für Sponsoren).

btn-youtube-ui-mode = YouTube-Benutzeroberfläche
yt-ui-mode-simple = Einfach
yt-ui-mode-balance = Ausgewogen
yt-ui-mode-advanced = Erweitert
desc-youtube-ui-mode =
    Wählen Sie den Stil der Benutzeroberfläche für YouTube-Downloads:
    
    • Einfach — 2 Schaltflächen (Video / Audio) für 1-Klick-Downloads.
    • Ausgewogen — Beste Qualitäten mit 1 Klick + Zugriff auf erweiterte Einstellungen.
    • Erweitert — Kontrollkästchen für Auflösungen, Tonspur und Video-Zuschnitt (Trim).
