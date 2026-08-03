#!/usr/bin/env python3
"""03 -- CMRR against frequency, driven by the AD3 through a precision divider.

===========================================================================
 THE PROTOCOL
===========================================================================

CMRR is a ratio of two amplitudes measured on the same instrument, so it needs
two passes at every frequency:

  PASS 1, DIFFERENTIAL.  The AD3 drives the 1k/100R/20R chain; the board's
  IN+/IN- sit across the 20 ohm bottom leg (tap "low", 1/56). 1 V peak at the
  generator becomes 17.9 mV at the board -- small enough not to rail at gain 8
  (full scale is +/-562 mV) and large enough to sit far above the noise.

  This pass exists because you cannot measure a ratio with an uncalibrated
  denominator. It also doubles as a frequency-response measurement and as an
  independent check on the voltage scale: after counts_to_volts, a correctly
  scaled system reports exactly the voltage that was applied, so the
  differential gain error should sit at 0 dB across the band. A FLAT OFFSET
  HERE IS A GAIN ERROR, and 20*log10(3) = 9.54 dB is what a gain-24 board
  read as gain 8 looks like.

  PASS 2, COMMON MODE.  IN+ and IN- are tied together and driven with the
  generator directly, referenced to the board's ground. Whatever appears
  differentially is leakage. CMRR = 20*log10(V_common / V_differential).

WHY A DIVIDER AT ALL. The AD3's smallest useful output is in the millivolt
range and its own noise sets a floor well above that. EEG-scale differential
signals are microvolts. The divider gets a clean, well-defined microvolt-scale
signal out of a generator that cannot produce one directly, and 0.1% parts
keep the ratio known to about 0.13% (1 sigma) -- 0.011 dB, negligible against
the numbers this sweep produces. Note that 0.1% RESISTORS do not give a 0.1%
RATIO: the 1 k part's tolerance is 1 ohm against a 1120 ohm chain and it
dominates. The script computes and prints the propagated figure at startup
rather than repeating this one.

MEASURE, DO NOT ASSUME, THE INPUT AMPLITUDE. Pass --ad3-amplitude the value
you read on the AD3 scope at the TOP of the divider, not the number on the
generator dial. The generator's output impedance in series with a 1120 ohm
chain is a real error of order 1%, and it drops out entirely if you measure.

===========================================================================
 THE MEASUREMENT CEILING
===========================================================================

You cannot measure a rejection deeper than your own noise floor. With a
coherent fit over T seconds, the amplitude estimate has a standard error of
about ASD/sqrt(T), so the smallest credible differential signal is roughly
3*ASD/sqrt(T) and the deepest reportable CMRR is

    ceiling_dB = 20*log10(V_common / (3 * ASD / sqrt(T)))

This script computes that ceiling at every frequency, plots it, and flags any
point sitting within 6 dB of it. A point at the ceiling is not a measurement
of the board -- it is a measurement of how long you recorded for. Raise the
common-mode drive or lengthen the capture; do not report the number.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np

import ad3
import artifacts
import board as boardmod
import config
import dsp
import gainguard
import vizstyle

CEILING_MARGIN_DB = 6.0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="CMRR against frequency via AD3 and a precision divider.",
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    boardmod.add_common_args(p)
    ad3.add_ad3_args(p)
    p.add_argument("--freqs", type=float, nargs="+", default=None,
                   help=f"sweep frequencies (default {config.CMRR_FREQS_HZ})")
    p.add_argument("--seconds-per-point", type=float,
                   default=config.CMRR_SECONDS_PER_POINT)
    p.add_argument("--cm-amplitude", type=float,
                   default=config.CMRR_CM_AMPLITUDE_V,
                   help="common-mode drive, volts peak (default "
                        f"{config.CMRR_CM_AMPLITUDE_V} -- start small, the "
                        "input common-mode range is narrow at high gain)")
    p.add_argument("--bias", action="store_true",
                   help="run with BIAS drive enabled (04 does both and "
                        "compares them)")
    p.add_argument("--tag", default="03_cmrr",
                   help="artifact name (04 uses this to store two sweeps)")
    return p


# ---------------------------------------------------------------------------

def sweep(brd, gen, args, mode: str, amplitude_at_input_v: float,
          generator_amplitude_v: float) -> list[dict]:
    """One pass over every frequency. Returns per-frequency rows."""
    rows = []
    freqs = args.freqs or list(config.CMRR_FREQS_HZ)
    nyq = 0.5 * args.fs
    for f0 in freqs:
        if f0 >= 0.45 * args.fs:
            print(f"  skipping {f0:g} Hz -- too close to Nyquist "
                  f"({nyq:g} Hz); aliasing would make the amplitude "
                  "meaningless", file=sys.stderr)
            continue
        gen.set_output(f0, generator_amplitude_v, note=mode)
        if args.synthetic:
            src = brd.source
            brd.set_scenario(lambda s, f=f0: src.tone(
                s, f, amplitude_at_input_v, mode, bias_on=args.bias))
        counts = brd.acquire(args.seconds_per_point)
        volts = gainguard.counts_to_volts(counts)

        amps, f_used = dsp.tone_amplitude_multichannel(volts, args.fs, f0)
        fx, pxx = dsp.welch_psd(volts, args.fs,
                                nperseg=min(1024, counts.shape[0]))
        _, floor_asd = dsp.tone_rms_from_psd(fx, np.median(pxx, axis=1), f0)
        sigma_a = floor_asd / math.sqrt(max(args.seconds_per_point, 1e-9))
        rows.append({
            "frequency_hz": f0,
            "frequency_fitted_hz": f_used,
            "applied_v": amplitude_at_input_v,
            "amplitudes_v": amps.tolist(),
            "median_amplitude_v": float(np.median(amps)),
            "noise_sigma_v": float(sigma_a),
            "detection_floor_v": float(3.0 * sigma_a),
        })
        print(f"    {f0:7.2f} Hz  {mode:<12s} "
              f"median {np.median(amps) * 1e6:11.4f} uV   "
              f"floor {3 * sigma_a * 1e6:8.4f} uV")
    return rows


def combine(diff_rows: list[dict], cm_rows: list[dict], cm_amplitude: float
            ) -> list[dict]:
    by_f = {r["frequency_hz"]: r for r in diff_rows}
    out = []
    for cm in cm_rows:
        f0 = cm["frequency_hz"]
        d = by_f.get(f0)
        amps = np.asarray(cm["amplitudes_v"])
        cmrr = dsp.cmrr_db(cm_amplitude, amps)
        ceiling = float(dsp.cmrr_db(cm_amplitude, cm["detection_floor_v"]))
        med = float(np.nanmedian(cmrr))
        row = {
            "frequency_hz": f0,
            "cmrr_median_db": med,
            "cmrr_min_db": float(np.nanmin(cmrr)),
            "cmrr_max_db": float(np.nanmax(cmrr)),
            "cmrr_per_channel_db": cmrr.tolist(),
            "measurement_ceiling_db": ceiling,
            "at_measurement_ceiling": bool(med > ceiling - CEILING_MARGIN_DB),
            "cm_amplitude_v": cm_amplitude,
        }
        if d is not None:
            row["differential_applied_v"] = d["applied_v"]
            row["differential_measured_v"] = d["median_amplitude_v"]
            row["differential_gain_error_db"] = float(
                dsp.differential_gain_error_db(d["median_amplitude_v"],
                                               d["applied_v"]))
        out.append(row)
    return out


def check_gain_from_sweep(rows: list[dict]) -> tuple[float, str]:
    """The differential pass is a second, independent gain check. Use it."""
    errs = [r["differential_gain_error_db"] for r in rows
            if "differential_gain_error_db" in r and np.isfinite(
                r["differential_gain_error_db"])]
    if not errs:
        return float("nan"), "no differential pass to check against"
    med = float(np.median(errs))
    if abs(med) < 1.0:
        return med, "flat within 1 dB -- the voltage scale is consistent"
    ratio = 10 ** (med / 20.0)
    implied = config.PGA_GAIN * ratio
    nearest = min(config.VALID_GAINS, key=lambda g: abs(math.log(g / implied)))
    return med, (
        f"differential gain is offset by {med:+.2f} dB ({ratio:.3f}x). "
        f"That is what running at gain {nearest} while scaling as gain "
        f"{config.PGA_GAIN} looks like. Re-run 00_gain_check.py before "
        "believing any CMRR number here.")


# ---------------------------------------------------------------------------

def figure(t: vizstyle.Theme, rows: list[dict], meta: dict):
    import matplotlib.pyplot as plt

    fig, (ax0, ax1) = plt.subplots(2, 1, figsize=(7.6, 7.2),
                                   height_ratios=(1.4, 1.0), sharex=True)
    f = np.array([r["frequency_hz"] for r in rows])
    per_ch = np.array([r["cmrr_per_channel_db"] for r in rows])
    med = np.array([r["cmrr_median_db"] for r in rows])
    ceil = np.array([r["measurement_ceiling_db"] for r in rows])

    for ch in range(per_ch.shape[1]):
        ax0.semilogx(f, per_ch[:, ch], color=t.deemphasis, linewidth=0.9,
                     alpha=0.8, zorder=2)
    ax0.semilogx(f, med, color=t.color(0), linewidth=vizstyle.LINE_W, zorder=4)
    ax0.semilogx(f, ceil, color=t.serious, linewidth=vizstyle.HAIRLINE_W * 1.6,
                 zorder=3)
    vizstyle.dot(ax0, f[-1], med[-1], t, t.color(0))
    vizstyle.end_label(ax0, f[-1], med[-1], f"{med[-1]:.0f} dB", t)

    limited = [i for i, r in enumerate(rows) if r["at_measurement_ceiling"]]
    for i in limited:
        ax0.annotate("at ceiling", xy=(f[i], med[i]), xytext=(0, -14),
                     textcoords="offset points", ha="center", fontsize=7.5,
                     color=t.serious)

    # Mark both mains frequencies when the sweep covers them: the same figure
    # is valid in either region and it is worth being able to read off both.
    marks = [x for x in (50.0, 60.0) if f.min() <= x <= f.max()]
    vizstyle.vertical_marks(ax0, marks, t,
                            labels=[f"{x:.0f} Hz" for x in marks],
                            y_frac=0.02, va="bottom")
    ax0.set_xlim(right=float(f[-1]) * 1.30)   # room for the end label
    ax0.set_ylabel("CMRR (dB)")
    vizstyle.title_block(
        ax0, "Common-mode rejection against frequency",
        f"common-mode drive {meta.get('cm_amplitude_v', 0) * 1e3:.0f} mV peak, "
        f"{meta.get('seconds_per_point', 0):g} s per point")
    vizstyle.legend(ax0, t, handles=[
        vizstyle.key_handle("per channel", t.deemphasis),
        vizstyle.key_handle("median", t.color(0)),
        vizstyle.key_handle("measurement ceiling", t.serious)],
        loc="lower left")

    err = np.array([r.get("differential_gain_error_db", np.nan) for r in rows])
    ax1.semilogx(f, err, color=t.color(0), linewidth=vizstyle.LINE_W, zorder=4)
    vizstyle.dot(ax1, f[-1], err[-1], t, t.color(0))
    vizstyle.reference_line(ax1, 0.0, "0 dB = scale factor is correct", t,
                            x=0.02, ha="left", va="top")
    span = max(1.2, float(np.nanmax(np.abs(err))) * 1.6) if np.isfinite(
        err).any() else 1.2
    ax1.set_ylim(-span, span)
    ax1.set_xlabel("frequency (Hz)")
    ax1.set_ylabel("differential gain error (dB)")
    vizstyle.title_block(
        ax1, "Differential path, same sweep",
        "a flat offset is a voltage-scale error; +9.54 dB is gain 24 read as "
        "gain 8")

    vizstyle.stamp(fig, meta, t)
    return fig


# ---------------------------------------------------------------------------

def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    artifacts.ensure_out(args.out_dir)
    boardmod.print_header("03  CMRR SWEEP", args)

    ratio = config.divider_ratio(tap=args.divider_tap)
    unc = config.divider_ratio_uncertainty(tap=args.divider_tap)
    applied_diff = args.ad3_amplitude * ratio
    print(f"  divider        1/{1 / ratio:.4f} at tap '{args.divider_tap}' "
          f"(+/-{unc * 100:.3f}%)")
    print(f"  differential   {args.ad3_amplitude:g} V peak in -> "
          f"{applied_diff * 1e6:.1f} uV peak at the board")
    print(f"  common mode    {args.cm_amplitude * 1e3:g} mV peak")
    fs_limit = config.full_scale_input_volts(config.PGA_GAIN)
    if applied_diff > 0.5 * fs_limit:
        print(f"\n  REFUSING: {applied_diff * 1e3:.1f} mV differential is more "
              f"than half of full scale ({fs_limit * 1e3:.0f} mV at gain "
              f"{config.PGA_GAIN}). Lower --ad3-amplitude or use the 'low' "
              "tap; a clipped sine reports a gain error that is not there.",
              file=sys.stderr)
        return 2

    brd = boardmod.open_board(args)
    gen = ad3.open_generator(args.ad3, args.synthetic)
    try:
        if args.bias and hasattr(brd, "set_bias"):
            brd.set_bias(True)

        if not args.synthetic:
            input("\n  PASS 1 of 2, DIFFERENTIAL.\n"
                  f"  Wire IN+/IN- across the {args.divider_tap} divider tap, "
                  "each through its 10 k series resistor.\n"
                  "  Press Enter to start the sweep: ")
        print("\n  pass 1: differential")
        diff_rows = sweep(brd, gen, args, "differential", applied_diff,
                          args.ad3_amplitude)

        if not args.synthetic:
            input("\n  PASS 2 of 2, COMMON MODE.\n"
                  "  Tie IN+ and IN- together (still through their 10 k "
                  "resistors) and drive that node from the generator, "
                  "referenced to board ground.\n"
                  "  Press Enter to start the sweep: ")
        print("\n  pass 2: common mode")
        cm_rows = sweep(brd, gen, args, "common", args.cm_amplitude,
                        args.cm_amplitude)

        rows = combine(diff_rows, cm_rows, args.cm_amplitude)
        gain_err, gain_note = check_gain_from_sweep(rows)

        print("\n   freq       CMRR (median)   spread    ceiling   diff error")
        for r in rows:
            flag = "  <-- AT CEILING" if r["at_measurement_ceiling"] else ""
            print(f"   {r['frequency_hz']:7.2f} Hz  {r['cmrr_median_db']:8.1f} dB  "
                  f"{r['cmrr_max_db'] - r['cmrr_min_db']:6.1f} dB  "
                  f"{r['measurement_ceiling_db']:8.1f} dB  "
                  f"{r.get('differential_gain_error_db', float('nan')):+7.2f} dB{flag}")
        at_mains = [r for r in rows if abs(r["frequency_hz"] - args.mains) < 1e-6]
        if at_mains:
            print(f"\n  CMRR at {args.mains:g} Hz: "
                  f"{at_mains[0]['cmrr_median_db']:.1f} dB")
        print(f"\n  differential gain error: {gain_err:+.2f} dB -- {gain_note}")

        meta = boardmod.base_meta(args.tag, args, {
            "divider_tap": args.divider_tap,
            "divider_ratio": ratio,
            "divider_ratio_uncertainty": unc,
            "generator": gen.describe(),
            "generator_amplitude_v": args.ad3_amplitude,
            "differential_applied_v": applied_diff,
            "cm_amplitude_v": args.cm_amplitude,
            "seconds_per_point": args.seconds_per_point,
            "bias_on": bool(args.bias),
            "rows": rows,
            "differential_gain_error_db": gain_err,
            "differential_gain_note": gain_note,
            "points_at_ceiling": [r["frequency_hz"] for r in rows
                                  if r["at_measurement_ceiling"]],
        })
        artifacts.write_json(args.out_dir, args.tag, meta)
        artifacts.write_csv(args.out_dir, args.tag, [
            {"frequency_hz": r["frequency_hz"],
             "cmrr_median_db": round(r["cmrr_median_db"], 2),
             "cmrr_min_db": round(r["cmrr_min_db"], 2),
             "cmrr_max_db": round(r["cmrr_max_db"], 2),
             "measurement_ceiling_db": round(r["measurement_ceiling_db"], 2),
             "at_measurement_ceiling": r["at_measurement_ceiling"],
             "differential_gain_error_db":
                 round(r.get("differential_gain_error_db", float("nan")), 3)}
            for r in rows])

        paths = vizstyle.render(
            lambda t: figure(t, rows, meta),
            artifacts.fig_stem(args.out_dir, args.tag),
            vizstyle.resolve_themes(args.theme))
        vizstyle.log_written(paths)
        return 0
    finally:
        gen.off() if hasattr(gen, "off") else None
        if hasattr(gen, "close"):
            gen.close()
        brd.close()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except gainguard.GainMismatch as exc:
        print(f"\n{'=' * 74}\n{exc}\n{'=' * 74}\n", file=sys.stderr)
        sys.exit(1)
