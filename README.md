# Voiceclipper

Voiceclipper reviews an audio recording, locates predetermined phrases, and exports each match as its own `.wav` clip.

## What it does

1. Transcribes the source recording with [faster-whisper](https://github.com/SYSTRAN/faster-whisper).
2. Searches transcript segments for the phrases you configure.
3. Slices the original audio around each match.
4. Writes one WAV file per matched phrase.

## Requirements

- Python 3.11+
- [ffmpeg](https://ffmpeg.org/) on your `PATH` (required for MP3, M4A, and other non-WAV formats)

**macOS (Homebrew):**
```bash
brew install ffmpeg
```

**Windows:**
```powershell
winget install Gyan.FFmpeg
```
After installing, open a new terminal so ffmpeg is on your PATH. If it still isn't picked up, add the bin folder manually:
```powershell
$env:PATH += ";C:\Users\<you>\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin"
```

## Setup

**macOS / Linux:**
```bash
cd voiceclipper
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

**Windows (PowerShell):**
```powershell
cd voiceclipper
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

Copy the example phrase list and edit it for your recording:

```bash
cp phrases.example.yaml phrases.yaml
```

## Usage

```bash
voiceclipper path/to/recording.mp3 --phrases phrases.yaml --output-dir output
```

Add `--process` to run the full audio processing chain on each clip (EQ, noise reduction, compression, loudness normalization):

```bash
voiceclipper recording.mp3 --phrases phrases.yaml --output-dir output --process
```

### Options

**Transcription:**

- `--model` — Whisper model size (`tiny`, `base`, `small`, `medium`, `large-v3`, …). Default: `base`. Use `small` or `medium` for better accuracy on noisy audio.
- `--device` — `cpu`, `cuda`, or `auto`.
- `--compute-type` — faster-whisper compute type (default: `int8` on CPU).

**Audio processing (`--process` must be set):**

- `--no-noise-reduction` — skip spectral noise reduction
- `--no-compression` — skip dynamic range compression
- `--highpass-hz` — high-pass filter cutoff in Hz (default: `80`)
- `--presence-gain-db` — presence boost in dB around `--presence-hz` (default: `2.5`)
- `--presence-hz` — center frequency for presence boost (default: `3000`)
- `--compression-ratio` — compression ratio, e.g. `3.0` means 3:1 (default: `3.0`)
- `--compression-threshold` — compression threshold in dBFS (default: `-18.0`)
- `--peak-limit` — true-peak ceiling in dBTP (default: `-1.0`)
- `--target-lufs` — target integrated loudness in LUFS (default: `-16.0`); pass `0` to skip normalization

Example output:

```text
saved output/intro.wav (1200-5400 ms) from segment: 'Welcome to the show, everyone.'
saved output/outro.wav (58200-60100 ms) from segment: 'Thanks for listening.'
```

## Phrase configuration

`phrases.yaml` defines the clips to extract:

```yaml
phrases:
  - id: intro
    text: "welcome to the show"
    padding_ms: 250
```

- `id` — output filename stem (`intro.wav`).
- `text` — phrase to find (case-insensitive substring match in a transcript segment).
- `padding_ms` — milliseconds of audio to keep before and after the matched segment.

## Project layout

```text
voiceclipper/
├── phrases.example.yaml
├── pyproject.toml
├── src/voiceclipper/
│   ├── cli.py          # command-line entry point
│   ├── clipper.py      # slice audio and write WAV files
│   ├── config.py       # phrase list and processing config loading
│   ├── detector.py     # match phrases to transcript segments
│   ├── pipeline.py     # end-to-end job runner
│   ├── processor.py    # audio processing chain (EQ, NR, compression, limiting)
│   └── transcriber.py  # faster-whisper wrapper
└── tests/
```

## Tests

```bash
pytest
```

## Roadmap

- Word-level timestamps for tighter clip boundaries
- Fuzzy matching and confidence thresholds
- Batch processing for multiple source files
- Optional speaker diarization before clipping

## License

MIT
