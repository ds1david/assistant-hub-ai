"""Windows per-process WASAPI loopback capture (SF-020 Issue #19).

Only imported on Windows, lazily, by `capture.py` when a channel is selected
by process (`DeviceSelector.process_id`/`process_name`) instead of a device.
Bypasses `PyAudioWPatch`/PortAudio entirely (research.md §2): there is no
PortAudio device index for a process-scoped `IAudioClient`, so this module
talks to `ActivateAudioInterfaceAsync` directly via `comtypes`, the same
"declare manually, no typelib generation, no third-party SDK" approach
already used for `IMMNotificationClient` in `mmdevice_notifications.py`
(SF-019).

Reuses `pycaw.api.audioclient.IAudioClient` (already declared with proper
`COMMETHOD` paramflags) instead of re-declaring it - `IAudioCaptureClient` has
no pycaw equivalent and is declared here.

`IActivateAudioInterfaceCompletionHandler` is a COM interface *this module
implements* (Windows calls into it when activation completes), declared via
`comtypes.STDMETHOD` (no paramflags) - so its callback method MUST accept an
explicit, unused `this` as the second argument, the exact same convention and
reason as `IMMNotificationClient` in `mmdevice_notifications.py` (SF-019
Issue #22 Bug A; see that module's docstring and
`specs/010-sf-019-callback-notpresent-fix/research.md` §1).
`IActivateAudioInterfaceAsyncOperation` and `IAudioCaptureClient` are only
ever *called* by this module, never implemented here, so that concern does
not apply to them.

Sources (Microsoft Learn, mmdeviceapi.h / audioclientactivationparams.h):
- `ActivateAudioInterfaceAsync`: minimum supported client Windows 10 Build
  20348 for `PROCESS_LOOPBACK_MODE_INCLUDE_TARGET_PROCESS_TREE`.
- `AUDIOCLIENT_ACTIVATION_PARAMS` / `AUDIOCLIENT_PROCESS_LOOPBACK_PARAMS` /
  `PROCESS_LOOPBACK_MODE`.

**Unverified until manual Windows validation** (specs/009-sf-020-process-capture/
quickstart.md §2, T024) - this is by far the riskiest, least-testable-in-WSL
part of this feature (P10): async COM activation with a hand-rolled
PROPVARIANT/VT_BLOB payload cannot be exercised without real Windows/COM.
"""

from __future__ import annotations

import logging
import threading
import time
from ctypes import (
    POINTER,
    Structure,
    byref,
    c_int32,
    c_ubyte,
    c_uint32,
    c_ulong,
    c_ushort,
    c_void_p,
    c_wchar_p,
    cast,
    memmove,
    sizeof,
)
from ctypes.wintypes import DWORD

# `HRESULT`/`WinDLL` are Windows-only in CPython's `ctypes` (they don't exist
# on Linux) - imported lazily inside the functions that need them, like every
# other Windows-only import in this module (comtypes, pycaw), so this module
# still *imports* cleanly on WSL/Linux even though nothing in it can *run*
# there (P3).

LOGGER = logging.getLogger(__name__)

# mmdeviceapi.h: magic device interface path that selects process-loopback
# activation instead of a real endpoint.
_VIRTUAL_AUDIO_DEVICE_PROCESS_LOOPBACK = "VAD\\Process_Loopback"

# audioclientactivationparams.h: AUDIOCLIENT_ACTIVATION_TYPE.
_AUDIOCLIENT_ACTIVATION_TYPE_PROCESS_LOOPBACK = 1

# audioclientactivationparams.h: PROCESS_LOOPBACK_MODE. INCLUDE (not EXCLUDE)
# is the default (research.md §1): many real targets (e.g. browsers) render
# audio from child processes, not the PID an operator would name.
_PROCESS_LOOPBACK_MODE_INCLUDE_TARGET_PROCESS_TREE = 0
_PROCESS_LOOPBACK_MODE_EXCLUDE_TARGET_PROCESS_TREE = 1

