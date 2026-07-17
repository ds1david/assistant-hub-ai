from pathlib import Path

import pytest

from assistant_hub_audio.profiles import load_profile


def test_loads_multi_channel_profile(tmp_path: Path) -> None:
    profile_path = tmp_path / "profile.yaml"
    profile_path.write_text(
        """
version: 1
name: test
channels:
  - id: local
    kind: input
    device:
      default: true
  - id: remote_bt
    kind: loopback
    device:
      nameRegex: Bluetooth.*loopback
""".strip(),
        encoding="utf-8",
    )

    profile = load_profile(profile_path)

    assert profile.name == "test"
    assert [channel.channel_id for channel in profile.channels] == ["local", "remote_bt"]
    assert profile.channels[0].source_type == "microphone"
    assert profile.channels[1].source_type == "system"
    assert profile.channels[0].processing.gain_db == 0.0


def test_rejects_duplicate_channel_ids(tmp_path: Path) -> None:
    profile_path = tmp_path / "profile.yaml"
    profile_path.write_text(
        """
version: 1
name: test
channels:
  - id: duplicate
    kind: input
    device:
      default: true
  - id: duplicate
    kind: loopback
    device:
      default: true
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unique"):
        load_profile(profile_path)


def test_channel_serialization_round_trip(tmp_path: Path) -> None:
    from assistant_hub_audio.profiles import channel_from_dict, channel_to_dict

    profile_path = tmp_path / "profile.yaml"
    profile_path.write_text(
        """
version: 1
name: test
channels:
  - id: remote_bt
    label: Audio remoto
    kind: loopback
    device:
      nameRegex: Bluetooth.*Loopback
""".strip(),
        encoding="utf-8",
    )
    original = load_profile(profile_path).channels[0]

    restored = channel_from_dict(channel_to_dict(original))

    assert restored == original


def test_loads_channel_processing(tmp_path: Path) -> None:
    profile_path = tmp_path / "profile.yaml"
    profile_path.write_text(
        """
version: 1
name: test-processing
channels:
  - id: local
    kind: input
    device:
      default: true
    processing:
      gainDb: 3
      noiseGateDb: -36
""".strip(),
        encoding="utf-8",
    )

    channel = load_profile(profile_path).channels[0]

    assert channel.processing.gain_db == 3.0
    assert channel.processing.noise_gate_db == -36.0
