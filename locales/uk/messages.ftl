msg-hello =
    Привіт! 👋
    Рада бачити тебе, { $name }.
    Напиши _/help_, якщо щось незрозуміло.
    Зазирни в @charlottesbasement — там я ділюся новинами та всякими дрібницями.

msg-help =
    Ось що я вмію:
      /start — Головне меню
      /help — Допомога
      /settings — Налаштування
      /saves — Моя медіатека
      /copy — Скопіювати медіа в буфер
      /support — Підтримати проєкт
      /cancel — Скасувати завантаження

    <b>Підтримувані платформи</b> <i>(натисни, щоб розгорнути)</i>:
    <blockquote expandable>
    <b>Музика:</b>
      • Spotify
      • Apple Music
      • Deezer
      • SoundCloud
      • YouTube Music
    <i>Знайду трек, обкладинку та всі теги.</i>

    <b>Відео:</b>
      • YouTube (відео, шортси, аудіо до 100 МБ, ⭐ 1 ГБ для Спонсорів)
      • TikTok (відео та фото)
      • Instagram (рілси та дописи)
      • Twitter / X (відео та картинки)
      • Reddit (усе медіа з дописів)
      • BlueSky, Twitch, NicoVideo

    <b>Арт:</b>
      • Pixiv
      • Pinterest
    </blockquote>

    🔍 <b>Інлайн-режим (працює в будь-якому чаті):</b>
      • <code>@{ $bot_username } &lt;текст&gt;</code> — пошук картинок і мемів (або просто <code>@{ $bot_username } </code> для нещодавніх)
      • <code>@{ $bot_username } #music &lt;трек&gt;</code> — пошук музики
      • <code>@{ $bot_username } #saved &lt;текст&gt;</code> — пошук по особистих збереженнях
      • <code>@{ $bot_username } paste</code> — вставити скопійоване медіа (буфер діє 1 годину)
    <i>Щоб зберегти моє медіа в бібліотеку, дай на нього відповідь командою <code>/save &lt;назва&gt;</code>.</i>

    Просто надішли мені посилання, і я все зроблю.

processing = Секунду, вже роблю... ⏳
added-to-queue = Додала тебе до черги, попереду ще { $count }.
starting-download = Починаю завантажувати! 🚀
invalid-callback = Ой, ця кнопка більше не працює, вибач.
url-expired = Посилання вже застаріло — надішлеш свіже?
setting-changed = Готово! *{ $setting }* тепер { $status }.
premium-granted = Ура, тобі відкрили безкоштовний преміум! Завантажуй скільки завгодно 🎉


# System & Payment
service-disabled = Цей сервіс зараз тимчасово вимкнено, вибач. Спробуй трохи пізніше.
support-invoice-title = Пожертвувати { $amount } ⭐
support-invoice-desc = Підтримай розробку Шарлотти!
support-success = Красно дякую тобі за підтримку 🧡
support-invalid-amount = Сума має бути від 1 до 100 000 Зірок. Спробуй ще раз:
support-invalid-number = Введи, будь ласка, число від 1 до 100 000:
payment-invalid-data = Помилка: неправильні дані платежу.
payment-invalid-format = Помилка: неправильний формат даних.
payment-link-expired = Помилка: посилання застаріло. Спробуй ще раз.
payment-success-download = Дякую за підтримку! Починаю завантаження...
payment-error-refund = Сталася помилка під час обробки. Зірки повернула...
premium-expired = Твій Спонсорський Преміум закінчився. Можеш продовжити у будь-який час 🌟
bot-ad-disable-alert = Щоб вимкнути рекламу бота, потрібне активне Спонсорство (100 Зірок).
download-failed-refund = Не вийшло завантажити, вибач. Зірки повернула.
not-your-request = Це не твій запит.
action-cancelled = Скасовано.
banned-global = Тебе заблоковано глобально.
banned-chat = Тебе заблоковано в цьому чаті.
too-many-requests = Забагато запитів поспіль, почекай трішки.
menu-not-yours = Це меню не для тебе, вибач.
general-error = Ой, щось пішло не так. Спробуєш пізніше?
btn-close = ✕ Закрити

# YouTube Trim
yt-trim-sponsor-only = Обрізка відео доступна тільки для Спонсорів.
yt-trim-ask-range = Надішли діапазон для обрізки, наприклад <code>01:20-02:45</code> або <code>90-165</code>:
yt-trim-invalid-range = Не зрозуміла формат, вибач. Потрібно ПОЧАТОК-КІНЕЦЬ, наприклад <code>1:30-2:45</code>. Ще раз?
yt-trim-end-before-start = Кінець має бути пізніше за початок. Спробуєш знову?
yt-trim-processing = Обрізаю кліп, зачекай трішки...
yt-trim-out-of-bounds = Цей діапазон виходить за тривалість відео ({ $duration }). Спробуєш ще раз?
yt-btn-full = 🎬 Повне відео
yt-btn-trim-locked = ★ Обрізка
yt-btn-cancel = Скасувати
yt-ask-quality = Обери якість:
yt-btn-video = Завантажити відео
yt-btn-audio = Завантажити аудіо
yt-btn-continue = Далі
yt-btn-advanced = Розширені налаштування
yt-btn-trim = Обрізка
yt-btn-trim-active = ✓ Обрізка
yt-btn-back = Назад
yt-label-channel = Канал: { $uploader }
yt-label-duration = Тривалість: { $duration }

