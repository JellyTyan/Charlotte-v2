msg-hello =
    Cześć! 👋
    Miło cię widzieć, { $name }.
    Wpisz _/help_, jeśli czegoś nie wiesz.
    Wpadnij na @charlottesbasement — dzielę się tam nowościami i różnymi drobiazgami.

msg-help =
    Oto co potrafię:
      /start — Menu główne
      /help — Pomoc
      /settings — Ustawienia
      /saves — Moja biblioteka
      /copy — Skopiuj multimedia do schowka
      /support — Wesprzyj projekt
      /cancel — Anuluj pobieranie

    <b>Obsługiwane platformy</b> <i>(kliknij, aby rozwinąć)</i>:
    <blockquote expandable>
    <b>Muzyka:</b>
      • Spotify
      • Apple Music
      • Deezer
      • SoundCloud
      • YouTube Music
    <i>Znajdę utwór, okładkę i wszystkie tagi.</i>

    <b>Wideo:</b>
      • YouTube (wideo, shortsy, audio do 100 MB, ⭐ 1 GB dla Sponsorów)
      • TikTok (wideo i zdjęcia)
      • Instagram (rolki i posty)
      • Twitter / X (wideo i zdjęcia)
      • Reddit (wszystkie multimedia z postów)
      • BlueSky, Twitch, NicoVideo

    <b>Grafika:</b>
      • Pixiv
      • Pinterest
    </blockquote>

    🔍 <b>Tryb inline (działa w każdym czacie):</b>
      • <code>@{ $bot_username } &lt;tekst&gt;</code> — szukaj grafik i memów (lub po prostu <code>@{ $bot_username } </code> dla ostatnich)
      • <code>@{ $bot_username } #music &lt;utwór&gt;</code> — szukaj muzyki
      • <code>@{ $bot_username } #saved &lt;tekst&gt;</code> — szukaj w zapisanych
      • <code>@{ $bot_username } paste</code> — wklej skopiowane multimedia (schowek działa przez 1 godzinę)
    <i>Aby zapisać multimedia ode mnie w bibliotece, odpowiedz na nie poleceniem <code>/save &lt;nazwa&gt;</code>.</i>

    Po prostu wyślij mi link, a ja wszystkim się zajmę.

processing = Sekundkę, już robię... ⏳
added-to-queue = Dodałam cię do kolejki, przed tobą jeszcze { $count }.
starting-download = Zaczynam pobierać! 🚀
invalid-callback = Ojej, ten przycisk już nie działa, przepraszam.
url-expired = Ten link już wygasł — wyślesz świeży?
setting-changed = Gotowe! *{ $setting }* to teraz { $status }.
premium-granted = Hura, masz darmowy dostęp premium! Pobieraj ile dusza zapragnie 🎉


# System & Payment
service-disabled = Ta usługa jest teraz tymczasowo wyłączona, przepraszam. Spróbuj trochę później.
support-invoice-title = Wesprzyj { $amount } ⭐
support-invoice-desc = Wesprzyj rozwój Charlotte!
support-success = Bardzo dziękuję ci za wsparcie 🧡
support-invalid-amount = Kwota musi wynosić od 1 do 100 000 Gwiazdek. Spróbuj jeszcze raz:
support-invalid-number = Wpisz, proszę, liczbę od 1 do 100 000:
payment-invalid-data = Błąd: nieprawidłowe dane płatności.
payment-invalid-format = Błąd: zły format danych.
payment-link-expired = Błąd: link wygasł. Spróbuj ponownie.
payment-success-download = Dziękuję za wsparcie! Zaczynam pobieranie...
payment-error-refund = Coś poszło nie tak podczas przetwarzania. Zwróciłam Gwiazdki...
premium-expired = Twoje Premium Sponsora wygasło. Możesz je odnowić w każdej chwili 🌟
bot-ad-disable-alert = Wyłączenie reklam bota wymaga aktywnego Sponsorowania (100 Gwiazdek).
download-failed-refund = Nie udało się pobrać, przepraszam. Zwróciłam Gwiazdki.
not-your-request = To nie twoje żądanie.
action-cancelled = Anulowano.
banned-global = Zostałeś(-aś) zablokowany(-a) globalnie.
banned-chat = Zostałeś(-aś) zablokowany(-a) na tym czacie.
too-many-requests = Za dużo zapytań pod rząd, poczekaj chwileczkę.
menu-not-yours = To menu nie jest dla ciebie, przepraszam.
general-error = Ojej, coś poszło nie tak. Spróbujesz później?
btn-close = ✕ Zamknij

