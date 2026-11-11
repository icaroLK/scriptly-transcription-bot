import subprocess
import sys
import tempfile
from pathlib import Path

from bot import FFMPEG_BIN, GROQ_MODEL, groq_client

MAX_MB = 24


def extract_audio(input_path: Path, output_path: Path, bitrate: str) -> None:
    result = subprocess.run(
        [
            FFMPEG_BIN, "-y", "-i", str(input_path),
            "-vn", "-ar", "16000", "-ac", "1", "-b:a", bitrate,
            str(output_path),
        ],
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


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python transcribe_file.py <path-to-video-or-audio>")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    if not input_path.exists():
        print(f"File not found: {input_path}")
        sys.exit(1)

    with tempfile.TemporaryDirectory() as tmpdir:
        audio_path = Path(tmpdir) / "audio.mp3"

        for bitrate in ("32k", "16k"):
            print(f"Extracting audio at {bitrate}...")
            extract_audio(input_path, audio_path, bitrate)
            size_mb = audio_path.stat().st_size / (1024 * 1024)
            print(f"Audio size: {size_mb:.1f} MB")
            if size_mb <= MAX_MB:
                break
        else:
            print("Still too large even at the lowest bitrate. Split the file and run this twice.")
            sys.exit(1)

        print("Transcribing (this can take a bit for long files)...")
        text = transcribe(audio_path)

    out_path = input_path.with_suffix(".txt")
    out_path.write_text(text, encoding="utf-8")
    print(f"Saved transcript to {out_path}")


if __name__ == "__main__":
    main()