btn-add-group = ➕ Додати до групи
btn-my-settings = ⚙️ Мої налаштування
already-downloading = Уже завантажую дещо для тебе, зачекай хвилинку 🐾


# Errors
error-invalid-url = Ой, щось із цим посиланням не так 🥺
error-private-content = Вибач, це закрите налаштуваннями приватності — я туди не доберуся.
error-large-file = Який великий файл... Такі я поки не вмію надсилати, вибач 😔
error-not-allowed = Вибач, ця функція вимкнена в налаштуваннях цього чату.
error-internal = Ой, у мене щось зламалося всередині... Спробуєш трішки пізніше?
error-not-found = Я все обшукала, але нічого не знайшла за цим посиланням. Точно не видалили?
error-region-restricted = Вибач, цей контент заблокований у моєму регіоні — не можу його дістати.
error-age-restricted = Це контент 18+, а до такого мені зась, вибач 🙈
error-download-canceled = Добре, зупинила завантаження.
error-generic = Ой, щось пішло не так, вибач.
error-preview-only = Вийшло завантажити тільки прев'ю, 30 секунд, а не повний трек, вибач.

download-cancel = Скасовую! Вже зупинила.
download-no-found = Хм, тут нічого скасовувати.
downloading-tracks = Збираю треки...
download-stats = Готово: завантажено { $success }, не вийшло — { $failed }.
all-tracks-success = Усі треки завантажилися, ура! 🎉
total-tracks = Усього треків: { $count }
release-date = Вийшло: { $date }
year = Рік: { $year }
playlist-stopped = Завантаження плейліста зупинила.
skipped-track = Пропустила трек: { $title }
yt-btn-topich = ТОПИЧ
yt-sponsor-only = Ця функція тільки для Спонсорів, вибач!

# Sponsor & Support
support-text =
    Шарлотта — некомерційний проєкт, який тримається на ентузіазмі. Я допомагаю зберігати та завантажувати медіа без реклами й обмежень.

    Сервери коштують близько 12€ на місяць, і ця сума сплачується з власної кишені. Бот завжди буде безкоштовним і відкритим для всіх.

    <b>Що дає спонсорка:</b>
    • YouTube: відео до 1 ГБ замість 100 МБ
    • YouTube: ТОПИЧ, максимальна якість оригінальним файлом
    • YouTube: обрізка відео перед надсиланням
    • Instagram і TikTok у найкращій якості
    • NSFW-медіа з Twitter, Reddit і Pixiv
    • До 1000 збережень замість 200

    <b>Як накопичуються Зірки:</b>
    Усі Зірки, які ти надсилаєш, складаються в скарбничку, навіть по 10 чи 50. Кожні 100 ⭐ дають 30 днів спонсорки, а якщо вона вже активна, дні додадуться до поточного терміну. За будь-який донат твоє ім'я з'явиться на дошці подяк.{ $status }

    Будь-яка підтримка дуже важлива, дякую, що ти зі мною ⭐

support-status-lifetime =
    ⭐ <b>Твій статус:</b> Спонсор (назавжди) 🌟

support-status-active =
    ⭐ <b>Твій статус:</b> Спонсор (до { $date })
    У скарбничці: { $progress }/100 ⭐ до наступного продовження

support-status-progress =
    ⭐ У скарбничці: { $progress }/100 ⭐ до спонсорки

support-btn-sponsor = ⭐ Спонсорка на 30 днів (100 ⭐)
support-btn-coffee = ☕ Пригостити кавою
support-btn-stars = ⭐ Надіслати Зірки
support-btn-supporters = 🤍 Дошка подяк
support-btn-back = 🔙 Назад

support-wall-empty =
    <b>Дошка подяк</b>

    Поки що тут нікого немає. Але ти можеш стати першим, хто підтримає мене і з'явиться в цьому списку ⭐

support-wall-text =
    <b>Дошка подяк</b>

    Щиро дякую всім, хто допомагає мені працювати та розвиватися:

    { $supporters }

    Ваша підтримка дуже багато важить ⭐

support-choose-stars = Обери, скільки Зірок хочеш надіслати на підтримку:
support-stars-ten = ⭐ 10 Зірок
support-stars-fifty = ⭐ 50 Зірок
support-stars-hundred = ⭐ 100 Зірок
support-stars-custom = ✏️ Своя сума

support-custom-prompt = Напиши, скільки Зірок хочеш надіслати (від 1 до 100 000):

support-success-sponsor =
    Красно дякую тобі за { $stars } ⭐!
    Спонсорство увімкнено на { $days } дн. (до { $date })! Твоє ім'я додано на дошку подяк ⭐

support-success-tip =
    Красно дякую тобі за { $stars } ⭐!
    Твоя підтримка дуже важлива! У скарбничці { $progress }/100 ⭐ до спонсорки ⭐

# Report command
report-reply-required = Відповідай командою <code>/report</code> на моє повідомлення, з яким щось пішло не так.
report-not-bot-message = Ця команда працює лише у відповідь на мої повідомлення 🐾
report-success = Дякую за репорт! Я передала все розробнику, скоро розберемося 🧡
error-send-failed = ❌ Не вдалося надіслати медіа в Telegram. Файл пошкоджений або відхилений сервером.
yt-trim-invalid-format = Не можу розібрати такий формат. Вкажи ПОЧАТОК-КІНЕЦЬ, наприклад <code>1:30-2:45</code>. Спробуєш ще раз?
