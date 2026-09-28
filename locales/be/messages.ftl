msg-hello =
    Прывітанне! 👋
    Рада цябе бачыць, { $name }.
    Напішы _/help_, калі штосьці незразумела.
    Зазірні ў @charlottesbasement — там я дзялюся навінамі і ўсялякімі дробязямі.

msg-help =
    Вось што я ўмею:
      /start — Галоўнае меню
      /help — Дапамога
      /settings — Налады
      /saves — Мой медыяпакой
      /copy — Скапіяваць медыя ў буфер
      /support — Падтрымаць праект
      /cancel — Скасаваць загрузку

    <b>Платформы, якія я падтрымліваю</b> <i>(націсні, каб разгарнуць)</i>:
    <blockquote expandable>
    <b>Музыка:</b>
      • Spotify
      • Apple Music
      • Deezer
      • SoundCloud
      • YouTube Music
    <i>Знайду трэк, вокладку і ўсе тэгі.</i>

    <b>Відэа:</b>
      • YouTube (відэа, шортсы, аўдыя да 100 МБ, ⭐ 1 ГБ для Спонсараў)
      • TikTok (відэа і фота)
      • Instagram (рылсы і допісы)
      • Twitter / X (відэа і выявы)
      • Reddit (усё медыя з допісаў)
      • BlueSky, Twitch, NicoVideo

    <b>Арт:</b>
      • Pixiv
      • Pinterest
    </blockquote>

    🔍 <b>Інлайн-рэжым (працуе ў любым чаце):</b>
      • <code>@{ $bot_username } &lt;тэкст&gt;</code> — пошук выяў і мемаў (або проста <code>@{ $bot_username } </code> для нядаўніх)
      • <code>@{ $bot_username } #music &lt;трэк&gt;</code> — пошук музыкі
      • <code>@{ $bot_username } #saved &lt;тэкст&gt;</code> — пошук па асабістых захаванках
      • <code>@{ $bot_username } paste</code> — уставіць скапіяванае медыя (буфер жыве 1 гадзіну)
    <i>Каб захаваць медыя ад мяне ў бібліятэку, адкажы на яго камандай <code>/save &lt;назва&gt;</code>.</i>

    Проста дашлі мне спасылку, і я ўсё зраблю.

processing = Хвілінку, ужо раблю... ⏳
added-to-queue = Дадала цябе ў чаргу, наперадзе яшчэ { $count }.
starting-download = Пачынаю спампоўваць! 🚀
invalid-callback = Ой, гэтая кнопка больш не працуе, прабач.
url-expired = Спасылка паспела састарэць — дашлеш свежую?
setting-changed = Гатова! *{ $setting }* цяпер { $status }.
premium-granted = Ура, табе адкрылі бясплатны прэміум! Спампоўвай колькі хочаш 🎉


# System & Payment
sponsor-alert = 30 дзён Прэміуму за 100 Зорак 🌟
sponsor-invoice-title = Спансарскі Прэміум (30 дзён)
sponsor-invoice-desc = 30 дзён прэміум-доступу: без рэкламы і з дадатковымі магчымасцямі.
sponsor-success = Дзякуй за падтрымку! Дарую табе 30 дзён Спансарскага Прэміуму 🌟
support-invoice-title = Ахвяраваць { $amount } ⭐
support-invoice-desc = Падтрымай распрацоўку Шарлоты!
support-success = Вялікі дзякуй табе за падтрымку 🧡
support-invalid-amount = Сума павінна быць ад 1 да 100 000 Зорак. Паспрабуй яшчэ раз:
support-invalid-number = Увядзі, калі ласка, лік ад 1 да 100 000:
payment-invalid-data = Памылка: няслушныя звесткі аплаты.
payment-invalid-format = Памылка: няслушны фармат звестак.
payment-link-expired = Памылка: спасылка састарэла. Паспрабуй яшчэ раз.
payment-success-download = Дзякуй за падтрымку! Пачынаю спампоўванне...
payment-error-refund = Сталася памылка пры апрацоўцы. Зоркі вярнула...
premium-expired = Твой Спансарскі Прэміум скончыўся. Можаш падоўжыць у любы час 🌟
bot-ad-disable-alert = Каб адключыць рэкламу бота, патрэбнае актыўнае Спансарства (100 Зорак).
download-failed-refund = Не атрымалася спампаваць, прабач. Зоркі вярнула.
not-your-request = Гэта не твой запыт.
action-cancelled = Скасавана.
banned-global = Ты заблакаваны(-ая) глабальна.
banned-chat = Ты заблакаваны(-ая) у гэтым чаце.
too-many-requests = Занадта шмат запытаў запар, пачакай крыху.
menu-not-yours = Гэтае меню не для цябе, прабач.
general-error = Ой, штосьці пайшло не так. Паспрабуеш пазней?
btn-close = ✕ Закрыць

