import numpy as np

from assistant_hub_audio.capture import TARGET_RATE, _normalize_pcm


def test_normalize_pcm_downmixes_stereo() -> None:
    stereo = np.array([[1000, 3000], [-1000, 1000]], dtype=np.int16).tobytes()
    result = np.frombuffer(_normalize_pcm(stereo, channels=2, source_rate=TARGET_RATE), dtype=np.int16)
    assert result.tolist() == [2000, 0]


def test_normalize_pcm_resamples() -> None:
    samples = np.zeros(48_000, dtype=np.int16).tobytes()
    result = _normalize_pcm(samples, channels=1, source_rate=48_000)
    assert len(result) == 16_000 * 2


def test_noise_gate_silences_quiet_audio() -> None:
    samples = np.full(TARGET_RATE, 100, dtype=np.int16).tobytes()
    result = np.frombuffer(
        _normalize_pcm(
            samples,
            channels=1,
            source_rate=TARGET_RATE,
            noise_gate_db=-38.0,
        ),
        dtype=np.int16,
    )
    assert np.count_nonzero(result) == 0


def test_noise_gate_preserves_loud_voice() -> None:
    samples = np.full(TARGET_RATE, 6000, dtype=np.int16).tobytes()
    result = np.frombuffer(
        _normalize_pcm(
            samples,
            channels=1,
            source_rate=TARGET_RATE,
            noise_gate_db=-38.0,
        ),
        dtype=np.int16,
    )
    assert np.count_nonzero(result) == TARGET_RATE
