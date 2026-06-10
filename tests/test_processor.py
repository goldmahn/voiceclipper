from __future__ import annotations

import math

import numpy as np
import pyloudnorm as pyln
import pytest
from pydub import AudioSegment

from voiceclipper.config import ProcessingConfig
from voiceclipper.processor import ProcessingChain, _from_numpy, _to_numpy


SAMPLE_RATE = 44100
DURATION_S = 2.0


def _sine_segment(freq: float = 440.0, amplitude: float = 0.3) -> AudioSegment:
    t = np.linspace(0, DURATION_S, int(SAMPLE_RATE * DURATION_S), endpoint=False)
    wave = (amplitude * np.sin(2 * math.pi * freq * t)).astype(np.float32)
    max_val = 32768
    pcm = (wave * max_val).astype(np.int16)
    return AudioSegment(
        pcm.tobytes(),
        frame_rate=SAMPLE_RATE,
        sample_width=2,
        channels=1,
    )


def _noisy_segment() -> AudioSegment:
    t = np.linspace(0, DURATION_S, int(SAMPLE_RATE * DURATION_S), endpoint=False)
    rng = np.random.default_rng(42)
    wave = (0.2 * np.sin(2 * math.pi * 440 * t) + 0.05 * rng.standard_normal(len(t))).astype(np.float32)
    wave = np.clip(wave, -1.0, 1.0)
    pcm = (wave * 32767).astype(np.int16)
    return AudioSegment(
        pcm.tobytes(),
        frame_rate=SAMPLE_RATE,
        sample_width=2,
        channels=1,
    )


# --- roundtrip helpers ---

def test_numpy_roundtrip():
    seg = _sine_segment()
    audio, sr = _to_numpy(seg)
    assert audio.shape[0] == 1
    assert sr == SAMPLE_RATE
    recovered = _from_numpy(audio, sr, seg)
    assert recovered.frame_rate == SAMPLE_RATE
    assert recovered.channels == 1


# --- full chain ---

def test_chain_runs_without_error():
    cfg = ProcessingConfig()
    chain = ProcessingChain(cfg)
    seg = _sine_segment()
    result = chain.process(seg)
    assert len(result) > 0


def test_chain_preserves_duration_approximately():
    cfg = ProcessingConfig()
    chain = ProcessingChain(cfg)
    seg = _sine_segment()
    result = chain.process(seg)
    assert abs(len(result) - len(seg)) < 50  # within 50 ms


def test_peak_stays_below_limit():
    cfg = ProcessingConfig(target_lufs=None)
    chain = ProcessingChain(cfg)
    seg = _sine_segment(amplitude=0.95)
    result = chain.process(seg)
    audio, _ = _to_numpy(result)
    peak_db = 20.0 * math.log10(float(np.max(np.abs(audio))) + 1e-9)
    assert peak_db <= cfg.peak_limit_dbtp + 0.5  # 0.5 dB tolerance for integer conversion


def test_loudness_normalization_hits_target():
    cfg = ProcessingConfig(target_lufs=-16.0, noise_reduction=False)
    chain = ProcessingChain(cfg)
    seg = _sine_segment(amplitude=0.1)
    result = chain.process(seg)
    audio, sr = _to_numpy(result)
    meter = pyln.Meter(sr)
    loudness = meter.integrated_loudness(audio[0])
    assert abs(loudness - cfg.target_lufs) < 2.0  # within 2 LUFS


def test_loudness_normalization_skipped_when_none():
    cfg = ProcessingConfig(target_lufs=None, noise_reduction=False)
    chain = ProcessingChain(cfg)
    seg = _sine_segment(amplitude=0.05)
    result = chain.process(seg)
    audio_in, _ = _to_numpy(seg)
    audio_out, _ = _to_numpy(result)
    # Without normalization, a quiet clip stays quiet
    assert np.max(np.abs(audio_out)) < 0.5


def test_noise_reduction_flag_false_still_runs():
    cfg = ProcessingConfig(noise_reduction=False)
    chain = ProcessingChain(cfg)
    seg = _noisy_segment()
    result = chain.process(seg)
    assert len(result) > 0


def test_compression_flag_false_still_runs():
    cfg = ProcessingConfig(compression=False)
    chain = ProcessingChain(cfg)
    seg = _sine_segment()
    result = chain.process(seg)
    assert len(result) > 0


def test_all_processing_disabled_except_eq_and_limit():
    cfg = ProcessingConfig(noise_reduction=False, compression=False, target_lufs=None)
    chain = ProcessingChain(cfg)
    seg = _sine_segment()
    result = chain.process(seg)
    assert len(result) > 0