# OLE Automation VARENUM: VT_BLOB. The only PROPVARIANT variant this module
# ever constructs.
_VT_BLOB = 65

# Audioclient.h: AUDCLNT_SHAREMODE_SHARED, AUDCLNT_STREAMFLAGS_LOOPBACK.
_AUDCLNT_SHAREMODE_SHARED = 0
_AUDCLNT_STREAMFLAGS_LOOPBACK = 0x00020000

_ACTIVATION_TIMEOUT_SECONDS = 5.0
_NEXT_PACKET_POLL_TIMEOUT_SECONDS = 5.0
_NEXT_PACKET_POLL_INTERVAL_SECONDS = 0.01


class _ProcessLoopbackParams(Structure):
    _fields_ = [("TargetProcessId", DWORD), ("ProcessLoopbackMode", c_int32)]


class _ActivationParams(Structure):
    _fields_ = [("ActivationType", c_int32), ("ProcessLoopbackParams", _ProcessLoopbackParams)]


class _Blob(Structure):
    _fields_ = [("cbSize", c_ulong), ("pBlobData", POINTER(c_ubyte))]


class _PropVariantBlob(Structure):
    """PROPVARIANT, restricted to the single variant (VT_BLOB) this module

    ever constructs - not a general-purpose PROPVARIANT. The header (`vt` +
    3 reserved WORDs, 8 bytes total) matches the real ABI; `blob` is
    ctypes-aligned the same way the real union member is, giving the same
    total size (24 bytes on x64) without hand-rolling every other variant.
    """

    _fields_ = [
        ("vt", c_ushort),
        ("wReserved1", c_ushort),
        ("wReserved2", c_ushort),
        ("wReserved3", c_ushort),
        ("blob", _Blob),
    ]


def _build_activate_completion_handler_interface() -> type:
    """`IActivateAudioInterfaceCompletionHandler` (mmdeviceapi.h), 1 method."""
    from ctypes import HRESULT

    from comtypes import GUID, IUnknown, STDMETHOD

    class IActivateAudioInterfaceCompletionHandler(IUnknown):
        _iid_ = GUID("{94EA2B94-E9CC-49E0-C0FF-EE64CA8F5B90}")
        _methods_ = [
            STDMETHOD(HRESULT, "ActivateCompleted", [c_void_p]),
        ]

    return IActivateAudioInterfaceCompletionHandler


def _build_async_operation_interface() -> type:
    """`IActivateAudioInterfaceAsyncOperation` (mmdeviceapi.h), 1 method."""
    from ctypes import HRESULT

    from comtypes import GUID, IUnknown, STDMETHOD

    class IActivateAudioInterfaceAsyncOperation(IUnknown):
        _iid_ = GUID("{72A22D78-CDE4-431D-B8CC-843A71199B6D}")
        _methods_ = [
            STDMETHOD(HRESULT, "GetActivateResult", [POINTER(HRESULT), POINTER(c_void_p)]),
        ]

    return IActivateAudioInterfaceAsyncOperation


def _build_audio_capture_client_interface() -> type:
    """`IAudioCaptureClient` (Audioclient.h). No pycaw equivalent exists."""
    from ctypes import HRESULT

    from comtypes import GUID, IUnknown, STDMETHOD

    class IAudioCaptureClient(IUnknown):
        _iid_ = GUID("{C8ADBD64-E71E-48a0-A4DE-185C395CD317}")
        _methods_ = [
            STDMETHOD(
                HRESULT,
                "GetBuffer",
                [
                    POINTER(POINTER(c_ubyte)),
                    POINTER(c_uint32),
                    POINTER(c_ulong),
                    POINTER(c_ulong),
                    POINTER(c_ulong),
                ],
            ),
            STDMETHOD(HRESULT, "ReleaseBuffer", [c_uint32]),
            STDMETHOD(HRESULT, "GetNextPacketSize", [POINTER(c_uint32)]),
        ]

    return IAudioCaptureClient


