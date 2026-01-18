settings-welcome = Hej! 👋 Tutaj możesz dostosować wszystko do siebie. Czuj się jak w domu!
settings-back = 🔙 Wstecz
settings-title = Ustawienia
settings-no-permission = Aww, nie masz uprawnień do zmiany tych ustawień!
settings-saved = Super! Ustawienia zaktualizowane! ✨
settings-no-allowed-groups = To ustawienie nie jest dostępne dla grup, sorki!
settings-no-allowed-dm = To ustawienie nie jest dla czatów prywatnych, sorki!

btn-language = Język
btn-title-language = Język tytułów
btn-blocked-services = Zablokowane serwisy

btn-send-raw = { $is_enabled ->
    [true] ✅ Art jako plik (Najlepsza jakość)
    *[false] ❌ Art jako plik (Najlepsza jakość)
}
btn-send-music-covers = { $is_enabled ->
    [true] ✅ Okładki muzyki
    *[false] ❌ Okładki muzyki
}
btn-send-reactions = { $is_enabled ->
    [true] ✅ Zabawne reakcje
    *[false] ❌ Zabawne reakcje
}
btn-auto-translate = { $is_enabled ->
    [true] ✅ Tłumacz tytuły
    *[false] ❌ Tłumacz tytuły
}
btn-auto-caption = { $is_enabled ->
    [true] ✅ Auto-opisy
    *[false] ❌ Auto-opisy
}
btn-notifications = { $is_enabled ->
    [true] ✅ Powiadomienia
    *[false] ❌ Powiadomienia
}
btn-allow-playlists = { $is_enabled ->
    [true] ✅ Zezwól na playlisty
    *[false] ❌ Zezwól na playlisty
}

desc-send-raw = Wyślę arty jako nieskompresowane pliki, więc jakość będzie kosmiczna! 🎨
desc-send-music-covers = Dołączę okładkę albumu do każdego utworu. 🎵
desc-send-reactions = Będę reagować emotkami, żebyś widział(a) postęp! ⚡
desc-send-notifications = Wyłącz, jeśli chcesz otrzymywać media bez dźwięku powiadomienia. 🔕
desc-auto-caption = Sama sprawdzę i dodam opisy do mediów. 📝
desc-auto-translate-titles = Przetłumaczę tytuły wideo na Twój język! 🌍
desc-allow-playlists = Pobiorę całe playlisty (ostrożnie z tym!). 📂
desc-lossless-mode = Spróbuję znaleźć dla Ciebie utwory w Hi-Res! Ale nie obiecuję, że znajdę, ani że będą to właściwe wersje. 🎧

setting-status-changed = { $is_enabled ->
    [true] Jeej! Ustawienie *{ $setting_name }* włączone!
    *[false] Zrozumiałam! Ustawienie *{ $setting_name }* wyłączone!
}

pick-language = Wybierz język! 🌍
pick-title-language = Wybierz język tytułów!
language-changed = Ekstra! Teraz mówię po *{ $language }*!
language-updated = Język zaktualizowany!
title-language-changed = Tytuły będą teraz po *{ $language }*!
title-language-updated = Język tytułów zaktualizowany!
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