# YouTube Trim
yt-trim-sponsor-only = Абразанне відэа даступнае толькі для Спансараў.
yt-trim-ask-range = Дашлі дыяпазон для абразання, напрыклад <code>01:20-02:45</code> або <code>90-165</code>:
yt-trim-invalid-range = Не зразумела фармат, прабач. Трэба ПАЧАТАК-КАНЕЦ, напрыклад <code>1:30-2:45</code>. Яшчэ раз?
yt-trim-end-before-start = Канец павінен быць пазней за пачатак. Паспрабуеш зноў?
yt-trim-processing = Абразаю кліп, пачакай крыху...
yt-trim-out-of-bounds = Гэты дыяпазон выходзіць за межы працягласці відэа ({ $duration }). Паспрабуеш яшчэ раз?
yt-btn-full = 🎬 Поўнае відэа
yt-btn-trim-locked = ★ Абразанне
yt-btn-cancel = Адмена
yt-ask-quality = Абяры якасць:
yt-btn-video = Спампаваць відэа
yt-btn-audio = Спампаваць аўдыя
yt-btn-continue = Далей
yt-btn-advanced = Пашыраныя налады
yt-btn-trim = Абразанне
yt-btn-trim-active = ✓ Абразанне
yt-btn-back = Назад
yt-label-channel = Канал: { $uploader }
yt-label-duration = Працягласць: { $duration }

btn-add-group = ➕ Дадаць у групу
btn-my-settings = ⚙️ Мае налады
already-downloading = Ужо спампоўваю штосьці для цябе, пачакай хвілінку 🐾


# Errors
error-invalid-url = Ой, штосьці з гэтай спасылкай не так 🥺
error-private-content = Прабач, гэта закрыта наладамі прыватнасці — я туды не дабяруся.
error-large-file = Які вялікі файл... Такія я пакуль не ўмею дасылаць, прабач 😔
error-not-allowed = Прабач, гэтая функцыя выключаная ў наладах гэтага чата.
error-internal = Ой, у мяне штосьці зламалася ўнутры... Паспрабуеш крыху пазней?
error-not-found = Я ўсё абшукала, але нічога не знайшла па гэтай спасылцы. Дакладна не выдалілі?
error-region-restricted = Прабач, гэты кантэнт заблакаваны ў маім рэгіёне — не магу яго дастаць.
error-age-restricted = Гэта кантэнт 18+, а да такога мне не дабрацца, прабач 🙈
error-download-canceled = Добра, спыніла спампоўванне.
error-generic = Ой, штосьці пайшло не так, прабач.
error-preview-only = Атрымалася спампаваць толькі прэв'ю, 30 секунд, а не поўны трэк, прабач.

download-cancel = Скасоўваю! Ужо спыніла.
download-no-found = Хм, тут няма чаго скасоўваць.
downloading-tracks = Збіраю трэкі...
download-stats = Гатова: спампавана { $success }, не атрымалася — { $failed }.
all-tracks-success = Усе трэкі спампаваліся, ура! 🎉
total-tracks = Усяго трэкаў: { $count }
release-date = Выйшла: { $date }
year = Год: { $year }
playlist-stopped = Загрузку плэйліста спыніла.
skipped-track = Прапусціла трэк: { $title }
yt-btn-topich = ТОПІЧ
yt-sponsor-only = Гэтая функцыя толькі для Спансараў, прабач!

