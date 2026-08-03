"""Link layer: talking to the board, or convincingly pretending to.

Two implementations of one interface.

``SerialBoard``   -- the real thing over USB serial.
``SyntheticBoard`` -- a model that answers register queries and produces
                      samples, so every analysis path in the suite runs today.

The synthetic board is not a stub. It has its own ``board_gain``, independent
of ``config.PGA_GAIN``, which is how the gain guard gets tested: set them to
different values and the guard must refuse to run. ``selftest.py`` does
exactly that, and treats the guard NOT firing as a failure.

RECORDINGS ARE STORED AS RAW ADC COUNTS, never as volts. The gain lives in the
sidecar metadata. If the scale factor later turns out to have been wrong, the
data is still good -- re-derive volts from counts with the right constant.
Storing volts would bake a mistake in permanently.
"""

from __future__ import annotations

import json
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

import numpy as np

import config
import synth


# ===========================================================================
# Recording container
# ===========================================================================

@dataclass
class Recording:
    counts: np.ndarray          # (n_samples, n_channels) int32
    fs_hz: float
    meta: dict

    @property
    def n_samples(self) -> int:
        return int(self.counts.shape[0])

    @property
    def n_channels(self) -> int:
        return int(self.counts.shape[1])

    @property
    def duration_s(self) -> float:
        return self.n_samples / self.fs_hz

    def volts(self) -> np.ndarray:
        """Input-referred volts. Goes through the gain guard, always."""
        import gainguard
        return gainguard.counts_to_volts(self.counts)


def save_recording(stem: Path, rec: Recording) -> tuple[Path, Path]:
    stem.parent.mkdir(parents=True, exist_ok=True)
    npz = stem.with_suffix(".npz")
    js = stem.with_suffix(".json")
    np.savez_compressed(npz, counts=rec.counts.astype(np.int32))
    js.write_text(json.dumps(rec.meta, indent=2, sort_keys=True, default=str))
    return npz, js


def load_recording(stem: Path) -> Recording:
    stem = Path(stem)
    if stem.suffix in (".npz", ".json"):
        stem = stem.with_suffix("")
    npz, js = stem.with_suffix(".npz"), stem.with_suffix(".json")
    if not npz.exists() or not js.exists():
        raise FileNotFoundError(
            f"Recording {stem} is incomplete: "
            f"{'counts missing' if not npz.exists() else 'metadata missing'}. "
            "Both the .npz and the .json are required -- counts without the "
            "gain metadata cannot be converted to volts.")
    meta = json.loads(js.read_text())
    with np.load(npz) as z:
        counts = z["counts"]
    return Recording(counts=counts, fs_hz=float(meta["fs_hz"]), meta=meta)


def base_meta(script: str, args, extra: Optional[dict] = None) -> dict:
    """Provenance stamped into every artifact this suite writes."""
    import gainguard
    v = gainguard.current_verdict()
    meta = {
        "script": script,
        "suite_version": config.SUITE_VERSION,
        "git_revision": config.git_revision(),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "fs_hz": float(getattr(args, "fs", config.FS_HZ)),
        "mains_hz": float(getattr(args, "mains", config.MAINS_HZ)),
        "source": "synthetic" if getattr(args, "synthetic", False) else "hardware",
        "synthetic": bool(getattr(args, "synthetic", False)),
        "host_pga_gain": v.host_gain,
        "board_pga_gain": v.board_gain,
        "gain_verified": v.verified,
        "gain_check_method": v.method,
        "gain_check_detail": v.detail,
        "lsb_volts": v.lsb_volts,
        "vref_v": config.VREF_V,
        "noise_band_hz": list(config.NOISE_BAND_HZ),
    }
    if extra:
        meta.update(extra)
    return meta


# ===========================================================================
# The synthetic board
# ===========================================================================

