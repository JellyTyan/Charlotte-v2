msg-hello =
    ¡Hola! 👋
    Me alegra verte, { $name }.
    Escribe _/help_ si tienes dudas sobre algo.
    Date una vuelta por @charlottesbasement — ahí comparto novedades y detallitos.

msg-help =
    Esto es todo lo que sé hacer:
      /start — Menú principal
      /help — Ayuda e información
      /settings — Ajustes
      /saves — Mi biblioteca
      /copy — Copiar multimedia al portapapeles
      /support — Apoyar el proyecto
      /cancel — Cancelar descarga

    <b>Plataformas compatibles</b> <i>(toca para desplegar)</i>:
    <blockquote expandable>
    <b>Música:</b>
      • Spotify
      • Apple Music
      • Deezer
      • SoundCloud
      • YouTube Music
    <i>Encontraré la pista, la portada y todas las etiquetas.</i>

    <b>Vídeo:</b>
      • YouTube (vídeos, shorts, audio de hasta 100 MB, ⭐ 1 GB para Patrocinadores)
      • TikTok (vídeos y fotos)
      • Instagram (reels y publicaciones)
      • Twitter / X (vídeos e imágenes)
      • Reddit (todo el contenido multimedia de las publicaciones)
      • BlueSky, Twitch, NicoVideo

    <b>Arte:</b>
      • Pixiv
      • Pinterest
    </blockquote>

    🔍 <b>Modo inline (funciona en cualquier chat):</b>
      • <code>@{ $bot_username } &lt;texto&gt;</code> — busca imágenes y memes (o solo <code>@{ $bot_username } </code> para recientes)
      • <code>@{ $bot_username } #music &lt;canción&gt;</code> — busca música
      • <code>@{ $bot_username } #saved &lt;texto&gt;</code> — busca en tus guardados
      • <code>@{ $bot_username } paste</code> — pega multimedia copiada (el portapapeles dura 1 hora)
    <i>Para guardar contenido que te envié en tu biblioteca, respóndele con <code>/save &lt;nombre&gt;</code>.</i>

    Solo mándame un enlace y me encargo de todo.

processing = Un segundo, ya me pongo a ello... ⏳
added-to-queue = Te añadí a la cola, tienes a { $count } por delante.
starting-download = ¡Empiezo a descargar! 🚀
invalid-callback = Vaya, este botón ya no funciona, lo siento.
url-expired = Ese enlace ya caducó — ¿me mandas uno nuevo?
setting-changed = ¡Listo! *{ $setting }* ahora está { $status }.
premium-granted = ¡Genial, te dieron acceso premium gratis! Descarga cuanto quieras 🎉


# System & Payment
sponsor-alert = 30 días de Premium por 100 Estrellas 🌟
sponsor-invoice-title = Premium de Patrocinador (30 días)
sponsor-invoice-desc = 30 días de acceso premium: sin anuncios y con funciones extra.
sponsor-success = ¡Gracias por tu apoyo! Te doy 30 días de Premium de Patrocinador 🌟
support-invoice-title = Donar { $amount } ⭐
support-invoice-desc = ¡Apoya el desarrollo de Charlotte!
support-success = Muchísimas gracias por tu apoyo 🧡
support-invalid-amount = La cantidad debe ser entre 1 y 100 000 Estrellas. Prueba otra vez:
support-invalid-number = Introduce un número entre 1 y 100 000, por favor:
payment-invalid-data = Error: datos de pago no válidos.
payment-invalid-format = Error: formato de datos incorrecto.
payment-link-expired = Error: el enlace caducó. Inténtalo de nuevo.
payment-success-download = ¡Gracias por tu apoyo! Empiezo a descargar...
payment-error-refund = Algo salió mal al procesar. Te reembolsé las Estrellas...
premium-expired = Tu Premium de Patrocinador terminó. Puedes renovarlo cuando quieras 🌟
bot-ad-disable-alert = Desactivar los anuncios del bot requiere Patrocinio activo (100 Estrellas).
download-failed-refund = No pude descargarlo, lo siento. Te devolví las Estrellas.
not-your-request = Esta solicitud no es tuya.
action-cancelled = Cancelado.
banned-global = Tienes un bloqueo global.
banned-chat = Tienes un bloqueo en este chat.
too-many-requests = Demasiadas peticiones seguidas, espera un poquito.
menu-not-yours = Este menú no es para ti, lo siento.
general-error = Vaya, algo salió mal. ¿Lo intentas más tarde?
btn-close = ✕ Cerrar

