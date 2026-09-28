msg-hello =
    Hey there! 👋
    Nice to see you, { $name }.
    Send _/help_ if you need any guidance.
    Check out @charlottesbasement — that's where I share updates and little notes.

msg-help =
    Here is what I can do:
      /start — Main menu
      /help — Help & info
      /settings — Settings
      /saves — My media library
      /copy — Copy media to clipboard
      /support — Support the project
      /cancel — Cancel download

    <b>Supported platforms</b> <i>(click to expand)</i>:
    <blockquote expandable>
    <b>Music:</b>
      • Spotify
      • Apple Music
      • Deezer
      • SoundCloud
      • YouTube Music
    <i>I'll find the track, album art, and all metadata.</i>

    <b>Video:</b>
      • YouTube (videos, shorts, audio up to 100 MB, ⭐ 1 GB for Sponsors)
      • TikTok (videos and photos)
      • Instagram (reels and posts)
      • Twitter / X (videos and images)
      • Reddit (all media from posts)
      • BlueSky, Twitch, NicoVideo

    <b>Art:</b>
      • Pixiv
      • Pinterest
    </blockquote>

    🔍 <b>Inline mode (works in any chat):</b>
      • <code>@{ $bot_username } &lt;query&gt;</code> — search pictures and memes (or just <code>@{ $bot_username } </code> for recent ones)
      • <code>@{ $bot_username } #music &lt;track&gt;</code> — search music
      • <code>@{ $bot_username } #saved &lt;query&gt;</code> — search your saved media
      • <code>@{ $bot_username } paste</code> — paste copied media (clipboard lasts for 1 hour)
    <i>To save media I sent you, reply to it with <code>/save &lt;name&gt;</code>.</i>

    Just send me a link and I'll take care of it.

processing = One second, working on it... ⏳
added-to-queue = Added you to the queue, { $count } ahead of you.
starting-download = Starting download! 🚀
invalid-callback = Oops, this button doesn't work anymore, sorry.
url-expired = That link has expired — could you send a fresh one?
setting-changed = Done! *{ $setting }* is now { $status }.
premium-granted = Yay, you got free premium access! Download as much as you like 🎉


# System & Payment
sponsor-alert = 30 days of Premium for 100 Stars 🌟
sponsor-invoice-title = Sponsor Premium (30 days)
sponsor-invoice-desc = 30 days of premium access: ad-free with extra features.
sponsor-success = Thank you for your support! Here is 30 days of Sponsor Premium 🌟
support-invoice-title = Donate { $amount } ⭐
support-invoice-desc = Support Charlotte's development!
support-success = Thank you so much for your support 🧡
support-invalid-amount = Amount must be between 1 and 100,000 Stars. Try again:
support-invalid-number = Please enter a number between 1 and 100,000:
payment-invalid-data = Error: invalid payment details.
payment-invalid-format = Error: invalid data format.
payment-link-expired = Error: link expired. Please try again.
payment-success-download = Thank you for your support! Starting download...
payment-error-refund = Something went wrong while processing. I refunded your Stars...
premium-expired = Your Sponsor Premium has expired. You can renew it anytime 🌟
bot-ad-disable-alert = Disabling bot ads requires an active Sponsorship (100 Stars).
download-failed-refund = Couldn't download that, sorry. I refunded your Stars.
not-your-request = This is not your request.
action-cancelled = Cancelled.
banned-global = You are globally banned.
banned-chat = You are banned in this chat.
too-many-requests = Too many requests at once, please slow down a bit.
menu-not-yours = This menu isn't for you, sorry.
general-error = Oops, something went wrong. Try again later?
btn-close = ✕ Close

# YouTube Trim
yt-trim-sponsor-only = Trimming video is only available to Sponsors.
yt-trim-ask-range = Send the time range to trim, like <code>01:20-02:45</code> or <code>90-165</code>:
yt-trim-invalid-range = Didn't catch that format, sorry. Use START-END, like <code>1:30-2:45</code>. Try again?
yt-trim-end-before-start = End time must be after start time. Want to try again?
yt-trim-processing = Trimming your clip, hold on a moment...
yt-trim-out-of-bounds = That range goes beyond video duration ({ $duration }). Try again?
yt-btn-full = 🎬 Full video
yt-btn-trim-locked = ★ Trim
yt-btn-cancel = Cancel
yt-ask-quality = Choose quality:
yt-btn-video = Download video
yt-btn-audio = Download audio
yt-btn-continue = Next
yt-btn-advanced = Advanced settings
yt-btn-trim = Trim
yt-btn-trim-active = ✓ Trim
yt-btn-back = Back
yt-label-channel = Channel: { $uploader }
yt-label-duration = Duration: { $duration }