def _build_completion_handler_class(completed: threading.Event, result: dict) -> type:
    from ctypes import HRESULT

    from comtypes import COMObject

    IActivateAudioInterfaceCompletionHandler = _build_activate_completion_handler_interface()
    IActivateAudioInterfaceAsyncOperation = _build_async_operation_interface()

    class _CompletionHandler(COMObject):
        _com_interfaces_ = [IActivateAudioInterfaceCompletionHandler]

        # `this` accepted-but-unused: see module docstring (SF-019 Issue #22
        # Bug A) - IActivateAudioInterfaceCompletionHandler is
        # STDMETHOD-declared (no paramflags), so comtypes always passes the
        # raw `this` pointer first.
        def IActivateAudioInterfaceCompletionHandler_ActivateCompleted(self, this, operation_ptr) -> None:
            try:
                operation = cast(operation_ptr, POINTER(IActivateAudioInterfaceAsyncOperation))
                activate_result = HRESULT()
                interface_ptr = c_void_p()
                operation.GetActivateResult(byref(activate_result), byref(interface_ptr))
                result["hresult"] = activate_result.value
                result["interface_ptr"] = interface_ptr.value
            except Exception as exc:  # noqa: BLE001 - callback must never raise into COM
                LOGGER.warning("Process-loopback activation completion callback failed: %s", exc)
                result["hresult"] = -1
            finally:
                completed.set()

    return _CompletionHandler


def _activate_audio_client_for_process(pid: int, *, include_process_tree: bool = True):
    """Call `ActivateAudioInterfaceAsync` for process-loopback and block

    until the (async, COM-driven) completion callback fires or times out.
    Returns a raw `IAudioClient` COM pointer (`pycaw.api.audioclient`).
    """
    from ctypes import HRESULT, WinDLL

    from comtypes import GUID
    from pycaw.api.audioclient import IAudioClient

    mode = (
        _PROCESS_LOOPBACK_MODE_INCLUDE_TARGET_PROCESS_TREE
        if include_process_tree
        else _PROCESS_LOOPBACK_MODE_EXCLUDE_TARGET_PROCESS_TREE
    )
    params = _ActivationParams(
        ActivationType=_AUDIOCLIENT_ACTIVATION_TYPE_PROCESS_LOOPBACK,
        ProcessLoopbackParams=_ProcessLoopbackParams(TargetProcessId=pid, ProcessLoopbackMode=mode),
    )
    # The blob buffer must outlive the ActivateAudioInterfaceAsync call
    # itself (read synchronously by mmdevapi.dll before it returns), which a
    # local variable kept alive for this function's scope already satisfies.
    params_buffer = (c_ubyte * sizeof(_ActivationParams))()
    memmove(params_buffer, byref(params), sizeof(_ActivationParams))

    activation_params = _PropVariantBlob()
    activation_params.vt = _VT_BLOB
    activation_params.blob.cbSize = sizeof(_ActivationParams)
    activation_params.blob.pBlobData = cast(params_buffer, POINTER(c_ubyte))

    IActivateAudioInterfaceCompletionHandler = _build_activate_completion_handler_interface()

    completed = threading.Event()
    result: dict = {}
    handler = _build_completion_handler_class(completed, result)()

    mmdevapi = WinDLL("Mmdevapi.dll")
    mmdevapi.ActivateAudioInterfaceAsync.argtypes = [
        c_wchar_p,
        POINTER(GUID),
        POINTER(_PropVariantBlob),
        POINTER(IActivateAudioInterfaceCompletionHandler),
        POINTER(c_void_p),
    ]
    mmdevapi.ActivateAudioInterfaceAsync.restype = HRESULT

    async_op_ptr = c_void_p()
    hr = mmdevapi.ActivateAudioInterfaceAsync(
        _VIRTUAL_AUDIO_DEVICE_PROCESS_LOOPBACK,
        byref(IAudioClient._iid_),
        byref(activation_params),
        handler,
        byref(async_op_ptr),
    )
    if hr != 0:
        raise RuntimeError(f"ActivateAudioInterfaceAsync failed with HRESULT {hr:#x} for pid={pid}")

    if not completed.wait(_ACTIVATION_TIMEOUT_SECONDS):
        raise RuntimeError(
            f"ActivateAudioInterfaceAsync did not complete within "
            f"{_ACTIVATION_TIMEOUT_SECONDS}s for pid={pid}"
        )
    if result.get("hresult") != 0 or not result.get("interface_ptr"):
        raise RuntimeError(
            f"Process-loopback activation failed for pid={pid}: HRESULT {result.get('hresult'):#x}"
        )

    return cast(c_void_p(result["interface_ptr"]), POINTER(IAudioClient))


