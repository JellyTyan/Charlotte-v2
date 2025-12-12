from fluentogram import TranslatorHub
from fluentogram.storage.file import FileStorage

def create_translator_hub() -> TranslatorHub:
    storage = FileStorage("locales/{locale}/")

    locales_map = {
        "en": "en",
        "ru": "ru"
    }

    hub = TranslatorHub(locales_map, storage=storage, root_locale="en")
    return hub
