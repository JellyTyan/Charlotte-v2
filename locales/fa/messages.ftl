msg-hello =
    سلام! 👋
    از دیدنت خوشحالم، { $name }.
    اگر راهنمایی خواستی، _/help_ رو بفرست.
    به کانال @charlottesbasement هم سر بزن — اونجا خبرها و یادداشت‌های کوچیک رو می‌ذارم.

msg-help =
    کارهایی که از دستم برمیاد:
      /start — منوی اصلی
      /help — راهنما
      /settings — تنظیمات
      /saves — کتابخانه رسانه من
      /copy — کپی رسانه در کلیپ‌بورد
      /support — حمایت از پروژه
      /cancel — لغو دانلود

    <b>پلتفرم‌های پشتیبانی‌شده</b> <i>(برای باز شدن لمس کن)</i>:
    <blockquote expandable>
    <b>موسیقی:</b>
      • Spotify
      • Apple Music
      • Deezer
      • SoundCloud
      • YouTube Music
    <i>آهنگ، کاور آلبوم و همه برچسب‌ها رو پیدا می‌کنم.</i>

    <b>ویدیو:</b>
      • YouTube (ویدیو، شورتز، صوت تا ۱۰۰ مگابایت، ⭐ ۱ گیگابایت برای حامیان)
      • TikTok (ویدیو و عکس)
      • Instagram (ریلز و پست‌ها)
      • Twitter / X (ویدیو و تصاویر)
      • Reddit (تمام رسانه‌های پست‌ها)
      • BlueSky, Twitch, NicoVideo

    <b>تصاویر هنری:</b>
      • Pixiv
      • Pinterest
    </blockquote>

    🔍 <b>حالت اینلاین (در هر چتی کار می‌کنه):</b>
      • <code>@{ $bot_username } &lt;متن&gt;</code> — جستجوی تصاویر و میم‌ها (یا فقط <code>@{ $bot_username } </code> برای موارد اخیر)
      • <code>@{ $bot_username } #music &lt;آهنگ&gt;</code> — جستجوی آهنگ
      • <code>@{ $bot_username } #saved &lt;متن&gt;</code> — جستجو در ذخیره‌شده‌های خودت
      • <code>@{ $bot_username } paste</code> — چسباندن رسانه کپی‌شده (کلیپ‌بورد تا ۱ ساعت معتبره)
    <i>برای ذخیره رسانه‌ای که فرستادم در کتابخانه‌ات، با دستور <code>/save &lt;نام&gt;</code> بهش ریپلای کن.</i>

    فقط لینک رو برام بفرست تا همه‌چیز رو مرتب کنم.

processing = یه ثانیه صبر کن، دارم آماده‌ش می‌کنم... ⏳
added-to-queue = به صف اضافه‌ت کردم، { $count } نفر جلوتر از تو هستن.
starting-download = شروع به دانلود کردم! 🚀
invalid-callback = ای وای، این دکمه دیگه کار نمی‌کنه، ببخشید.
url-expired = این لینک منقضی شده — می‌تونی یه لینک تازه برام بفرستی؟
setting-changed = انجام شد! *{ $setting }* الان { $status } است.
premium-granted = آخ جون، پرمیوم رایگان برات فعال شد! هرچقدر می‌خوای دانلود کن 🎉


# System & Payment
service-disabled = این سرویس فعلاً موقتاً غیرفعاله، ببخشید. کمی بعد دوباره امتحان کن.
support-invoice-title = اهدا { $amount } ⭐
support-invoice-desc = از توسعه شارلوت حمایت کن!
support-success = یک دنیا از حمایتت ممنونم 🧡
support-invalid-amount = مبلغ باید بین ۱ تا ۱۰۰٬۰۰۰ ستاره باشه. دوباره امتحان کن:
support-invalid-number = لطفاً یک عدد بین ۱ تا ۱۰۰٬۰۰۰ وارد کن:
payment-invalid-data = خطا: اطلاعات پرداخت نامعتبره.
payment-invalid-format = خطا: قالب اطلاعات نادرسته.
payment-link-expired = خطا: لینک منقضی شده. دوباره امتحان کن.
payment-success-download = ممنون از حمایتت! شروع به دانلود کردم...
payment-error-refund = موقع پردازش مشکلی پیش اومد. ستاره‌ها رو پس دادم...
premium-expired = پرمیوم حامی تموم شد. هر زمان خواستی می‌تونی تمدیدش کنی 🌟
bot-ad-disable-alert = غیرفعال کردن تبلیغات ربات نیاز به حمایت فعال داره (۱۰۰ ستاره).
download-failed-refund = نتونستم دانلودش کنم، ببخشید. ستاره‌هات رو پس دادم.
not-your-request = این درخواست مال تو نیست.
action-cancelled = لغو شد.
banned-global = تو به طور سراسری مسدود شدی.
banned-chat = تو در این چت مسدود شدی.
too-many-requests = تعداد درخواست‌ها پشت سر هم زیاده، یه کم صبر کن.
menu-not-yours = این منو برای تو نیست، ببخشید.
general-error = ای وای، مشکلی پیش اومد. می‌خوای بعداً دوباره امتحان کنی؟
btn-close = ✕ بستن

