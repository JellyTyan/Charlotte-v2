msg-hello =
    Hallo! 👋
    Schön dich zu sehen, { $name }.
    Schreib _/help_, wenn du Fragen hast.
    Schau mal bei @charlottesbasement vorbei — da teile ich Neuigkeiten und Kleinigkeiten.

msg-help =
    Das kann ich alles:
      /start — Hauptmenü
      /help — Hilfe & Info
      /settings — Einstellungen
      /saves — Meine Mediathek
      /copy — Medien in Zwischenablage kopieren
      /support — Projekt unterstützen
      /cancel — Download abbrechen

    <b>Unterstützte Plattformen</b> <i>(zum Ausklappen tippen)</i>:
    <blockquote expandable>
    <b>Musik:</b>
      • Spotify
      • Apple Music
      • Deezer
      • SoundCloud
      • YouTube Music
    <i>Ich finde den Track, das Albumcover und alle Tags.</i>

    <b>Video:</b>
      • YouTube (Videos, Shorts, Audio bis 100 MB, ⭐ 1 GB für Sponsoren)
      • TikTok (Videos und Fotos)
      • Instagram (Reels und Beiträge)
      • Twitter / X (Videos und Bilder)
      • Reddit (alle Medien aus Beiträgen)
      • BlueSky, Twitch, NicoVideo

    <b>Art:</b>
      • Pixiv
      • Pinterest
    </blockquote>

    🔍 <b>Inline-Modus (funktioniert in jedem Chat):</b>
      • <code>@{ $bot_username } &lt;Suchbegriff&gt;</code> — Suche nach Bildern und Memes (oder einfach <code>@{ $bot_username } </code> für aktuelle)
      • <code>@{ $bot_username } #music &lt;Track&gt;</code> — Musiksuche
      • <code>@{ $bot_username } #saved &lt;Suchbegriff&gt;</code> — Suche in deinen gespeicherten Medien
      • <code>@{ $bot_username } paste</code> — kopierte Medien einfügen (Zwischenablage hält 1 Stunde)
    <i>Um Medien von mir in deiner Bibliothek zu speichern, antworte darauf mit <code>/save &lt;Name&gt;</code>.</i>

    Schick mir einfach einen Link und ich kümmere mich darum.

processing = Sekunde, bin schon dran... ⏳
added-to-queue = Du bist in der Warteschlange, vor dir sind noch { $count }.
starting-download = Download startet! 🚀
invalid-callback = Huch, dieser Button funktioniert nicht mehr, tut mir leid.
url-expired = Der Link ist abgelaufen — schickst du mir einen neuen?
setting-changed = Fertig! *{ $setting }* ist jetzt { $status }.
premium-granted = Juhu, du hast kostenlosen Premium-Zugang erhalten! Lade so viel du willst 🎉


# System & Payment
service-disabled = Dieser Dienst ist gerade vorübergehend deaktiviert, tut mir leid. Versuch es etwas später.
support-invoice-title = { $amount } ⭐ spenden
support-invoice-desc = Unterstütze Charlottes Entwicklung!
support-success = Vielen Dank für deine Unterstützung 🧡
support-invalid-amount = Betrag muss zwischen 1 und 100.000 Sternen liegen. Bitte versuche es erneut:
support-invalid-number = Bitte gib eine Zahl zwischen 1 und 100.000 ein:
payment-invalid-data = Fehler: ungültige Zahlungsdaten.
payment-invalid-format = Fehler: ungültiges Datenformat.
payment-link-expired = Fehler: Link abgelaufen. Bitte versuche es erneut.
payment-success-download = Danke für deine Unterstützung! Download startet...
payment-error-refund = Beim Verarbeiten ist ein Fehler aufgetreten. Sterne erstattet...
premium-expired = Dein Sponsoren-Premium ist abgelaufen. Du kannst es jederzeit verlängern 🌟
bot-ad-disable-alert = Das Deaktivieren der Bot-Werbung erfordert ein aktives Sponsoring (100 Sterne).
download-failed-refund = Konnte das leider nicht herunterladen, tut mir leid. Sterne erstattet.
not-your-request = Das ist nicht deine Anfrage.
action-cancelled = Abgebrochen.
banned-global = Du bist global gesperrt.
banned-chat = Du bist in diesem Chat gesperrt.
too-many-requests = Zu viele Anfragen hintereinander, bitte warte einen Moment.
menu-not-yours = Dieses Menü ist nicht für dich, tut mir leid.
general-error = Huch, da ist etwas schiefgelaufen. Magst du es später nochmal versuchen?
btn-close = ✕ Schließen

