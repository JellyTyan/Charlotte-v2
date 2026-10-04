saves-usage = So speicherst du in der Mediathek:
    Antworte auf eine Nachricht mit Video, Foto, GIF oder Audio mit <code>/save &lt;Name&gt;</code>

saves-no-name = Gib einen Namen für das gespeicherte Medium an, z. B. <code>/save Kätzchen</code>.

saves-name-too-long = Der Name ist zu lang, maximal 128 Zeichen.

saves-no-media = Habe in dieser Nachricht keine passenden Medien gefunden (Video, Foto, Audio oder GIF).

saves-bot-only = Du kannst nur Medien speichern, die über mich heruntergeladen wurden. Antworte mit <code>/save &lt;Name&gt;</code> auf meine Nachricht.

saves-limit-reached = Limit gespeicherter Medien erreicht (<b>{ $current }/{ $limit }</b>). Nicht mehr Benötigtes über /saves löschen?

saves-saved = { $emoji } Gespeichert als «<b>{ $label }</b>»!

    { $status }

    Du kannst es in jedem Chat senden:
    <code>@{ $bot_username } { $label }</code>

    Alle deine gespeicherten Medien: /saves

saves-status-private = 🔒 <i>Privat, nur für dich sichtbar</i>
saves-status-public = 🌐 <i>Öffentlich, für jeden in der Suche sichtbar</i>
saves-status-pending = ⏳ <i>Zur Überprüfung für die öffentliche Bibliothek eingereicht</i>

saves-btn-make-public = 🌐 Öffentlich machen
saves-btn-make-private = 🔒 Privat machen
saves-toast-public = Meme ist jetzt öffentlich in der Suche!
saves-toast-pending = Zur Überprüfung gesendet. Sobald bestätigt, erscheint es in der öffentlichen Suche.
saves-toast-private = Versteckt, jetzt nur für dich sichtbar.

saves-empty = Deine Mediathek ist aktuell noch leer.

    Um Medien hinzuzufügen, antworte auf ein heruntergeladenes Video, Foto oder Audio mit <code>/save &lt;Name&gt;</code>

saves-header = <b>Deine Mediathek</b> ({ $count }):

saves-deleted-toast = Aus gespeicherten Medien entfernt.
saves-missing-toast = Konnte dieses Element nicht finden, vielleicht wurde es schon gelöscht?

saves-mod-approved =
    <b>Dein gespeichertes Medium wurde genehmigt!</b> 🎉

    Meme «<b>{ $label }</b>» hat die Moderation bestanden und ist jetzt in der öffentlichen Suche für alle sichtbar.

saves-mod-rejected =
    <b>Veröffentlichungsantrag abgelehnt</b>

    Meme «<b>{ $label }</b>» hat die Moderation nicht bestanden, bleibt aber in deinen privaten Sicherungen sicher 🔒

copy-usage = So kopierst du Medien in die Zwischenablage:
    Antworte auf eine Nachricht mit Video, Foto, GIF oder Audio mit <code>/copy</code>

copy-bot-only = Es können nur Medien kopiert werden, die von mir stammen. Antworte mit <code>/copy</code> auf meine Nachricht.

copy-no-media = Habe in dieser Nachricht keine passenden Medien gefunden (Video, Foto, Audio oder GIF).

copy-copied = <b>In Zwischenablage kopiert!</b>

    Um es in einem beliebigen Chat einzufügen, schreibe:
    <code>@{ $bot_username } paste</code>

    <i>Zwischenablage bleibt 1 Stunde erhalten</i>

saves-banned-alert = Dein Zugriff zum Einreichen von Memes in die öffentliche Bibliothek wurde eingeschränkt.
saves-mod-banned =
    <b>Zugriff eingeschränkt</b>

    Ein Administrator hat dir das Vorschlagen von Memes für die öffentliche Bibliothek untersagt. Deine privaten Medien bleiben erhalten 🔒

saves-label-reserved = Der Name «<b>{ $label }</b>» ist vom Bot für Systembefehle reserviert. Bitte wähle einen anderen!
saves-label-trash = Der Name ist ungültig oder besteht nur aus Symbolen. Bitte wähle einen aussagekräftigen Namen.
saves-dupe-media = Diese Datei ist bereits als «<b>{ $existing_label }</b>» in deiner Mediathek gespeichert.
saves-dupe-public = Diese Datei existiert bereits in der öffentlichen Meme-Bibliothek!
saves-rename-remoderation = Name geändert — zur erneuten Moderation eingereicht, bevor sie in der öffentlichen Suche erscheint.

saves-list-hint = Wähle ein Element zum Ansehen und Verwalten:
saves-card =
    { $emoji } <b>{ $label }</b>

    { $status }
    👁 Verwendungen: <b>{ $uses }</b>
    📅 Hinzugefügt: <b>{ $date }</b>

    <i>In jedem Chat senden:</i>
    <code>@{ $bot_username } { $label }</code>
saves-btn-preview = 👁 Vorschau
saves-btn-send = 🚀 In den Chat
saves-btn-rename = ✏️ Umbenennen
saves-btn-delete = 🗑 Löschen
saves-btn-back = ◀️ Zur Liste
saves-btn-close = ❌ Schließen
saves-btn-cancel = ◀️ Abbrechen
saves-foreign-library = ❌ Das ist nicht deine Mediathek
saves-preview-failed = Vorschau konnte nicht gesendet werden.
saves-rename-prompt =
    ✏️ <b>Umbenennen</b> «{ $label }»

    Sende den neuen Namen als Nachricht (max. { $max } Zeichen):
saves-renamed = ✅ Name aktualisiert: «<b>{ $label }</b>»
saves-label-word-too-long = Ein Wort im Namen ist zu lang. Bitte wähle einen kürzeren Namen.
