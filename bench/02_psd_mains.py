#!/usr/bin/env python3
"""02 -- power spectral density with the mains harmonic comb annotated.

The point of annotating harmonics rather than notching them is that the SHAPE
of the comb tells you where the pickup is coming from:

  * Fundamental only, harmonics absent      -> magnetic coupling into a loop.
    Find the loop: a cable running parallel to a mains lead, or the ground
    lead taking a different route back than the signal pair.

  * Strong odd harmonics (3rd, 5th, 7th)    -> capacitive coupling from a
    device with a switching supply or a triac dimmer. Mains itself is a clean
    sine; the odd-harmonic structure is added by whatever is loading it.

  * Comb present on one channel only        -> that input's fixture, not the
    board. Check the resistor's leads before you check the amplifier.

  * Comb present with the inputs shorted    -> it is getting in after the
    input pins: supply, reference, or the digital side.

This script measures; it does not notch. A notch filter applied before you
understand the comb removes the evidence, and the residual it leaves behind is
indistinguishable from a low-noise front end.
"""

from __future__ import annotations

import argparse
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


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="PSD with mains fundamental and harmonics annotated.",
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    boardmod.add_common_args(p)
    p.add_argument("--seconds", type=float, default=120.0,
                   help="capture length (default 120; longer means finer bins "
                        "and a better-resolved comb)")
    p.add_argument("--condition", default="10k",
                   choices=("10k", "short", "imbalance"),
                   help="fixture condition (default 10k)")
    p.add_argument("--bias", action="store_true", help="record with BIAS on")
    p.add_argument("--from-recording", type=Path, default=None,
                   help="analyse an existing recording stem instead of "
                        "acquiring (e.g. out/data/01_raw_10k)")
    p.add_argument("--prominence-db", type=float, default=10.0,
                   help="a harmonic this far above the local floor is called "
                        "present (default 10 dB)")
    return p


def analyse(volts: np.ndarray, fs: float, mains_hz: float,
            prominence_db: float) -> dict:
    f, pxx = dsp.welch_psd(volts, fs)
    med = np.median(pxx, axis=1)
    rows = dsp.harmonic_table(f, med, mains_hz)
    present = [r for r in rows if r["prominence_db"] >= prominence_db]

    keep = dsp.mains_mask(f, mains_hz, f_max=float(f[-1]))
    wide = (config.NOISE_BAND_HZ[0], 0.45 * fs)
    total = dsp.band_rms(f, pxx, wide)
    clean = dsp.band_rms(f, pxx, wide, mask=keep)
    mains_power = np.maximum(total ** 2 - clean ** 2, 0.0)

    # Per-channel fundamental, so a single bad fixture is visible.
    per_ch_f0 = np.array([dsp.tone_rms_from_psd(f, pxx[:, c], mains_hz)[0]
                          for c in range(pxx.shape[1])])

    odd = sum(r["amplitude_uvrms"] ** 2 for r in present if r["harmonic"] % 2 == 1
              and r["harmonic"] > 1)
    even = sum(r["amplitude_uvrms"] ** 2 for r in present if r["harmonic"] % 2 == 0)

    return {
        "f": f, "pxx": pxx, "median_pxx": med,
        "harmonics": rows,
        "harmonics_present": [r["harmonic"] for r in present],
        "wideband_rms_uv": (total * 1e6).tolist(),
        "wideband_rms_no_mains_uv": (clean * 1e6).tolist(),
        "mains_contribution_uvrms": (np.sqrt(mains_power) * 1e6).tolist(),
        "fundamental_per_channel_uvrms": (per_ch_f0 * 1e6).tolist(),
        "odd_harmonic_energy_uv2": float(odd),
        "even_harmonic_energy_uv2": float(even),
        "coupling_hint": _hint(rows, present, odd, even),
    }


def _hint(rows, present, odd, even) -> str:
    if not present:
        return ("no harmonic clears the prominence threshold -- either the "
                "bench is quiet or the inputs are not connected to anything "
                "that can pick up. Confirm with the imbalance fixture, which "
                "should show MORE mains, not the same.")
    if len(present) == 1 and present[0]["harmonic"] == 1:
        return ("fundamental only, no harmonics: magnetic coupling into a "
                "loop. Look for a cable running alongside a mains lead and "
                "for a ground return that does not follow the signal pair.")
    if odd > 3.0 * max(even, 1e-12):
        return ("odd harmonics dominate: capacitive coupling from a switching "
                "supply or a dimmer. Unplug things one at a time.")
    return ("both odd and even harmonics present: mixed coupling, or "
            "clipping somewhere in the chain. Check for railing before "
            "chasing the layout.")


