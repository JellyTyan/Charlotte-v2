settings-welcome = Прывітанне! Тут можна ўсё наладзіць пад сябе, не саромейся.
settings-back = 🔙 Назад
settings-title = Налады
settings-no-permission = Ой, у цябе няма правоў змяняць гэтыя налады.
settings-saved = Налады абнавіла! ✨
settings-no-allowed-groups = Гэтая налада недаступная ў групах, прабач.
settings-no-allowed-dm = Гэтую наладу нельга змяняць у асабістых паведамленнях.

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
    [true] 🟢 Зухаватыя
    *[false] ⚪ Зухаватыя
}
btn-auto-translate = { $is_enabled ->
    [true] 🟢 Пераклад
    *[false] ⚪ Пераклад
}
btn-auto-caption = { $is_enabled ->
    [true] 🟢 Апісанні
    *[false] ⚪ Апісанні
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

desc-send-raw = Буду адпраўляць медыя файламі — так якасць найвышэйшая.
desc-send-music-covers = Далучу вокладку да кожнага трэка.
desc-send-reactions = Буду ставіць эмодзі-рэакцыі, каб ты бачыў(-ла) працэс.
desc-negativity-mode = Буду выкарыстоўваць крыху больш зухаватыя эмодзі ў рэакцыях.
desc-send-notifications = Выключы, калі хочаш атрымліваць медыя без гуку.
desc-auto-caption = Сама праверу і дадам апісанне да медыя.
desc-auto-translate-titles = Перакладу апісанні відэа на тваю мову.
desc-allow-playlists = Спампую цэлыя плэйлісты — асцярожна з гэтым.
desc-allow-nsfw = Дазволіць NSFW-кантэнт у гэтым чаце.
desc-lossless-mode = Паспрабую знайсці Hi-Res версію песні. Не абяцаю, што атрымаецца.

setting-status-changed = { $is_enabled ->
    [true] Уключыла *{ $setting_name }*!
    *[false] Выключыла *{ $setting_name }*.
}

pick-language = Абяры мову 🌍
pick-title-language = Абяры мову для апісанняў
language-changed = Цяпер размаўляю на такой мове: *{ $language }*!
language-updated = Мову абнавіла.
title-language-changed = Цяпер апісанні будуць на такой мове: *{ $language }*.
title-language-updated = Мову апісанняў абнавіла.
setting-updated = Гатова, абнавіла.
invalid-setting = Хм, не ведаю такой налады.
error-updating = Не атрымалася абнавіць, прабач. Паспрабуем яшчэ раз?
enabled = уключана
disabled = выключана
enable = Уключыць
disable = Выключыць
back = Назад
service-status-changed = Сэрвіс { $service } цяпер { $status }.
blocked = заблакаваны
unblocked = разблакаваны
settings-not-found = Не магу знайсці гэтыя налады.
no-permission-service = Табе нельга змяняць гэтыя налады.
error-service-status = Не атрымалася абнавіць статус сэрвісу, прабач.
current-status = Бягучы статус: { $status }

btn-configure-services = ⚙️ Налады сэрвісаў
settings-select-service = Абяры сэрвіс для налады:
settings-service-title = **Налады { $name }**
btn-lossless = { $is_enabled ->
    [true] 🟢 LOSSLESS
    *[false] ⚪ LOSSLESS
}
btn-service-enabled = { $is_enabled ->
    [true] 🟢 Сэрвіс
    *[false] ⚪ Сэрвіс
}

btn-news-spam = { $is_enabled ->
    [true] 🟢 Рассылка
    *[false] ⚪ Рассылка
}
desc-news-spam = Дазволіць дасылаць табе навіны і абнаўленні.

btn-bot-sign = { $is_enabled ->
    [true] 🟢 Bot Ad 🧡
    *[false] ⚪ Bot Ad 🧡
}
desc-bot-sign = Дадаваць подпіс «Charlotte 🧡» да медыя. Адключыць можна бясплатна.

btn-simple-mode = { $is_enabled ->
    [true] 🟢 Просты рэжым
    *[false] ⚪ Просты рэжым
}
desc-simple =
    Просты інтэрфейс YouTube:
    Уключана — толькі дзве кнопкі (Відэа ці Аўдыя), спампоўванне ў найлепшай якасці да 100 МБ (да 1 ГБ для Спансараў).
    Выключана — выбар раздзяляльнасці, абразанне відэа (для Спансараў).

btn-youtube-ui-mode = Інтэрфейс YouTube
yt-ui-mode-simple = Просты
yt-ui-mode-balance = Збалансаваны
yt-ui-mode-advanced = Пашыраны
desc-youtube-ui-mode =
    Абяры стыль інтэрфейсу для спампоўвання з YouTube:

    • Просты — 2 кнопкі (Відэа / Аўдыя), спампоўванне ў адзін клік.
    • Збалансаваны — кнопкі найлепшых якасцяў у адзін клік + доступ да пашыраных налад.
    • Пашыраны — выбар любой якасці, аўдыядарожкі і абразання відэа (Trim).

btn-experimental = 🧪 Новыя функцыі
desc-experimental-features =
    Эксперыментальныя функцыі працуюць толькі ў новых афіцыйных кліентах Telegram і могуць паводзіць сябе нестабільна ў старых або старонніх.

btn-ephemeral-messages = { $is_enabled ->
    [true] 🟢 Эфемерныя паведамленні
    *[false] ⚪ Эфемерныя паведамленні
}
desc-ephemeral-messages = Адпраўляць службовыя паведамленні ў групах як эфемерныя, бачныя толькі табе. Калі выключана — дасылаю звычайныя паведамленні з аўтавыдаленнем.
btn-chat-banned-users = 🚫 Бан-ліст чата
desc-chat-banned-users = Кіраванне карыстальнікамі, заблакаванымі ў гэтым чаце.
cban-usage = Пазнач ID карыстальніка або адкажы на яго паведамленне: <code>/cban &lt;user_id&gt;</code>
cban-cannot-ban-self = Нельга заблакаваць самога сябе.
cban-cannot-ban-admin = Нельга заблакаваць адміністратара чата.
cban-cannot-ban-bot = Нельга заблакаваць бота.
cban-success = Карыстальнік <code>{ $user_id }</code> заблакаваны ў гэтым чаце.
cban-already-banned = Карыстальнік <code>{ $user_id }</code> ужо заблакаваны ў гэтым чаце.
cunban-usage = Пазнач ID карыстальніка або адкажы на яго паведамленне: <code>/cunban &lt;user_id&gt;</code>
cunban-not-banned = Карыстальнік <code>{ $user_id }</code> не заблакаваны ў гэтым чаце.
cunban-success = Карыстальнік <code>{ $user_id }</code> разблакаваны ў гэтым чаце.
cbanlist-empty = У гэтым чаце няма заблакаваных карыстальнікаў.
cbanlist-title = <b>Бан-ліст чата:</b>
btn-unban-user = ❌ Разблакаваць { $user_id }
