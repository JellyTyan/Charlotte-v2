settings-welcome = Hej! 👋 Tutaj możesz dostosować wszystko do siebie. Czuj się jak w domu!
settings-back = 🔙 Wstecz
settings-title = Ustawienia
settings-no-permission = Aww, nie masz uprawnień do zmiany tych ustawień!
settings-saved = Super! Ustawienia zaktualizowane! ✨
settings-no-allowed-groups = To ustawienie nie jest dostępne dla grup, sorki!
settings-no-allowed-dm = To ustawienie nie jest dla czatów prywatnych, sorki!

btn-language = Język
btn-title-language = Język opisów
btn-blocked-services = Zablokowane serwisy

btn-send-raw = { $is_enabled ->
    [true] ✅ Wyślij jako plik
    *[false] ❌ Wyślij jako plik
}
btn-send-music-covers = { $is_enabled ->
    [true] ✅ Okładki muzyki
    *[false] ❌ Okładki muzyki
}
btn-send-reactions = { $is_enabled ->
    [true] ✅ Reakcje
    *[false] ❌ Reakcje
}
btn-negativity = { $is_enabled ->
    [true] ✅ Negatywność
    *[false] ❌ Negatywność
}
btn-auto-translate = { $is_enabled ->
    [true] ✅ Tłumacz opisy
    *[false] ❌ Tłumacz opisy
}
btn-auto-caption = { $is_enabled ->
    [true] ✅ Opisy
    *[false] ❌ Opisy
}
btn-notifications = { $is_enabled ->
    [true] ✅ Powiadomienia
    *[false] ❌ Powiadomienia
}
btn-allow-playlists = { $is_enabled ->
    [true] ✅ Playlisty
    *[false] ❌ Playlisty
}
btn-allow-nsfw = { $is_enabled ->
    [true] ✅ NSFW
    *[false] ❌ NSFW
}

desc-send-raw = Będę wysyłać media jako pliki dla najlepszej jakości! 🎨
desc-send-music-covers = Dołączę okładkę albumu do każdego utworu. 🎵
desc-send-reactions = Będę reagować emotkami, żebyś widział(a) postęp! ⚡
desc-negativity-mode = Będę używać toksycznych emoji w reakcjach! 😈
desc-send-notifications = Wyłącz, jeśli chcesz otrzymywać media bez dźwięku powiadomienia. 🔕
desc-auto-caption = Sama sprawdzę i dodam opisy do mediów. 📝
desc-auto-translate-titles = Przetłumaczę opisy wideo na Twój język! 🌍
desc-allow-playlists = Pobiorę całe playlisty (ostrożnie z tym!). 📂
desc-allow-nsfw = Zezwalaj na zawartość NSFW w tym czacie. 🔞
desc-lossless-mode = Spróbuję znaleźć dla Ciebie utwory w Hi-Res! Ale nie obiecuję, że znajdę, ani że będą to właściwe wersje. 🎧

setting-status-changed = { $is_enabled ->
    [true] Jeej! Ustawienie *{ $setting_name }* włączone!
    *[false] Zrozumiałam! Ustawienie *{ $setting_name }* wyłączone!
}

pick-language = Wybierz język! 🌍
pick-title-language = Wybierz język opisów!
language-changed = Ekstra! Teraz mówię po *{ $language }*!
language-updated = Język zaktualizowany!
title-language-changed = Opisy będą teraz po *{ $language }*!
title-language-updated = Język opisów zaktualizowany!
setting-updated = Gotowe! Zaktualizowano.
invalid-setting = Ups, to ustawienie wygląda dziwnie!
error-updating = O nie, nie udało się zaktualizować. Spróbuj ponownie?
setting-changed = Zrobione! *{ $setting }* jest teraz { $status }!
enabled = włączone
disabled = wyłączone
enable = Włącz
disable = Wyłącz
back = Wstecz
service-status-changed = Serwis { $service } jest teraz { $status }!
blocked = zablokowany
unblocked = odblokowany
settings-not-found = Hmm, nie mogę znaleźć tych ustawień!
no-permission-service = Nie możesz dotykać tych ustawień!
error-service-status = Nie udało się zaktualizować statusu serwisu. :(
current-status = Obecny status: { $status }

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

btn-news-spam = { $is_enabled ->
    [true] ✅ Newsletter
    *[false] ❌ Newsletter
}
desc-news-spam = Zezwól botowi na wysyłanie nowości i aktualizacji! 📰

btn-bot-sign = { $is_enabled ->
    [true] 🧡 Bot Ad [ON]
   *[false] 🧡 Bot Ad [OFF]
}
desc-bot-sign = Append a promotional signature "Charlotte 🧡" to downloaded media. Disabling this requires Sponsorship 🌟.
