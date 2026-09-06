settings-welcome = Прывітанне! 👋 Тут ты можаш наладзіць усё пад сябе. Адчувай сябе як дома!
settings-back = 🔙 Назад
settings-title = Налады
settings-no-permission = Оў, у цябе няма правоў змяняць гэтыя налады!
settings-saved = Супер! Налады абноўлены! ✨
settings-no-allowed-groups = Гэта налада недаступная для груп, прабач!
settings-no-allowed-dm = Гэта налада не для асабістых, прабач!

btn-language = Мова
btn-title-language = Апісанні
btn-blocked-services = Блакаванне сэрвісаў

btn-send-raw = { $is_enabled ->
    [true] 🟢 Файлам
    *[false] ⚪ Файлам
}
btn-send-music-covers = { $is_enabled ->
    [true] 🟢 Вокладкі
    *[false] ⚪ Вокладкі
}
btn-send-reactions = { $is_enabled ->
    [true] 🟢 Рэакцыі
    *[false] ⚪ Рэакцыі
}
btn-negativity = { $is_enabled ->
    [true] 🟢 Негатыўчык
    *[false] ⚪ Негатыўчык
}
btn-auto-translate = { $is_enabled ->
    [true] 🟢 Аўтапераклад
    *[false] ⚪ Аўтапераклад
}
btn-auto-caption = { $is_enabled ->
    [true] 🟢 Апісанне
    *[false] ⚪ Апісанне
}
btn-notifications = { $is_enabled ->
    [true] 🟢 Апавяшчэнні
    *[false] ⚪ Апавяшчэнні
}
btn-allow-playlists = { $is_enabled ->
    [true] 🟢 Плэйлісты
    *[false] ⚪ Плэйлісты
}
btn-allow-nsfw = { $is_enabled ->
    [true] 🟢 NSFW
    *[false] ⚪ NSFW
}

desc-send-raw = Буду кідаць медыя файламі для дасягнення высокай якасці! 🎨
desc-send-music-covers = Прымацую прыгожую вокладку да кожнага трэка. 🎵
desc-send-reactions = Буду рэагаваць эмодзі, каб ты бачыў(ла) працэс! ⚡
desc-negativity-mode = Буду выкарыстоўваць таксічныя эмодзі пры рэакцыях! 😈
desc-send-notifications = Выключы, калі хочаш атрымліваць медыя без гуку апавяшчэння. 🔕
desc-auto-caption = Я сама праверу і дадам апісанне да медыя. 📝
desc-auto-translate-titles = Перакладу апісанні відэа на тваю мову! 🌍
desc-allow-playlists = Спампую цэлыя плэйлісты (асцярожна з гэтым!). 📂
desc-allow-nsfw = Дазволіць NSFW кантэнт у гэтым чаце. 🔞
desc-lossless-mode = Я паспрабую знайсці для вас песні ў Hi-Res! Але я не абяцаю, што знайду, і ці будзе гэта правільная. 🎧

setting-status-changed = { $is_enabled ->
    [true] Ура! Налада *{ $setting_name }* уключана!
    *[false] Зразумела! Налада *{ $setting_name }* выключана!
}

pick-language = Выбірай мову! 🌍
pick-title-language = Абяры мову для апісанняў!
language-changed = Клас! Цяпер я размаўляю на *{ $language }*!
language-updated = Мова абноўлена!
title-language-changed = Цяпер апісанні будуць на *{ $language }*!
title-language-updated = Мова апісанняў абноўлена!
setting-updated = Гатова! Абнавіла.
invalid-setting = Ой, нейкая дзіўная налада...
error-updating = Ох, не атрымалася абнавіць. Паспрабуем яшчэ раз?
setting-changed = Зроблена! *{ $setting }* цяпер { $status }!
enabled = уключана
disabled = выключана
enable = Уключыць
disable = Выключыць
back = Назад
service-status-changed = Сэрвіс { $service } цяпер { $status }!
blocked = заблакаваны
unblocked = разблакаваны
settings-not-found = Хм, не магу знайсці налады!
no-permission-service = Табе нельга чапаць гэтыя налады!
error-service-status = Не атрымалася абнавіць статус сэрвісу. :(
current-status = Бягучы статус: { $status }

btn-configure-services = ⚙️ Configure Services
settings-select-service = Select a service to configure:
settings-service-title = ⚙️ **{ $name } Settings**
btn-lossless = { $is_enabled ->
    [true] 🟢 LOSSLESS
    *[false] ⚪ LOSSLESS
}
btn-service-enabled = { $is_enabled ->
    [true] 🟢 Сервіс
    *[false] ⚪ Сервіс
}

btn-news-spam = { $is_enabled ->
    [true] 🟢 Рассылка
    *[false] ⚪ Рассылка
}
desc-news-spam = Дазволіць боту дасылаць вам навіны і абнаўленні! 📰

btn-bot-sign = { $is_enabled ->
    [true] 🟢 Bot Ad 🧡
    *[false] ⚪ Bot Ad 🧡
}
desc-bot-sign = Дадаваць рэкламны подпіс «Charlotte 🧡» да медыя. Адключэнне цалкам бясплатнае! ✨

btn-simple-mode = { $is_enabled ->
    [true] 🟢 Просты рэжым
    *[false] ⚪ Просты рэжым
}
desc-simple =
    Просты інтэрфейс YouTube:
    Укл — толькі дзве кнопкі (Відэа ці Аўдыё), спампоўка ў максімальнай якасці да 100 МБ (да 1 ГБ для Спонсараў).
    Выкл — выбар дазволу, абрэзка відэа (для Спонсараў).

btn-youtube-ui-mode = Інтэрфейс YouTube
yt-ui-mode-simple = Просты
yt-ui-mode-balance = Збалансаваны
yt-ui-mode-advanced = Пашыраны
desc-youtube-ui-mode =
    Выберыце стыль інтэрфейсу для спампоўвання з YouTube:
    
    • Просты — 2 кнопкі (Відэа / Аўдыё) для спампоўвання ў 1 клік.
    • Збалансаваны — кнопкі лепшых якасцей у 1 клік + доступ да пашыраных налад.
    • Пашыраны — выбар якасці чэкбоксамі, аўдыёдарожкі і абрэзкі відэа (Trim).