# YouTube Trim
yt-trim-sponsor-only = El recorte de vídeo solo está disponible para Patrocinadores.
yt-trim-ask-range = Envía el rango de tiempo a recortar, por ejemplo <code>01:20-02:45</code> o <code>90-165</code>:
yt-trim-invalid-range = No entendí ese formato, perdona. Usa INICIO-FIN, por ejemplo <code>1:30-2:45</code>. ¿Otra vez?
yt-trim-end-before-start = El final debe ser posterior al inicio. ¿Lo intentas de nuevo?
yt-trim-processing = Recortando el clip, espera un momentito...
yt-trim-out-of-bounds = Ese rango se pasa de la duración del vídeo ({ $duration }). ¿Pruebas otra vez?
yt-btn-full = 🎬 Vídeo completo
yt-btn-trim-locked = ★ Recorte
yt-btn-cancel = Cancelar
yt-ask-quality = Elige la calidad:
yt-btn-video = Descargar vídeo
yt-btn-audio = Descargar audio
yt-btn-continue = Siguiente
yt-btn-advanced = Ajustes avanzados
yt-btn-trim = Recorte
yt-btn-trim-active = ✓ Recorte
yt-btn-back = Atrás
yt-label-channel = Canal: { $uploader }
yt-label-duration = Duración: { $duration }

btn-add-group = ➕ Añadir al grupo
btn-my-settings = ⚙️ Mis ajustes
already-downloading = Ya estoy descargando algo para ti, espera un momento 🐾


# Errors
error-invalid-url = Vaya, hay algo raro con este enlace 🥺
error-private-content = Lo siento, esto es privado — no puedo llegar hasta ahí.
error-large-file = Qué archivo tan grande... Aún no sé enviar cosas tan pesadas, lo siento 😔
error-not-allowed = Lo siento, esta función está desactivada en los ajustes de este chat.
error-internal = Vaya, algo se rompió por dentro... ¿Podrías probar un poco más tarde?
error-not-found = Busqué por todos lados pero no encontré nada en este enlace. ¿Seguro que no se borró?
error-region-restricted = Lo siento, este contenido está bloqueado en mi región — no puedo acceder a él.
error-age-restricted = Esto es contenido para mayores de 18 y no tengo acceso, perdón 🙈
error-download-canceled = De acuerdo, detuve la descarga.
error-generic = Vaya, algo salió mal, perdona.
error-preview-only = Solo pude descargar una vista previa de 30 segundos, no la canción entera, lo siento.

download-cancel = ¡Cancelando! Ya lo detuve.
download-no-found = Mmm, aquí no hay nada que cancelar.
downloading-tracks = Recopilando pistas...
download-stats = Listo: { $success } descargadas, fallaron { $failed }.
all-tracks-success = ¡Se descargaron todas las pistas, qué bien! 🎉
total-tracks = Pistas en total: { $count }
release-date = Lanzamiento: { $date }
year = Año: { $year }
playlist-stopped = Descarga de lista de reproducción detenida.
skipped-track = Pista omitida: { $title }
yt-btn-topich = TOPICH
yt-sponsor-only = Esta función es solo para Patrocinadores, ¡lo siento!

