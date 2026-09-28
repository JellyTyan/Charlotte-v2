settings-welcome = Cześć! Tutaj możesz dostosować wszystko pod siebie, rozgość się.
settings-back = 🔙 Wstecz
settings-title = Ustawienia
settings-no-permission = Ojej, nie masz uprawnień do zmiany tych ustawień.
settings-saved = Ustawienia zaktualizowane! ✨
settings-no-allowed-groups = To ustawienie nie jest dostępne w grupach, przepraszam.
settings-no-allowed-dm = Tego ustawienia nie można zmieniać w wiadomościach prywatnych.

btn-language = Język
btn-title-language = Podpisy
btn-blocked-services = Blokada serwisów

btn-send-raw = { $is_enabled ->
    [true] 🟢 Jako plik
    *[false] ⚪ Jako plik
}
btn-send-music-covers = { $is_enabled ->
    [true] 🟢 Okładki
    *[false] ⚪ Okładki
}
btn-send-reactions = { $is_enabled ->
    [true] 🟢 Reakcje
    *[false] ⚪ Reakcje
}
btn-negativity = { $is_enabled ->
    [true] 🟢 Z pazurem
    *[false] ⚪ Z pazurem
}
btn-auto-translate = { $is_enabled ->
    [true] 🟢 Tłumaczenie
    *[false] ⚪ Tłumaczenie
}
btn-auto-caption = { $is_enabled ->
    [true] 🟢 Podpisy
    *[false] ⚪ Podpisy
}
btn-notifications = { $is_enabled ->
    [true] 🟢 Powiadomienia
    *[false] ⚪ Powiadomienia
}
btn-allow-playlists = { $is_enabled ->
    [true] 🟢 Playlisty
    *[false] ⚪ Playlisty
}
btn-allow-nsfw = { $is_enabled ->
    [true] 🟢 NSFW
    *[false] ⚪ NSFW
}

desc-send-raw = Będę wysyłać multimedia jako pliki — to zachowuje najwyższą jakość.
desc-send-music-covers = Dołączę okładkę albumu do każdego utworu.
desc-send-reactions = Będę dodawać reakcje emoji, abyś widział(-a) postęp prac.
desc-negativity-mode = Będę używać nieco bardziej zadziornych reakcji emoji.
desc-send-notifications = Wyłącz, jeśli chcesz otrzymywać multimedia po cichu.
desc-auto-caption = Sama sprawdzę i dodam opisy do multimediów.
desc-auto-translate-titles = Przetłumaczę opisy wideo na twój język.
desc-allow-playlists = Pobiorę całe playlisty — ostrożnie z tym.
desc-allow-nsfw = Zezwól na treści NSFW na tym czacie.
desc-lossless-mode = Spróbuję znaleźć wersję Hi-Res utworu. Nie obiecuję jednak, że się uda.

setting-status-changed = { $is_enabled ->
    [true] Włączyłam *{ $setting_name }*!
    *[false] Wyłączyłam *{ $setting_name }*.
}

pick-language = Wybierz język 🌍
pick-title-language = Wybierz język podpisów
language-changed = Teraz mówię po *{ $language }*!
language-updated = Język zaktualizowany.
title-language-changed = Teraz opisy będą po *{ $language }*.
title-language-updated = Język podpisów zaktualizowany.
setting-updated = Gotowe, zaktualizowałam.
invalid-setting = Hmm, nie znam takiego ustawienia.
error-updating = Nie udało się zaktualizować, przepraszam. Spróbujemy jeszcze raz?
enabled = włączone
disabled = wyłączone
enable = Włącz
disable = Wyłącz
back = Wstecz
service-status-changed = Serwis { $service } jest teraz { $status }.
blocked = zablokowany
unblocked = odblokowany
settings-not-found = Nie mogę znaleźć tych ustawień.
no-permission-service = Nie możesz zmieniać tych ustawień.
error-service-status = Nie udało się zaktualizować statusu serwisu, przepraszam.
current-status = Aktualny status: { $status }