# YouTube Trim
yt-trim-sponsor-only = برش ویدیو فقط برای حامیان در دسترسه.
yt-trim-ask-range = بازه زمانی برای برش رو بفرست، مثلاً <code>01:20-02:45</code> یا <code>90-165</code>:
yt-trim-invalid-range = قالبش رو متوجه نشدم، ببخشید. باید شروع-پایان باشه، مثلاً <code>1:30-2:45</code>. دوباره؟
yt-trim-end-before-start = زمان پایان باید بعد از زمان شروع باشه. دوباره امتحان می‌کنی؟
yt-trim-processing = دارم کلیپ رو برش می‌دم، یه کم صبر کن...
yt-trim-out-of-bounds = این بازه بیشتر از مدت زمان ویدیوئه ({ $duration }). دوباره امتحان می‌کنی؟
yt-btn-full = 🎬 ویدیوی کامل
yt-btn-trim-locked = ★ برش
yt-btn-cancel = لغو
yt-ask-quality = کیفیت رو انتخاب کن:
yt-btn-video = دانلود ویدیو
yt-btn-audio = دانلود صوت
yt-btn-continue = بعدی
yt-btn-advanced = تنظیمات پیشرفته
yt-btn-trim = برش
yt-btn-trim-active = ✓ برش
yt-btn-back = بازگشت
yt-label-channel = کانال: { $uploader }
yt-label-duration = مدت زمان: { $duration }

btn-add-group = ➕ افزودن به گروه
btn-my-settings = ⚙️ تنظیمات من
already-downloading = همین الان دارم چیزی برات دانلود می‌کنم، یه لحظه وایسا 🐾


# Errors
error-invalid-url = ای وای، این لینک مشکلی داره 🥺
error-private-content = ببخشید، این محتوا خصوصیه — من بهش دسترسی ندارم.
error-large-file = چه فایل بزرگی... هنوز نمی‌تونم این‌قدر فایل‌های بزرگ بفرستم، ببخشید 😔
error-not-allowed = ببخشید، این ویژگی در تنظیمات این چت غیرفعال شده.
error-internal = ای وای، یه چیزی توی من خراب شده... می‌تونی یه کم بعد دوباره امتحان کنی؟
error-not-found = همه‌جا رو گشتم ولی چیزی با این لینک پیدا نشد. مطمئنی حذف نشده؟
error-region-restricted = ببخشید، این محتوا در منطقه من مسدوده — نمی‌تونم بهش برسم.
error-age-restricted = این محتوا ۱۸+ سال است و من اجازه دسترسی بهش رو ندارم، ببخشید 🙈
error-download-canceled = باشه، دانلود رو متوقف کردم.
error-generic = ای وای، مشکلی پیش اومد، ببخشید.
error-preview-only = فقط تونستم پیش‌نمایش ۳۰ ثانیه‌ای رو دانلود کنم، نه کل آهنگ رو، ببخشید.

download-cancel = دارم لغو می‌کنم! متوقفش کردم.
download-no-found = اوم، چیزی برای لغو کردن اینجا نیست.
downloading-tracks = در حال جمع‌آوری آهنگ‌ها...
download-stats = آماده شد: { $success } دانلود شد، { $failed } ناموفق بود.
all-tracks-success = همه آهنگ‌ها دانلود شدن، ایول! 🎉
total-tracks = کل آهنگ‌ها: { $count }
release-date = انتشار: { $date }
year = سال: { $year }
playlist-stopped = دانلود پلی‌لیست متوقف شد.
skipped-track = رد شدن از آهنگ: { $title }
yt-btn-topich = TOPICH
yt-sponsor-only = این قابلیت فقط مخصوص حامیانه، ببخشید!

