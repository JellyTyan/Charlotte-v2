settings-welcome = ¡Hola! 👋 Aquí puedes personalizar todo a tu gusto. ¡Siéntete como en casa!
settings-back = 🔙 Atrás
settings-title = Ajustes
settings-no-permission = ¡Aww, no tienes permiso para cambiar estos ajustes!
settings-saved = ¡Genial! ¡Ajustes actualizados! ✨
settings-no-allowed-groups = ¡Este ajuste no está disponible para grupos, lo siento!
settings-no-allowed-dm = ¡Este ajuste no es para chats privados, lo siento!

btn-language = Idioma
btn-title-language = Idioma de descripciones
btn-blocked-services = Servicios bloqueados

btn-send-raw = { $is_enabled ->
    [true] ✅ Enviar como archivo
    *[false] ❌ Enviar como archivo
}
btn-send-music-covers = { $is_enabled ->
    [true] ✅ Portadas de música
    *[false] ❌ Portadas de música
}
btn-send-reactions = { $is_enabled ->
    [true] ✅ Reacciones
    *[false] ❌ Reacciones
}
btn-negativity = { $is_enabled ->
    [true] ✅ Negatividad
    *[false] ❌ Negatividad
}
btn-auto-translate = { $is_enabled ->
    [true] ✅ Traducir descripciones
    *[false] ❌ Traducir descripciones
}
btn-auto-caption = { $is_enabled ->
    [true] ✅ Descripciones
    *[false] ❌ Descripciones
}
btn-notifications = { $is_enabled ->
    [true] ✅ Notificaciones
    *[false] ❌ Notificaciones
}
btn-allow-playlists = { $is_enabled ->
    [true] ✅ Playlists
    *[false] ❌ Playlists
}
btn-allow-nsfw = { $is_enabled ->
    [true] ✅ NSFW
    *[false] ❌ NSFW
}

desc-send-raw = ¡Enviaré los medios como archivos para obtener la mejor calidad! 🎨
desc-send-music-covers = Adjuntaré la portada del álbum a cada canción. 🎵
desc-send-reactions = ¡Reaccionaré con emojis para que veas mi progreso! ⚡
desc-negativity-mode = ¡Usaré algunos emojis tóxicos al reaccionar! 😈
desc-send-notifications = Desactiva para recibir medios sin sonido de notificación. 🔕
desc-auto-caption = Verificaré y añadiré descripciones automáticamente. 📝
desc-auto-translate-titles = ¡Traduciré las descripciones de video a tu idioma! 🌍
desc-allow-playlists = Descargaré playlists completas (¡cuidado con esto!). 📂
desc-allow-nsfw = Permitir contenido NSFW en este chat. 🔞
desc-lossless-mode = ¡Intentaré buscar canciones en Hi-Res para ti! Pero no prometo encontrarlas ni que sean las correctas. 🎧

setting-status-changed = { $is_enabled ->
    [true] ¡Yay! ¡El ajuste *{ $setting_name }* está activado!
    *[false] ¡Entendido! ¡El ajuste *{ $setting_name }* está desactivado!
}

pick-language = ¡Elige tu idioma! 🌍
pick-title-language = ¡Elige el idioma para descripciones!
language-changed = ¡Genial! ¡Ahora hablo en *{ $language }*!
language-updated = ¡Idioma actualizado!
title-language-changed = ¡Las descripciones estarán en *{ $language }* ahora!
title-language-updated = ¡Idioma de descripciones actualizado!
setting-updated = ¡Listo! Actualizado.
invalid-setting = ¡Ups, ese ajuste se ve raro!
error-updating = Oh no, no pude actualizar eso. ¿Probamos otra vez?
setting-changed = ¡Hecho! *{ $setting }* está ahora { $status }!
enabled = activado
disabled = desactivado
enable = Activar
disable = Desactivar
back = Atrás
service-status-changed = ¡El servicio { $service } está ahora { $status }!
blocked = bloqueado
unblocked = desbloqueado
settings-not-found = ¡Hmm, no encuentro esos ajustes!
no-permission-service = ¡No puedes tocar estos ajustes!
error-service-status = No pude actualizar el estado del servicio. :(
current-status = Estado actual: { $status }

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
    [true] ✅ Boletines
    *[false] ❌ Boletines
}
desc-news-spam = ¡Permite que el bot te envíe noticias y actualizaciones! 📰

btn-bot-sign = { $is_enabled ->
    [true] 🧡 Bot Ad [ON]
   *[false] 🧡 Bot Ad [OFF]
}
desc-bot-sign = Append a promotional signature "Charlotte 🧡" to downloaded media. Disabling this requires Sponsorship 🌟.
