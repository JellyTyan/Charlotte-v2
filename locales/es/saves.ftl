saves-usage = Para guardar en la biblioteca:
    Responde a un mensaje con vídeo, foto, GIF o música con <code>/save &lt;nombre&gt;</code>

saves-no-name = Ponle un nombre al guardado, por ejemplo <code>/save gatitos</code>.

saves-name-too-long = El nombre es demasiado largo, máximo 128 caracteres.

saves-no-media = No encontré multimedia compatible en ese mensaje (vídeo, foto, audio o GIF).

saves-bot-only = Solo puedes guardar cosas descargadas a través de mí. Responde con <code>/save &lt;nombre&gt;</code> a mi mensaje.

saves-limit-reached = Llegaste al límite de guardados (<b>{ $current }/{ $limit }</b>). ¿Borras algo con /saves?

saves-saved = { $emoji } ¡Guardado como «<b>{ $label }</b>»!

    { $status }

    Puedes enviarlo en cualquier chat:
    <code>@{ $bot_username } { $label }</code>

    Todos tus guardados: /saves

saves-status-private = 🔒 <i>Privado, solo lo ves tú</i>
saves-status-public = 🌐 <i>Público, visible para todos en la búsqueda</i>
saves-status-pending = ⏳ <i>Enviado a revisión para la biblioteca pública</i>

saves-btn-make-public = 🌐 Hacer público
saves-btn-make-private = 🔒 Hacer privado
saves-toast-public = ¡El meme ya es público en la búsqueda!
saves-toast-pending = Enviado a revisión. En cuanto se apruebe, saldrá en la búsqueda pública.
saves-toast-private = Guardadito, ahora solo lo ves tú.

saves-empty = Tu biblioteca está vacía por ahora.

    Para añadir cosas, responde a un vídeo, foto o música descargada con <code>/save &lt;nombre&gt;</code>

saves-header = <b>Tu biblioteca</b> ({ $count }):

saves-deleted-toast = Eliminado de tus guardados.
saves-missing-toast = No encontré ese elemento, ¿quizá ya se borró?

saves-mod-approved =
    <b>¡Aprobaron tu archivo guardado!</b> 🎉

    El meme «<b>{ $label }</b>» superó la moderación y ya lo puede encontrar todo el mundo en la búsqueda pública.

saves-mod-rejected =
    <b>Solicitud de publicación rechazada</b>

    El meme «<b>{ $label }</b>» no superó la moderación, pero sigue a salvo en tus guardados privados 🔒

copy-usage = Para copiar multimedia al portapapeles:
    Responde a un mensaje con vídeo, foto, GIF o música con <code>/copy</code>

copy-bot-only = Solo se puede copiar contenido enviado por mí. Responde con <code>/copy</code> a mi mensaje.

copy-no-media = No encontré multimedia compatible en ese mensaje (vídeo, foto, audio o GIF).

copy-copied = <b>¡Copiado al portapapeles!</b>

    Para pegarlo en cualquier chat, escribe:
    <code>@{ $bot_username } paste</code>

    <i>El portapapeles dura 1 hora</i>

saves-banned-alert = Se ha restringido tu acceso para sugerir memes a la biblioteca pública.
saves-mod-banned =
    <b>Acceso restringido</b>

    Un administrador te restringió proponer memes a la biblioteca pública. Tus guardados privados siguen contigo 🔒

saves-label-reserved = El nombre «<b>{ $label }</b>» está reservado por el bot para comandos del sistema. ¡Por favor elige otro!
saves-label-trash = El nombre no es válido o solo contiene símbolos. Por favor indica un nombre claro.
saves-dupe-media = Este archivo ya está guardado en tu biblioteca como «<b>{ $existing_label }</b>».
saves-dupe-public = ¡Este archivo ya está publicado en la biblioteca pública de memes!
saves-rename-remoderation = Nombre modificado — enviado a moderación antes de mostrarse en la búsqueda pública.

saves-list-hint = Elige un guardado para verlo y gestionarlo:
saves-card =
    { $emoji } <b>{ $label }</b>

    { $status }
    👁 Usos: <b>{ $uses }</b>
    📅 Añadido: <b>{ $date }</b>

    <i>Envíalo en cualquier chat:</i>
    <code>@{ $bot_username } { $label }</code>
saves-btn-preview = 👁 Ver
saves-btn-send = 🚀 Al chat
saves-btn-rename = ✏️ Renombrar
saves-btn-delete = 🗑 Eliminar
saves-btn-back = ◀️ A la lista
saves-btn-close = ❌ Cerrar
saves-btn-cancel = ◀️ Cancelar
saves-foreign-library = ❌ Esta no es tu biblioteca
saves-preview-failed = No se pudo enviar la vista previa.
saves-rename-prompt =
    ✏️ <b>Renombrar</b> «{ $label }»

    Envía el nuevo nombre en un mensaje (hasta { $max } caracteres):
saves-renamed = ✅ Nombre actualizado: «<b>{ $label }</b>»
saves-label-word-too-long = Una de las palabras del nombre es demasiado larga. Usa un nombre más corto.
