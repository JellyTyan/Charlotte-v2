msg-hello =
    Привет! 👋
    Рада тебя видеть, { $name }.
    Напиши _/help_, если что-то непонятно.
    Загляни в @charlottesbasement — там я делюсь новостями и всякими мелочами.

msg-help =
    Вот что я умею:
      /start — Главное меню
      /help — Помощь
      /settings — Настройки
      /saves — Моя медиатека
      /copy — Скопировать медиа в буфер
      /support — Поддержать проект
      /cancel — Отменить загрузку

    <b>Поддерживаемые платформы</b> <i>(нажми, чтобы развернуть)</i>:
    <blockquote expandable>
    <b>Музыка:</b>
      • Spotify
      • Apple Music
      • Deezer
      • SoundCloud
      • YouTube Music
    <i>Найду трек, обложку и все теги.</i>

    <b>Видео:</b>
      • YouTube (видео, шортсы, аудио до 100 МБ, ⭐ 1 ГБ для Спонсоров)
      • TikTok (видео и фото)
      • Instagram (рилсы и посты)
      • Twitter / X (видео и картинки)
      • Reddit (всё медиа из постов)
      • BlueSky, Twitch, NicoVideo

    <b>Арт:</b>
      • Pixiv
      • Pinterest
    </blockquote>

    🔍 <b>Инлайн-режим (работает в любом чате):</b>
      • <code>@{ $bot_username } &lt;текст&gt;</code> — поиск картинок и мемов (или просто <code>@{ $bot_username } </code> для недавних)
      • <code>@{ $bot_username } #music &lt;трек&gt;</code> — поиск музыки
      • <code>@{ $bot_username } #saved &lt;текст&gt;</code> — поиск по личным сохранёнкам
      • <code>@{ $bot_username } paste</code> — вставить скопированное медиа (буфер живёт час)
    <i>Чтобы сохранить медиа от меня в библиотеку, ответь на него командой <code>/save &lt;название&gt;</code>.</i>

    Просто пришли мне ссылку, и я всё сделаю.

processing = Секунду, уже делаю... ⏳
added-to-queue = Добавила тебя в очередь, впереди ещё { $count }.
starting-download = Начинаю скачивать! 🚀
invalid-callback = Ой, эта кнопка уже не работает, прости.
url-expired = Ссылка успела устареть — пришлёшь свежую?
setting-changed = Готово! *{ $setting }* теперь { $status }.
premium-granted = Ура, тебе открыли бесплатный премиум! Загружай сколько хочешь 🎉


# System & Payment
service-disabled = Этот сервис сейчас временно отключён, прости. Попробуй чуть позже.
support-invoice-title = Пожертвовать { $amount } ⭐
support-invoice-desc = Поддержи разработку Шарлотты!
support-success = Спасибо тебе большое за поддержку 🧡
support-invalid-amount = Сумма должна быть от 1 до 100 000 Звёзд. Попробуй ещё раз:
support-invalid-number = Введи, пожалуйста, число от 1 до 100 000:
payment-invalid-data = Ошибка: неверные данные об оплате.
payment-invalid-format = Ошибка: неверный формат данных.
payment-link-expired = Ошибка: ссылка устарела. Попробуй ещё раз.
payment-success-download = Спасибо за поддержку! Начинаю скачивание...
payment-error-refund = Ошибка при обработке запроса. Средства вернула...
premium-expired = Твой Спонсорский Премиум закончился. Можешь продлить в любое время 🌟
bot-ad-disable-alert = Чтобы отключить рекламу бота, нужно активное Спонсорство (100 Звёзд).
download-failed-refund = Не получилось скачать, прости. Деньги вернула.
not-your-request = Это не твой запрос.
action-cancelled = Отменено.
banned-global = Ты заблокирован(а) глобально.
banned-chat = Ты заблокирован(а) в этом чате.
too-many-requests = Слишком много запросов подряд, подожди немного.
menu-not-yours = Это меню не для тебя, прости.
general-error = Ой, что-то пошло не так. Попробуй позже?
btn-close = ✕ Закрыть

# YouTube Trim
yt-trim-sponsor-only = Обрезка видео доступна только для Спонсоров.
yt-trim-ask-range = Пришли диапазон для обрезки, например <code>01:20-02:45</code> или <code>90-165</code>:
yt-trim-invalid-range = Не поняла формат, прости. Нужно СТАРТ-КОНЕЦ, например <code>1:30-2:45</code>. Ещё раз?
yt-trim-end-before-start = Конец должен быть позже начала. Попробуешь снова?
yt-trim-processing = Обрезаю клип, подожди немного...
yt-trim-out-of-bounds = Этот диапазон выходит за длительность видео ({ $duration }). Попробуешь ещё раз?
yt-btn-full = 🎬 Полное видео
yt-btn-trim-locked = ★ Обрезка
yt-btn-cancel = Отмена
yt-ask-quality = Выбери качество:
yt-btn-video = Скачать видео
yt-btn-audio = Скачать аудио
yt-btn-continue = Далее
yt-btn-advanced = Расширенные настройки
yt-btn-trim = Обрезка
yt-btn-trim-active = ✓ Обрезка
yt-btn-back = Назад
yt-label-channel = Канал: { $uploader }
yt-label-duration = Длительность: { $duration }