# Sponsor & Support
support-text =
    شارلوت یک پروژه دلی است که با عشق ساخته شده. کمکت می‌کنم رسانه‌ها رو بدون تبلیغات و محدودیت ذخیره کنی.

    سرورها ماهانه حدود ۱۲ یورو هزینه دارن که از جیب پرداخت می‌شه. ربات همیشه رایگان و عمومی باقی می‌مونه.

    <b>مزایای حامی:</b>
    • یوتیوب: ویدیو تا ۱ گیگابایت به‌جای ۱۰۰ مگابایت
    • یوتیوب: TOPICH، بالاترین کیفیت به‌صورت فایل اصلی
    • یوتیوب: برش ویدیو قبل از ارسال
    • اینستاگرام و تیک‌تاک با بهترین کیفیت
    • رسانه‌های NSFW از توییتر، ردیت و پیکسیو
    • تا ۱۰۰۰ رسانه ذخیره‌شده به‌جای ۲۰۰

    <b>ستاره‌ها چطور جمع می‌شن:</b>
    همه ستاره‌هایی که می‌فرستی توی قلکت جمع می‌شن، حتی ۱۰ یا ۵۰ تا. هر ۱۰۰ ⭐ یعنی ۳۰ روز حمایت، و اگه فعال باشه روزها به مدت فعلی اضافه می‌شن. با هر کمکی اسمت روی تابلوی سپاسگزاری میاد.{ $status }

    هر حمایتی برای من دنیایی ارزش داره، مرسی که هستی ⭐

support-status-lifetime =
    ⭐ <b>وضعیت تو:</b> حامی (همیشگی) 🌟

support-status-active =
    ⭐ <b>وضعیت تو:</b> حامی (تا { $date })
    در قلک: { $progress }/100 ⭐ تا تمدید بعدی

support-status-progress =
    ⭐ در قلک: { $progress }/100 ⭐ تا حمایت

support-btn-sponsor = ⭐ حمایت ۳۰ روزه (۱۰۰ ⭐)
support-btn-coffee = ☕ خرید یک فنجان قهوه
support-btn-stars = ⭐ ارسال ستاره
support-btn-supporters = 🤍 تابلوی سپاسگزاری
support-btn-back = 🔙 بازگشت

support-wall-empty =
    <b>تابلوی سپاسگزاری</b>

    هنوز کسی اینجا نیست. ولی تو می‌تونی اولین نفری باشی که از من حمایت می‌کنه و اسمش اینجاست ⭐

support-wall-text =
    <b>تابلوی سپاسگزاری</b>

    یک تشکر بزرگ از همه عزیزانی که کمکم می‌کنن فعال بمونم و رشد کنم:

    { $supporters }

    حمایت شما برای من خیلی باارزشه ⭐

support-choose-stars = انتخاب کن چه تعداد ستاره می‌خوای برای حمایت بفرستی:
support-stars-ten = ⭐ ۱۰ ستاره
support-stars-fifty = ⭐ ۵۰ ستاره
support-stars-hundred = ⭐ ۱۰۰ ستاره
support-stars-custom = ✏️ مبلغ دلخواه

support-custom-prompt = بنویس چند تا ستاره می‌خوای بفرستی (از ۱ تا ۱۰۰٬۰۰۰):

support-success-sponsor =
    خیلی خیلی ممنونم بابت { $stars } ⭐!
    حمایت به مدت { $days } روز فعال شد (تا { $date })! اسمت به تابلوی سپاسگزاری اضافه شد ⭐

support-success-tip =
    خیلی خیلی ممنونم بابت { $stars } ⭐!
    حمایتت خیلی باارزشه! در قلک: { $progress }/100 ⭐ تا حامی شدن ⭐

# Report command
report-reply-required = لطفاً دستور <code>/report</code> را در پاسخ به پیام من که مشکلی دارد بفرست.
report-not-bot-message = این دستور فقط در پاسخ به پیام‌های خود من کار می‌کند 🐾
report-success = ممنون که گزارش دادی! اطلاعات را برای توسعه‌دهنده فرستادم و به‌زودی بررسی می‌کنیم 🧡
error-send-failed = ❌ ارسال رسانه به تلگرام ناموفق بود. فایل ممکن است خراب باشد یا تلگرام آن را رد کرده باشد.
yt-trim-invalid-format = فرمت نامعتبر است. از فرمت شروع-پایان استفاده کنید، مانند <code>1:30-2:45</code>. دوباره امتحان می‌کنید؟
