settings-welcome = Привітик! 👋 Тут ти можеш налаштувати все під себе. Почувайся як удома!
settings-back = 🔙 Назад
settings-title = Налаштування
settings-no-permission = Оу, у тебе немає прав змінювати ці налаштування!
settings-saved = Супер! Налаштування оновлено! ✨
settings-no-allowed-groups = Це налаштування недоступне для груп, вибач!
settings-no-allowed-dm = Це налаштування не для особистих, вибач!

btn-language = Мова
btn-title-language = Мова назв
btn-blocked-services = Блокування сервісів

btn-send-raw = { $is_enabled ->
    [true] ✅ Арт файлом (Найкраща якість)
    *[false] ❌ Арт файлом (Найкраща якість)
}
btn-send-music-covers = { $is_enabled ->
    [true] ✅ Обкладинки музики
    *[false] ❌ Обкладинки музики
}
btn-send-reactions = { $is_enabled ->
    [true] ✅ Прикольні реакції
    *[false] ❌ Прикольні реакції
}
btn-auto-translate = { $is_enabled ->
    [true] ✅ Автопереклад назв
    *[false] ❌ Автопереклад назв
}
btn-auto-caption = { $is_enabled ->
    [true] ✅ Опис
    *[false] ❌ Опис
}
btn-notifications = { $is_enabled ->
    [true] ✅ Сповіщення
    *[false] ❌ Сповіщення
}
btn-allow-playlists = { $is_enabled ->
    [true] ✅ Дозволити плейлісти
    *[false] ❌ Дозволити плейлісти
}

desc-send-raw = Буду кидати арти файлами, щоб якість була просто космос! 🎨
desc-send-music-covers = Прикріплю гарну обкладинку до кожного треку. 🎵
desc-send-reactions = Буду реагувати емодзі, щоб ти бачив(ла) процес! ⚡
desc-send-notifications = Вимкни, якщо хочеш отримувати медіа без звуку (тихо). 🔕
desc-auto-caption = Я сама перевірю та додам опис до медіа. 📝
desc-auto-translate-titles = Перекладу назви відео твоєю мовою! 🌍
desc-allow-playlists = Завантажу цілі плейлісти (обережно з цим!). 📂
desc-lossless-mode = Я спробую знайти Hi-Res пісні для вас! Тільки я не обіцяю, що знайду і чи знайду правильну. 🎧

setting-status-changed = { $is_enabled ->
    [true] Ура! Налаштування *{ $setting_name }* увімкнено!
    *[false] Зрозуміла! Налаштування *{ $setting_name }* вимкнено!
}

pick-language = Обирай мову! 🌍
pick-title-language = Обери мову для назв!
language-changed = Клас! Тепер я розмовляю *{ $language }*!
language-updated = Мову оновлено!
title-language-changed = Тепер назви будуть *{ $language }*!
title-language-updated = Мову назв оновлено!
setting-updated = Готово! Оновила.
invalid-setting = Ой, якесь дивне налаштування...
error-updating = Ох, не вийшло оновити. Спробуємо ще раз?
setting-changed = Зроблено! *{ $setting }* тепер { $status }!
enabled = увімкнено
disabled = вимкнено
enable = Увімкнути
disable = Вимкнути
back = Назад
service-status-changed = Сервіс { $service } тепер { $status }!
blocked = заблоковано
unblocked = розблоковано
settings-not-found = Хм, не можу знайти налаштування!
no-permission-service = Тобі не можна чіпати ці налаштування!
error-service-status = Не вийшло оновити статус сервісу. :(
current-status = Поточний статус: { $status }

btn-configure-services = ⚙️ Налаштування сервісів
settings-select-service = Оберіть сервіс для налаштування:
settings-service-title = ⚙️ **Налаштування { $name }**
btn-lossless = { $is_enabled ->
    [true] ✅ LOSSLESS
    *[false] ❌ LOSSLESS
}
btn-service-enabled = { $is_enabled ->
    [true] �� Увімкнено: ✅
    *[false] 🎧 Увімкнено: ❌
}
