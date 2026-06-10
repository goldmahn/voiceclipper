# Voiceclipper

Voiceclipper reviews audio recordings, locates predetermined phrases, and exports each match as its own `.wav` clip. It is designed for building voice corpora: one session in, many clipped WAVs plus a machine-readable manifest out.

## What it does

1. Transcribes the source recording with [faster-whisper](https://github.com/SYSTRAN/faster-whisper) using word-level timestamps.
2. Locates every occurrence of each configured phrase in the transcript.
3. Sets clip boundaries from word timestamps, extending only into neighboring pauses (not across adjacent speech).
4. Exports clips with **ffmpeg** (no full-file decode in RAM).
5. Writes one WAV per matched utterance, a per-session **`manifest.json`**, and a cached **`transcript.words.json`** for fast re-runs.

Repeated phrases are numbered: `who_sent_you.wav`, `who_sent_you1.wav`, …

## Requirements

- Python 3.11+
- [ffmpeg](https://ffmpeg.org/) and **ffprobe** on your `PATH`

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

Copy the phrase list and edit it for your corpus:

```bash
cp phrases.example.yaml phrases.yaml
```

## Usage

### Single recording

```bash
voiceclipper clip recordings/session_001.mp3 \
  --phrases phrases.yaml \
  --output-dir corpus/sessions
```

Backward-compatible shorthand (same as `clip`):

```bash
voiceclipper recordings/session_001.mp3 --phrases phrases.yaml --output-dir corpus/sessions
```

Output layout:

```text
corpus/sessions/session_001/
├── manifest.json
├── transcript.words.json
└── clips/
    ├── who_sent_you.wav
    └── …
```

### Batch (many recordings)

```bash
voiceclipper batch recordings/ \
  --phrases phrases.yaml \
  --output-dir corpus/sessions \
  --skip-existing \
  --index corpus/index.jsonl
```

`--skip-existing` skips sessions whose manifest already matches the source audio **and** phrases file hashes.

### Re-export without re-transcribing

After editing `phrases.yaml`, re-clip using the cached transcript:

```bash
voiceclipper clip recordings/session_001.mp3 \
  --phrases phrases.yaml \
  --output-dir corpus/sessions \
  --manifest-only
```

## Options

| Flag | Default | Purpose |
|------|---------|---------|
| `--model` | `base` | Whisper model size |
| `--device` | `cpu` | Inference device |
| `--compute-type` | `int8` | Quantization (good default on Apple Silicon) |
| `--session-id` | input filename stem | Output subdirectory name |
| `--manifest-only` | off | Reuse cached transcript; re-export clips/manifest |

## Long recordings on Apple Silicon

Tested for hour-long sessions on an **M1 with 16 GB RAM**:

- Clips are exported via **ffmpeg seek**, so export memory stays flat even for multi-hour sources.
- Whisper still transcribes the full file once; expect roughly real-time to 2× realtime on CPU with `--model base --compute-type int8`.
- Use `--skip-existing` in batch mode to resume large corpus builds safely.
- Use `--manifest-only` to iterate on phrase lists without paying transcription cost again.

For very long files, `--model tiny` trades accuracy for speed.

## Manifest

Each session writes `manifest.json` (schema v1) describing the source file, phrase config, every exported clip (`clip_id`, timestamps, paths), and missing phrase ids. Downstream tools (for example an audio cleaner) should read manifests rather than re-parsing YAML.

## Phrase configuration

See [`phrases.example.yaml`](phrases.example.yaml):

```yaml
phrases:
  - id: who_sent_you
    text: "Who sent you?"
    padding_ms: 250
```

- `id` — filename stem (`who_sent_you.wav`; repeats become `who_sent_you1.wav`, …).
- `text` — case-insensitive word sequence match.
- `padding_ms` — padding into neighboring pauses only (not into adjacent speech).

## Tests

```bash
pytest
```

## Monitored runs (Ginnungagap)

For long sessions, use the resource logger and macOS notification wrapper:

```bash
./scripts/run-monitored.sh --notify \
  --log corpus/sessions/my_session/resource.log \
  -- voiceclipper clip recording.mp3 --phrases phrases.yaml --output-dir corpus/sessions
```

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for release history.

## License

MIT
