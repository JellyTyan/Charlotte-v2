settings-welcome = ¡Hola! Aquí puedes personalizar todo a tu gusto, estás en tu casa.
settings-back = 🔙 Atrás
settings-title = Ajustes
settings-no-permission = Vaya, no tienes permiso para cambiar estos ajustes.
settings-saved = ¡Ajustes actualizados! ✨
settings-no-allowed-groups = Este ajuste no está disponible en grupos, lo siento.
settings-no-allowed-dm = Este ajuste no se puede cambiar por mensaje privado.

btn-language = Idioma
btn-title-language = Descripciones
btn-blocked-services = Servicios bloqueados

btn-send-raw = { $is_enabled ->
    [true] 🟢 Como archivo
    *[false] ⚪ Como archivo
}
btn-send-music-covers = { $is_enabled ->
    [true] 🟢 Portadas
    *[false] ⚪ Portadas
}
btn-send-reactions = { $is_enabled ->
    [true] 🟢 Reacciones
    *[false] ⚪ Reacciones
}
btn-negativity = { $is_enabled ->
    [true] 🟢 Modo pícaro
    *[false] ⚪ Modo pícaro
}
btn-auto-translate = { $is_enabled ->
    [true] 🟢 Traducción
    *[false] ⚪ Traducción
}
btn-auto-caption = { $is_enabled ->
    [true] 🟢 Descripciones
    *[false] ⚪ Descripciones
}
btn-notifications = { $is_enabled ->
    [true] 🟢 Notificaciones
    *[false] ⚪ Notificaciones
}
btn-allow-playlists = { $is_enabled ->
    [true] 🟢 Listas
    *[false] ⚪ Listas
}
btn-allow-nsfw = { $is_enabled ->
    [true] 🟢 NSFW
    *[false] ⚪ NSFW
}

desc-send-raw = Enviaré el contenido como archivo para mantener la máxima calidad.
desc-send-music-covers = Adjuntaré la portada del álbum a cada pista.
desc-send-reactions = Pondré reacciones con emojis para que veas el progreso.
desc-negativity-mode = Usaré emojis un poquito más atrevidos en las reacciones.
desc-send-notifications = Desactívalo si quieres recibir el contenido sin sonido.
desc-auto-caption = Comprobaré y añadiré descripción al contenido automáticamente.
desc-auto-translate-titles = Traduciré las descripciones de los vídeos a tu idioma.
desc-allow-playlists = Descargar listas de reproducción enteras — con cuidado.
desc-allow-nsfw = Permitir contenido NSFW en este chat.
desc-lossless-mode = Intentaré buscar una versión Hi-Res de la canción. No prometo que funcione.

setting-status-changed = { $is_enabled ->
    [true] ¡Activé *{ $setting_name }*!
    *[false] Desactivé *{ $setting_name }*.
}

pick-language = Elige idioma 🌍
pick-title-language = Elige idioma de descripciones
language-changed = ¡Ahora hablo en *{ $language }*!
language-updated = Idioma actualizado.
title-language-changed = Ahora las descripciones estarán en *{ $language }*.
title-language-updated = Idioma de descripciones actualizado.
setting-updated = Listo, actualizado.
invalid-setting = Mmm, no conozco ese ajuste.
error-updating = No pude actualizarlo, perdón. ¿Lo intentamos otra vez?
enabled = activado
disabled = desactivado
enable = Activar
disable = Desactivar
back = Atrás
service-status-changed = El servicio { $service } ahora está { $status }.
blocked = bloqueado
unblocked = desbloqueado
settings-not-found = No encuentro estos ajustes.
no-permission-service = No tienes permiso para cambiar estos ajustes.
error-service-status = No se pudo actualizar el estado del servicio, perdón.
current-status = Estado actual: { $status }

btn-configure-services = ⚙️ Configurar servicios
settings-select-service = Elige un servicio para configurar:
settings-service-title = **Ajustes de { $name }**
btn-lossless = { $is_enabled ->
    [true] 🟢 LOSSLESS
    *[false] ⚪ LOSSLESS
}
btn-service-enabled = { $is_enabled ->
    [true] 🟢 Servicio
    *[false] ⚪ Servicio
}

btn-news-spam = { $is_enabled ->
    [true] 🟢 Difusión
    *[false] ⚪ Difusión
}
desc-news-spam = Permitir que te envíe noticias y novedades.

btn-bot-sign = { $is_enabled ->
    [true] 🟢 Bot Ad 🧡
    *[false] ⚪ Bot Ad 🧡
}
desc-bot-sign = Añadir la firma «Charlotte 🧡» a los archivos. Desactivarlo es totalmente gratis.

btn-simple-mode = { $is_enabled ->
    [true] 🟢 Modo simple
    *[false] ⚪ Modo simple
}
desc-simple =
    Interfaz sencilla de YouTube:
    Activado — solo dos botones (Vídeo o Audio), descarga en máxima calidad hasta 100 MB (hasta 1 GB para Patrocinadores).
    Desactivado — selector de resolución, recorte de vídeo (para Patrocinadores).

btn-youtube-ui-mode = Interfaz de YouTube
yt-ui-mode-simple = Simple
yt-ui-mode-balance = Equilibrada
yt-ui-mode-advanced = Avanzada
desc-youtube-ui-mode =
    Elige el estilo de interfaz para descargar de YouTube:

    • Simple — 2 botones (Vídeo / Audio), descarga en un toque.
    • Equilibrada — botones de mejores calidades en un toque + acceso a ajustes avanzados.
    • Avanzada — elige cualquier calidad, pista de audio y recorte de vídeo (Trim).

btn-experimental = 🧪 Nuevas funciones
desc-experimental-features =
    Las funciones experimentales solo funcionan en aplicaciones oficiales recientes de Telegram y pueden comportarse de forma inestable en clientes antiguos o de terceros.

btn-ephemeral-messages = { $is_enabled ->
    [true] 🟢 Mensajes efímeros
    *[false] ⚪ Mensajes efímeros
}
desc-ephemeral-messages = Enviar avisos de servicio en grupos como mensajes efímeros visibles solo para ti. Si está desactivado — envío mensajes normales con borrado automático.
btn-chat-banned-users = 🚫 Lista de bloqueados
desc-chat-banned-users = Administrar usuarios bloqueados en este chat.
cban-usage = Especifica el ID de usuario o responde a su mensaje: <code>/cban &lt;user_id&gt;</code>
cban-cannot-ban-self = No puedes bloquearte a ti mismo.
cban-cannot-ban-admin = No puedes bloquear a los administradores del chat.
cban-cannot-ban-bot = No puedes bloquear al bot.
cban-success = El usuario <code>{ $user_id }</code> ha sido bloqueado en este chat.
cban-already-banned = El usuario <code>{ $user_id }</code> ya está bloqueado en este chat.
cunban-usage = Especifica el ID de usuario o responde a su mensaje: <code>/cunban &lt;user_id&gt;</code>
cunban-not-banned = El usuario <code>{ $user_id }</code> no está bloqueado en este chat.
cunban-success = El usuario <code>{ $user_id }</code> ha sido desbloqueado en este chat.
cbanlist-empty = No hay usuarios bloqueados en este chat.
cbanlist-title = <b>Lista de bloqueados del chat:</b>
btn-unban-user = ❌ Desbloquear { $user_id }