btn-configure-services = ⚙️ Ustawienia serwisów
settings-select-service = Wybierz serwis do skonfigurowania:
settings-service-title = **Ustawienia { $name }**
btn-lossless = { $is_enabled ->
    [true] 🟢 LOSSLESS
    *[false] ⚪ LOSSLESS
}
btn-service-enabled = { $is_enabled ->
    [true] 🟢 Serwis
    *[false] ⚪ Serwis
}

btn-news-spam = { $is_enabled ->
    [true] 🟢 Newsletter
    *[false] ⚪ Newsletter
}
desc-news-spam = Pozwól na wysyłanie ci nowości i aktualizacji.

btn-bot-sign = { $is_enabled ->
    [true] 🟢 Bot Ad 🧡
    *[false] ⚪ Bot Ad 🧡
}
desc-bot-sign = Dodawaj podpis „Charlotte 🧡” do multimediów. Wyłączenie jest całkowicie darmowe.

btn-simple-mode = { $is_enabled ->
    [true] 🟢 Tryb prosty
    *[false] ⚪ Tryb prosty
}
desc-simple =
    Prosty interfejs YouTube:
    Włączony — tylko dwa przyciski (Wideo lub Audio), pobieranie w najlepszej jakości do 100 MB (do 1 GB dla Sponsorów).
    Wyłączony — wybór rozdzielczości, przycinanie wideo (dla Sponsorów).

btn-youtube-ui-mode = Interfejs YouTube
yt-ui-mode-simple = Prosty
yt-ui-mode-balance = Zbalansowany
yt-ui-mode-advanced = Zaawansowany
desc-youtube-ui-mode =
    Wybierz styl interfejsu do pobierania z YouTube:

    • Prosty — 2 przyciski (Wideo / Audio), pobieranie jednym kliknięciem.
    • Zbalansowany — przyciski najlepszych jakości jednym kliknięciem + dostęp do zaawansowanych ustawień.
    • Zaawansowany — wybór dowolnej jakości, ścieżki dźwiękowej i przycinanie wideo (Trim).

btn-experimental = 🧪 Nowe funkcje
desc-experimental-features =
    Funkcje eksperymentalne działają tylko w nowszych oficjalnych aplikacjach Telegrama i mogą działać niestabilnie w starszych lub nieoficjalnych klientach.

btn-ephemeral-messages = { $is_enabled ->
    [true] 🟢 Wiadomości efemeryczne
    *[false] ⚪ Wiadomości efemeryczne
}
desc-ephemeral-messages = Wysyłaj wiadomości serwisowe w grupach jako efemeryczne, widoczne tylko dla ciebie. Gdy wyłączone — wysyłam zwykłe wiadomości z automatycznym usuwaniem.
btn-chat-banned-users = 🚫 Lista zablokowanych
desc-chat-banned-users = Zarządzaj użytkownikami zablokowanymi na tym czacie.
cban-usage = Podaj ID użytkownika lub odpowiedz na jego wiadomość: <code>/cban &lt;user_id&gt;</code>
cban-cannot-ban-self = Nie możesz zablokować samego siebie.
cban-cannot-ban-admin = Nie możesz zablokować administratora czatu.
cban-cannot-ban-bot = Nie możesz zablokować bota.
cban-success = Użytkownik <code>{ $user_id }</code> został zablokowany na tym czacie.
cban-already-banned = Użytkownik <code>{ $user_id }</code> jest już zablokowany na tym czacie.
cunban-usage = Podaj ID użytkownika lub odpowiedz na jego wiadomość: <code>/cunban &lt;user_id&gt;</code>
cunban-not-banned = Użytkownik <code>{ $user_id }</code> nie jest zablokowany na tym czacie.
cunban-success = Użytkownik <code>{ $user_id }</code> został odblokowany na tym czacie.
cbanlist-empty = Brak zablokowanych użytkowników na tym czacie.
cbanlist-title = <b>Lista zablokowanych na czacie:</b>
btn-unban-user = ❌ Odblokuj { $user_id }
