from utils import get_ytdlp_options, random_cookie_file


def get_audio_options():
    opts = get_ytdlp_options()
    opts["format"] = "bestaudio"
    opts["outtmpl"] = "storage/temp/%(title)s.%(ext)s"
    opts["postprocessors"] = [
        {
            'key': 'SponsorBlock',
            'api': 'https://sponsor.ajay.app',
            'categories': ['sponsor', 'intro', 'outro', 'selfpromo', 'preview', 'interaction', 'filler'],
        },
        {
            'key': 'ModifyChapters',
            'remove_sponsor_segments': ['sponsor', 'intro', 'outro', 'selfpromo', 'preview', 'interaction', 'filler']
        },
        {
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }
    ]

    cookie_file = random_cookie_file("youtube")
    if cookie_file:
        opts["cookiefile"] = cookie_file

    return opts
