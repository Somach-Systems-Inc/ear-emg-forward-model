#!/usr/bin/env python3
"""01 -- input-referred noise floor with electrode-equivalent loading.

===========================================================================
 WHY 10 kOHM RESISTORS AND NOT A SHORT
===========================================================================

The obvious way to measure a front end's noise floor is to short the inputs
together. The ADS1299 will even do it for you in silicon: CHnSET MUX = 001
disconnects the pins and ties the amplifier's own inputs together. It is one
register write, it needs no parts, and the number it produces is the one the
datasheet quotes.

It is also close to useless as a prediction of what this board will do on a
head, because a short sets the source impedance to zero and three of the four
things that dominate a real recording are proportional to source impedance:

1. **Current noise has nowhere to develop a voltage.** Every amplifier input
   draws a fluctuating current i_n. Across a source impedance R that becomes a
   voltage i_n x R, in series with the signal. At R = 0 the term is exactly
   zero, so a shorted measurement reports an amplifier with no current noise
   at all -- regardless of how much it has.

2. **The source's own thermal noise is missing.** A resistor at temperature T
   generates sqrt(4kTR) V/sqrt(Hz) whether or not anything is connected to it.
   For 10 kOhm in each leg that is 18.1 nV/sqrt(Hz) differential, about
   0.13 uVrms over 0.5-50 Hz -- comparable to the ADS1299's own noise at gain
   8. A skin-electrode interface has at least this much impedance and
   therefore at least this much noise. It is a floor no front end can beat,
   and a shorted test hides it completely.

3. **Common-mode rejection stops being a system property.** CMRR at the
   system level is set by how well the two input paths match, not by the
   amplifier alone. Mains common-mode voltage divides through R+ and R- into
   the differential input; if R+ = R- exactly, nothing converts. A short makes
   the two paths identical by construction, so a shorted test measures the
   amplifier's intrinsic CMRR and tells you nothing about the CMRR you will
   get with electrodes whose impedances differ by 30%.

10 kOhm is chosen because it is what a well-prepped wet electrode actually
presents (roughly 5-20 kOhm at DC after a minute of settling), and 0.1%
because it bounds the mismatch: two 10 k 0.1% parts differ by at most 20 Ohm,
so the common-mode-to-differential conversion contributed by the FIXTURE is
0.2% at worst and cannot be mistaken for the board's own limitation.

The right protocol is not "10 k instead of a short" -- it is BOTH, plus a
deliberately mismatched pair:

    --condition short       amplifier alone. The datasheet comparison point.
    --condition 10k         electrode-equivalent. The number that predicts
                            real recordings.
    --condition imbalance   10 k against 11 k. How much of your system CMRR
                            was really impedance matching?
    --condition all         all three in one run.

The difference between the first two is your source-impedance penalty. The
difference between the second and third is your sensitivity to electrode
mismatch. Neither is visible from a single measurement, which is why a
single measurement is not the protocol.

===========================================================================

What a bad result looks like: see README.md, "01 Noise floor".
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np

import artifacts
import board as boardmod
import config
import dsp
import gainguard
import vizstyle

CONDITION_LABELS = {
    "short": "shorted inputs (amplifier alone)",
    "10k": "10 k 0.1% per leg (electrode-equivalent)",
    "imbalance": "10 k / 11 k (deliberate mismatch)",
}

# Legend keys stay short; the full sentence belongs in the subtitle. A legend
# of three long labels covers the bars it is meant to explain.
CONDITION_SHORT = {"short": "shorted", "10k": "10 k / 10 k",
                   "imbalance": "10 k / 11 k"}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Input-referred noise floor under electrode-equivalent load.",
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    boardmod.add_common_args(p)
    p.add_argument("--condition", default="10k",
                   choices=("10k", "short", "imbalance", "all"),
                   help="fixture condition (default 10k)")
    p.add_argument("--seconds", type=float, default=120.0,
                   help="capture length per condition (default 120)")
    p.add_argument("--bias", action="store_true",
                   help="record with BIAS drive enabled")
    return p


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def analyse(volts: np.ndarray, fs: float, mains_hz: float) -> dict:
    f, pxx = dsp.welch_psd(volts, fs)
    band = config.NOISE_BAND_HZ
    wide = (config.NOISE_BAND_HZ[0], 0.45 * fs)
    keep = dsp.mains_mask(f, mains_hz, f_max=float(f[-1]))

    rms_band = dsp.band_rms(f, pxx, band)
    rms_wide = dsp.band_rms(f, pxx, wide)
    rms_wide_nomains = dsp.band_rms(f, pxx, wide, mask=keep)
    hp = dsp.highpass(volts, fs, band[0])
    pp = dsp.robust_peak_to_peak(hp)

    per_band = {}
    for name, (lo, hi) in config.EEG_BANDS_HZ.items():
        if hi <= 0.45 * fs:
            per_band[name] = (dsp.band_rms(f, pxx, (lo, hi)) * 1e6).tolist()

    # Median ASD in a quiet decade, the number you compare to a datasheet.
    quiet = (f >= 20.0) & (f <= min(45.0, 0.4 * fs)) & keep
    asd_flat = np.median(dsp.amplitude_spectral_density(pxx[quiet, :]), axis=0)

    return {
        "f": f, "pxx": pxx,
        "rms_band_uv": rms_band * 1e6,
        "rms_wide_uv": rms_wide * 1e6,
        "rms_wide_nomains_uv": rms_wide_nomains * 1e6,
        "pp_uv": pp * 1e6,
        "asd_flat_nv_rthz": asd_flat * 1e9,
        "per_band_uv": per_band,
    }


def expectations(condition: str) -> dict:
    """Physical and datasheet-derived reference levels for this fixture."""
    r_diff = (0.0 if condition == "short"
              else config.differential_source_resistance())
    if condition == "imbalance":
        r_diff = config.SOURCE_R_OHM + config.SOURCE_R_OHM * 1.10
    thermal_rms = (config.johnson_noise_rms(r_diff) if r_diff > 0 else 0.0)
    amp_rms = config.EXPECTED_INPUT_NOISE_URMS[config.PGA_GAIN] * 1e-6
    total = math.hypot(thermal_rms, amp_rms)
    return {
        "source_r_differential_ohm": r_diff,
        "thermal_density_nv_rthz": (config.johnson_noise_density(r_diff) * 1e9
                                    if r_diff > 0 else 0.0),
        "thermal_rms_uv": thermal_rms * 1e6,
        "amplifier_rms_uv": amp_rms * 1e6,
        "expected_total_uv": total * 1e6,
        "limit_uv": total * 1e6 * config.NOISE_PASS_FACTOR,
        "expected_source": config.EXPECTED_NOISE_SOURCE,
    }


def verdict(res: dict, exp: dict) -> dict:
    rms = np.asarray(res["rms_band_uv"])
    over = [int(i) + 1 for i in np.where(rms > exp["limit_uv"])[0]]
    outliers = dsp.outlier_channels(rms, factor=2.0)
    ok = not over
    return {
        "pass": ok,
        "channels_over_limit": over,
        "outlier_channels": outliers,
        "median_uv": float(np.median(rms)),
        "limit_uv": exp["limit_uv"],
        "headroom_ratio": float(exp["limit_uv"] / max(float(np.median(rms)), 1e-12)),
    }


# ---------------------------------------------------------------------------
# Figure
# ---------------------------------------------------------------------------

def figure(t: vizstyle.Theme, results: dict, meta: dict):
    """Two panels, one x-axis each, no dual axes.

    Panel A uses EMPHASIS rather than eight categorical hues: every channel in
    the de-emphasis gray, the across-channel median in slot 1. Eight hues here
    would spend the whole palette on identity nobody needs -- the story is the
    shape of the floor and any channel that leaves the pack.
    """
    import matplotlib.pyplot as plt

    conds = list(results.keys())
    fig, (ax0, ax1) = plt.subplots(2, 1, figsize=(7.6, 7.4),
                                   height_ratios=(1.35, 1.0))

    # The 10 k condition is the one that predicts real recordings, so it leads
    # panel A whenever it was measured.
    primary = "10k" if "10k" in conds else conds[0]
    r = results[primary]["analysis"]
    exp = results[primary]["expected"]
    f, pxx = r["f"], r["pxx"]
    asd = dsp.amplitude_spectral_density(pxx) * 1e9
    lo = max(f[1], 0.3)

    for ch in range(asd.shape[1]):
        ax0.loglog(f[1:], asd[1:, ch], color=t.deemphasis, linewidth=0.8,
                   alpha=0.75, zorder=2)
    med = np.median(asd, axis=1)
    ax0.loglog(f[1:], med[1:], color=t.color(0), linewidth=vizstyle.LINE_W,
               zorder=4)
    if exp["thermal_density_nv_rthz"] > 0:
        vizstyle.reference_line(
            ax0, exp["thermal_density_nv_rthz"],
            f"Johnson noise of {exp['source_r_differential_ohm'] / 1e3:.0f} k "
            f"= {exp['thermal_density_nv_rthz']:.1f} nV/rtHz  (a floor no "
            "amplifier can beat)", t, x=0.5, ha="center")

    fmax = float(f[-1])
    harm = dsp.mains_harmonics(meta["mains_hz"], fmax)
    labels = [f"{meta['mains_hz']:.0f} Hz" if i == 0 else
              (f"x{i + 1}" if i < 3 else None) for i in range(len(harm))]
    vizstyle.vertical_marks(ax0, harm, t, labels=labels)

    ax0.set_xlim(lo, fmax)
    # Headroom above the mains spikes, so the legend has somewhere to sit that
    # is not on top of the Johnson reference line at the bottom of the panel.
    ax0.set_ylim(top=ax0.get_ylim()[1] * 3.0)
    ax0.set_xlabel("frequency (Hz)")
    ax0.set_ylabel("input-referred noise (nV/rtHz)")
    vizstyle.title_block(
        ax0, f"Noise density -- {CONDITION_LABELS[primary]}",
        "a rising left edge is 1/f; spikes on the comb are mains pickup")
    vizstyle.legend(ax0, t, handles=[
        vizstyle.key_handle("per channel", t.deemphasis),
        vizstyle.key_handle("median", t.color(0))], loc="upper left")

    # -- panel B: per-channel band RMS, one bar series per condition
    e0 = results[primary]["expected"]
    width = 0.8 / len(conds)
    for i, cond in enumerate(conds):
        rms = np.asarray(results[cond]["analysis"]["rms_band_uv"])
        x = np.arange(1, len(rms) + 1) + (i - (len(conds) - 1) / 2) * width
        vizstyle.bars(ax1, x, rms, t, t.color(i), width=width,
                      label=CONDITION_SHORT[cond])
    # One reference line only. The expected level is a number, not a mark --
    # drawing it too put a label across the bars it was meant to explain.
    vizstyle.reference_line(ax1, e0["limit_uv"],
                            f"limit {e0['limit_uv']:.2f} uV", t,
                            color=t.serious)
    ax1.set_ylim(0, max(e0["limit_uv"] * 1.30,
                        float(max(np.max(results[c]["analysis"]["rms_band_uv"])
                                  for c in conds)) * 1.55))
    ax1.set_xticks(np.arange(1, config.N_CHANNELS + 1))
    ax1.set_xlabel("channel")
    ax1.set_ylabel(f"{config.NOISE_BAND_HZ[0]:g}-{config.NOISE_BAND_HZ[1]:g} Hz "
                   "noise (uVrms)")
    vizstyle.title_block(
        ax1, "Band noise per channel",
        f"expected {e0['expected_total_uv']:.2f} uVrms at gain "
        f"{config.PGA_GAIN}; the gap between conditions is the "
        "source-impedance penalty")
    if len(conds) >= 2:
        vizstyle.legend(ax1, t, loc="upper left", ncol=len(conds))

    vizstyle.stamp(fig, meta, t)
    return fig


# ---------------------------------------------------------------------------

def record(brd, args, condition: str) -> np.ndarray:
    if args.synthetic:
        src = brd.source
        brd.condition = condition
        brd.set_scenario(lambda s: src.noise_floor(
            s, condition=condition, bias_on=args.bias))
    else:
        input(f"\n  Wire the inputs for: {CONDITION_LABELS[condition]}\n"
              "  Then press Enter to record: ")
    return brd.acquire(args.seconds)


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    artifacts.ensure_out(args.out_dir)
    boardmod.print_header("01  NOISE FLOOR", args)

    conditions = (["short", "10k", "imbalance"] if args.condition == "all"
                  else [args.condition])
    brd = boardmod.open_board(args, condition=conditions[0])
    results: dict[str, dict] = {}
    all_meta = {}
    try:
        if args.bias and hasattr(brd, "set_bias"):
            brd.set_bias(True)

        for cond in conditions:
            print(f"\n  recording {args.seconds:g} s -- {CONDITION_LABELS[cond]}")
            counts = record(brd, args, cond)
            volts = gainguard.counts_to_volts(counts)
            res = analyse(volts, args.fs, args.mains)
            exp = expectations(cond)
            ver = verdict(res, exp)
            results[cond] = {"analysis": res, "expected": exp, "verdict": ver}

            meta = boardmod.base_meta("01_noise_floor", args, {
                "condition": cond,
                "condition_label": CONDITION_LABELS[cond],
                "bias_on": bool(args.bias),
                "seconds": args.seconds,
                "expected": exp,
                "verdict": ver,
                "per_channel": {
                    "band_rms_uv": np.asarray(res["rms_band_uv"]).tolist(),
                    "wideband_rms_uv": np.asarray(res["rms_wide_uv"]).tolist(),
                    "wideband_rms_no_mains_uv":
                        np.asarray(res["rms_wide_nomains_uv"]).tolist(),
                    "pp_uv": np.asarray(res["pp_uv"]).tolist(),
                    "asd_flat_nv_rthz": np.asarray(res["asd_flat_nv_rthz"]).tolist(),
                    "eeg_bands_uv": res["per_band_uv"],
                },
                "summary": dsp.summarise_channels(res["rms_band_uv"], "uv"),
            })
            all_meta[cond] = meta

            rec = boardmod.Recording(counts=counts, fs_hz=args.fs, meta=meta)
            boardmod.save_recording(
                Path(args.out_dir) / "data" / f"01_raw_{cond}", rec)
            artifacts.write_json(args.out_dir, f"01_noise_floor_{cond}", meta)
            artifacts.write_csv(args.out_dir, f"01_noise_floor_{cond}", [
                {"channel": i + 1,
                 "band_rms_uv": round(float(res["rms_band_uv"][i]), 4),
                 "wideband_rms_uv": round(float(res["rms_wide_uv"][i]), 4),
                 "wideband_rms_no_mains_uv":
                     round(float(res["rms_wide_nomains_uv"][i]), 4),
                 "pp_uv": round(float(res["pp_uv"][i]), 3),
                 "asd_flat_nv_rthz": round(float(res["asd_flat_nv_rthz"][i]), 2)}
                for i in range(len(res["rms_band_uv"]))])

            print(f"    median {config.NOISE_BAND_HZ[0]:g}-"
                  f"{config.NOISE_BAND_HZ[1]:g} Hz : "
                  f"{np.median(res['rms_band_uv']):.3f} uVrms   "
                  f"expected {exp['expected_total_uv']:.3f}   "
                  f"limit {exp['limit_uv']:.3f}")
            print(f"    thermal floor of the fixture      : "
                  f"{exp['thermal_rms_uv']:.3f} uVrms")
            print(f"    verdict: {'PASS' if ver['pass'] else 'FAIL'}"
                  + (f"  channels over limit: {ver['channels_over_limit']}"
                     if ver["channels_over_limit"] else ""))
            if ver["outlier_channels"]:
                print(f"    outlier channels (>2x median): "
                      f"{ver['outlier_channels']} -- suspect the fixture on "
                      "those inputs before suspecting the board")

        if len(conditions) > 1:
            penalty = (np.median(results["10k"]["analysis"]["rms_band_uv"]) /
                       np.median(results["short"]["analysis"]["rms_band_uv"]))
            print(f"\n  source-impedance penalty (10k / short): {penalty:.2f}x")
            print("  this is the number a shorted-input measurement cannot "
                  "give you.")

        primary_meta = all_meta[conditions[-1] if "10k" not in conditions else "10k"]
        paths = vizstyle.render(
            lambda t: figure(t, results, primary_meta),
            artifacts.fig_stem(args.out_dir, "01_noise_floor"),
            vizstyle.resolve_themes(args.theme))
        vizstyle.log_written(paths)

        return 0 if all(r["verdict"]["pass"] for r in results.values()) else 1
    finally:
        brd.close()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except gainguard.GainMismatch as exc:
        print(f"\n{'=' * 74}\n{exc}\n{'=' * 74}\n", file=sys.stderr)
        sys.exit(1)
