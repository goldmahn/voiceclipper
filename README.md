# Voiceclipper

Voiceclipper reviews an audio recording, locates predetermined phrases, and exports each match as its own `.wav` clip.

## What it does

1. Transcribes the source recording with [faster-whisper](https://github.com/SYSTRAN/faster-whisper).
2. Searches transcript segments for the phrases you configure.
3. Slices the original audio around each match.
4. Writes one WAV file per matched phrase.

## Requirements

- Python 3.11+
- [ffmpeg](https://ffmpeg.org/) on your `PATH` (used by `pydub` for audio I/O)

On macOS with Homebrew:

```bash
brew install ffmpeg
```

## Setup

```bash
cd voiceclipper
python3 -m venv .venv
source .venv/bin/activate
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

Options:

- `--model` — Whisper model size (`tiny`, `base`, `small`, `medium`, `large-v3`, …). Default: `base`.
- `--device` — `cpu`, `cuda`, or `auto`.
- `--compute-type` — faster-whisper compute type (default: `int8` on CPU).

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
│   ├── config.py       # phrase list loading
│   ├── detector.py     # match phrases to transcript segments
│   ├── pipeline.py     # end-to-end job runner
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
