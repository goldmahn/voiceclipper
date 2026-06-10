# Voiceclipper

Voiceclipper reviews audio recordings, locates predetermined phrases, and exports each match as its own `.wav` clip. It is designed for building voice corpora: one session in, many clipped WAVs plus a machine-readable manifest out.

## What it does

1. Transcribes the source recording with [faster-whisper](https://github.com/SYSTRAN/faster-whisper) using word-level timestamps.
2. Locates every occurrence of each configured phrase in the transcript.
3. Sets clip boundaries from word timestamps, extending only into neighboring pauses (not across adjacent speech).
4. Exports clips with **ffmpeg** (no full-file decode in RAM).
5. Writes one WAV per matched utterance, a per-session **`manifest.json`**, and a cached **`transcript.words.json`** for fast re-runs.
6. Runs **LUFS Buff** to normalize loudness into `normalized_clips/`.
7. Runs **Corpus Finisher** to pad and finalize clips into `training_clips/`.

Repeated phrases are numbered: `who_sent_you.wav`, `who_sent_you1.wav`, …

## Requirements

- Python 3.11+
- [ffmpeg](https://ffmpeg.org/) and **ffprobe** on your `PATH`
- [Node.js](https://nodejs.org/) 18+ with **LUFS Buff](../lufs-buff) and [Corpus Finisher](../corpus-finisher) available (sibling projects, `PATH`, or `LUFS_BUFF_CLI` / `CORPUS_FINISHER_CLI`)

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

### Where things go

| Folder | Purpose |
|--------|---------|
| **`samples - START HERE/`** | Drop your source recording here (`.m4a`, `.mp3`, `.wav`, …) |
| **`corpus/sessions/`** | Pipeline output — created automatically; one subfolder per session |

You do **not** need an `output/` or `recordings/` folder. Those were leftovers from older defaults or examples.

### Single recording

```bash
voiceclipper clip "samples - START HERE/your_recording.m4a" \
  --phrases phrases.yaml
```

`--output-dir corpus/sessions` is the default. Explicit form:

```bash
voiceclipper clip "samples - START HERE/your_recording.m4a" \
  --phrases phrases.yaml \
  --output-dir corpus/sessions
```

Output layout:

```text
corpus/sessions/session_001/
├── manifest.json
├── transcript.words.json
├── clips/                 # raw phrase extracts (VoiceClipper)
├── normalized_clips/      # loudness-normalized (LUFS Buff)
├── training_clips/        # padded + faded for model training (Corpus Finisher)
└── reports/
    ├── qc-report.json
    └── finalize-report.json
```

By default, VoiceClipper automatically runs **LUFS Buff** and **Corpus Finisher** after clip export. Use `--no-postprocess` to export clips only.

Repeated phrases are numbered: `who_sent_you.wav`, `who_sent_you1.wav`, …

### Batch (many recordings)

```bash
voiceclipper batch "samples - START HERE/" \
  --phrases phrases.yaml \
  --skip-existing \
  --index corpus/index.jsonl
```

`--skip-existing` skips sessions whose manifest already matches the source audio **and** phrases file hashes.

### Re-export without re-transcribing

After editing `phrases.yaml`, re-clip using the cached transcript:

```bash
voiceclipper clip "samples - START HERE/session_001.mp3" \
  --phrases phrases.yaml \
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
| `--no-postprocess` | off | Skip LUFS Buff and Corpus Finisher |
| `--target-lufs` | `-23` | Target integrated loudness for LUFS Buff |
| `--pad` | `75` | Leading/trailing training padding (ms) |
| `--fade` | `3` | Edge fade duration (ms); use `0` to disable |
| `--metadata` | off | JSON file with speaker and session metadata |
| `--interactive-metadata` | off | Prompt for speaker and session metadata before processing |

## Metadata capture

VoiceClipper owns metadata capture for the Corpus Voces pipeline. Downstream tools inherit the session manifest rather than asking the same questions again.

Three layers are supported:

1. **Speaker metadata** — identity, consent, language, vocal notes
2. **Session metadata** — recording date, room, microphone, device, notes
3. **Clip/content metadata** — optional per-phrase fields in `phrases.yaml`

### Interactive metadata

```bash
voiceclipper clip "samples - START HERE/test.m4a" \
  --phrases phrases.yaml \
  --interactive-metadata
```

### Metadata JSON

Load speaker and session fields from a JSON file:

```bash
voiceclipper clip "samples - START HERE/test.m4a" \
  --phrases phrases.yaml \
  --metadata metadata/example_session.json
```

If both `--metadata` and `--interactive-metadata` are supplied, JSON loads first and prompts fill or override missing values.

See [`metadata/example_session.json`](metadata/example_session.json) for a starter template.

### Phrase content metadata

Optional per-phrase metadata in `phrases.yaml`:

```yaml
phrases:
  - id: close_the_door
    text: "Close the door."
    padding_ms: 250
    metadata:
      species: human
      situation: warning
      emotion: tense
      intensity: 3
      character_archetype: guard
      delivery_style: controlled
      context_notes: "A wary guard trying not to alarm the others."
```

Repeated clips inherit the same phrase metadata automatically. Phrase files without a `metadata` block continue to work unchanged.

## Long recordings on Apple Silicon

Tested for hour-long sessions on an **M1 with 16 GB RAM**:

- Clips are exported via **ffmpeg seek**, so export memory stays flat even for multi-hour sources.
- Whisper still transcribes the full file once; expect roughly real-time to 2× realtime on CPU with `--model base --compute-type int8`.
- Use `--skip-existing` in batch mode to resume large corpus builds safely.
- Use `--manifest-only` to iterate on phrase lists without paying transcription cost again.

For very long files, `--model tiny` trades accuracy for speed.

## Manifest

Each session writes `manifest.json` (schema v2) describing:

- speaker metadata
- session metadata
- source file and phrase config
- every exported clip with timestamps, paths, and optional `content_metadata`
- processing history for VoiceClipper, LUFS Buff, and Corpus Finisher

Post-process QC reports also preserve speaker/session metadata and attach clip content metadata to per-clip report entries.

## Corpus Voces pipeline

```text
source recording
  → VoiceClipper (clips/)
  → LUFS Buff (normalized_clips/)
  → Corpus Finisher (training_clips/)
```

VoiceClipper orchestrates the downstream Node stages with explicit session paths. Override tool locations with:

```bash
export LUFS_BUFF_CLI="node ../lufs-buff/src/cli.js"
export CORPUS_FINISHER_CLI="node ../corpus-finisher/src/cli.js"
```

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