# Sponsor & Support
sponsor-text =
    Si quieres apoyarme a mí y a este proyecto, puedes patrocinar durante 30 días.

    Lo que obtienes:
      • Descarga de vídeos grandes de YouTube (hasta 1 GB en vez de 100 MB)
      • Recorte de vídeos de YouTube antes de enviarlos
      • Acceso a multimedia NSFW (Twitter y Reddit)
      • Tu nombre en el muro de agradecimientos en /support

    El patrocinio cuesta 100 Estrellas por 30 días ⭐

sponsor-btn-buy = ⭐ Hacerse Patrocinador (100 Estrellas)

support-text =
    Charlotte es un proyecto hecho con mucho cariño y dedicación. Te ayudo a guardar y descargar multimedia sin anuncios ni limitaciones.

    Los servidores cuestan unos 12€ al mes y se pagan de mi propio bolsillo. El bot siempre será gratuito y abierto para todos.

    <b>Patrocinio:</b>
    Por cada 100 Estrellas recibes <b>30 días de ventajas de patrocinio</b>:
    • Descarga de vídeos grandes de YouTube (hasta 1 GB en vez de 100 MB)
    • Recorte de vídeos de YouTube antes de enviarlos
    • Acceso a multimedia NSFW (Twitter, Reddit, Pixiv)
    • Tu nombre en el muro de agradecimientos{ $status }

    Cualquier apoyo significa muchísimo para mí, gracias por estar aquí ⭐

support-status-lifetime =
    ⭐ <b>Tu estado:</b> Patrocinador (de por vida) 🌟

support-status-active =
    ⭐ <b>Tu estado:</b> Patrocinador (hasta { $date })
    En la hucha: { $progress }/100 ⭐ para la próxima renovación

support-status-progress =
    ⭐ En la hucha: { $progress }/100 ⭐ para el patrocinio

support-btn-sponsor = ⭐ Patrocinio de 30 días (100 ⭐)
support-btn-coffee = ☕ Invitar a un café
support-btn-stars = ⭐ Enviar Estrellas
support-btn-supporters = 🤍 Muro de agradecimientos
support-btn-back = 🔙 Atrás

support-wall-empty =
    <b>Muro de agradecimientos</b>

    Aún no hay nadie por aquí. Pero puedes ser la primera persona en apoyarme y salir en esta lista ⭐

support-wall-text =
    <b>Muro de agradecimientos</b>

    Muchísimas gracias a todos los que me ayudan a seguir funcionando y mejorando:

    { $supporters }

    Vuestro apoyo significa muchísimo ⭐

support-choose-stars = Elige cuántas Estrellas quieres enviar para apoyar:
support-stars-ten = ⭐ 10 Estrellas
support-stars-fifty = ⭐ 50 Estrellas
support-stars-hundred = ⭐ 100 Estrellas
support-stars-custom = ✏️ Otra cantidad

support-custom-prompt = Escribe cuántas Estrellas quieres enviar (de 1 a 100 000):

support-success-sponsor =
    ¡Muchísimas gracias por las { $stars } ⭐!
    ¡Patrocinio activado por { $days } días (hasta { $date })! Se añadió tu nombre al muro de agradecimientos ⭐

support-success-tip =
    ¡Muchísimas gracias por las { $stars } ⭐!
    ¡Tu apoyo vale un montón! En la hucha: { $progress }/100 ⭐ para el patrocinio ⭐

# Report command
report-reply-required = Responde con <code>/report</code> al mensaje mío con el que hubo algún problema.
report-not-bot-message = Este comando solo funciona respondiendo a mis mensajes 🐾
report-success = ¡Gracias por avisarme! Le pasé todo al desarrollador y lo revisaremos pronto 🧡
error-send-failed = ❌ No se pudo enviar el archivo a Telegram. El archivo podría estar dañado o rechazado.
yt-trim-invalid-format = No reconocí ese formato. Usa INICIO-FIN, como <code>1:30-2:45</code>. ¿Quieres intentarlo de nuevo?
