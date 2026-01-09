from fluentogram import TranslatorHub
from fluentogram.storage.file import FileStorage

def create_translator_hub() -> TranslatorHub:
    storage = FileStorage("locales/{locale}/")

    locales_map = {
        "en": "en",
        "ru": ("ru", "en"),
        "uk": ("uk", "en"),
        "be": ("be", "en"),
        "cs": ("cs", "en"),
        "pl": ("pl", "en"),
        "de": ("de", "en"),
        "es": ("es", "en"),
        "fa": ("fa", "en")
    }

    hub = TranslatorHub(locales_map, storage=storage, root_locale="en")
    return hub
