settings-welcome = سلام! اینجا می‌تونی همه‌چیز رو مطابق سلیقه‌ت تنظیم کنی، راحت باش.
settings-back = 🔙 بازگشت
settings-title = تنظیمات
settings-no-permission = ای وای، دسترسی لازم برای تغییر این تنظیمات رو نداری.
settings-saved = تنظیمات به‌روز شد! ✨
settings-no-allowed-groups = این تنظیم در گروه‌ها در دسترس نیست، ببخشید.
settings-no-allowed-dm = این تنظیم در پیام خصوصی قابل تغییر نیست.

btn-language = زبان
btn-title-language = توضیحات
btn-blocked-services = مسدودسازی سرویس‌ها

btn-send-raw = { $is_enabled ->
    [true] 🟢 به صورت فایل
    *[false] ⚪ به صورت فایل
}
btn-send-music-covers = { $is_enabled ->
    [true] 🟢 کاورها
    *[false] ⚪ کاورها
}
btn-send-reactions = { $is_enabled ->
    [true] 🟢 واکنش‌ها
    *[false] ⚪ واکنش‌ها
}
btn-negativity = { $is_enabled ->
    [true] 🟢 حالت شوخ
    *[false] ⚪ حالت شوخ
}
btn-auto-translate = { $is_enabled ->
    [true] 🟢 ترجمه
    *[false] ⚪ ترجمه
}
btn-auto-caption = { $is_enabled ->
    [true] 🟢 توضیحات
    *[false] ⚪ توضیحات
}
btn-notifications = { $is_enabled ->
    [true] 🟢 اعلان‌ها
    *[false] ⚪ اعلان‌ها
}
btn-allow-playlists = { $is_enabled ->
    [true] 🟢 پلی‌لیست‌ها
    *[false] ⚪ پلی‌لیست‌ها
}
btn-allow-nsfw = { $is_enabled ->
    [true] 🟢 NSFW
    *[false] ⚪ NSFW
}

desc-send-raw = رسانه‌ها رو به صورت فایل می‌فرستم — این‌طوری کیفیتشون عالی می‌مونه.
desc-send-music-covers = به هر آهنگ، کاور آلبوم رو اضافه می‌کنم.
desc-send-reactions = ایموجی واکنش می‌ذارم تا بتونی روند پیشرفت رو ببینی.
desc-negativity-mode = از ایموجی‌های کمی شیطنت‌آمیزتر در واکنش‌ها استفاده می‌کنم.
desc-send-notifications = اگر می‌خوای رسانه‌ها بی‌صدا برات ارسال بشن، این رو خاموش کن.
desc-auto-caption = خودم بررسی می‌کنم و به رسانه‌ها توضیحات اضافه می‌کنم.
desc-auto-translate-titles = توضیحات ویدیوها رو به زبان تو ترجمه می‌کنم.
desc-allow-playlists = دانلود کل پلی‌لیست — فقط حواست به حجمش باشه.
desc-allow-nsfw = اجازه ارسال محتوای NSFW در این چت.
desc-lossless-mode = سعی می‌کنم نسخه Hi-Res آهنگ رو پیدا کنم. البته تضمین نمی‌کنم بشه.

setting-status-changed = { $is_enabled ->
    [true] *{ $setting_name }* فعال شد!
    *[false] *{ $setting_name }* غیرفعال شد.
}

pick-language = زبان را انتخاب کن 🌍
pick-title-language = زبان توضیحات را انتخاب کن
language-changed = از حالا به زبان *{ $language }* صحبت می‌کنم!
language-updated = زبان به‌روز شد.
title-language-changed = از حالا توضیحات به زبان *{ $language }* خواهد بود.
title-language-updated = زبان توضیحات به‌روز شد.
setting-updated = انجام شد، به‌روزرسانی کردم.
invalid-setting = اوم، من این تنظیم رو نمی‌شناسم.
error-updating = نتونستم به‌روزرسانی کنم، ببخشید. دوباره امتحان کنیم؟
enabled = فعال
disabled = غیرفعال
enable = فعال کردن
disable = غیرفعال کردن
back = بازگشت
service-status-changed = سرویس { $service } اکنون { $status } شد.
blocked = مسدود شد
unblocked = رفع مسدودیت شد
settings-not-found = این تنظیمات رو پیدا نکردم.
no-permission-service = تو اجازه تغییر این تنظیمات رو نداری.
error-service-status = تغییر وضعیت سرویس ناموفق بود، ببخشید.
current-status = وضعیت کنونی: { $status }

