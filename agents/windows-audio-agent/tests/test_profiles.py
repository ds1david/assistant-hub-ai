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


ENDPOINT_ID = "{0.0.1.00000000}.{a1b2c3d4-1111-2222-3333-444444444444}"


def test_loads_endpoint_id_selector(tmp_path: Path) -> None:
    profile_path = tmp_path / "profile.yaml"
    profile_path.write_text(
        f"""
version: 1
name: test-endpoint
channels:
  - id: local
    kind: input
    device:
      endpointId: "{ENDPOINT_ID}"
""".strip(),
        encoding="utf-8",
    )

    channel = load_profile(profile_path).channels[0]

    assert channel.selector.endpoint_id == ENDPOINT_ID
    assert channel.selector.index is None


def test_endpoint_id_may_coexist_with_index(tmp_path: Path) -> None:
    profile_path = tmp_path / "profile.yaml"
    profile_path.write_text(
        f"""
version: 1
name: test-endpoint-index
channels:
  - id: local
    kind: input
    device:
      endpointId: "{ENDPOINT_ID}"
      index: 5
""".strip(),
        encoding="utf-8",
    )

    channel = load_profile(profile_path).channels[0]

    assert channel.selector.endpoint_id == ENDPOINT_ID
    assert channel.selector.index == 5


def test_rejects_endpoint_id_combined_with_name_regex(tmp_path: Path) -> None:
    profile_path = tmp_path / "profile.yaml"
    profile_path.write_text(
        f"""
version: 1
name: test-invalid
channels:
  - id: local
    kind: input
    device:
      endpointId: "{ENDPOINT_ID}"
      nameRegex: Microfone.*
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="device selector"):
        load_profile(profile_path)


def test_rejects_blank_endpoint_id(tmp_path: Path) -> None:
    profile_path = tmp_path / "profile.yaml"
    profile_path.write_text(
        """
version: 1
name: test-blank
channels:
  - id: local
    kind: input
    device:
      endpointId: "  "
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="endpointId"):
        load_profile(profile_path)


def test_endpoint_id_round_trips_through_worker_json(tmp_path: Path) -> None:
    from assistant_hub_audio.profiles import channel_from_dict, channel_to_dict

    profile_path = tmp_path / "profile.yaml"
    profile_path.write_text(
        f"""
version: 1
name: test-roundtrip
channels:
  - id: remote
    kind: loopback
    device:
      endpointId: "{ENDPOINT_ID}"
      index: 7
""".strip(),
        encoding="utf-8",
    )
    original = load_profile(profile_path).channels[0]

    serialized = channel_to_dict(original)
    restored = channel_from_dict(serialized)

    assert serialized["device"] == {"endpointId": ENDPOINT_ID, "index": 7}
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
