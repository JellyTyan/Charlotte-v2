settings-welcome = ¡Hola! 👋 Aquí puedes personalizar todo a tu gusto. ¡Siéntete como en casa!
settings-back = 🔙 Atrás
settings-title = Ajustes
settings-no-permission = ¡Aww, no tienes permiso para cambiar estos ajustes!
settings-saved = ¡Genial! ¡Ajustes actualizados! ✨
settings-no-allowed-groups = ¡Este ajuste no está disponible para grupos, lo siento!
settings-no-allowed-dm = ¡Este ajuste no es para chats privados, lo siento!

btn-language = Idioma
btn-title-language = Idioma de títulos
btn-blocked-services = Servicios bloqueados

btn-send-raw = { $is_enabled ->
    [true] ✅ Arte como archivo (Mejor calidad)
    *[false] ❌ Arte como archivo (Mejor calidad)
}
btn-send-music-covers = { $is_enabled ->
    [true] ✅ Portadas de música
    *[false] ❌ Portadas de música
}
btn-send-reactions = { $is_enabled ->
    [true] ✅ Reacciones divertidas
    *[false] ❌ Reacciones divertidas
}
btn-auto-translate = { $is_enabled ->
    [true] ✅ Traducir títulos
    *[false] ❌ Traducir títulos
}
btn-auto-caption = { $is_enabled ->
    [true] ✅ Auto-descripciones
    *[false] ❌ Auto-descripciones
}
btn-notifications = { $is_enabled ->
    [true] ✅ Notificaciones
    *[false] ❌ Notificaciones
}
btn-allow-playlists = { $is_enabled ->
    [true] ✅ Permitir playlists
    *[false] ❌ Permitir playlists
}

desc-send-raw = ¡Enviaré el arte como archivos sin comprimir para una calidad estelar! 🎨
desc-send-music-covers = Adjuntaré la portada del álbum a cada canción. 🎵
desc-send-reactions = ¡Reaccionaré con emojis para que veas mi progreso! ⚡
desc-send-notifications = Desactiva para recibir medios sin sonido de notificación. 🔕
desc-auto-caption = Verificaré y añadiré descripciones automáticamente. 📝
desc-auto-translate-titles = ¡Traduciré los títulos de video a tu idioma! 🌍
desc-allow-playlists = Descargaré playlists completas (¡cuidado con esto!). 📂
desc-lossless-mode = ¡Intentaré buscar canciones en Hi-Res para ti! Pero no prometo encontrarlas ni que sean las correctas. 🎧

setting-status-changed = { $is_enabled ->
    [true] ¡Yay! ¡El ajuste *{ $setting_name }* está activado!
    *[false] ¡Entendido! ¡El ajuste *{ $setting_name }* está desactivado!
}

pick-language = ¡Elige tu idioma! 🌍
pick-title-language = ¡Elige el idioma para títulos!
language-changed = ¡Genial! ¡Ahora hablo en *{ $language }*!
language-updated = ¡Idioma actualizado!
title-language-changed = ¡Los títulos estarán en *{ $language }* ahora!
title-language-updated = ¡Idioma de títulos actualizado!
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
