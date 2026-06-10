from __future__ import annotations

import numpy as np
import noisereduce as nr
import pyloudnorm as pyln
from pedalboard import Pedalboard, Compressor, HighpassFilter, LowShelfFilter, PeakFilter, Limiter
from pydub import AudioSegment

from voiceclipper.config import ProcessingConfig


def _to_numpy(segment: AudioSegment) -> tuple[np.ndarray, int]:
    """Convert pydub AudioSegment to float32 numpy array (channels, samples)."""
    samples = np.array(segment.get_array_of_samples(), dtype=np.float32)
    samples /= float(1 << (segment.sample_width * 8 - 1))
    if segment.channels > 1:
        samples = samples.reshape((-1, segment.channels)).T
    else:
        samples = samples.reshape((1, -1))
    return samples, segment.frame_rate


def _from_numpy(audio: np.ndarray, sample_rate: int, original: AudioSegment) -> AudioSegment:
    """Convert float32 numpy array (channels, samples) back to pydub AudioSegment."""
    audio = np.clip(audio, -1.0, 1.0)
    sample_width = original.sample_width
    max_val = float(1 << (sample_width * 8 - 1))
    int_audio = (audio * max_val).astype(np.int16 if sample_width == 2 else np.int32)
    if int_audio.shape[0] == 1:
        interleaved = int_audio[0]
    else:
        interleaved = int_audio.T.reshape(-1)
    return AudioSegment(
        interleaved.tobytes(),
        frame_rate=sample_rate,
        sample_width=sample_width,
        channels=original.channels,
    )


class ProcessingChain:
    def __init__(self, config: ProcessingConfig) -> None:
        self.config = config
        self._board = self._build_board()

    def _build_board(self) -> Pedalboard:
        plugins = []

        plugins.append(HighpassFilter(cutoff_frequency_hz=float(self.config.highpass_hz)))

        plugins.append(
            PeakFilter(
                cutoff_frequency_hz=float(self.config.presence_hz),
                gain_db=self.config.presence_gain_db,
                q=0.9,
            )
        )

        if self.config.compression:
            plugins.append(
                Compressor(
                    threshold_db=self.config.compression_threshold_db,
                    ratio=self.config.compression_ratio,
                    attack_ms=5.0,
                    release_ms=100.0,
                )
            )

        plugins.append(Limiter(threshold_db=self.config.peak_limit_dbtp, release_ms=50.0))

        return Pedalboard(plugins)

    def process(self, segment: AudioSegment) -> AudioSegment:
        audio, sr = _to_numpy(segment)

        if self.config.noise_reduction:
            reduced = np.stack(
                [nr.reduce_noise(y=ch, sr=sr, stationary=False) for ch in audio]
            )
            audio = reduced

        audio = self._board(audio, sr)

        if self.config.target_lufs is not None:
            meter = pyln.Meter(sr)
            # pyloudnorm expects (samples, channels)
            mono_or_stereo = audio.T if audio.shape[0] > 1 else audio[0]
            loudness = meter.integrated_loudness(mono_or_stereo)
            if np.isfinite(loudness):
                gain = self.config.target_lufs - loudness
                audio = audio * (10.0 ** (gain / 20.0))
                # re-limit after loudness adjustment
                audio = self._board(audio, sr)

        return _from_numpy(audio, sr, segment)