# YouTube Trim
yt-trim-sponsor-only = Przycinanie wideo jest dostępne tylko dla Sponsorów.
yt-trim-ask-range = Podaj zakres do przycięcia, np. <code>01:20-02:45</code> lub <code>90-165</code>:
yt-trim-invalid-range = Nie zrozumiałam formatu, przepraszam. Użyj POCZĄTEK-KONIEC, np. <code>1:30-2:45</code>. Jeszcze raz?
yt-trim-end-before-start = Koniec musi być później niż początek. Spróbujesz znowu?
yt-trim-processing = Przycinam klip, poczekaj chwileczkę...
yt-trim-out-of-bounds = Ten zakres wykracza poza czas trwania wideo ({ $duration }). Spróbujesz jeszcze raz?
yt-btn-full = 🎬 Pełne wideo
yt-btn-trim-locked = ★ Przycinanie
yt-btn-cancel = Anuluj
yt-ask-quality = Wybierz jakość:
yt-btn-video = Pobierz wideo
yt-btn-audio = Pobierz audio
yt-btn-continue = Dalej
yt-btn-advanced = Ustawienia zaawansowane
yt-btn-trim = Przycinanie
yt-btn-trim-active = ✓ Przycinanie
yt-btn-back = Wstecz
yt-label-channel = Kanał: { $uploader }
yt-label-duration = Czas trwania: { $duration }

btn-add-group = ➕ Dodaj do grupy
btn-my-settings = ⚙️ Moje ustawienia
already-downloading = Już coś dla ciebie pobieram, poczekaj chwileczkę 🐾


# Errors
error-invalid-url = Ojej, coś jest nie tak z tym linkiem 🥺
error-private-content = Przepraszam, to jest prywatne — nie mam tam dostępu.
error-large-file = Jaki wielki plik... Nie potrafię jeszcze przesyłać takich olbrzymów, przepraszam 😔
error-not-allowed = Przepraszam, ta funkcja jest wyłączona w ustawieniach tego czatu.
error-internal = Ojej, coś mi się w środku zepsuło... Spróbujesz troszkę później?
error-not-found = Szukałam wszędzie, ale nic pod tym linkiem nie znalazłam. Na pewno nie został usunięty?
error-region-restricted = Przepraszam, ta treść jest zablokowana w moim regionie — nie mogę jej pobrać.
error-age-restricted = To treść 18+, a do takich nie mam dostępu, przepraszam 🙈
error-download-canceled = Dobrze, zatrzymałam pobieranie.
error-generic = Ojej, coś poszło nie tak, przepraszam.
error-preview-only = Udało się pobrać tylko 30-sekundowy zwiastun, a nie cały utwór, przepraszam.

download-cancel = Anuluję! Już zatrzymane.
download-no-found = Hmm, nie ma tu czego anulować.
downloading-tracks = Zbieram utwory...
download-stats = Gotowe: pobrano { $success }, nie udało się — { $failed }.
all-tracks-success = Wszystkie utwory pobrane, hura! 🎉
total-tracks = Łącznie utworów: { $count }
release-date = Wydano: { $date }
year = Rok: { $year }
playlist-stopped = Pobieranie playlisty zatrzymane.
skipped-track = Pominięto utwór: { $title }
yt-btn-topich = TOPICH
yt-sponsor-only = Ta funkcja jest tylko dla Sponsorów, przepraszam!

