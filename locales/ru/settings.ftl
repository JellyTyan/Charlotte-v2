settings-welcome = Приветик! 👋 Здесь ты можешь настроить всё под себя. Чувствуй себя как дома!
settings-back = 🔙 Назад
settings-title = Настройки
settings-no-permission = Оу, у тебя нет прав менять эти настройки!
settings-saved = Супер! Настройки обновлены! ✨
settings-no-allowed-groups = Эта настройка недоступна для групп, прости!
settings-no-allowed-dm = Эту настройку нельзя менять в личке!

btn-language = Язык
btn-title-language = Язык описаний
btn-blocked-services = Блокировка сервисов

btn-send-raw = { $is_enabled ->
    [true] ✅ Отправить файлом
    *[false] ❌ Отправить файлом
}
btn-send-music-covers = { $is_enabled ->
    [true] ✅ Обложки музыки
    *[false] ❌ Обложки музыки
}
btn-send-reactions = { $is_enabled ->
    [true] ✅ Реакции
    *[false] ❌ Реакции
}
btn-negativity = { $is_enabled ->
    [true] ✅ Негативчик
    *[false] ❌ Негативчик
}
btn-auto-translate = { $is_enabled ->
    [true] ✅ Автоперевод описаний
    *[false] ❌ Автоперевод описаний
}
btn-auto-caption = { $is_enabled ->
    [true] ✅ Описание
    *[false] ❌ Описание
}
btn-notifications = { $is_enabled ->
    [true] ✅ Уведомления
    *[false] ❌ Уведомления
}
btn-allow-playlists = { $is_enabled ->
    [true] ✅ Плейлисты
    *[false] ❌ Плейлисты
}
btn-allow-nsfw = { $is_enabled ->
    [true] ✅ NSFW
    *[false] ❌ NSFW
}

desc-send-raw = Буду кидать медиа файлами для достижения высокого качества! 🎨
desc-send-music-covers = Прикреплю красивую обложку к каждому треку. 🎵
desc-send-reactions = Буду реагировать эмодзи, чтобы ты видел(а) процесс! ⚡
desc-negativity-mode = Буду использовать токсичные эмодзи при реакциях! 😈
desc-send-notifications = Выключи, если хочешь получать медиа без звука (тихо). 🔕
desc-auto-caption = Я сама проверю и добавлю описание к медиа. 📝
desc-auto-translate-titles = Переведу описания видео на твой язык! 🌍
desc-allow-playlists = Скачаю целые плейлисты (аккуратно с этим!). 📂
desc-allow-nsfw = Разрешить NSFW контент в этом чате. 🔞
desc-lossless-mode = Я попытаюсь найти Hi-Res песни для вас! Только я не обещаю, что найду и найду ли правильный. 🎧

setting-status-changed = { $is_enabled ->
    [true] Ура! Настройка *{ $setting_name }* включена!
    *[false] Поняла! Настройка *{ $setting_name }* выключена!
}

pick-language = Выбирай язык! 🌍
pick-title-language = Выбери язык для описаний!
language-changed = Класс! Теперь я говорю на *{ $language }*!
language-updated = Язык обновлён!
title-language-changed = Теперь описания будут на *{ $language }*!
title-language-updated = Язык описаний обновлён!
setting-updated = Готово! Обновила.
invalid-setting = Ой, какая-то странная настройка...
error-updating = Ох, не вышло обновить. Попробуем ещё раз?
setting-changed = Сделано! *{ $setting }* теперь { $status }!
enabled = включено
disabled = выключено
enable = Включить
disable = Выключить
back = Назад
service-status-changed = Сервис { $service } теперь { $status }!
blocked = заблокирован
unblocked = разблокирован
settings-not-found = Хм, не могу найти настройки!
no-permission-service = Тебе нельзя трогать эти настройки!
error-service-status = Не получилось обновить статус сервиса. :(
current-status = Текущий статус: { $status }

btn-configure-services = ⚙️ Настройка сервисов
settings-select-service = Выберите сервис для настройки:
settings-service-title = ⚙️ **Настройки { $name }**
btn-lossless = { $is_enabled ->
    [true] ✅ LOSSLESS
    *[false] ❌ LOSSLESS
}
btn-service-enabled = { $is_enabled ->
    [true] ✅ Включен
    *[false] ❌ Включен
}

btn-news-spam = { $is_enabled ->
    [true] ✅ Рассылка
    *[false] ❌ Рассылка
}
desc-news-spam = Позволить боту отправлять вам новости и обновления! 📰
