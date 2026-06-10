from __future__ import annotations

from voiceclipper.transcriber import TranscriptWord


def clip_boundaries(
    words: list[TranscriptWord],
    start_word_index: int,
    end_word_index: int,
    padding_ms: int,
    *,
    pause_gap_ms: int = 200,
    audio_length_ms: int,
) -> tuple[int, int]:
    start_ms = int(words[start_word_index].start * 1000)
    end_ms = int(words[end_word_index].end * 1000)

    gap_before_ms = (
        int((words[start_word_index].start - words[start_word_index - 1].end) * 1000)
        if start_word_index > 0
        else start_ms
    )
    gap_after_ms = (
        int((words[end_word_index + 1].start - words[end_word_index].end) * 1000)
        if end_word_index < len(words) - 1
        else max(0, audio_length_ms - end_ms)
    )

    if start_word_index == 0:
        pre_pad = min(padding_ms, start_ms)
    elif gap_before_ms >= pause_gap_ms:
        pre_pad = min(padding_ms, max(0, gap_before_ms - 20))
    else:
        pre_pad = 0

    if end_word_index == len(words) - 1:
        post_pad = min(padding_ms, max(0, audio_length_ms - end_ms))
    elif gap_after_ms >= pause_gap_ms:
        post_pad = min(padding_ms, max(0, gap_after_ms - 20))
    else:
        post_pad = 0

    return max(0, start_ms - pre_pad), min(audio_length_ms, end_ms + post_pad)
