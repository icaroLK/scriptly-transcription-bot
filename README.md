# telegram-transcription

A Telegram bot that transcribes voice notes, audio files, and video notes — including
WhatsApp-style `.ogg`/`.opus` files — using the Groq Whisper API.

How it works: any audio/video message the bot receives is downloaded, converted to
mp3 with `ffmpeg` (this normalizes every input format), and sent to Groq's
`whisper-large-v3-turbo` model for transcription. The reply is the transcribed text.

## 1. Prerequisites

- Python 3.10+
- `ffmpeg` on your PATH

Install ffmpeg on Windows (pick one):

```bash
winget install ffmpeg
```

```bash
choco install ffmpeg
```

Verify it's on PATH (restart your terminal first if you just installed it):

```bash
ffmpeg -version
```

## 2. Get your keys

- **Telegram bot token**: message [@BotFather](https://t.me/BotFather) on Telegram,
  send `/newbot`, follow the prompts, copy the token it gives you.
- **Groq API key**: sign up free at [console.groq.com](https://console.groq.com) →
  API Keys → Create key.

## 3. Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in your two keys:

```bash
copy .env.example .env
```

## 4. Run it

```bash
python bot.py
```

Leave it running in this terminal (e.g. in a VS Code integrated terminal), open
Telegram, find your bot, send `/start`, then send it a voice note or audio file.

## 5. Deploying later (free VPS)

Nothing about this script changes when you move it to a server — it's the same
`bot.py` polling Telegram, so no public URL/webhook is needed.

1. Copy the whole project folder to the server (or `git clone` your repo there).
2. Install ffmpeg on the server:
   - Ubuntu/Debian (most free-tier VPS images): `sudo apt install -y ffmpeg`
3. Repeat the venv + `pip install` + `.env` steps above.
4. Keep it running in the background with a systemd service, for example
   `/etc/systemd/system/transcription-bot.service`:

   ```ini
   [Unit]
   Description=Telegram transcription bot
   After=network.target

   [Service]
   WorkingDirectory=/home/<user>/telegram-transcription
   ExecStart=/home/<user>/telegram-transcription/.venv/bin/python bot.py
   Restart=always
   User=<user>

   [Install]
   WantedBy=multi-user.target
   ```

   Then: `sudo systemctl enable --now transcription-bot`.

   (Until you get the Oracle box, you could also just run it under `tmux`/`screen`
   on any free VM, or even leave it running on your own PC.)

## Notes

- The bot only keeps audio in a temp directory for the duration of one request —
  nothing is stored permanently.
- `GROQ_MODEL` in `.env` can be swapped to `whisper-large-v3` for max accuracy
  (slower) instead of the default `whisper-large-v3-turbo` (fast).