def figure(t: vizstyle.Theme, res: dict, meta: dict):
    import matplotlib.pyplot as plt

    fig, (ax0, ax1) = plt.subplots(2, 1, figsize=(7.6, 7.4),
                                   height_ratios=(1.4, 1.0))
    f = res["f"]
    asd = dsp.amplitude_spectral_density(res["pxx"]) * 1e9
    f0 = meta["mains_hz"]

    for ch in range(asd.shape[1]):
        ax0.loglog(f[1:], asd[1:, ch], color=t.deemphasis, linewidth=0.8,
                   alpha=0.7, zorder=2)
    med = dsp.amplitude_spectral_density(res["median_pxx"]) * 1e9
    ax0.loglog(f[1:], med[1:], color=t.color(0), linewidth=vizstyle.LINE_W,
               zorder=4)

    harm = dsp.mains_harmonics(f0, float(f[-1]))
    # Label the first three only. A number on all eight is unreadable and the
    # comb spacing already says which is which.
    labels = [f"{f0:.0f} Hz", "2nd", "3rd"] + [None] * max(0, len(harm) - 3)
    vizstyle.vertical_marks(ax0, harm, t, labels=labels[:len(harm)])

    ax0.set_xlim(max(f[1], 0.3), float(f[-1]))
    ax0.set_xlabel("frequency (Hz)")
    ax0.set_ylabel("input-referred noise (nV/rtHz)")
    vizstyle.title_block(
        ax0, f"Noise density with the {f0:.0f} Hz comb marked",
        f"harmonics above the local floor: "
        f"{res['harmonics_present'] or 'none'}")
    vizstyle.legend(ax0, t, handles=[
        vizstyle.key_handle("per channel", t.deemphasis),
        vizstyle.key_handle("median", t.color(0))], loc="lower left")

    rows = res["harmonics"]
    ks = [r["harmonic"] for r in rows]
    amps = [r["amplitude_uvrms"] for r in rows]
    vizstyle.bars(ax1, ks, amps, t, t.color(0), width=0.6)
    if amps:
        i = int(np.argmax(amps))
        ax1.annotate(f"{amps[i]:.3f} uVrms at {rows[i]['frequency_hz']:.0f} Hz",
                     xy=(ks[i], amps[i]), xytext=(0, 7),
                     textcoords="offset points", ha="center", fontsize=8.5,
                     color=t.secondary)
        ax1.set_ylim(0, max(amps) * 1.35)
    vizstyle.category_axis(ax1, ks)
    ax1.set_xlabel(f"harmonic of {f0:.0f} Hz")
    ax1.set_ylabel("amplitude (uVrms)")
    vizstyle.title_block(ax1, "Harmonic amplitudes", res["coupling_hint"])

    vizstyle.stamp(fig, meta, t)
    return fig


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    artifacts.ensure_out(args.out_dir)
    boardmod.print_header("02  PSD AND MAINS HARMONICS", args)

    brd = None
    try:
        if args.from_recording:
            rec = boardmod.load_recording(args.from_recording)
            gainguard.inherit(rec.meta, origin=str(args.from_recording))
            counts = rec.counts
            args.fs = rec.fs_hz
            args.synthetic = bool(rec.meta.get("synthetic", args.synthetic))
            src_meta = {"reanalysed_from": str(args.from_recording),
                        "condition": rec.meta.get("condition"),
                        "bias_on": rec.meta.get("bias_on")}
        else:
            brd = boardmod.open_board(args, condition=args.condition)
            if args.bias and hasattr(brd, "set_bias"):
                brd.set_bias(True)
            if args.synthetic:
                s = brd.source
                brd.set_scenario(lambda sec: s.noise_floor(
                    sec, condition=args.condition, bias_on=args.bias))
            else:
                input(f"\n  Wire the {args.condition} fixture, then press "
                      "Enter to record: ")
            print(f"\n  recording {args.seconds:g} s")
            counts = brd.acquire(args.seconds)
            src_meta = {"condition": args.condition, "bias_on": bool(args.bias),
                        "seconds": args.seconds}

        volts = gainguard.counts_to_volts(counts)
        res = analyse(volts, args.fs, args.mains, args.prominence_db)

        print("\n  harmonic   freq     amplitude      above floor")
        for r in res["harmonics"]:
            flag = "*" if r["prominence_db"] >= args.prominence_db else " "
            print(f"   {flag} {r['harmonic']:<6d} {r['frequency_hz']:7.1f} Hz "
                  f"{r['amplitude_uvrms']:10.4f} uVrms "
                  f"{r['prominence_db']:9.1f} dB")
        print(f"\n  wideband RMS with mains    : "
              f"{np.median(res['wideband_rms_uv']):.3f} uVrms")
        print(f"  wideband RMS without mains : "
              f"{np.median(res['wideband_rms_no_mains_uv']):.3f} uVrms")
        print(f"  mains contribution         : "
              f"{np.median(res['mains_contribution_uvrms']):.3f} uVrms")
        print(f"\n  {res['coupling_hint']}")

        meta = boardmod.base_meta("02_psd_mains", args, {
            **src_meta,
            "prominence_threshold_db": args.prominence_db,
            "harmonics": res["harmonics"],
            "harmonics_present": res["harmonics_present"],
            "wideband_rms_uv": res["wideband_rms_uv"],
            "wideband_rms_no_mains_uv": res["wideband_rms_no_mains_uv"],
            "mains_contribution_uvrms": res["mains_contribution_uvrms"],
            "fundamental_per_channel_uvrms": res["fundamental_per_channel_uvrms"],
            "coupling_hint": res["coupling_hint"],
        })
        artifacts.write_json(args.out_dir, "02_psd_mains", meta)
        artifacts.write_csv(args.out_dir, "02_psd_mains", [
            {k: (round(v, 5) if isinstance(v, float) else v)
             for k, v in r.items()} for r in res["harmonics"]])

        paths = vizstyle.render(
            lambda t: figure(t, res, meta),
            artifacts.fig_stem(args.out_dir, "02_psd_mains"),
            vizstyle.resolve_themes(args.theme))
        vizstyle.log_written(paths)
        return 0
    finally:
        if brd is not None:
            brd.close()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except gainguard.GainMismatch as exc:
        print(f"\n{'=' * 74}\n{exc}\n{'=' * 74}\n", file=sys.stderr)
        sys.exit(1)
