saves-usage = To save to your media library:
    Reply to a message containing a video, photo, GIF, or audio with <code>/save &lt;name&gt;</code>

saves-no-name = Give your save a name, like <code>/save kittens</code>.

saves-name-too-long = That name is too long, max 128 characters.

saves-no-media = Didn't find any suitable media in that message (video, photo, audio, or GIF).

saves-bot-only = You can only save media downloaded through me. Reply with <code>/save &lt;name&gt;</code> to my message.

saves-limit-reached = You've reached your save limit (<b>{ $current }/{ $limit }</b>). Remove some via /saves?

saves-saved = { $emoji } Saved as «<b>{ $label }</b>»!

    { $status }

    Send it in any chat:
    <code>@{ $bot_username } { $label }</code>

    All your saves: /saves

saves-status-private = 🔒 <i>Private, visible only to you</i>
saves-status-public = 🌐 <i>Public, visible to everyone in search</i>
saves-status-pending = ⏳ <i>Submitted for review to public library</i>

saves-btn-make-public = 🌐 Make public
saves-btn-make-private = 🔒 Make private
saves-toast-public = Meme is now public in search!
saves-toast-pending = Sent for review. Once approved, it'll show up in public search.
saves-toast-private = Tucked away, now visible only to you.

saves-empty = Your media library is empty for now.

    To add media, reply to a downloaded video, photo, or audio with <code>/save &lt;name&gt;</code>

saves-header = <b>Your media library</b> ({ $count }):

saves-deleted-toast = Removed from your saves.
saves-missing-toast = Couldn't find that item, maybe it was already deleted?

saves-mod-approved =
    <b>Your save was approved!</b> 🎉

    Meme «<b>{ $label }</b>» passed moderation and is now visible in public search.

saves-mod-rejected =
    <b>Publication request rejected</b>

    Meme «<b>{ $label }</b>» didn't pass moderation, but stays safe in your private saves 🔒

copy-usage = To copy media to clipboard:
    Reply to a message with a video, photo, GIF, or audio with <code>/copy</code>

copy-bot-only = You can only copy media sent by me. Reply with <code>/copy</code> to my message.

copy-no-media = Didn't find any suitable media in that message (video, photo, audio, or GIF).

copy-copied = <b>Copied to clipboard!</b>

    To paste it in any chat, type:
    <code>@{ $bot_username } paste</code>

    <i>Clipboard lasts for 1 hour</i>

saves-banned-alert = Your access to submitting memes to the public library was restricted.
saves-mod-banned =
    <b>Access restricted</b>

    An administrator restricted you from suggesting memes to the public library. Your private saves stay with you 🔒

saves-label-reserved = The name «<b>{ $label }</b>» is reserved by the bot for system commands. Please choose another!
saves-label-trash = Name is invalid or consists only of symbols. Please choose a meaningful name.
saves-dupe-media = This file is already saved in your library as «<b>{ $existing_label }</b>».
saves-dupe-label =
    You already have a save named «<b>{ $label }</b>».
    Do you want to replace the old media with this one?
saves-replace-expired = This confirmation dialog has expired. Please try /save again.
saves-replaced-toast = Media replaced successfully!
saves-cancelled-toast = Replacement cancelled.
saves-replace-cancelled = Replacement cancelled. The original media remains unchanged.
saves-dupe-public = This media is already available in the public meme library!
saves-dupe-label-short = You already have a save with this name!
saves-rename-remoderation = Name changed — submitted for re-moderation before appearing in public search.

saves-list-hint = Pick a save to view and manage:
saves-card =
    { $emoji } <b>{ $label }</b>

    { $status }
    👁 Uses: <b>{ $uses }</b>
    📅 Added: <b>{ $date }</b>

    <i>Send in any chat:</i>
    <code>@{ $bot_username } { $label }</code>
saves-btn-preview = 👁 Preview
saves-btn-send = 🚀 Send to chat
saves-btn-rename = ✏️ Rename
saves-btn-delete = 🗑 Delete
saves-btn-back = ◀️ Back to list
saves-btn-close = ❌ Close
saves-btn-cancel = ◀️ Cancel
saves-btn-replace = 🔄 Replace media
saves-foreign-library = ❌ This is not your library
saves-preview-failed = Couldn't send the preview.
saves-rename-prompt =
    ✏️ <b>Renaming</b> «{ $label }»

    Send the new name as a message (up to { $max } characters):
saves-renamed = ✅ Name updated: «<b>{ $label }</b>»
saves-label-word-too-long = One of the words in the name is too long. Please use a shorter name.
