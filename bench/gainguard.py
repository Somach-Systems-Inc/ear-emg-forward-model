"""The gain guard.

This module exists to make one specific mistake impossible: recording EEG at
PGA gain 8 while the host scales counts as though the gain were 24, producing
voltages that are wrong by exactly 3.000x and look completely plausible.

Three mechanisms, in increasing order of strength:

1. **Register check** -- read CHnSET from the ADS1299, decode bits [6:4], and
   compare against ``config.PGA_GAIN``. Catches a stale edit in config.py or a
   board that was reflashed and forgotten.

2. **Physical check** -- drive a known amplitude in (the chip's own internal
   test signal needs no external hardware; the AD3 through the precision
   divider is the external version) and confirm the recovered amplitude
   matches. Catches everything the register check does *plus* a firmware that
   reports a gain it did not actually program, a wrong VREF, and a host
   scale factor that is wrong for some reason other than gain.

3. **The latch** -- ``counts_to_volts()`` raises unless one of the above has
   run in this process. There is no path from ADC counts to a voltage in this
   suite that skips the check. That is the point: a guard you can forget to
   call is not a guard.

The override path is deliberately ugly. ``mark_unverified()`` lets you proceed
without a board that can report its registers, but it stamps
``gain_verified: false`` into every metadata file and puts a banner across
every figure. The doubt propagates into the artifact instead of evaporating.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field, asdict
from typing import Optional

import numpy as np

import config


class GainMismatch(RuntimeError):
    """Host gain constant disagrees with the hardware. Fatal."""


class GainNotVerified(RuntimeError):
    """Someone tried to convert counts to volts before proving the scale."""


@dataclass
class GainVerdict:
    host_gain: int
    board_gain: Optional[int]
    verified: bool
    method: str
    detail: str = ""
    lsb_volts: float = field(init=False)

    def __post_init__(self) -> None:
        self.lsb_volts = config.lsb_volts(self.host_gain)

    def as_meta(self) -> dict:
        d = asdict(self)
        d["unverified_reason"] = "" if self.verified else self.detail
        return d


# --- the latch -------------------------------------------------------------

_VERDICT: Optional[GainVerdict] = None


def current_verdict() -> GainVerdict:
    if _VERDICT is None:
        raise GainNotVerified(
            "counts_to_volts() called before the gain was checked.\n"
            "Call gainguard.verify_gain(board) at the top of the run, or "
            "gainguard.mark_unverified(reason) if you are knowingly working "
            "without a board that can report its registers.\n"
            "This is not a formality: the conversion factor depends entirely "
            "on the gain, so an unverified conversion is an unverified voltage."
        )
    return _VERDICT


def reset() -> None:
    """Clear the latch. For tests only."""
    global _VERDICT
    _VERDICT = None


def counts_to_volts(counts: np.ndarray) -> np.ndarray:
    """ADC counts -> input-referred volts. The only conversion in the suite."""
    return np.asarray(counts, dtype=np.float64) * current_verdict().lsb_volts


def volts_to_counts(volts: np.ndarray) -> np.ndarray:
    return np.asarray(volts, dtype=np.float64) / current_verdict().lsb_volts


# --- 1. the register check -------------------------------------------------

def verify_gain(board, *, host_gain: int = config.PGA_GAIN) -> GainVerdict:
    """Read the gain out of the hardware and refuse to continue on mismatch.

    ``board`` is anything with ``read_channel_registers() -> dict[int, int]``
    mapping channel index to CHnSET byte, and ``describe() -> dict``.
    """
    global _VERDICT

    if host_gain not in config.VALID_GAINS:
        _die(f"config.PGA_GAIN = {host_gain} is not a legal ADS1299 gain.\n"
             f"Legal values: {', '.join(map(str, config.VALID_GAINS))}.")

    regs = board.read_channel_registers()
    if not regs:
        raise GainMismatch(_no_registers_report(board, host_gain))

    gains = {}
    for ch, reg in sorted(regs.items()):
        try:
            gains[ch] = config.gain_from_chnset(reg)
        except ValueError as exc:
            raise GainMismatch(
                _report(host_gain, None,
                        f"CH{ch + 1}SET = 0x{reg:02X} does not decode: {exc}")
            ) from exc

    distinct = sorted(set(gains.values()))
    if len(distinct) > 1:
        detail = ", ".join(f"CH{c + 1}={g}" for c, g in sorted(gains.items()))
        raise GainMismatch(_mixed_gain_report(host_gain, detail))

    board_gain = distinct[0]
    if board_gain != host_gain:
        raise GainMismatch(_report(host_gain, board_gain,
                                   "register read of every enabled channel"))

    _VERDICT = GainVerdict(
        host_gain=host_gain, board_gain=board_gain, verified=True,
        method="chnset-register-read",
        detail=f"{len(gains)} channels all report gain {board_gain}")
    _announce(_VERDICT, board)
    return _VERDICT


def inherit(meta: dict, *, host_gain: int = config.PGA_GAIN,
            origin: str = "saved recording") -> GainVerdict:
    """Adopt the gain verdict stored with a saved recording.

    Re-analysing an old capture is legitimate; re-analysing it under a
    DIFFERENT gain constant is not, because the counts on disk were only ever
    meaningful alongside the gain they were captured with. That is the whole
    reason recordings store counts and metadata rather than volts.
    """
    global _VERDICT
    recorded = meta.get("host_pga_gain")
    if recorded != host_gain:
        raise GainMismatch(
            "RECORDING WAS CAPTURED AT A DIFFERENT GAIN -- REFUSING\n\n"
            f"  {origin} captured with host gain {recorded}\n"
            f"  config.PGA_GAIN is now {host_gain}\n\n"
            "Either analyse it with the constant it was captured under, or "
            "accept that the numbers change by "
            f"{(recorded or 1) / host_gain:.3f}x and say so explicitly.\n"
            "The counts on disk are fine. It is the interpretation that is "
            "in question, and this suite will not pick one for you."
        )
    was_verified = bool(meta.get("gain_verified", False))
    _VERDICT = GainVerdict(
        host_gain=host_gain, board_gain=meta.get("board_pga_gain"),
        verified=was_verified, method="inherited-from-recording",
        detail=(f"{origin} captured {meta.get('timestamp_utc', '?')}, "
                f"originally verified by {meta.get('gain_check_method', '?')}"
                if was_verified else
                f"{origin} was itself never gain-verified: "
                f"{meta.get('gain_check_detail', 'no reason recorded')}"))
    if was_verified:
        _announce(_VERDICT, None)
    else:
        _box("GAIN NOT VERIFIED -- inherited doubt\n"
             f"  {_VERDICT.detail}\n"
             "  Re-analysis cannot create certainty the capture did not have.",
             stream=sys.stderr)
    return _VERDICT


def mark_unverified(reason: str, *, host_gain: int = config.PGA_GAIN) -> GainVerdict:
    """Proceed without a hardware check, loudly and permanently on the record."""
    global _VERDICT
    _VERDICT = GainVerdict(host_gain=host_gain, board_gain=None, verified=False,
                           method="unverified", detail=reason)
    banner = (
        "GAIN NOT VERIFIED -- every voltage below is provisional\n"
        f"  reason        : {reason}\n"
        f"  assuming gain : {host_gain} (config.PGA_GAIN)\n"
        f"  scale factor  : {config.lsb_volts(host_gain) * 1e6:.5f} uV/count\n"
        "  Outputs are stamped gain_verified=false and figures carry a banner.\n"
        "  If a real board is attached, stop and fix the link instead."
    )
    _box(banner, stream=sys.stderr)
    return _VERDICT


# --- 2. the physical check -------------------------------------------------

def verify_gain_physically(measured_amplitude_v: float,
                           expected_amplitude_v: float,
                           *,
                           host_gain: int = config.PGA_GAIN,
                           tolerance: float = 0.10,
                           source: str = "internal test signal") -> GainVerdict:
    """Confirm the scale factor against a known injected amplitude.

    ``measured_amplitude_v`` must already have been through
    ``counts_to_volts``, i.e. it is what the host *believes* the amplitude is.
    If the host gain is wrong by a factor k, this number is wrong by k and the
    check fails with the actual gain named.

    The tolerance is 10% by default. It has to swallow the divider tolerance,
    the generator's amplitude accuracy, and any uncertainty in the datasheet's
    test-signal constant -- and it still catches the smallest possible gain
    error, 8 -> 6, which is 1.33x.
    """
    global _VERDICT

    if expected_amplitude_v <= 0:
        _die("expected_amplitude_v must be positive")

    ratio = measured_amplitude_v / expected_amplitude_v
    if abs(ratio - 1.0) <= tolerance:
        prior = _VERDICT
        _VERDICT = GainVerdict(
            host_gain=host_gain,
            board_gain=prior.board_gain if prior else host_gain,
            verified=True, method="physical-amplitude-check",
            detail=(f"{source}: measured {measured_amplitude_v * 1e6:.2f} uV vs "
                    f"expected {expected_amplitude_v * 1e6:.2f} uV "
                    f"({(ratio - 1) * 100:+.2f}%)"))
        _announce(_VERDICT, None)
        return _VERDICT

    # A recording scaled with the wrong constant reads
    #     v_reported = v_true * gain_board / gain_host
    # so the ratio measured/expected IS gain_board / gain_host, and the gain
    # actually programmed into the part is host_gain * ratio. Getting this
    # inversion backwards would send Carl to reconfigure the wrong end.
    implied = host_gain * ratio
    nearest = min(config.VALID_GAINS, key=lambda g: abs(np.log(g / implied)))
    nearest_err = abs(nearest - implied) / implied
    raise GainMismatch(_physical_report(
        host_gain, ratio, implied, nearest, nearest_err,
        measured_amplitude_v, expected_amplitude_v, source, tolerance))


# --- the reports -----------------------------------------------------------

def _box(text: str, stream=sys.stdout) -> None:
    rule = "=" * 74
    print(f"\n{rule}\n{text}\n{rule}\n", file=stream, flush=True)


def _announce(v: GainVerdict, board) -> None:
    where = ""
    if board is not None:
        d = board.describe()
        where = f"  link          : {d.get('kind', '?')} {d.get('detail', '')}\n"
    print(
        f"[gain] OK  host={v.host_gain}  board={v.board_gain}  "
        f"{v.lsb_volts * 1e6:.5f} uV/count  via {v.method}\n"
        f"{where}       {v.detail}", flush=True)


def _scale_lines(host_gain: int, board_gain: Optional[int]) -> str:
    h = config.lsb_volts(host_gain) * 1e6
    lines = [f"  host  config.PGA_GAIN = {host_gain:<3d} -> {h:.5f} uV/count"]
    if board_gain is not None:
        b = config.lsb_volts(board_gain) * 1e6
        lines.append(f"  board CHnSET gain  = {board_gain:<3d} -> {b:.5f} uV/count")
        lines.append(f"  every voltage this suite produces would be wrong by "
                     f"{board_gain / host_gain:.3f}x")
    return "\n".join(lines)


_WHAT_TO_CHECK = """\
WHAT TO CHECK, in this order:

  1. What is the board actually set to right now? Run
         python bench/00_gain_check.py --dump-registers
     and read the CHnSET line. That is ground truth; config.py is just a
     claim about it.

  2. If the BOARD is wrong: reconfigure it and re-run. The board ships at
     gain 24. If it has been power-cycled or reflashed since you last set
     gain 8, it is back at 24 and this is exactly the failure this guard
     exists for.

  3. If the HOST is wrong: edit PGA_GAIN in bench/config.py. It is the only
     place in the repo that declares a gain -- there is no flag and no
     environment variable to hunt for. Add the old value to the History
     block rather than deleting it.

  4. Do NOT "fix" this by scaling the data afterwards. Recordings are stored
     as raw ADC counts with the gain in the sidecar metadata precisely so a
     mistake here is recoverable -- re-derive volts from counts once the
     constant is right, do not multiply a saved voltage.

  5. If the board genuinely cannot report its registers, re-run with
     --unverified and a reason. The data will be usable but every figure and
     metadata file will say the gain was never proven."""


def _report(host_gain: int, board_gain: Optional[int], how: str) -> str:
    return (
        "GAIN MISMATCH -- REFUSING TO RECORD\n\n"
        f"{_scale_lines(host_gain, board_gain)}\n"
        f"  detected by   : {how}\n\n"
        f"{_WHAT_TO_CHECK}"
    )


def _mixed_gain_report(host_gain: int, detail: str) -> str:
    return (
        "CHANNELS ARE AT DIFFERENT GAINS -- REFUSING TO RECORD\n\n"
        f"  host  config.PGA_GAIN = {host_gain}\n"
        f"  board {detail}\n\n"
        "A single scale factor cannot describe this board. Either the\n"
        "configuration command only reached some channels, or channel setup\n"
        "is being done per-channel somewhere and has drifted.\n\n"
        "Set every channel to the same gain and re-run. If you genuinely want\n"
        "mixed gains, this suite is the wrong tool -- it assumes one scale\n"
        "factor for the whole board, and quietly supporting per-channel gains\n"
        "would reintroduce exactly the class of error it exists to prevent."
    )


def _no_registers_report(board, host_gain: int) -> str:
    d = board.describe() if board is not None else {}
    return (
        "BOARD REPORTED NO REGISTERS -- REFUSING TO RECORD\n\n"
        f"  link          : {d.get('kind', '?')} {d.get('detail', '')}\n"
        f"  host  config.PGA_GAIN = {host_gain} "
        f"-> {config.lsb_volts(host_gain) * 1e6:.5f} uV/count\n"
        "  board          : silent\n\n"
        "The register dump came back empty, so the gain is unknown. An\n"
        "unknown gain is not the same as the expected gain, and this suite\n"
        "will not pretend otherwise.\n\n"
        "  * Wrong port, or something else is holding it open?\n"
        "  * Is the firmware still streaming? Most firmwares ignore register\n"
        "    queries mid-stream -- stop the stream first.\n"
        "  * Does this firmware speak a different dialect? There is exactly\n"
        "    one place to teach it: SerialBoard._REGISTER_DUMP_CMD and\n"
        "    SerialBoard._parse_register_dump in bench/board.py.\n\n"
        "  * If the firmware simply cannot report registers, re-run with\n"
        "    --unverified 'firmware has no register query' AND run\n"
        "    00_gain_check.py, which proves the scale factor physically\n"
        "    from a known injected amplitude instead."
    )


def _physical_report(host_gain, ratio, implied, nearest, nearest_err,
                     measured_v, expected_v, source, tolerance) -> str:
    naming = ""
    if nearest_err < 0.08:
        naming = (f"\n  YOUR DATA IS CONSISTENT WITH GAIN {nearest}, NOT "
                  f"{host_gain}.\n"
                  f"  The board is almost certainly running at {nearest}. "
                  f"{'It ships at 24.' if nearest == 24 else ''}")
    return (
        "PHYSICAL GAIN CHECK FAILED -- REFUSING TO RECORD\n\n"
        f"  injected      : {source}\n"
        f"  expected      : {expected_v * 1e6:>12.3f} uV\n"
        f"  measured      : {measured_v * 1e6:>12.3f} uV\n"
        f"  ratio         : {ratio:>12.4f}  (tolerance +/-{tolerance * 100:.0f}%)\n"
        f"  implied gain  : {implied:>12.2f}\n"
        f"{naming}\n\n"
        f"{_scale_lines(host_gain, nearest if nearest_err < 0.08 else None)}\n\n"
        "The register read and the physics disagree, or the register read was\n"
        "skipped. Trust the physics: a known voltage went in and the wrong\n"
        "number came out.\n\n"
        f"{_WHAT_TO_CHECK}\n\n"
        "  6. If the ratio is not close to any legal gain ratio, suspect the\n"
        "     injection path instead -- divider wired to the wrong tap, the\n"
        "     generator loaded by something unexpected, or VREF set to 4.0 V\n"
        "     rather than 4.5 V in CONFIG3."
    )


def _die(msg: str) -> None:
    _box("BENCH CONFIGURATION ERROR\n\n" + msg, stream=sys.stderr)
    raise SystemExit(2)