class SyntheticBoard:
    """A modelled ADS1299 that answers register reads and streams samples."""

    def __init__(self, *, board_gain: int = config.PGA_GAIN,
                 synth_cfg: Optional[synth.SynthConfig] = None,
                 condition: str = "10k"):
        if board_gain not in config.VALID_GAINS:
            raise ValueError(f"synthetic board gain {board_gain} is not legal")
        self.board_gain = board_gain
        self.cfg = synth_cfg or synth.SynthConfig()
        self.source = synth.SyntheticSource(self.cfg)
        self.condition = condition
        self.mux = "normal"
        self.bias_on = False
        self._scenario: Optional[Callable[[float], np.ndarray]] = None

    # -- interface ----------------------------------------------------------

    def describe(self) -> dict:
        return {
            "kind": "synthetic",
            "detail": (f"modelled ADS1299 at gain {self.board_gain}, "
                       f"fixture={self.condition}, bias={'on' if self.bias_on else 'off'}"),
            "board_gain": self.board_gain,
            "fs_hz": self.cfg.fs_hz,
            "n_channels": self.cfg.n_channels,
        }

    def read_channel_registers(self) -> dict[int, int]:
        code = config.GAIN_CODES[self.board_gain]
        reg = (code << config.CHNSET_GAIN_SHIFT) | config.MUX_CODES[self.mux]
        return {ch: reg for ch in range(self.cfg.n_channels)}

    def read_named_registers(self) -> dict[str, int]:
        cfg3 = 0b11100000 | (config.CONFIG3_PD_BIAS_BIT if self.bias_on else 0)
        return {"ID": 0x3E, "CONFIG1": 0x96, "CONFIG2": 0xC0, "CONFIG3": cfg3}

    def set_mux(self, mux: str) -> None:
        if mux not in config.MUX_CODES:
            raise ValueError(f"unknown mux {mux!r}")
        self.mux = mux

    def set_bias(self, enabled: bool) -> None:
        self.bias_on = bool(enabled)

    def set_scenario(self, fn: Optional[Callable[[float], np.ndarray]]) -> None:
        """Override what the next acquisitions contain (volts, (n, ch))."""
        self._scenario = fn

    def acquire(self, seconds: float) -> np.ndarray:
        if self._scenario is not None:
            volts = self._scenario(seconds)
        elif self.mux == "test":
            volts = self.source.test_signal(seconds)
        elif self.mux == "shorted":
            volts = self.source.noise_floor(seconds, condition="short",
                                            bias_on=self.bias_on)
        else:
            volts = self.source.noise_floor(seconds, condition=self.condition,
                                            bias_on=self.bias_on)
        return self.volts_to_counts(volts)

    def volts_to_counts(self, volts: np.ndarray) -> np.ndarray:
        """Quantise using the BOARD's gain, not the host's.

        This is the whole mechanism of the mismatch test: the board encodes
        with its own scale factor and the host decodes with config.PGA_GAIN.
        If they differ, every voltage comes out wrong by the ratio -- exactly
        as it would on the bench.
        """
        lsb = config.lsb_volts(self.board_gain)
        counts = np.round(np.asarray(volts) / lsb)
        fs = config.ADC_FULL_SCALE_COUNTS
        n_clipped = int(np.count_nonzero(np.abs(counts) > fs))
        if n_clipped:
            print(f"[synthetic] WARNING: {n_clipped} samples clipped at full "
                  f"scale ({config.full_scale_input_volts(self.board_gain) * 1e3:.1f} mV "
                  f"at gain {self.board_gain}). Reduce the drive amplitude.",
                  file=sys.stderr)
        return np.clip(counts, -fs - 1, fs).astype(np.int32)

    def close(self) -> None:
        pass


# ===========================================================================
# The real board
# ===========================================================================

_CHNSET_RE = re.compile(r"\bCH(\d)SET\b", re.IGNORECASE)
_NAMED_RE = re.compile(r"\b(ID|CONFIG[1-4]|LOFF|BIAS_SENSP|BIAS_SENSN|"
                       r"LOFF_SENSP|LOFF_SENSN|LOFF_FLIP|GPIO|MISC[12])\b",
                       re.IGNORECASE)