btn-add-group = ➕ Добавить в группу
btn-my-settings = ⚙️ Мои настройки
already-downloading = Уже качаю для тебя, подожди чуть-чуть 🐾


# Errors
error-invalid-url = Ой, что-то с этой ссылкой не так 🥺
error-private-content = Прости, это закрыто настройками приватности — я туда не достучусь.
error-large-file = Какой большой файл... Такие я пока не умею пересылать, прости 😔
error-not-allowed = Прости, эта функция выключена в настройках этого чата.
error-internal = Ой, у меня что-то сломалось внутри... Попробуешь чуть позже?
error-not-found = Я всё обыскала, но ничего не нашла по этой ссылке. Точно не удалили?
error-region-restricted = Прости, этот контент заблокирован в моём регионе — не могу его достать.
error-age-restricted = Это контент 18+, а до такого мне не добраться, прости 🙈
error-download-canceled = Хорошо, остановила загрузку.
error-generic = Ой, что-то пошло не так, прости.
error-preview-only = Получилось скачать только превью, 30 секунд, а не полный трек, прости.

download-cancel = Отменяю! Уже остановила.
download-no-found = Хм, тут нечего отменять.
downloading-tracks = Собираю треки...
download-stats = Готово: скачано { $success }, не получилось — { $failed }.
all-tracks-success = Все треки скачались, ура! 🎉
total-tracks = Всего треков: { $count }
release-date = Вышло: { $date }
year = Год: { $year }
playlist-stopped = Загрузку плейлиста остановила.
skipped-track = Пропустила трек: { $title }
yt-btn-topich = ТОПИЧ
yt-sponsor-only = Эта функция только для Спонсоров, прости!

# Sponsor & Support
support-text =
    Шарлотта — некоммерческий проект, который держится на энтузиазме. Я помогаю сохранять и скачивать медиа без рекламы и ограничений.

    Серверы стоят около 12€ в месяц, и эта сумма оплачивается из своего кармана. Бот всегда будет бесплатным и открытым для всех.

    <b>Что даёт спонсорка:</b>
    • YouTube: видео до 1 ГБ вместо 100 МБ
    • YouTube: ТОПИЧ, максимальное качество оригинальным файлом
    • YouTube: обрезка видео перед отправкой
    • Instagram и TikTok в лучшем качестве
    • NSFW-медиа из Twitter, Reddit и Pixiv
    • До 1000 сохранёнок вместо 200

    <b>Как копятся Звёзды:</b>
    Все Звёзды, которые ты отправляешь, складываются в копилку, даже по 10 или 50. Каждые 100 ⭐ дают 30 дней спонсорки, а если она уже активна, дни добавятся к текущему сроку. За любой донат твоё имя появится на доске благодарностей.{ $status }

    Любая поддержка очень важна, спасибо, что ты со мной ⭐

support-status-lifetime =
    ⭐ <b>Твой статус:</b> Спонсор (навсегда) 🌟

support-status-active =
    ⭐ <b>Твой статус:</b> Спонсор (до { $date })
    В копилке: { $progress }/100 ⭐ до следующего продления

support-status-progress =
    ⭐ В копилке: { $progress }/100 ⭐ до спонсорки

support-btn-sponsor = ⭐ Спонсорка на 30 дней (100 ⭐)
support-btn-coffee = ☕ Купить кофе
support-btn-stars = ⭐ Отправить Звёзды
support-btn-supporters = 🤍 Доска благодарностей
support-btn-back = 🔙 Назад

support-wall-empty =
    <b>Доска благодарностей</b>

    Пока здесь никого нет. Но ты можешь стать первым, кто поддержит меня и появится в этом списке ⭐

support-wall-text =
    <b>Доска благодарностей</b>

    Спасибо всем, кто помогает мне работать и развиваться:

    { $supporters }

    Ваша поддержка очень много значит ⭐

support-choose-stars = Выбери, сколько Звёзд хочешь отправить на поддержку:
support-stars-ten = ⭐ 10 Звёзд
support-stars-fifty = ⭐ 50 Звёзд
support-stars-hundred = ⭐ 100 Звёзд
support-stars-custom = ✏️ Своя сумма

support-custom-prompt = Напиши, сколько Звёзд хочешь отправить (от 1 до 100 000):

support-success-sponsor =
    Спасибо тебе огромное за { $stars } ⭐!
    Спонсорка включена на { $days } дн. (до { $date })! Твоё имя добавлено на доску благодарностей ⭐

support-success-tip =
    Спасибо тебе огромное за { $stars } ⭐!
    Твоя поддержка очень важна! В копилке { $progress }/100 ⭐ до спонсорки ⭐

# Report command
report-reply-required = Ответь командой <code>/report</code> на моё сообщение, с которым что-то пошло не так.
report-not-bot-message = Эта команда работает только в ответ на мои сообщения 🐾
report-success = Спасибо за репорт! Я передала всё разработчику, скоро разберёмся 🧡
error-send-failed = ❌ Не удалось отправить медиа в Telegram. Файл повреждён или отклонён сервером.
yt-trim-invalid-format = Не могу разобрать такой формат. Укажи НАЧАЛО-КОНЕЦ, например <code>1:30-2:45</code>. Попробуешь ещё раз?