# YouTube Trim
yt-trim-sponsor-only = Videos zuschneiden ist nur für Sponsoren verfügbar.
yt-trim-ask-range = Sende den Zeitbereich zum Zuschneiden, z. B. <code>01:20-02:45</code> oder <code>90-165</code>:
yt-trim-invalid-range = Das Format habe ich nicht verstanden, sorry. Verwende START-ENDE, z. B. <code>1:30-2:45</code>. Nochmal?
yt-trim-end-before-start = Endzeit muss nach der Startzeit liegen. Nochmal versuchen?
yt-trim-processing = Schneide Clip zu, warte bitte einen Moment...
yt-trim-out-of-bounds = Dieser Bereich liegt außerhalb der Videodauer ({ $duration }). Nochmal versuchen?
yt-btn-full = 🎬 Ganzes Video
yt-btn-trim-locked = ★ Zuschneiden
yt-btn-cancel = Abbrechen
yt-ask-quality = Qualität wählen:
yt-btn-video = Video herunterladen
yt-btn-audio = Audio herunterladen
yt-btn-continue = Weiter
yt-btn-advanced = Erweiterte Einstellungen
yt-btn-trim = Zuschneiden
yt-btn-trim-active = ✓ Zuschneiden
yt-btn-back = Zurück
yt-label-channel = Kanal: { $uploader }
yt-label-duration = Dauer: { $duration }

btn-add-group = ➕ Zu Gruppe hinzufügen
btn-my-settings = ⚙️ Meine Einstellungen
already-downloading = Ich lade schon etwas für dich herunter, warte kurz 🐾


# Errors
error-invalid-url = Huch, mit diesem Link stimmt etwas nicht 🥺
error-private-content = Tut mir leid, das ist privat — da komme ich nicht ran.
error-large-file = Was für eine riesige Datei... So große Dateien kann ich noch nicht versenden, sorry 😔
error-not-allowed = Tut mir leid, diese Funktion ist in den Chateinstellungen deaktiviert.
error-internal = Huch, in mir ist etwas kaputtgegangen... Magst du es gleich nochmal versuchen?
error-not-found = Ich habe überall gesucht, aber unter diesem Link nichts gefunden. Sicher nicht gelöscht?
error-region-restricted = Tut mir leid, dieser Inhalt ist in meiner Region gesperrt — kann ihn nicht abrufen.
error-age-restricted = Das ist Inhalt ab 18, da habe ich leider keinen Zugriff, sorry 🙈
error-download-canceled = Alles klar, Download abgebrochen.
error-generic = Huch, da ist etwas schiefgelaufen, tut mir leid.
error-preview-only = Konnte nur eine 30-Sekunden-Vorschau herunterladen, nicht den ganzen Track, sorry.

download-cancel = Breche ab! Schon gestoppt.
download-no-found = Hmm, hier gibt es nichts abzubrechen.
downloading-tracks = Sammle Tracks...
download-stats = Fertig: { $success } heruntergeladen, { $failed } fehlgeschlagen.
all-tracks-success = Alle Tracks heruntergeladen, juhu! 🎉
total-tracks = Tracks insgesamt: { $count }
release-date = Veröffentlicht: { $date }
year = Jahr: { $year }
playlist-stopped = Playlist-Download gestoppt.
skipped-track = Track übersprungen: { $title }
yt-btn-topich = TOPICH
yt-sponsor-only = Diese Funktion ist nur für Sponsoren, tut mir leid!