_BIN8_RE = re.compile(r"\b([01]{8})\b")
_HEX0X_RE = re.compile(r"\b0[xX]([0-9A-Fa-f]{1,2})\b")
_HEX2_RE = re.compile(r"\b([0-9A-Fa-f]{2})\b")


def parse_register_dump(text: str) -> dict[int, int]:
    """Extract CHnSET bytes from a firmware register dump.

    Tolerant by design, because firmware dialects vary and a rigid parser here
    turns into 'the guard could not read the gain' on the one day it matters.
    Recognises, per line::

        CH1SET, 05, 60, 01100000      (OpenBCI-style: address, value, bits)
        CH1SET = 0x60
        CH1SET: 96

    Preference order is binary field, then 0x-prefixed hex, then the last bare
    two-digit hex token on the line -- the bare-hex case is last because a
    dump that prints the register address alongside the value is ambiguous,
    and the value is conventionally printed after the address.
    """
    out: dict[int, int] = {}
    for line in text.splitlines():
        m = _CHNSET_RE.search(line)
        if not m:
            continue
        ch = int(m.group(1)) - 1
        rest = line[m.end():]
        b = _BIN8_RE.search(rest)
        if b:
            out[ch] = int(b.group(1), 2)
            continue
        h = _HEX0X_RE.search(rest)
        if h:
            out[ch] = int(h.group(1), 16)
            continue
        bare = _HEX2_RE.findall(rest)
        if bare:
            out[ch] = int(bare[-1], 16)
    return out


def _value_on_line(rest: str):
    b = _BIN8_RE.search(rest)
    if b:
        return int(b.group(1), 2)
    h = _HEX0X_RE.search(rest)
    if h:
        return int(h.group(1), 16)
    bare = _HEX2_RE.findall(rest)
    return int(bare[-1], 16) if bare else None


def parse_named_registers(text: str) -> dict[str, int]:
    """Extract the non-channel registers (CONFIG1..4, LOFF, ...) from a dump.

    04_bias_on_off.py uses this to CONFIRM that a bias toggle actually landed,
    rather than trusting that the person at the keyboard did what the prompt
    asked. A write you did not read back is a hope, not a configuration.
    """
    out: dict[str, int] = {}
    for line in text.splitlines():
        m = _NAMED_RE.search(line)
        if not m:
            continue
        val = _value_on_line(line[m.end():])
        if val is not None:
            out[m.group(1).upper()] = val
    return out


