import logging
import random
import time
from contextvars import ContextVar

from aiogram.types import Message
from fluentogram import TranslatorRunner
from fluentogram.exceptions import KeyNotFoundError

logger = logging.getLogger(__name__)

# set by ServiceBlockMiddleware so media downloads can report progress without touching each handler
current_context: ContextVar[tuple[Message, TranslatorRunner] | None] = ContextVar("progress_ctx", default=None)

# stages worth telling the user about (after a short quiet period)
_SHOWN_STAGES = {"queued", "downloading", "retrying", "processing"}
_QUIET_SECONDS = 6.0  # fast downloads finish before a status would be useful
_MIN_EDIT_INTERVAL = 3.0


def _pick(i18n: TranslatorRunner, base: str) -> str | None:
    """Random variant of `<base>-1..3`; missing keys raise or come back as the key itself."""
    texts = []
    for n in (1, 2, 3):
        try:
            t = i18n.get(f"{base}-{n}")
        except KeyNotFoundError:
            continue
        if not t.startswith("status-"):
            texts.append(t)
    return random.choice(texts) if texts else None


class StatusMessage:
    """One reply that follows media-core's task stage (stage/attempt/reason from GET /status) and vanishes at the end."""

    def __init__(self, message: Message, i18n: TranslatorRunner):
        self._message = message
        self._i18n = i18n
        self._sent: Message | None = None
        self._last_key: tuple | None = None
        self._last_edit = 0.0
        self._started = time.monotonic()

    @classmethod
    def from_context(cls) -> "StatusMessage | None":
        ctx = current_context.get()
        return cls(*ctx) if ctx else None

    def _text(self, stage: str, reason: str | None) -> str | None:
        base = f"status-{stage}"
        if reason:
            if text := _pick(self._i18n, f"{base}-{reason.replace('_', '-')}"):
                return text
        return _pick(self._i18n, base)

    async def update(self, stage: str | None, attempt: int | None, reason: str | None) -> None:
        key = (stage, attempt, reason)
        if stage not in _SHOWN_STAGES or key == self._last_key:
            return
        if not self._sent and time.monotonic() - self._started < _QUIET_SECONDS:
            return
        if self._sent and time.monotonic() - self._last_edit < _MIN_EDIT_INTERVAL:
            return
        text = self._text(stage, reason)
        if not text:
            return
        self._last_key = key
        self._last_edit = time.monotonic()
        try:
            if self._sent:
                await self._sent.edit_text(text)
            else:
                self._sent = await self._message.reply(text)
        except Exception:
            logger.debug("status message update failed", exc_info=True)

    async def close(self) -> None:
        if self._sent:
            try:
                await self._sent.delete()
            except Exception:
                logger.debug("status message delete failed", exc_info=True)
            self._sent = None
