msg-hello =
    Ahoj! 👋
    Ráda tě vidím, { $name }.
    Napiš _/help_, pokud něčemu nerozumíš.
    Mrkni na @charlottesbasement — tam sdílím novinky a různé drobnosti.

msg-help =
    Tohle všechno umím:
      /start — Hlavní menu
      /help — Nápověda
      /settings — Nastavení
      /saves — Moje knihovna médií
      /copy — Zkopírovat média do schránky
      /support — Podpořit projekt
      /cancel — Zrušit stahování

    <b>Podporované platformy</b> <i>(kliknutím rozbalíš)</i>:
    <blockquote expandable>
    <b>Hudba:</b>
      • Spotify
      • Apple Music
      • Deezer
      • SoundCloud
      • YouTube Music
    <i>Najdu skladbu, přebal alba i všechny štítky.</i>

    <b>Video:</b>
      • YouTube (videa, shortsy, audio do 100 MB, ⭐ 1 GB pro Sponzory)
      • TikTok (videa a fotky)
      • Instagram (reels a příspěvky)
      • Twitter / X (videa a obrázky)
      • Reddit (všechna média z příspěvků)
      • BlueSky, Twitch, NicoVideo

    <b>Umění:</b>
      • Pixiv
      • Pinterest
    </blockquote>

    🔍 <b>Inline režim (funguje v každém chatu):</b>
      • <code>@{ $bot_username } &lt;dotaz&gt;</code> — hledání obrázků a memů (nebo jen <code>@{ $bot_username } </code> pro nedávné)
      • <code>@{ $bot_username } #music &lt;skladba&gt;</code> — hledání hudby
      • <code>@{ $bot_username } #saved &lt;dotaz&gt;</code> — hledání v uložených médiích
      • <code>@{ $bot_username } paste</code> — vložit zkopírované médium (schránka vydrží 1 hodinu)
    <i>Chceš-li médium ode mě uložit do knihovny, odpověz na něj příkazem <code>/save &lt;název&gt;</code>.</i>

    Prostě mi pošli odkaz a já se o všechno postarám.

processing = Vteřinku, už na tom dělám... ⏳
added-to-queue = Přidala jsem tě do fronty, před tebou je ještě { $count }.
starting-download = Začínám stahovat! 🚀
invalid-callback = Jejda, tohle tlačítko už nefunguje, promiň.
url-expired = Odkaz už vypršel — pošleš mi čerstvý?
setting-changed = Hotovo! *{ $setting }* je teď { $status }.
premium-granted = Hurá, máš bezplatný prémiový přístup! Stahuj, kolik chceš 🎉


# System & Payment
service-disabled = Tato služba je teď dočasně vypnutá, promiň. Zkus to o něco později.
support-invoice-title = Přispět { $amount } ⭐
support-invoice-desc = Podpoř vývoj Charlotte!
support-success = Moc ti děkuji za podporu 🧡
support-invalid-amount = Částka musí být mezi 1 a 100 000 Hvězdami. Zkus to znovu:
support-invalid-number = Zadej, prosím, číslo od 1 do 100 000:
payment-invalid-data = Chyba: neplatné platební údaje.
payment-invalid-format = Chyba: neplatný formát údajů.
payment-link-expired = Chyba: odkaz vypršel. Zkus to znovu.
payment-success-download = Děkuji za podporu! Začínám stahovat...
payment-error-refund = Při zpracování se stala chyba. Hvězdy jsem vrátila...
premium-expired = Tvé Sponzorské Premium vypršelo. Můžeš si ho kdykoliv prodloužit 🌟
bot-ad-disable-alert = Vypnutí reklamy bota vyžaduje aktivní Sponzorství (100 Hvězd).
download-failed-refund = Nepodařilo se stáhnout, promiň. Hvězdy jsem ti vrátila.
not-your-request = Tohle není tvůj požadavek.
action-cancelled = Zrušeno.
banned-global = Máš globální zákaz.
banned-chat = Máš zákaz v tomto chatu.
too-many-requests = Příliš mnoho požadavků za sebou, chvilku počkej.
menu-not-yours = Tohle menu není pro tebe, promiň.
general-error = Jejda, něco se pokazilo. Zkusíš to později?
btn-close = ✕ Zavřít

# YouTube Trim
yt-trim-sponsor-only = Ořezání videa je dostupné pouze pro Sponzory.
yt-trim-ask-range = Pošli časový rozsah k ořezání, např. <code>01:20-02:45</code> nebo <code>90-165</code>:
yt-trim-invalid-range = Nerozuměla jsem formátu, promiň. Použij ZAČÁTEK-KONEC, např. <code>1:30-2:45</code>. Znovu?
yt-trim-end-before-start = Konec musí být později než začátek. Zkusíš to ještě jednou?
yt-trim-processing = Ořezávám klip, chvilku počkej...
yt-trim-out-of-bounds = Tento rozsah přesahuje délku videa ({ $duration }). Zkusíš to znovu?
yt-btn-full = 🎬 Celé video
yt-btn-trim-locked = ★ Ořezání
yt-btn-cancel = Zrušit
yt-ask-quality = Vyber kvalitu:
yt-btn-video = Stáhnout video
yt-btn-audio = Stáhnout audio
yt-btn-continue = Další
yt-btn-advanced = Pokročilé nastavení
yt-btn-trim = Ořezání
yt-btn-trim-active = ✓ Ořezání
yt-btn-back = Zpět
yt-label-channel = Kanál: { $uploader }
yt-label-duration = Délka: { $duration }