class SerialBoard:
    """USB-serial link to the Cerelog ESP-EEG.

    NOT TESTED AGAINST HARDWARE -- the board arrives 2026-08-06. The dialect
    below is the OpenBCI Cyton command set, which ESP32 EEG firmwares in this
    lineage commonly speak. ``parse_register_dump`` IS tested, against canned
    dumps in ``selftest.py``.

    If the firmware turns out to speak something else, there are exactly three
    things to change and they are all in this class: ``_CMD_*``, the framing in
    ``_read_frames``, and nothing else. Do not scatter protocol knowledge into
    the analysis scripts.
    """

    _CMD_REGISTER_DUMP = b"?"
    _CMD_STREAM_START = b"b"
    _CMD_STREAM_STOP = b"s"
    _CMD_RESET = b"v"

    # 33-byte OpenBCI binary frame: 0xA0, sample#, 8 x 3-byte big-endian
    # signed sample, 6 aux bytes, stop byte 0xC0..0xCF.
    _FRAME_START = 0xA0
    _FRAME_LEN = 33

    def __init__(self, port: str, *, baud: int = config.SERIAL_BAUD,
                 fs_hz: float = config.FS_HZ,
                 n_channels: int = config.N_CHANNELS,
                 timeout_s: float = config.SERIAL_TIMEOUT_S):
        try:
            import serial  # noqa: PLC0415  -- optional dependency
        except ImportError as exc:
            raise RuntimeError(
                "pyserial is not installed, so hardware mode is unavailable.\n"
                "  pip install pyserial\n"
                "Synthetic mode (--synthetic) needs no serial support and is "
                "how every analysis path in this suite was verified."
            ) from exc
        self._serial = serial
        self.port = port
        self.fs_hz = fs_hz
        self.n_channels = n_channels
        self.ser = serial.Serial(port, baud, timeout=timeout_s)
        time.sleep(2.0)  # ESP32 boards reset on port open
        self.ser.reset_input_buffer()

    def describe(self) -> dict:
        return {"kind": "serial", "detail": f"{self.port} @ {self.ser.baudrate} baud",
                "fs_hz": self.fs_hz, "n_channels": self.n_channels}

    # -- registers ----------------------------------------------------------

    def _command(self, cmd: bytes, settle_s: float = 0.4) -> str:
        self.ser.reset_input_buffer()
        self.ser.write(cmd)
        self.ser.flush()
        time.sleep(settle_s)
        chunks = []
        deadline = time.time() + config.SERIAL_TIMEOUT_S
        while time.time() < deadline:
            data = self.ser.read(self.ser.in_waiting or 1)
            if not data:
                break
            chunks.append(data)
            time.sleep(0.05)
        return b"".join(chunks).decode("ascii", errors="replace")

    last_register_dump: str = ""

    def _dump(self) -> str:
        self._command(self._CMD_STREAM_STOP, settle_s=0.3)
        self.last_register_dump = self._command(self._CMD_REGISTER_DUMP,
                                                settle_s=0.8)
        return self.last_register_dump

    def read_channel_registers(self) -> dict[int, int]:
        return parse_register_dump(self._dump())

    def read_named_registers(self) -> dict[str, int]:
        return parse_named_registers(self._dump())

    def set_mux(self, mux: str) -> None:
        raise NotImplementedError(
            "Setting the input MUX over serial is firmware-specific and is not "
            "implemented, because guessing it and being wrong is worse than "
            "not having it. Set the MUX from the firmware's own console, then "
            "re-run -- 00_gain_check.py --dump-registers will confirm the MUX "
            "field actually changed before you record anything.")

    def set_bias(self, enabled: bool) -> None:
        raise NotImplementedError(
            "Toggling BIAS over serial is firmware-specific and is not "
            "implemented. Use 04_bias_on_off.py --manual, which prompts you to "
            "change it and then RE-READS CONFIG3 to confirm the change took "
            "effect before recording. Never assume a write landed.")

    # -- streaming ----------------------------------------------------------

    def acquire(self, seconds: float) -> np.ndarray:
        n_want = int(round(seconds * self.fs_hz))
        self.ser.reset_input_buffer()
        self.ser.write(self._CMD_STREAM_START)
        self.ser.flush()
        try:
            frames = self._read_frames(n_want, seconds * 1.5 + 5.0)
        finally:
            self.ser.write(self._CMD_STREAM_STOP)
            self.ser.flush()
        if len(frames) < n_want * 0.9:
            raise RuntimeError(
                f"Acquisition came up short: wanted {n_want} samples, got "
                f"{len(frames)} in {seconds * 1.5 + 5.0:.0f} s.\n"
                "Do not analyse this -- a partial capture with dropped frames "
                "corrupts every spectral estimate in the suite.\n"
                "Check: is the sample rate really "
                f"{self.fs_hz:g} SPS? Is the USB link keeping up at "
                f"{self.ser.baudrate} baud? Is another process reading the port?")
        return np.array(frames[:n_want], dtype=np.int32)

    def _read_frames(self, n_want: int, timeout_s: float) -> list[list[int]]:
        buf = bytearray()
        frames: list[list[int]] = []
        deadline = time.time() + timeout_s
        while len(frames) < n_want and time.time() < deadline:
            buf.extend(self.ser.read(max(self.ser.in_waiting, 1)))
            while True:
                start = buf.find(self._FRAME_START)
                if start < 0 or len(buf) - start < self._FRAME_LEN:
                    if start > 0:
                        del buf[:start]
                    break
                frame = bytes(buf[start:start + self._FRAME_LEN])
                del buf[:start + self._FRAME_LEN]
                if not (0xC0 <= frame[-1] <= 0xCF):
                    continue  # not a real frame boundary, resync
                samples = []
                for ch in range(self.n_channels):
                    o = 2 + 3 * ch
                    raw = (frame[o] << 16) | (frame[o + 1] << 8) | frame[o + 2]
                    if raw & 0x800000:
                        raw -= 1 << 24
                    samples.append(raw)
                frames.append(samples)
        return frames

    def close(self) -> None:
        try:
            self.ser.write(self._CMD_STREAM_STOP)
            self.ser.close()
        except Exception:
            pass


