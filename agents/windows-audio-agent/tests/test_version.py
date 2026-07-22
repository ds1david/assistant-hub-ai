from pathlib import Path

import assistant_hub_audio


def test_version_matches_root_version_file() -> None:
    version_file = Path(__file__).resolve().parents[3] / "VERSION"
    expected = version_file.read_text(encoding="utf-8").strip()

    assert assistant_hub_audio.__version__ == expected
