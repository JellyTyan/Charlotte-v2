saves-usage = Aby zapisać do biblioteki:
    Odpowiedz na wiadomość z wideo, zdjęciem, GIF-em lub muzyką poleceniem <code>/save &lt;nazwa&gt;</code>

saves-no-name = Podaj nazwę dla zapisanego elementu, np. <code>/save kotki</code>.

saves-name-too-long = Nazwa jest zbyt długa, maksymalnie 128 znaków.

saves-no-media = Nie znalazłam w tej wiadomości odpowiednich multimediów (wideo, zdjęcie, audio lub GIF).

saves-bot-only = Zapisać można tylko to, co zostało pobrane przeze mnie. Odpowiedz <code>/save &lt;nazwa&gt;</code> na moją wiadomość.

saves-limit-reached = Osiągnięto limit zapisanych multimediów (<b>{ $current }/{ $limit }</b>). Usunąć zbędne przez /saves?

saves-saved = { $emoji } Zapisano jako «<b>{ $label }</b>»!

    { $status }

    Możesz to wysłać na dowolnym czacie:
    <code>@{ $bot_username } { $label }</code>

    Wszystkie twoje zapisy: /saves

saves-status-private = 🔒 <i>Prywatne, widoczne tylko dla ciebie</i>
saves-status-public = 🌐 <i>Publiczne, widoczne dla wszystkich w wyszukiwarce</i>
saves-status-pending = ⏳ <i>Przesłano do weryfikacji w publicznej bibliotece</i>

saves-btn-make-public = 🌐 Zrób publicznym
saves-btn-make-private = 🔒 Zrób prywatnym
saves-toast-public = Teraz mem jest widoczny dla wszystkich w wyszukiwarce!
saves-toast-pending = Wysłano do weryfikacji. Po zatwierdzeniu pojawi się w wyszukiwarce publicznej.
saves-toast-private = Schowano, teraz widoczne tylko dla ciebie.

saves-empty = Na razie masz pusto w bibliotece.

    Aby dodać multimedia, odpowiedz na pobrane wideo, zdjęcie lub muzykę poleceniem <code>/save &lt;nazwa&gt;</code>

saves-header = <b>Twoja biblioteka</b> ({ $count }):

saves-deleted-toast = Usunięto z zapisanych.
saves-missing-toast = Nie znalazłam tego elementu, może został już usunięty?

saves-mod-approved =
    <b>Twój zapis został zatwierdzony!</b> 🎉

    Mem «<b>{ $label }</b>» przeszedł moderację i jest teraz widoczny dla wszystkich w wyszukiwarce publicznej.

saves-mod-rejected =
    <b>Wniosek o publikację odrzucony</b>

    Mem «<b>{ $label }</b>» nie przeszedł moderacji, ale pozostał w twoich prywatnych zapisach 🔒

copy-usage = Aby skopiować multimedia do schowka:
    Odpowiedz na wiadomość z wideo, zdjęciem, GIF-em lub muzyką poleceniem <code>/copy</code>

copy-bot-only = Kopiować można tylko to, co przysłałam ja. Odpowiedz <code>/copy</code> na moją wiadomość.

copy-no-media = Nie znalazłam w tej wiadomości odpowiednich multimediów (wideo, zdjęcie, audio lub GIF).

copy-copied = <b>Skopiowano do schowka!</b>

    Aby wkleić to na dowolnym czacie, wpisz:
    <code>@{ $bot_username } paste</code>

    <i>Schowek działa przez 1 godzinę</i>

saves-banned-alert = Ograniczono ci możliwość dodawania memów do wspólnej biblioteki.
saves-mod-banned =
    <b>Dostęp ograniczony</b>

    Administrator zablokował ci możliwość proponowania memów do biblioteki publicznej. Twoje prywatne zapisy pozostają z tobą 🔒

saves-label-reserved = Nazwa «<b>{ $label }</b>» jest zarezerwowana przez bota dla komend systemowych. Wybierz inną!
saves-label-trash = Nazwa jest nieprawidłowa lub zawiera wyłącznie symbole. Wybierz czytelną nazwę.
saves-dupe-media = Ten plik jest już zapisany w twojej bibliotece jako «<b>{ $existing_label }</b>».
saves-dupe-label =
    Masz już zapis o nazwie «<b>{ $label }</b>».
    Czy chcesz zastąpić stary plik tym nowym?
saves-replace-expired = Czas na potwierdzenie upłynął. Spróbuj ponownie użyć /save.
saves-replaced-toast = Plik został pomyślnie zastąpiony!
saves-cancelled-toast = Anulowano zastąpienie.
saves-replace-cancelled = Zastąpienie anulowane. Poprzedni plik pozostał bez zmian.
saves-dupe-public = Ten plik znajduje się już w publicznej bibliotece memów!
saves-dupe-label-short = Masz już zapis o takiej nazwie!
saves-rename-remoderation = Nazwa została zmieniona — mem wysłano do ponownej moderacji przed wyświetleniem w wyszukiwaniu publicznym.

saves-list-hint = Wybierz zapis, aby go wyświetlić i zarządzać nim:
saves-card =
    { $emoji } <b>{ $label }</b>

    { $status }
    👁 Użycia: <b>{ $uses }</b>
    📅 Dodano: <b>{ $date }</b>

    <i>Wyślij w dowolnym czacie:</i>
    <code>@{ $bot_username } { $label }</code>
saves-btn-preview = 👁 Podgląd
saves-btn-send = 🚀 Do czatu
saves-btn-rename = ✏️ Zmień nazwę
saves-btn-delete = 🗑 Usuń
saves-btn-back = ◀️ Do listy
saves-btn-close = ❌ Zamknij
saves-btn-cancel = ◀️ Anuluj
saves-btn-replace = 🔄 Zamień media
saves-foreign-library = ❌ To nie jest twoja biblioteka
saves-preview-failed = Nie udało się wysłać podglądu.
saves-rename-prompt =
    ✏️ <b>Zmiana nazwy</b> «{ $label }»

    Wyślij nową nazwę w wiadomości (maks. { $max } znaków):
saves-renamed = ✅ Nazwa zmieniona: «<b>{ $label }</b>»
saves-label-word-too-long = Jedno ze słów w nazwie jest za długie. Podaj krótszą nazwę.
