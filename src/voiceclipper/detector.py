from __future__ import annotations

import re
from dataclasses import dataclass

from voiceclipper.config import PhraseTarget
from voiceclipper.transcriber import TranscriptWord

_TOKEN_RE = re.compile(r"\w+(?:'\w+)?", re.UNICODE)


@dataclass(frozen=True)
class PhraseMatch:
    phrase: PhraseTarget
    matched_text: str
    start_ms: int
    end_ms: int
    start_word_index: int
    end_word_index: int


def _tokenize(text: str) -> list[str]:
    return [token.casefold() for token in _TOKEN_RE.findall(text)]


def _word_tokens(word: TranscriptWord) -> list[str]:
    return _tokenize(word.text)


def find_phrase_matches(
    phrases: list[PhraseTarget],
    words: list[TranscriptWord],
) -> list[PhraseMatch]:
    if not words:
        return []

    word_tokens = [_word_tokens(word) for word in words]
    flat_tokens: list[str] = []
    token_word_indices: list[int] = []
    for word_index, tokens in enumerate(word_tokens):
        for token in tokens:
            flat_tokens.append(token)
            token_word_indices.append(word_index)

    matches: list[PhraseMatch] = []
    for phrase in phrases:
        phrase_tokens = _tokenize(phrase.text)
        if not phrase_tokens:
            continue

        token_count = len(phrase_tokens)
        for start_token in range(len(flat_tokens) - token_count + 1):
            if flat_tokens[start_token : start_token + token_count] != phrase_tokens:
                continue

            start_word_index = token_word_indices[start_token]
            end_word_index = token_word_indices[start_token + token_count - 1]
            start_word = words[start_word_index]
            end_word = words[end_word_index]

            start_ms = max(0, int(start_word.start * 1000) - phrase.padding_ms)
            end_ms = int(end_word.end * 1000) + phrase.padding_ms
            matched_text = " ".join(word.text for word in words[start_word_index : end_word_index + 1])

            matches.append(
                PhraseMatch(
                    phrase=phrase,
                    matched_text=matched_text,
                    start_ms=start_ms,
                    end_ms=end_ms,
                    start_word_index=start_word_index,
                    end_word_index=end_word_index,
                )
            )

    matches.sort(key=lambda match: (match.start_ms, match.phrase.id))
    return matches