# ===========================================================================
# Shared CLI
# ===========================================================================

def add_common_args(parser) -> None:
    g = parser.add_argument_group("acquisition")
    g.add_argument("--synthetic", action="store_true",
                   help="run with no hardware attached, against the modelled "
                        "front end in synth.py (first-class mode: every "
                        "analysis path is verified this way)")
    g.add_argument("--port", default=None,
                   help="serial port of the Cerelog board (hardware mode)")
    g.add_argument("--fs", type=float, default=config.FS_HZ,
                   help=f"sample rate, SPS (default {config.FS_HZ:g})")
    g.add_argument("--mains", type=float, default=config.MAINS_HZ,
                   choices=(50.0, 60.0),
                   help=f"mains frequency (default {config.MAINS_HZ:g}, SF)")
    g.add_argument("--channels", type=int, default=config.N_CHANNELS,
                   help="number of channels to record")
    g.add_argument("--out-dir", type=Path, default=config.OUT_DIR,
                   help="where artifacts are written")
    g.add_argument("--theme", default="both", choices=("light", "dark", "both"),
                   help="figure theme to render (default both)")

    s = parser.add_argument_group("synthetic model")
    s.add_argument("--seed", type=int, default=20260806,
                   help="RNG seed, so synthetic runs are reproducible")
    s.add_argument("--synthetic-board-gain", type=int, default=None,
                   choices=config.VALID_GAINS,
                   help="gain the SIMULATED board reports. Defaults to "
                        "config.PGA_GAIN. Set it to something else to prove "
                        "the gain guard actually fires -- that is a test, not "
                        "a workaround.")

    v = parser.add_argument_group("gain verification")
    v.add_argument("--unverified", metavar="REASON", default=None,
                   help="proceed without proving the gain against hardware. "
                        "Requires a written reason, which is stamped into "
                        "every output file and printed on every figure.")


def resolve_synth_config(args) -> synth.SynthConfig:
    cfg = synth.SynthConfig(fs_hz=args.fs, n_channels=args.channels,
                            seed=args.seed)
    cfg.mains.f0_hz = args.mains
    return cfg


def open_board(args, *, condition: str = "10k"):
    """Open the link the CLI asked for, and verify the gain before returning.

    No script in this suite gets a board object that has not been through the
    guard. That is enforced here rather than left to each script to remember.
    """
    import gainguard

    if args.synthetic:
        board_gain = args.synthetic_board_gain or config.PGA_GAIN
        board = SyntheticBoard(board_gain=board_gain,
                               synth_cfg=resolve_synth_config(args),
                               condition=condition)
    else:
        if not args.port:
            raise SystemExit(
                "No --port given and --synthetic not set.\n"
                "  Hardware:  --port /dev/tty.usbserial-XXXX\n"
                "  No board:  --synthetic\n"
                "There is no default port. Guessing one and recording from "
                "the wrong device is a failure mode worth an extra flag.")
        board = SerialBoard(args.port, fs_hz=args.fs, n_channels=args.channels)

    if args.unverified:
        gainguard.mark_unverified(args.unverified)
    else:
        gainguard.verify_gain(board)
    return board


def print_header(title: str, args) -> None:
    mode = "SYNTHETIC (no hardware)" if args.synthetic else f"HARDWARE {args.port}"
    print(f"\n{'-' * 74}\n{title}\n  mode {mode}   fs {args.fs:g} SPS   "
          f"mains {args.mains:g} Hz\n{'-' * 74}", flush=True)
