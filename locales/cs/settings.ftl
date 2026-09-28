settings-welcome = Ahoj! Tady si můžeš všechno nastavit podle sebe, udělej si pohodlí.
settings-back = 🔙 Zpět
settings-title = Nastavení
settings-no-permission = Jejda, nemáš oprávnění měnit toto nastavení.
settings-saved = Nastavení aktualizováno! ✨
settings-no-allowed-groups = Toto nastavení není dostupné ve skupinách, promiň.
settings-no-allowed-dm = Toto nastavení nelze měnit v soukromých zprávách.

btn-language = Jazyk
btn-title-language = Popisky
btn-blocked-services = Blokování služeb

btn-send-raw = { $is_enabled ->
    [true] 🟢 Jako soubor
    *[false] ⚪ Jako soubor
}
btn-send-music-covers = { $is_enabled ->
    [true] 🟢 Přebaly
    *[false] ⚪ Přebaly
}
btn-send-reactions = { $is_enabled ->
    [true] 🟢 Reakce
    *[false] ⚪ Reakce
}
btn-negativity = { $is_enabled ->
    [true] 🟢 Drzejší režim
    *[false] ⚪ Drzejší režim
}
btn-auto-translate = { $is_enabled ->
    [true] 🟢 Překlad
    *[false] ⚪ Překlad
}
btn-auto-caption = { $is_enabled ->
    [true] 🟢 Popisky
    *[false] ⚪ Popisky
}
btn-notifications = { $is_enabled ->
    [true] 🟢 Upozornění
    *[false] ⚪ Upozornění
}
btn-allow-playlists = { $is_enabled ->
    [true] 🟢 Playlisty
    *[false] ⚪ Playlisty
}
btn-allow-nsfw = { $is_enabled ->
    [true] 🟢 NSFW
    *[false] ⚪ NSFW
}

desc-send-raw = Budu posílat média jako soubory — to zachová nejvyšší kvalitu.
desc-send-music-covers = Připojím přebal alba ke každé skladbě.
desc-send-reactions = Budu dávat emoji reakce, abys viděl(a) postup.
desc-negativity-mode = V reakcích budu používat o něco drzejší emoji.
desc-send-notifications = Vypni, pokud chceš dostávat média potichu.
desc-auto-caption = Sama zkontroluji a přidám popis k médiím.
desc-auto-translate-titles = Přeložím popisy videí do tvého jazyka.
desc-allow-playlists = Stáhnu celé playlisty — opatrně s tím.
desc-allow-nsfw = Povolit NSFW obsah v tomto chatu.
desc-lossless-mode = Pokusím se najít Hi-Res verzi skladby. Neslibuji však, že to vyjde.

setting-status-changed = { $is_enabled ->
    [true] Zapnula jsem *{ $setting_name }*!
    *[false] Vypnula jsem *{ $setting_name }*.
}

pick-language = Vyber jazyk 🌍
pick-title-language = Vyber jazyk pro popisky
language-changed = Teď mluvím v jazyce *{ $language }*!
language-updated = Jazyk aktualizován.
title-language-changed = Popisy teď budou v jazyce *{ $language }*.
title-language-updated = Jazyk popisků aktualizován.
setting-updated = Hotovo, aktualizováno.
invalid-setting = Hmm, toto nastavení neznám.
error-updating = Nepodařilo se aktualizovat, promiň. Zkusíme to znovu?
enabled = zapnuto
disabled = vypnuto
enable = Zapnout
disable = Vypnout
back = Zpět
service-status-changed = Služba { $service } je teď { $status }.
blocked = zablokována
unblocked = odblokována
settings-not-found = Tato nastavení nemohu najít.
no-permission-service = Nemáš oprávnění měnit tato nastavení.
error-service-status = Nepodařilo se aktualizovat stav služby, promiň.
current-status = Současný stav: { $status }

btn-configure-services = ⚙️ Nastavení služeb
settings-select-service = Vyber službu k nastavení:
settings-service-title = **Nastavení { $name }**
btn-lossless = { $is_enabled ->
    [true] 🟢 LOSSLESS
    *[false] ⚪ LOSSLESS
}
btn-service-enabled = { $is_enabled ->
    [true] 🟢 Služba
    *[false] ⚪ Služba
}

btn-news-spam = { $is_enabled ->
    [true] 🟢 Odběr zpráv
    *[false] ⚪ Odběr zpráv
}
desc-news-spam = Povolit zasílání novinek a aktualizací.

btn-bot-sign = { $is_enabled ->
    [true] 🟢 Bot Ad 🧡
    *[false] ⚪ Bot Ad 🧡
}
desc-bot-sign = Přidávat podpis „Charlotte 🧡“ k médiím. Vypnutí je zcela zdarma.

btn-simple-mode = { $is_enabled ->
    [true] 🟢 Jednoduchý režim
    *[false] ⚪ Jednoduchý režim
}
desc-simple =
    Jednoduché rozhraní YouTube:
    Zapnuto — pouze dvě tlačítka (Video nebo Audio), stahování v nejvyšší kvalitě do 100 MB (až 1 GB pro Sponzory).
    Vypnuto — výběr rozlišení, ořezání videa (pro Sponzory).

btn-youtube-ui-mode = Rozhraní YouTube
yt-ui-mode-simple = Jednoduché
yt-ui-mode-balance = Vyvážené
yt-ui-mode-advanced = Pokročilé
desc-youtube-ui-mode =
    Vyber styl rozhraní pro stahování z YouTube:

    • Jednoduché — 2 tlačítka (Video / Audio), stahování jedním kliknutím.
    • Vyvážené — tlačítka nejlepších kvalit na jedno kliknutí + přístup k pokročilému nastavení.
    • Pokročilé — výběr libovolné kvality, zvukové stopy a ořezání videa (Trim).

btn-experimental = 🧪 Nové funkce
desc-experimental-features =
    Experimentální funkce fungují pouze v novějších oficiálních aplikacích Telegramu a ve starších nebo alternativních klientech se mohou chovat nestabilně.

btn-ephemeral-messages = { $is_enabled ->
    [true] 🟢 Efemérní zprávy
    *[false] ⚪ Efemérní zprávy
}
desc-ephemeral-messages = Odesílat servisní zprávy ve skupinách jako efemérní zprávy viditelné pouze pro tebe. Při vypnutí posílám běžné automaticky mazané zprávy.
btn-chat-banned-users = 🚫 Seznam blokovaných
desc-chat-banned-users = Správa uživatelů blokovaných v tomto chatu.
cban-usage = Zadej ID uživatele nebo odpověz na jeho zprávu: <code>/cban &lt;user_id&gt;</code>
cban-cannot-ban-self = Nemůžeš zablokovat sám sebe.
cban-cannot-ban-admin = Správce chatu nelze zablokovat.
cban-cannot-ban-bot = Bota nelze zablokovat.
cban-success = Uživatel <code>{ $user_id }</code> byl v tomto chatu zablokován.
cban-already-banned = Uživatel <code>{ $user_id }</code> je v tomto chatu již zablokován.
cunban-usage = Zadej ID uživatele nebo odpověz na jeho zprávu: <code>/cunban &lt;user_id&gt;</code>
cunban-not-banned = Uživatel <code>{ $user_id }</code> není v tomto chatu zablokován.
cunban-success = Uživatel <code>{ $user_id }</code> byl v tomto chatu odblokován.
cbanlist-empty = V tomto chatu nejsou žádní zablokovaní uživatelé.
cbanlist-title = <b>Seznam blokovaných v chatu:</b>
btn-unban-user = ❌ Odblokovat { $user_id }