class ProcessLoopbackStream:
    """Loopback capture for a single process, scoped via `IAudioClient`.

    Exposes the same minimal surface `_capture_once` already uses for a
    `PyAudioWPatch` stream (`read`/`stop_stream`/`close`), so `capture.py`
    only needs to branch on *how* the stream is constructed (research.md §2).
    """

    def __init__(self, pid: int, *, sample_rate: int = 48_000, channels: int = 2) -> None:
        self._sample_rate = sample_rate
        self._channels = channels
        self._closed = False
        self._client = _activate_audio_client_for_process(pid)
        self._capture_client = None
        self._start()

    def _start(self) -> None:
        from pycaw.api.audioclient.depend import WAVEFORMATEX

        # capture.py's _normalize_pcm already resamples/downmixes to
        # TARGET_RATE (16kHz mono int16) regardless of source format, same
        # as device-based channels - this format only needs to be a format
        # WASAPI shared-mode loopback accepts.
        block_align = 2 * self._channels
        fmt = WAVEFORMATEX(
            wFormatTag=1,  # WAVE_FORMAT_PCM
            nChannels=self._channels,
            nSamplesPerSec=self._sample_rate,
            nAvgBytesPerSec=self._sample_rate * block_align,
            nBlockAlign=block_align,
            wBitsPerSample=16,
            cbSize=0,
        )
        self._client.Initialize(
            _AUDCLNT_SHAREMODE_SHARED,
            _AUDCLNT_STREAMFLAGS_LOOPBACK,
            10_000_000,  # 1s buffer, REFERENCE_TIME (100ns units)
            0,
            byref(fmt),
            None,
        )
        IAudioCaptureClient = _build_audio_capture_client_interface()
        capture_client_ptr = c_void_p()
        self._client.GetService(byref(IAudioCaptureClient._iid_), byref(capture_client_ptr))
        self._capture_client = cast(capture_client_ptr, POINTER(IAudioCaptureClient))
        self._client.Start()

    def read(self, chunk_size: int, exception_on_overflow: bool = False) -> bytes:
        # Polling loop matching PyAudioWPatch's blocking `read()` semantics:
        # wait until at least one packet is available, then drain it.
        deadline = time.monotonic() + _NEXT_PACKET_POLL_TIMEOUT_SECONDS
        next_packet_size = c_uint32()
        while time.monotonic() < deadline:
            self._capture_client.GetNextPacketSize(byref(next_packet_size))
            if next_packet_size.value:
                break
            time.sleep(_NEXT_PACKET_POLL_INTERVAL_SECONDS)
        else:
            return b"\x00\x00" * chunk_size  # silence, same shape callers expect

        data_ptr = POINTER(c_ubyte)()
        num_frames = c_uint32()
        flags = c_ulong()
        self._capture_client.GetBuffer(byref(data_ptr), byref(num_frames), byref(flags), None, None)
        block_align = 2 * self._channels
        byte_count = num_frames.value * block_align
        raw = bytes((c_ubyte * byte_count).from_address(cast(data_ptr, c_void_p).value))
        self._capture_client.ReleaseBuffer(num_frames.value)
        return raw

    def stop_stream(self) -> None:
        if self._client is not None and not self._closed:
            try:
                self._client.Stop()
            except Exception as exc:  # noqa: BLE001 - stop must stay best-effort
                LOGGER.warning("Failed to stop process-loopback stream: %s", exc)

    def close(self) -> None:
        if self._closed:
            return
        self.stop_stream()
        self._closed = True