# Sponsor & Support
sponsor-text =
    Калі хочаш падтрымаць мяне і праект, можна аформіць спансарства на 30 дзён.

    Што ты атрымаеш:
      • Спампоўванне вялікіх відэа з YouTube (да 1 ГБ замест 100 МБ)
      • Абразанне відэа з YouTube перад адпраўкай
      • Доступ да NSFW-медыя (Twitter і Reddit)
      • Тваё імя з'явіцца на дошцы падзяк у /support

    Спансарства афармляецца за 100 Зорак на 30 дзён ⭐

sponsor-btn-buy = ⭐ Стаць спансарам (100 Зорак)

support-text =
    Шарлота — некамерцыйны праект, які трымаецца на энтузіязме. Я дапамагаю захоўваць і спампоўваць медыя без рэкламы і абмежаванняў.

    Серверы каштуюць каля 12€ у месяц, і гэтая сума аплачваецца з уласнай кішэні. Бот заўсёды будзе бясплатным і адкрытым для ўсіх.

    <b>Спансарства:</b>
    За кожныя 100 Зорак ты атрымліваеш <b>30 дзён спансарства</b>:
    • Спампоўванне вялікіх відэа з YouTube (да 1 ГБ замест 100 МБ)
    • Абразанне відэа з YouTube перад адпраўкай
    • Доступ да NSFW-медыя (Twitter, Reddit, Pixiv)
    • Тваё імя на дошцы падзяк{ $status }

    Любая падтрымка вельмі важная, дзякуй, што ты са мной ⭐

support-status-lifetime =
    ⭐ <b>Твой статус:</b> Спансар (назаўжды) 🌟

support-status-active =
    ⭐ <b>Твой статус:</b> Спансар (да { $date })
    У скарбонцы: { $progress }/100 ⭐ да наступнага падаўжэння

support-status-progress =
    ⭐ У скарбонцы: { $progress }/100 ⭐ да спансарства

support-btn-sponsor = ⭐ Спансарства на 30 дзён (100 ⭐)
support-btn-coffee = ☕ Частаваць кавай
support-btn-stars = ⭐ Адправіць Зоркі
support-btn-supporters = 🤍 Дошка падзяк
support-btn-back = 🔙 Назад

support-wall-empty =
    <b>Дошка падзяк</b>

    Пакуль тут нікога няма. Але ты можаш стаць першым, хто падтрымае мяне і з'явіцца ў гэтым спісе ⭐

support-wall-text =
    <b>Дошка падзяк</b>

    Вялікі дзякуй усім, хто дапамагае мне працаваць і развівацца:

    { $supporters }

    Ваша падтрымка вельмі шмат значыць ⭐

support-choose-stars = Абяры, колькі Зорак хочаш адправіць на падтрымку:
support-stars-ten = ⭐ 10 Зорак
support-stars-fifty = ⭐ 50 Зорак
support-stars-hundred = ⭐ 100 Зорак
support-stars-custom = ✏️ Свая сума

support-custom-prompt = Напішы, колькі Зорак хочаш адправіць (ад 1 да 100 000):

support-success-sponsor =
    Вялікі дзякуй табе за { $stars } ⭐!
    Спансарства ўключана на { $days } дзён (да { $date })! Тваё імя дададзена на дошку падзяк ⭐

support-success-tip =
    Вялікі дзякуй табе за { $stars } ⭐!
    Твая падтрымка вельмі важная! У скарбонцы { $progress }/100 ⭐ да спансаркі ⭐

# Report command
report-reply-required = Аддкажы камандай <code>/report</code> на маё паведамленне, з якім штосьці пайшло не так.
report-not-bot-message = Гэтая каманда працуе толькі ў адказ на мае паведамленні 🐾
report-success = Дзякуй за рэпарт! Я перадала ўсё распрацоўшчыку, хутка разбяромся 🧡
error-send-failed = ❌ Не ўдалося адправіць медыя ў Telegram. Файл пашкоджаны ці адхілены серверам.
yt-trim-invalid-format = Не магу разабраць такі фармат. Укажы ПАЧАТАК-КАНЕЦ, напрыклад <code>1:30-2:45</code>. Паспрабуеш яшчэ раз?
