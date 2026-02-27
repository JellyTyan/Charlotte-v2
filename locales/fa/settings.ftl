settings-welcome = سلام! 👋 اینجا می‌تونی همه چیز رو به سلیقه خودت تنظیم کنی. راحت باش!
settings-back = 🔙 بازگشت
settings-title = تنظیمات
settings-no-permission = اوه، شما اجازه تغییر این تنظیمات رو نداری!
settings-saved = عالی! تنظیمات به‌روز شد! ✨
settings-no-allowed-groups = این تنظیم برای گروه‌ها در دسترس نیست، ببخشید!
settings-no-allowed-dm = این تنظیم برای چت خصوصی نیست، ببخشید!

btn-language = زبان
btn-title-language = زبان توضیحات
btn-blocked-services = سرویس‌های مسدود

btn-send-raw = { $is_enabled ->
    [true] ✅ ارسال فایل (بهترین کیفیت)
    *[false] ❌ ارسال فایل (بهترین کیفیت)
}
btn-send-music-covers = { $is_enabled ->
    [true] ✅ کاور موزیک
    *[false] ❌ کاور موزیک
}
btn-send-reactions = { $is_enabled ->
    [true] ✅ واکنش‌های بامزه
    *[false] ❌ واکنش‌های بامزه
}
btn-auto-translate = { $is_enabled ->
    [true] ✅ ترجمه توضیحات
    *[false] ❌ ترجمه توضیحات
}
btn-auto-caption = { $is_enabled ->
    [true] ✅ توضیحات
    *[false] ❌ توضیحات
}
btn-notifications = { $is_enabled ->
    [true] ✅ تبلیغات
    *[false] ❌ تبلیغات
}
btn-allow-playlists = { $is_enabled ->
    [true] ✅ اجازه پلی‌لیست
    *[false] ❌ اجازه پلی‌لیست
}

desc-send-raw = تصاویر رو به صورت فایل می‌فرستم تا کیفیت عالی باشه! 🎨
desc-send-music-covers = کاور آلبوم رو به هر آهنگ می‌چسبونم. 🎵
desc-send-reactions = با ایموجی واکنش نشون میدم تا ببینی دارم کار می‌کنم! ⚡
desc-send-notifications = غیرفعال کن تا فایل‌ها رو بی‌صدا دریافت کنی. 🔕
desc-auto-caption = خودم چک می‌کنم و توضیحات رو به مدیا اضافه می‌کنم. 📝
desc-auto-translate-titles = توضیحات ویدیوها رو به زبان تو ترجمه می‌کنم! 🌍
desc-allow-playlists = کل پلی‌لیست رو دانلود می‌کنم (با احتیاط استفاده کن!). 📂
desc-lossless-mode = من سعی می‌کنم آهنگ‌های Hi-Res را برای شما پیدا کنم! اما قول نمی‌دهم که آن را پیدا کنم یا اینکه نسخه درست باشد. 🎧

setting-status-changed = { $is_enabled ->
    [true] هورا! تنظیم *{ $setting_name }* فعال شد!
    *[false] حله! تنظیم *{ $setting_name }* غیرفعال شد!
}

pick-language = زبانت رو انتخاب کن! 🌍
pick-title-language = زبان توضیحات رو انتخاب کن!
language-changed = عالی! حالا به *{ $language }* صحبت می‌کنم!
language-updated = زبان به‌روز شد!
title-language-changed = حالا توضیحات به *{ $language }* خواهند بود!
title-language-updated = زبان توضیحات به‌روز شد!
setting-updated = انجام شد! به‌روزرسانی شد.
invalid-setting = اوه، این تنظیم عجیب به نظر میاد!
error-updating = وای، نشد به‌روز کنم. دوباره امتحان کنیم؟
setting-changed = انجام شد! *{ $setting }* اکنون { $status } است!
enabled = فعال
disabled = غیرفعال
enable = فعال‌سازی
disable = غیرفعال‌سازی
back = بازگشت
service-status-changed = سرویس { $service } اکنون { $status } است!
blocked = مسدود
unblocked = آزاد
settings-not-found = همم، تنظیمات رو پیدا نمی‌کنم!
no-permission-service = اجازه دستکاری این تنظیمات رو نداری!
error-service-status = نشد وضعیت سرویس رو تغییر بدم. :(
current-status = وضعیت فعلی: { $status }

btn-configure-services = ⚙️ Configure Services
settings-select-service = Select a service to configure:
settings-service-title = ⚙️ **{ $name } Settings**
btn-lossless = { $is_enabled ->
    [true] ✅ LOSSLESS
    *[false] ❌ LOSSLESS
}
btn-service-enabled = { $is_enabled ->
    [true] ✅ Enabled
    *[false] ❌ Enabled
}