btn-add-group = ➕ Přidat do skupiny
btn-my-settings = ⚙️ Moje nastavení
already-downloading = Už pro tebe něco stahuji, chvilku počkej 🐾


# Errors
error-invalid-url = Jejda, s tímto odkazem je něco v nepořádku 🥺
error-private-content = Promiň, tohle je soukromé — tam se nedostanu.
error-large-file = To je moc velký soubor... Takové obry zatím posílat neumím, promiň 😔
error-not-allowed = Promiň, tato funkce je v nastavení tohoto chatu vypnutá.
error-internal = Jejda, ve mně se něco pokazilo... Zkusíš to o chvilku později?
error-not-found = Prohledala jsem všechno, ale na tomto odkazu nic není. Není smazaný?
error-region-restricted = Promiň, tento obsah je v mém regionu blokovaný — nemůžu ho stáhnout.
error-age-restricted = Tohle je obsah 18+ a k tomu se nedostanu, promiň 🙈
error-download-canceled = Dobře, stahování jsem zastavila.
error-generic = Jejda, něco se pokazilo, promiň.
error-preview-only = Podařilo se stáhnout jen 30sekundovou ukázku, nikoliv celou skladbu, promiň.

download-cancel = Ruším! Už jsem to zastavila.
download-no-found = Hmm, tady není co rušit.
downloading-tracks = Shromažďuji skladby...
download-stats = Hotovo: staženo { $success }, nepovedlo se — { $failed }.
all-tracks-success = Všechny skladby staženy, hurá! 🎉
total-tracks = Celkem skladeb: { $count }
release-date = Vydáno: { $date }
year = Rok: { $year }
playlist-stopped = Stahování playlistu zastaveno.
skipped-track = Přeskočena skladba: { $title }
yt-btn-topich = TOPICH
yt-sponsor-only = Tato funkce je pouze pro Sponzory, promiň!

# Sponsor & Support
support-text =
    Charlotte je srdcový projekt tvořený s láskou. Pomáhám ti ukládat a stahovat média bez reklam a omezení.

    Servery stojí okolo 12€ měsíčně a hradím je z vlastní kapsy. Bot bude vždy zdarma a otevřený pro všechny.

    <b>Co dává sponzorství:</b>
    • YouTube: videa až 1 GB místo 100 MB
    • YouTube: TOPICH, maximální kvalita jako originální soubor
    • YouTube: ořezání videa před odesláním
    • Instagram a TikTok v nejlepší kvalitě
    • NSFW média z Twitteru, Redditu a Pixivu
    • Až 1000 uložených médií místo 200

    <b>Jak se sbírají Hvězdy:</b>
    Všechny Hvězdy, které pošleš, se sčítají v pokladničce, i po 10 nebo 50. Každých 100 ⭐ dá 30 dní sponzorství, a pokud už je aktivní, dny se přičtou k aktuálnímu termínu. Za jakýkoli dar se tvé jméno objeví na zdi díků.{ $status }

    Každá podpora pro mě moc znamená, děkuji, že jsi se mnou ⭐

support-status-lifetime =
    ⭐ <b>Tvůj status:</b> Sponzor (navždy) 🌟

support-status-active =
    ⭐ <b>Tvůj status:</b> Sponzor (do { $date })
    V pokladničce: { $progress }/100 ⭐ do dalšího prodloužení

support-status-progress =
    ⭐ V pokladničce: { $progress }/100 ⭐ do sponzorství

support-btn-sponsor = ⭐ Sponzorství na 30 dní (100 ⭐)
support-btn-coffee = ☕ Koupit kávu
support-btn-stars = ⭐ Poslat Hvězdy
support-btn-supporters = 🤍 Zeď díků
support-btn-back = 🔙 Zpět

support-wall-empty =
    <b>Zeď díků</b>

    Zatím tu nikdo není. Ale můžeš být prvním, kdo mě podpoří a objeví se na tomto seznamu ⭐

support-wall-text =
    <b>Zeď díků</b>

    Velké poděkování všem, kteří mi pomáhají fungovat a růst:

    { $supporters }

    Vaše podpora pro mě moc znamená ⭐

support-choose-stars = Vyber, kolik Hvězd chceš poslat na podporu:
support-stars-ten = ⭐ 10 Hvězd
support-stars-fifty = ⭐ 50 Hvězd
support-stars-hundred = ⭐ 100 Hvězd
support-stars-custom = ✏️ Vlastní částka

support-custom-prompt = Napiš, kolik Hvězd chceš poslat (od 1 do 100 000):

support-success-sponsor =
    Moc ti děkuji za { $stars } ⭐!
    Sponzorství aktivováno na { $days } dní (do { $date })! Tvé jméno bylo přidáno na zeď díků ⭐

support-success-tip =
    Moc ti děkuji za { $stars } ⭐!
    Tvá podpora je úžasná! V pokladničce je { $progress }/100 ⭐ do sponzorství ⭐

# Report command
report-reply-required = Odpověz příkazem <code>/report</code> na mou zprávu, se kterou je něco špatně.
report-not-bot-message = Tento příkaz funguje jen jako odpověď na moje zprávy 🐾
report-success = Děkuju za nahlášení! Všechno jsem předala vývojáři, brzy to vyřešíme 🧡
error-send-failed = ❌ Odeslání médií do Telegramu se nezdařilo. Soubor může být poškozen nebo odmítnut.
yt-trim-invalid-format = Tento formát se nepodařilo rozpoznat. Použij ZAČÁTEK-KONEC, např. <code>1:30-2:45</code>. Zkusit znovu?
