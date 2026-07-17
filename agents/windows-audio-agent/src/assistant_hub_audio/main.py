from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from .capture import run_agent, run_channel_worker
from .devices import list_devices, resolve_profile
from .profiles import channel_from_dict, default_profile, load_profile

VERSION = "0.1.6"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Assistant Hub AI Windows audio agent")
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    parser.add_argument("--log-level", default="INFO", help="Logging level (default: INFO)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list-devices", help="List Windows audio devices")
    list_parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")

    probe = subparsers.add_parser("probe", help="Resolve and validate every channel in an audio profile")
    probe.add_argument("--profile", type=Path, required=True)

    run = subparsers.add_parser("run", help="Capture one or more channels in foreground")
    run.add_argument("--session", required=True, help="Session identifier")
    run.add_argument("--server", default=None, help="Transcription service WebSocket base URL")
    run.add_argument("--profile", type=Path, default=None, help="YAML audio profile")
    run.add_argument("--microphone-device", type=int, default=None, help="Legacy default-profile override")
    run.add_argument("--system-device", type=int, default=None, help="Legacy default-profile override")
    run.add_argument("--record-dir", type=Path, default=None)

    # Internal subprocess entry point. It is intentionally undocumented in the
    # regular usage flow; the foreground supervisor launches one per channel.
    worker = subparsers.add_parser("_worker", help=argparse.SUPPRESS)
    worker.add_argument("--session", required=True)
    worker.add_argument("--server", required=True)
    worker.add_argument("--channel-json", required=True)
    worker.add_argument("--record-path", type=Path, default=None)
    return parser


def _print_devices(as_json: bool) -> None:
    devices = list_devices()
    if as_json:
        print(json.dumps(devices, indent=2, ensure_ascii=False))
        return
    for device in devices:
        marker = " loopback" if device.get("isLoopbackDevice") else ""
        print(
            f"[{device['index']:>2}] {device['name']} | "
            f"in={device['maxInputChannels']} out={device['maxOutputChannels']} "
            f"rate={device['defaultSampleRate']}{marker}"
        )


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    level_name = args.log_level.upper()
    logging.basicConfig(
        level=getattr(logging, level_name, logging.INFO),
        format="%(asctime)s %(levelname)s pid=%(process)d %(threadName)s %(message)s",
    )

    if args.command == "list-devices":
        _print_devices(args.json)
        return

    if args.command == "probe":
        profile = load_profile(args.profile)
        for channel, device in resolve_profile(profile.channels):
            print(
                f"OK channel={channel.channel_id} kind={channel.kind} "
                f"device=[{device['index']}] {device['name']} rate={device['defaultSampleRate']}"
            )
        return

    if args.command == "_worker":
        raw_channel = json.loads(args.channel_json)
        if not isinstance(raw_channel, dict):
            raise ValueError("--channel-json must contain a JSON object")
        run_channel_worker(
            channel=channel_from_dict(raw_channel),
            session_id=args.session,
            server_url=args.server,
            record_path=args.record_path,
        )
        return

    profile = (
        load_profile(args.profile)
        if args.profile is not None
        else default_profile(
            microphone_device=args.microphone_device,
            system_device=args.system_device,
        )
    )
    server_url = args.server or profile.server_url or "ws://127.0.0.1:8001"
    try:
        run_agent(
            session_id=args.session,
            server_url=server_url,
            profile=profile,
            record_dir=args.record_dir,
            log_level=level_name,
        )
    except RuntimeError as exc:
        logging.getLogger(__name__).error("%s", exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
