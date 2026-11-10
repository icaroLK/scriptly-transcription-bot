import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

load_dotenv()

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
GROQ_API_KEY = os.environ["GROQ_API_KEY"]
GROQ_MODEL = os.environ.get("GROQ_MODEL", "whisper-large-v3-turbo")


def find_ffmpeg() -> str:
    env_path = os.environ.get("FFMPEG_PATH")
    if env_path and Path(env_path).exists():
        return env_path

    on_path = shutil.which("ffmpeg")
    if on_path:
        return on_path

    winget_packages = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages"
    if winget_packages.exists():
        matches = list(winget_packages.glob("Gyan.FFmpeg_*/**/bin/ffmpeg.exe"))
        if matches:
            return str(matches[0])

    raise RuntimeError(
        "ffmpeg not found. Install it (winget install ffmpeg) or set FFMPEG_PATH in .env"
    )


FFMPEG_BIN = find_ffmpeg()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
logger = logging.getLogger("transcribe-bot")

groq_client = Groq(api_key=GROQ_API_KEY)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "👋 Hey, I'm your transcription bot.\n\n"
        "What I can transcribe:\n"
        "🎤 Voice notes\n"
        "🎵 Audio files: mp3, wav, m4a...\n"
        "💬 WhatsApp voice notes (.ogg/.opus)\n"
        "📹 Video notes\n\n"
        "Drop one in and I'll send the text back in a few seconds."
    )


def convert_to_mp3(input_path: Path, output_path: Path) -> None:
    result = subprocess.run(
        [FFMPEG_BIN, "-y", "-i", str(input_path), "-ar", "16000", "-ac", "1", str(output_path)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr[-2000:])


def transcribe(audio_path: Path) -> str:
    with open(audio_path, "rb") as f:
        transcription = groq_client.audio.transcriptions.create(
            file=(audio_path.name, f.read()),
            model=GROQ_MODEL,
        )
    return transcription.text.strip()


async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    audio_obj = (
        message.voice or message.audio or message.video_note or message.video or message.document
    )
    if audio_obj is None:
        return

    await context.bot.send_chat_action(chat_id=message.chat_id, action="typing")
    status_msg = await message.reply_text("Transcribing...")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_dir = Path(tmpdir)
        tg_file = await context.bot.get_file(audio_obj.file_id)
        raw_path = tmp_dir / "input"
        await tg_file.download_to_drive(custom_path=raw_path)

        mp3_path = tmp_dir / "audio.mp3"
        try:
            convert_to_mp3(raw_path, mp3_path)
        except RuntimeError:
            logger.exception("ffmpeg conversion failed")
            await status_msg.edit_text(
                "Couldn't process that file - make sure it's an audio or video file."
            )
            return

        try:
            text = transcribe(mp3_path)
        except Exception:
            logger.exception("transcription failed")
            await status_msg.edit_text("Transcription failed, sorry. Try again?")
            return

    await status_msg.edit_text(text if text else "Couldn't hear any speech in that.")


def main() -> None:
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(
        MessageHandler(
            filters.VOICE | filters.AUDIO | filters.VIDEO_NOTE | filters.VIDEO | filters.Document.AUDIO,
            handle_audio,
        )
    )
    logger.info("Bot starting (polling)...")
    app.run_polling()


if __name__ == "__main__":
    main()