btn-configure-services = ⚙️ تنظیمات سرویس‌ها
settings-select-service = سرویس مورد نظرت رو برای تنظیم انتخاب کن:
settings-service-title = **تنظیمات { $name }**
btn-lossless = { $is_enabled ->
    [true] 🟢 LOSSLESS
    *[false] ⚪ LOSSLESS
}
btn-service-enabled = { $is_enabled ->
    [true] 🟢 سرویس
    *[false] ⚪ سرویس
}

btn-news-spam = { $is_enabled ->
    [true] 🟢 خبرنامه
    *[false] ⚪ خبرنامه
}
desc-news-spam = اجازه بده اخبار و به‌روزرسانی‌ها رو برات بفرستم.

btn-bot-sign = { $is_enabled ->
    [true] 🟢 Bot Ad 🧡
    *[false] ⚪ Bot Ad 🧡
}
desc-bot-sign = افزودن امضای «Charlotte 🧡» به رسانه‌ها. غیرفعال کردنش کاملاً رایگانه.

btn-simple-mode = { $is_enabled ->
    [true] 🟢 حالت ساده
    *[false] ⚪ حالت ساده
}
desc-simple =
    رابط کاربری ساده یوتیوب:
    روشن — فقط دو دکمه (ویدیو یا صوت)، دانلود با بالاترین کیفیت تا ۱۰۰ مگابایت (تا ۱ گیگابایت برای حامیان).
    خاموش — انتخاب رزولوشن، برش ویدیو (مخصوص حامیان).

btn-youtube-ui-mode = رابط کاربری یوتیوب
yt-ui-mode-simple = ساده
yt-ui-mode-balance = متعادل
yt-ui-mode-advanced = پیشرفته
desc-youtube-ui-mode =
    سبک رابط کاربری را برای دانلود از یوتیوب انتخاب کن:

    • ساده — ۲ دکمه (ویدیو / صوت)، دانلود با یک کلیک.
    • متعادل — دکمه‌های بهترین کیفیت با یک کلیک + دسترسی به تنظیمات پیشرفته.
    • پیشرفته — انتخاب هر کیفیتی، ترک صوتی و برش ویدیو (Trim).

btn-experimental = 🧪 قابلیت‌های جدید
desc-experimental-features =
    قابلیت‌های آزمایشی فقط در نسخه‌های جدید و رسمی تلگرام کار می‌کنن و ممکنه در نسخه‌های قدیمی یا غیررسمی درست کار نکنن.

btn-ephemeral-messages = { $is_enabled ->
    [true] 🟢 پیام‌های موقت
    *[false] ⚪ پیام‌های موقت
}
desc-ephemeral-messages = ارسال پیام‌های سیستمی در گروه‌ها به صورت پیام موقت که فقط برای خودت قابل دیدنه. اگر خاموش باشه، پیام‌های عادی با حذف خودکار می‌فرستم.
btn-chat-banned-users = 🚫 لیست مسدودشده‌ها
desc-chat-banned-users = مدیریت کاربران مسدودشده در این گفتگو.
cban-usage = شناسه کاربر را مشخص کنید یا به پیام او پاسخ دهید: <code>/cban &lt;user_id&gt;</code>
cban-cannot-ban-self = نمی‌توانید خودتان را مسدود کنید.
cban-cannot-ban-admin = نمی‌توانید مدیران گروه را مسدود کنید.
cban-cannot-ban-bot = نمی‌توانید ربات را مسدود کنید.
cban-success = کاربر <code>{ $user_id }</code> در این گفتگو مسدود شد.
cban-already-banned = کاربر <code>{ $user_id }</code> از قبل در این گفتگو مسدود است.
cunban-usage = شناسه کاربر را مشخص کنید یا به پیام او پاسخ دهید: <code>/cunban &lt;user_id&gt;</code>
cunban-not-banned = کاربر <code>{ $user_id }</code> در این گفتگو مسدود نیست.
cunban-success = کاربر <code>{ $user_id }</code> در این گفتگو رفع مسدودیت شد.
cbanlist-empty = هیچ کاربر مسدودشده‌ای در این گفتگو وجود ندارد.
cbanlist-title = <b>لیست مسدودشده‌های گفتگو:</b>
btn-unban-user = ❌ رفع مسدودیت { $user_id }
