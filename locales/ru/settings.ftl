settings-welcome = Привет! Здесь можно настроить всё под себя, не стесняйся.
settings-back = 🔙 Назад
settings-title = Настройки
settings-no-permission = Ой, у тебя нет прав менять эти настройки.
settings-saved = Настройки обновила! ✨
settings-no-allowed-groups = Эта настройка недоступна в группах, прости.
settings-no-allowed-dm = Эту настройку нельзя менять в личке.

btn-language = Язык
btn-title-language = Описания
btn-blocked-services = Блокировка сервисов

btn-send-raw = { $is_enabled ->
    [true] 🟢 Файлом
    *[false] ⚪ Файлом
}
btn-send-music-covers = { $is_enabled ->
    [true] 🟢 Обложки
    *[false] ⚪ Обложки
}
btn-send-reactions = { $is_enabled ->
    [true] 🟢 Реакции
    *[false] ⚪ Реакции
}
btn-negativity = { $is_enabled ->
    [true] 🟢 Негативчик
    *[false] ⚪ Негативчик
}
btn-auto-translate = { $is_enabled ->
    [true] 🟢 Автоперевод
    *[false] ⚪ Автоперевод
}
btn-auto-caption = { $is_enabled ->
    [true] 🟢 Описание
    *[false] ⚪ Описание
}
btn-notifications = { $is_enabled ->
    [true] 🟢 Уведомления
    *[false] ⚪ Уведомления
}
btn-allow-playlists = { $is_enabled ->
    [true] 🟢 Плейлисты
    *[false] ⚪ Плейлисты
}
btn-allow-nsfw = { $is_enabled ->
    [true] 🟢 NSFW
    *[false] ⚪ NSFW
}

desc-send-raw = Буду отправлять медиа файлами — так качество выше.
desc-send-music-covers = Прикреплю обложку к каждому треку.
desc-send-reactions = Буду ставить эмодзи-реакции, чтобы ты видел(а) процесс.
desc-negativity-mode = Буду использовать чуть более дерзкие эмодзи в реакциях.
desc-send-notifications = Выключи, если хочешь получать медиа без звука.
desc-auto-caption = Сама проверю и добавлю описание к медиа.
desc-auto-translate-titles = Переведу описания видео на твой язык.
desc-allow-playlists = Скачаю целые плейлисты — аккуратно с этим.
desc-allow-nsfw = Разрешить NSFW-контент в этом чате.
desc-lossless-mode = Попробую найти Hi-Res версию песни. Не обещаю, что получится.

setting-status-changed = { $is_enabled ->
    [true] Включила *{ $setting_name }*!
    *[false] Выключила *{ $setting_name }*.
}

pick-language = Выбери язык 🌍
pick-title-language = Выбери язык для описаний
language-changed = Теперь говорю на *{ $language }*!
language-updated = Язык обновила.
title-language-changed = Теперь описания будут на *{ $language }*.
title-language-updated = Язык описаний обновила.
setting-updated = Готово, обновила.
invalid-setting = Хм, не знаю такой настройки.
error-updating = Не получилось обновить, прости. Попробуем ещё раз?
enabled = включено
disabled = выключено
enable = Включить
disable = Выключить
back = Назад
service-status-changed = Сервис { $service } теперь { $status }.
blocked = заблокирован
unblocked = разблокирован
settings-not-found = Не могу найти эти настройки.
no-permission-service = Тебе нельзя менять эти настройки.
error-service-status = Не получилось обновить статус сервиса, прости.
current-status = Текущий статус: { $status }

btn-configure-services = ⚙️ Настройка сервисов
settings-select-service = Выбери сервис для настройки:
settings-service-title = **Настройки { $name }**
btn-lossless = { $is_enabled ->
    [true] 🟢 LOSSLESS
    *[false] ⚪ LOSSLESS
}
btn-service-enabled = { $is_enabled ->
    [true] 🟢 Сервис
    *[false] ⚪ Сервис
}

btn-news-spam = { $is_enabled ->
    [true] 🟢 Рассылка
    *[false] ⚪ Рассылка
}
desc-news-spam = Разрешить присылать тебе новости и обновления.

btn-bot-sign = { $is_enabled ->
    [true] 🟢 Bot Ad 🧡
    *[false] ⚪ Bot Ad 🧡
}
desc-bot-sign = Добавлять подпись «Charlotte 🧡» к медиа. Отключить можно бесплатно.

btn-simple-mode = { $is_enabled ->
    [true] 🟢 Простой режим
    *[false] ⚪ Простой режим
}
desc-simple =
    Простой интерфейс YouTube:
    Включено — только две кнопки (Видео или Аудио), скачивание в максимальном качестве до 100 МБ (до 1 ГБ для Спонсоров).
    Выключено — выбор разрешения, обрезка видео (для Спонсоров).

btn-youtube-ui-mode = Интерфейс YouTube
yt-ui-mode-simple = Простой
yt-ui-mode-balance = Сбалансированный
yt-ui-mode-advanced = Расширенный
desc-youtube-ui-mode =
    Выбери стиль интерфейса для скачивания с YouTube:

    • Простой — 2 кнопки (Видео / Аудио), скачивание в один клик.
    • Сбалансированный — кнопки лучших качеств в один клик + доступ к расширенным настройкам.
    • Расширенный — выбор любого качества, аудиодорожки и обрезки видео (Trim).

btn-experimental = 🧪 Новые функции
desc-experimental-features =
    Экспериментальные функции работают только в новых официальных клиентах Telegram и могут вести себя нестабильно в старых или сторонних.

btn-ephemeral-messages = { $is_enabled ->
    [true] 🟢 Эфемерные сообщения
    *[false] ⚪ Эфемерные сообщения
}
desc-ephemeral-messages = Отправлять служебные сообщения в группах как эфемерные, видимые только тебе. Если выключено — присылаю обычные сообщения с автоудалением.

btn-chat-banned-users = 🚫 Бан-лист чата
desc-chat-banned-users = Управление пользователями, заблокированными в этом чате.
cban-usage = Укажи ID пользователя или ответь на его сообщение: <code>/cban &lt;user_id&gt;</code>
cban-cannot-ban-self = Нельзя заблокировать самого себя.
cban-cannot-ban-admin = Нельзя заблокировать администратора чата.
cban-cannot-ban-bot = Нельзя заблокировать бота.
cban-success = Пользователь <code>{ $user_id }</code> заблокирован в этом чате.
cban-already-banned = Пользователь <code>{ $user_id }</code> уже заблокирован в этом чате.
cunban-usage = Укажи ID пользователя или ответь на его сообщение: <code>/cunban &lt;user_id&gt;</code>
cunban-not-banned = Пользователь <code>{ $user_id }</code> не заблокирован в этом чате.
cunban-success = Пользователь <code>{ $user_id }</code> разблокирован в этом чате.
cbanlist-empty = В этом чате нет заблокированных пользователей.
cbanlist-title = <b>Бан-лист чата:</b>
btn-unban-user = ❌ Разблокировать { $user_id }
