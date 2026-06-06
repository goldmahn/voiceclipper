from __future__ import annotations

from dataclasses import dataclass

from voiceclipper.config import PhraseTarget
from voiceclipper.transcriber import TranscriptSegment


@dataclass(frozen=True)
class PhraseMatch:
    phrase: PhraseTarget
    segment: TranscriptSegment
    start_ms: int
    end_ms: int


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


def find_phrase_matches(
    phrases: list[PhraseTarget],
    segments: list[TranscriptSegment],
) -> list[PhraseMatch]:
    matches: list[PhraseMatch] = []
    seen_ids: set[str] = set()

    for phrase in phrases:
        if phrase.id in seen_ids:
            continue

        needle = _normalize(phrase.text)
        for segment in segments:
            if needle not in _normalize(segment.text):
                continue

            start_ms = max(0, int(segment.start * 1000) - phrase.padding_ms)
            end_ms = int(segment.end * 1000) + phrase.padding_ms
            matches.append(
                PhraseMatch(
                    phrase=phrase,
                    segment=segment,
                    start_ms=start_ms,
                    end_ms=end_ms,
                )
            )
            seen_ids.add(phrase.id)
            break

    return matches
