import logging
from pathlib import Path
from typing import List

from aiogram.types import InaccessibleMessage, MaybeInaccessibleMessage, Message, FSInputFile
from aiogram.enums import ParseMode

from models.metadata_models import MediaMetadata
from models.media_models import MediaContent, MediaType

logger = logging.getLogger(__name__)


class SendManager:
    """Handles sending media files to users"""

    async def send_media(self, media_content: List[MediaContent], message: Message | MaybeInaccessibleMessage):
        """Send media content to user"""

        if not isinstance(message, Message) or not isinstance(message, InaccessibleMessage):
            return

        try:
            for content in media_content:
                if content.type == MediaType.AUDIO:
                    await self.send_audio(content, message)
                elif content.type == MediaType.VIDEO:
                    await self.send_video(content, message)
                elif content.type == MediaType.PHOTO:
                    await self.send_photo(content, message)
                else:
                    await self.send_document(content, message)

        except Exception as e:
            logger.error(f"Failed to send media: {e}")
            await message.edit_text(f"Failed to send media: {str(e)}")

    async def send_audio(self, content: MediaContent, message: Message | InaccessibleMessage):
        """Send audio file"""
        audio_file = FSInputFile(content.path, filename=f"{content.title}.mp3")

        thumbnail = None
        if content.cover and content.cover.exists():
            thumbnail = FSInputFile(content.cover)

        await message.answer_audio(
            audio=audio_file,
            title=content.title,
            performer=content.performer,
            duration=content.duration,
            thumbnail=thumbnail
        )

    async def send_video(self, content: MediaContent, message: Message | InaccessibleMessage):
        """Send video file"""
        video_file = FSInputFile(content.path, filename=f"{content.title}.mp4")

        await message.answer_video(
            video=video_file,
            caption=content.title,
            duration=content.duration,
            width=content.width,
            height=content.height
        )

    async def send_photo(self, content: MediaContent, message: Message | InaccessibleMessage):
        """Send photo file"""
        photo_file = FSInputFile(content.path)

        await message.answer_photo(
            photo=photo_file,
            caption=content.title
        )

    async def send_document(self, content: MediaContent, message: Message | InaccessibleMessage):
        """Send as document"""
        doc_file = FSInputFile(content.path, filename=content.title)

        await message.answer_document(
            document=doc_file,
            caption=content.title
        )

    async def process_and_send(self, metadata: MediaMetadata, message: Message | InaccessibleMessage):
        pass