# Sponsor & Support
support-text =
    Charlotte to projekt tworzony z pasją i sercem. Pomagam zapisywać i pobierać multimedia bez reklam i ograniczeń.

    Serwery kosztują około 12€ miesięcznie, co opłacane jest z własnej kieszeni. Bot zawsze pozostanie darmowy i otwarty dla każdego.

    <b>Co daje sponsorowanie:</b>
    • YouTube: filmy do 1 GB zamiast 100 MB
    • YouTube: TOPICH, maksymalna jakość jako oryginalny plik
    • YouTube: przycinanie filmów przed wysłaniem
    • Instagram i TikTok w najlepszej jakości
    • Multimedia NSFW z Twittera, Reddita i Pixiv
    • Do 1000 zapisanych multimediów zamiast 200

    <b>Jak zbierają się Gwiazdki:</b>
    Wszystkie Gwiazdki, które wysyłasz, trafiają do skarbonki, nawet po 10 czy 50. Każde 100 ⭐ to 30 dni sponsorowania, a jeśli jest już aktywne, dni dodadzą się do obecnego terminu. Za każdą wpłatę twoje imię pojawi się na tablicy podziękowań.{ $status }

    Każde wsparcie jest dla mnie ogromnie ważne, dziękuję, że jesteś ze mną ⭐

support-status-lifetime =
    ⭐ <b>Twój status:</b> Sponsor (na zawsze) 🌟

support-status-active =
    ⭐ <b>Twój status:</b> Sponsor (do { $date })
    W skarbonce: { $progress }/100 ⭐ do kolejnego odnowienia

support-status-progress =
    ⭐ W skarbonce: { $progress }/100 ⭐ do sponsorowania

support-btn-sponsor = ⭐ Sponsorowanie na 30 dni (100 ⭐)
support-btn-coffee = ☕ Postaw kawę
support-btn-stars = ⭐ Wyślij Gwiazdki
support-btn-supporters = 🤍 Tablica podziękowań
support-btn-back = 🔙 Wstecz

support-wall-empty =
    <b>Tablica podziękowań</b>

    Na razie nikogo tu nie ma. Ale możesz być pierwszą osobą, która mnie wesprze i pojawi się na tej liście ⭐

support-wall-text =
    <b>Tablica podziękowań</b>

    Ogromne podziękowania dla wszystkich, którzy pomagają mi działać i rozwijać się:

    { $supporters }

    Wasze wsparcie znaczy dla mnie bardzo wiele ⭐

support-choose-stars = Wybierz, ile Gwiazdek chcesz przekazać na wsparcie:
support-stars-ten = ⭐ 10 Gwiazdek
support-stars-fifty = ⭐ 50 Gwiazdek
support-stars-hundred = ⭐ 100 Gwiazdek
support-stars-custom = ✏️ Własna kwota

support-custom-prompt = Wpisz, ile Gwiazdek chcesz wysłać (od 1 do 100 000):

support-success-sponsor =
    Bardzo dziękuję za { $stars } ⭐!
    Sponsorowanie włączone na { $days } dni (do { $date })! Twoje imię zostało dodane do tablicy podziękowań ⭐

support-success-tip =
    Bardzo dziękuję za { $stars } ⭐!
    Twoje wsparcie wiele dla mnie znaczy! W skarbonce: { $progress }/100 ⭐ do sponsorowania ⭐

# Report command
report-reply-required = Odpowiedz komendą <code>/report</code> na moją wiadomość, z którą coś poszło nie tak.
report-not-bot-message = Ta komenda działa tylko w odpowiedzi na moje wiadomości 🐾
report-success = Dzięki za zgłoszenie! Przekazałam wszystko programiście, zaraz się temu przyjrzymy 🧡
error-send-failed = ❌ Nie udało się wysłać pliku do Telegrama. Plik może być uszkodzony lub odrzucony.
yt-trim-invalid-format = Nie rozpoznaję tego formatu. Podaj POCZĄTEK-KONIEC, np. <code>1:30-2:45</code>. Spróbujesz ponownie?