# Sponsor & Support
support-text =
    Charlotte ist ein Herzensprojekt, das mit Liebe gepflegt wird. Ich helfe dir, Medien ohne Werbung und Einschränkungen zu speichern.

    Die Server kosten etwa 12€ im Monat, die aus eigener Tasche bezahlt werden. Der Bot bleibt immer kostenlos und offen für alle.

    <b>Sponsoren-Vorteile:</b>
    • YouTube: Videos bis 1 GB statt 100 MB
    • YouTube: TOPICH, maximale Qualität als Originaldatei
    • YouTube: Videos vor dem Senden zuschneiden
    • Instagram und TikTok in bester Qualität
    • NSFW-Medien von Twitter, Reddit und Pixiv
    • Bis zu 1000 gespeicherte Medien statt 200

    <b>So sammeln sich Sterne:</b>
    Alle Sterne, die du schickst, landen in deiner Spardose, auch 10 oder 50 auf einmal. Je 100 ⭐ gibt es 30 Tage Sponsoring, und wenn es schon aktiv ist, werden die Tage einfach angehängt. Bei jeder Spende kommt dein Name auf die Dankestafel.{ $status }

    Jede Unterstützung bedeutet mir unglaublich viel, danke, dass du da bist ⭐

support-status-lifetime =
    ⭐ <b>Dein Status:</b> Sponsor (dauerhaft) 🌟

support-status-active =
    ⭐ <b>Dein Status:</b> Sponsor (bis { $date })
    In der Spardose: { $progress }/100 ⭐ bis zur nächsten Verlängerung

support-status-progress =
    ⭐ In der Spardose: { $progress }/100 ⭐ bis zum Sponsoring

support-btn-sponsor = ⭐ 30 Tage Sponsoring (100 ⭐)
support-btn-coffee = ☕ Kaffee spendieren
support-btn-stars = ⭐ Sterne senden
support-btn-supporters = 🤍 Dankestafel
support-btn-back = 🔙 Zurück

support-wall-empty =
    <b>Dankestafel</b>

    Hier ist noch niemand eingetragen. Aber du kannst der Erste sein, der mich unterstützt und hier erscheint ⭐

support-wall-text =
    <b>Dankestafel</b>

    Vielen Dank an alle, die mir helfen zu laufen und zu wachsen:

    { $supporters }

    Eure Unterstützung bedeutet mir sehr viel ⭐

support-choose-stars = Wähle, wie viele Sterne du zur Unterstützung senden möchtest:
support-stars-ten = ⭐ 10 Sterne
support-stars-fifty = ⭐ 50 Sterne
support-stars-hundred = ⭐ 100 Sterne
support-stars-custom = ✏️ Eigener Betrag

support-custom-prompt = Schreibe, wie viele Sterne du senden möchtest (1 bis 100.000):

support-success-sponsor =
    Vielen lieben Dank für { $stars } ⭐!
    Sponsoring aktiviert für { $days } Tage (bis { $date })! Dein Name steht jetzt auf der Dankestafel ⭐

support-success-tip =
    Vielen lieben Dank für { $stars } ⭐!
    Deine Unterstützung bedeutet mir viel! In der Spardose: { $progress }/100 ⭐ bis zum Sponsoring ⭐

# Report command
report-reply-required = Antworte mit <code>/report</code> auf meine Nachricht, bei der etwas nicht geklappt hat.
report-not-bot-message = Dieser Befehl funktioniert nur als Antwort auf meine Nachrichten 🐾
report-success = Danke fürs Melden! Ich habe alles an den Entwickler weitergeleitet, wir kümmern uns darum 🧡
error-send-failed = ❌ Fehler beim Senden der Medien an Telegram. Die Datei ist möglicherweise beschädigt oder wurde abgelehnt.
yt-trim-invalid-format = Konnte das Format leider nicht erkennen. Verwende START-ENDE, z. B. <code>1:30-2:45</code>. Noch einmal versuchen?
