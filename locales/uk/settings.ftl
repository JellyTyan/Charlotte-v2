settings-welcome = Привіт! Тут можна все налаштувати під себе, не соромся.
settings-back = 🔙 Назад
settings-title = Налаштування
settings-no-permission = Ой, у тебе немає прав змінювати ці налаштування.
settings-saved = Налаштування оновила! ✨
settings-no-allowed-groups = Це налаштування недоступне в групах, вибач.
settings-no-allowed-dm = Це налаштування не можна змінювати в приватних повідомленнях.

btn-language = Мова
btn-title-language = Описи
btn-blocked-services = Блокування сервісів

btn-send-raw = { $is_enabled ->
    [true] 🟢 Файлом
    *[false] ⚪ Файлом
}
btn-send-music-covers = { $is_enabled ->
    [true] 🟢 Обкладинки
    *[false] ⚪ Обкладинки
}
btn-send-reactions = { $is_enabled ->
    [true] 🟢 Реакції
    *[false] ⚪ Реакції
}
btn-negativity = { $is_enabled ->
    [true] 🟢 З перчинкою
    *[false] ⚪ З перчинкою
}
btn-auto-translate = { $is_enabled ->
    [true] 🟢 Переклад
    *[false] ⚪ Переклад
}
btn-auto-caption = { $is_enabled ->
    [true] 🟢 Описи
    *[false] ⚪ Описи
}
btn-notifications = { $is_enabled ->
    [true] 🟢 Сповіщення
    *[false] ⚪ Сповіщення
}
btn-allow-playlists = { $is_enabled ->
    [true] 🟢 Плейлісти
    *[false] ⚪ Плейлісти
}
btn-allow-nsfw = { $is_enabled ->
    [true] 🟢 NSFW
    *[false] ⚪ NSFW
}

desc-send-raw = Надсилатиму медіа файлами — так якість найвища.
desc-send-music-covers = Додаватиму обкладинку до кожного треку.
desc-send-reactions = Ставитиму емодзі-реакції, щоб ти бачив(-ла) процес.
desc-negativity-mode = Використовуватиму трішки зухваліші емодзі в реакціях.
desc-send-notifications = Вимкни, якщо хочеш отримувати медіа без звуку.
desc-auto-caption = Сама перевірю і додам опис до медіа.
desc-auto-translate-titles = Перекладатиму описи відео твоєю мовою.
desc-allow-playlists = Завантажуватиму цілі плейлісти — обережно з цим.
desc-allow-nsfw = Дозволити NSFW-вміст у цьому чаті.
desc-lossless-mode = Спробую знайти Hi-Res версію пісні. Не обіцяю, що вийде.

setting-status-changed = { $is_enabled ->
    [true] Увімкнула *{ $setting_name }*!
    *[false] Вимкнула *{ $setting_name }*.
}

pick-language = Обери мову 🌍
pick-title-language = Обери мову для описів
language-changed = Тепер розмовляю такою мовою: *{ $language }*!
language-updated = Мову оновила.
title-language-changed = Тепер описи будуть такою мовою: *{ $language }*.
title-language-updated = Мову описів оновила.
setting-updated = Готово, оновила.
invalid-setting = Хм, не знаю такого налаштування.
error-updating = Не вийшло оновити, вибач. Спробуємо ще раз?
enabled = увімкнено
disabled = вимкнено
enable = Увімкнути
disable = Вимкнути
back = Назад
service-status-changed = Сервіс { $service } тепер { $status }.
blocked = заблоковано
unblocked = розблоковано
settings-not-found = Не можу знайти ці налаштування.
no-permission-service = Тобі не можна змінювати ці налаштування.
error-service-status = Не вийшло оновити статус сервісу, вибач.
current-status = Поточний статус: { $status }

btn-configure-services = ⚙️ Налаштування сервісів
settings-select-service = Обери сервіс для налаштування:
settings-service-title = **Налаштування { $name }**
btn-lossless = { $is_enabled ->
    [true] 🟢 LOSSLESS
    *[false] ⚪ LOSSLESS
}
btn-service-enabled = { $is_enabled ->
    [true] 🟢 Сервіс
    *[false] ⚪ Сервіс
}

btn-news-spam = { $is_enabled ->
    [true] 🟢 Розсилка
    *[false] ⚪ Розсилка
}
desc-news-spam = Дозволити надсилати тобі новини й оновлення.

btn-bot-sign = { $is_enabled ->
    [true] 🟢 Bot Ad 🧡
    *[false] ⚪ Bot Ad 🧡
}
desc-bot-sign = Додавати підпис «Charlotte 🧡» до медіа. Вимкнути можна безкоштовно.

btn-simple-mode = { $is_enabled ->
    [true] 🟢 Простий режим
    *[false] ⚪ Простий режим
}
desc-simple =
    Простий інтерфейс YouTube:
    Увімкнено — лише дві кнопки (Відео або Аудіо), завантаження в максимальній якості до 100 МБ (до 1 ГБ для Спонсорів).
    Вимкнено — вибір роздільної здатності, обрізка відео (для Спонсорів).

btn-youtube-ui-mode = Інтерфейс YouTube
yt-ui-mode-simple = Простий
yt-ui-mode-balance = Збалансований
yt-ui-mode-advanced = Розширений
desc-youtube-ui-mode =
    Обери стиль інтерфейсу для завантаження з YouTube:

    • Простий — 2 кнопки (Відео / Аудіо), завантаження в один клік.
    • Збалансований — кнопки найкращих якостей в один клік + доступ до розширених налаштувань.
    • Розширений — вибір будь-якої якості, аудіодоріжки та обрізки відео (Trim).

btn-experimental = 🧪 Нові функції
desc-experimental-features =
    Експериментальні функції працюють лише в нових офіційних клієнтах Telegram і можуть поводитися нестабільно в старих або сторонніх.

btn-ephemeral-messages = { $is_enabled ->
    [true] 🟢 Ефемерні повідомлення
    *[false] ⚪ Ефемерні повідомлення
}
desc-ephemeral-messages = Надсилати службові повідомлення в групах як ефемерні, видимі лише тобі. Якщо вимкнено — надсилатиму звичайні повідомлення з автовидаленням.
btn-chat-banned-users = 🚫 Бан-лист чату
desc-chat-banned-users = Керування користувачами, заблокованими в цьому чаті.
cban-usage = Вкажи ID користувача або дай відповідь на його повідомлення: <code>/cban &lt;user_id&gt;</code>
cban-cannot-ban-self = Не можна заблокувати самого себе.
cban-cannot-ban-admin = Не можна заблокувати адміністратора чату.
cban-cannot-ban-bot = Не можна заблокувати бота.
cban-success = Користувач <code>{ $user_id }</code> заблокований у цьому чаті.
cban-already-banned = Користувач <code>{ $user_id }</code> вже заблокований у цьому чаті.
cunban-usage = Вкажи ID користувача або дай відповідь на його повідомлення: <code>/cunban &lt;user_id&gt;</code>
cunban-not-banned = Користувач <code>{ $user_id }</code> не заблокований у цьому чаті.
cunban-success = Користувач <code>{ $user_id }</code> розблокований у цьому чаті.
cbanlist-empty = У цьому чаті немає заблокованих користувачів.
cbanlist-title = <b>Бан-лист чату:</b>
btn-unban-user = ❌ Розблокувати { $user_id }