btn-add-group = ➕ Add to group
btn-my-settings = ⚙️ My settings
already-downloading = I'm already downloading something for you, hold on a sec 🐾


# Errors
error-invalid-url = Oops, something is wrong with this link 🥺
error-private-content = Sorry, that's set to private — I can't reach it.
error-large-file = That file is huge... I can't send files that large yet, sorry 😔
error-not-allowed = Sorry, this feature is disabled in this chat's settings.
error-internal = Oops, something broke on my end... Could you try a bit later?
error-not-found = I searched everywhere, but found nothing at this link. Are you sure it's not deleted?
error-region-restricted = Sorry, this content is region-locked — I can't get to it.
error-age-restricted = This is 18+ content, and I can't access that, sorry 🙈
error-download-canceled = Alright, stopped the download.
error-generic = Oops, something went wrong, sorry.
error-preview-only = Only managed to grab a 30-second preview, not the full track, sorry.

download-cancel = Cancelling! Already stopped.
download-no-found = Hmm, nothing to cancel here.
downloading-tracks = Fetching tracks...
download-stats = Done: downloaded { $success }, failed { $failed }.
all-tracks-success = All tracks downloaded, yay! 🎉
total-tracks = Total tracks: { $count }
release-date = Released: { $date }
year = Year: { $year }
playlist-stopped = Playlist download stopped.
skipped-track = Skipped track: { $title }
yt-btn-topich = TOPICH
yt-sponsor-only = This feature is only for Sponsors, sorry!

# Sponsor & Support
sponsor-text =
    If you'd like to support me and this project, you can get sponsorship for 30 days.

    What you get:
      • Download large YouTube videos (up to 1 GB instead of 100 MB)
      • Trim YouTube videos before sending
      • Access to NSFW media (Twitter and Reddit)
      • Your name on the supporter board in /support

    Sponsorship is 100 Stars for 30 days ⭐

sponsor-btn-buy = ⭐ Become a Sponsor (100 Stars)

support-text =
    Charlotte is a passion project built with care. I help you save and download media without ads or restrictions.

    Servers cost about €12/month, paid out of pocket. The bot will always remain free and open for everyone.

    <b>Sponsorship:</b>
    Every 100 Stars gives you <b>30 days of sponsor perks</b>:
    • Download large YouTube videos (up to 1 GB instead of 100 MB)
    • Trim YouTube videos before sending
    • Access to NSFW media (Twitter, Reddit, Pixiv)
    • Your name on the supporter board{ $status }

    Any support means the world to me, thank you for being here ⭐

support-status-lifetime =
    ⭐ <b>Your status:</b> Sponsor (lifetime) 🌟

support-status-active =
    ⭐ <b>Your status:</b> Sponsor (until { $date })
    Progress: { $progress }/100 ⭐ to next renewal

support-status-progress =
    ⭐ Progress: { $progress }/100 ⭐ to sponsorship

support-btn-sponsor = ⭐ 30-Day Sponsorship (100 ⭐)
support-btn-coffee = ☕ Buy a coffee
support-btn-stars = ⭐ Send Stars
support-btn-supporters = 🤍 Supporter Board
support-btn-back = 🔙 Back

support-wall-empty =
    <b>Supporter Board</b>

    Nobody is here yet. But you could be the first to support me and appear on this list ⭐

support-wall-text =
    <b>Supporter Board</b>

    Big thanks to everyone helping me run and grow:

    { $supporters }

    Your support means so much ⭐

support-choose-stars = Choose how many Stars you'd like to send in support:
support-stars-ten = ⭐ 10 Stars
support-stars-fifty = ⭐ 50 Stars
support-stars-hundred = ⭐ 100 Stars
support-stars-custom = ✏️ Custom amount

support-custom-prompt = Type how many Stars you want to send (from 1 to 100,000):

support-success-sponsor =
    Thank you so much for { $stars } ⭐!
    Sponsorship active for { $days } days (until { $date })! Your name was added to the supporter board ⭐

support-success-tip =
    Thank you so much for { $stars } ⭐!
    Your support means a lot! { $progress }/100 ⭐ to sponsorship ⭐

# Report command
report-reply-required = Reply with <code>/report</code> to the message from me that has an issue.
report-not-bot-message = This command only works in reply to my messages 🐾
report-success = Thanks for letting me know! I passed the details to the developer, we'll sort it out soon 🧡
error-send-failed = ❌ Failed to send media to Telegram. The file might be corrupted or Telegram rejected it.
yt-trim-invalid-format = Didn't catch that format, sorry. Use START-END, like <code>1:30-2:45</code>. Try again?
