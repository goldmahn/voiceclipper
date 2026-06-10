# Voiceclipper

Voiceclipper reviews an audio recording, locates predetermined phrases, and exports each match as its own `.wav` clip.

## What it does

1. Transcribes the source recording with [faster-whisper](https://github.com/SYSTRAN/faster-whisper) using word-level timestamps.
2. Locates every occurrence of each configured phrase in the transcript.
3. Sets clip boundaries from word timestamps, extending only into neighboring pauses (not across adjacent speech).
4. Writes one WAV file per matched utterance. Repeated phrases are numbered (`who_sent_you.wav`, `who_sent_you1.wav`, …).

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

Copy the v1 phrase list and edit it if needed:

```bash
cp phrases.example.yaml phrases.yaml
```

## Target phrases (v1)

The first generation of Voiceclipper listens for these ten phrases. They are defined in [`phrases.example.yaml`](phrases.example.yaml):

1. "Who sent you?"
2. "I don't like this place."
3. "You're late."
4. "Close the door behind you."
5. "We've been waiting for hours."
6. "What do you want from me?"
7. "I didn't expect company tonight."
8. "You should sit down."
9. "I've heard that before."
10. "Keep your voice down."

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

`phrases.yaml` defines the clips to extract. See [`phrases.example.yaml`](phrases.example.yaml) for the full v1 list:

```yaml
phrases:
  - id: who_sent_you
    text: "Who sent you?"
    padding_ms: 250
```

- `id` — output filename stem (`who_sent_you.wav`; repeats become `who_sent_you1.wav`, …).
- `text` — phrase to find (case-insensitive word sequence match).
- `padding_ms` — milliseconds of audio to keep before and after the matched words before pause snapping.

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

- Fuzzy matching and confidence thresholds
- Batch processing for multiple source files
- Optional speaker diarization before clipping

## License

MIT
