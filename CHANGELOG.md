# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned

- Fuzzy matching and confidence thresholds
- Chunked transcription for very long single files
- Optional speaker diarization before clipping

## [0.5.0] - 2026-06-10

### Added

- Corpus Voces metadata capture for speaker, session, and phrase/content layers.
- Manifest schema v2 with `session`, `speaker`, `processing`, and per-clip `content_metadata`.
- `--metadata` JSON input and `--interactive-metadata` prompt mode.
- Optional `metadata` blocks in `phrases.yaml`.
- Downstream manifest handoff to LUFS Buff and Corpus Finisher via `--manifest`.

## [0.4.0] - 2026-06-10

### Added

- Automatic post-processing pipeline: VoiceClipper now invokes **LUFS Buff** and **Corpus Finisher** after clip export.
- Session outputs include `normalized_clips/`, `training_clips/`, and `reports/` with QC summaries.
- CLI flags: `--no-postprocess`, `--target-lufs`, `--pad`, `--fade`.
- Environment overrides: `LUFS_BUFF_CLI`, `CORPUS_FINISHER_CLI`.

## [0.3.0] - 2026-06-10

### Added

- Session-scoped output directories with `clips/`, `manifest.json`, and `transcript.words.json`.
- Manifest schema v1 for downstream corpus tooling (stable `clip_id`, source/phrases hashes, per-clip metadata).
- `voiceclipper batch` for processing directories of recordings with `--skip-existing`, `--fail-fast`, and `--index`.
- `--session-id`, `--manifest-only`, and backward-compatible `voiceclipper file.mp3` shorthand.
- ffmpeg-based clip export to avoid loading entire recordings into RAM.
- Transcript cache for fast re-clipping when `phrases.yaml` changes.
- Full Corpus Voces phrase list (100 lines) in `phrases.example.yaml`.
- `scripts/run-monitored.sh` for resource logging and macOS completion notifications.
- Cursor project rule for monitored runs on Ginnungagap.

### Changed

- Default output is now `output/<session_id>/clips/` instead of a flat `output/` folder.

## [0.2.0] - 2026-06-10

### Added

- Word-level transcription via faster-whisper (`word_timestamps=True`).
- Detection of every occurrence of each configured phrase (not just the first match).
- Gap-based clip boundaries from Whisper word timestamps, with padding limited to neighboring pauses.
- Numbered export filenames for repeated phrases (`who_sent_you.wav`, `who_sent_you1.wav`, …).
- `audioop-lts` dependency for Python 3.13+ compatibility with pydub.
- v1 phrase list in `phrases.example.yaml` (ten scripted dialogue lines).
- Tests for boundaries, clip naming, and multi-occurrence phrase detection.

### Changed

- Clips are exported per matched utterance instead of per Whisper segment.
- Phrase matching uses case-insensitive word-sequence comparison instead of segment substring search.
- CLI output reports matched phrase text instead of the enclosing transcript segment.
- README updated to describe word-level clipping behavior.

### Fixed

- Exported clips no longer span multiple phrases when Whisper groups several lines into one segment.
- Waveform silence detection no longer expands clips across adjacent speech.

## [0.1.0] - 2026-06-06

### Added

- Initial CLI and pipeline for phrase-based audio clipping.
- faster-whisper transcription, YAML phrase configuration, and WAV export via pydub.
- Example phrase config and basic detector/clipper tests.
