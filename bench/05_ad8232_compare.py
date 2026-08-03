#!/usr/bin/env python3
"""05 -- Cerelog ESP-EEG against an AD8232, side by side.

===========================================================================
 THE ONLY WAY THIS COMPARISON IS HONEST
===========================================================================

The two devices have completely different signal chains: an ADS1299 at PGA
gain 8 into a 24-bit converter, against an AD8232 instrumentation amp at
gain 100 (plus whatever second stage you built) into whatever ADC you
digitised it with. Comparing them means dividing each one's raw numbers by
its OWN chain before anything is plotted.

That is the same class of error the gain guard exists for, one level up, and
it is why this script makes you state the AD8232 chain explicitly:

    --ad8232-total-gain      instrumentation gain x any second stage
    --ad8232-adc-bits        digitiser resolution
    --ad8232-adc-span        digitiser full-scale span, volts
    --ad8232-units           whether the file holds counts or volts

There is no default that guesses. A comparison plotted with the wrong chain
constant is not a weaker result -- it is a wrong one, and it will favour
whichever device you got wrong.

===========================================================================
 WHAT USUALLY DECIDES IT, AND IT IS NOT THE AMPLIFIER
===========================================================================

The AD8232 is a good part. It was designed for millivolt-scale ECG on a
single lead, and it does that well. EEG is two orders of magnitude smaller,
and two things follow:

  1. Its input noise (about 14 uV peak-to-peak over 0.5-40 Hz, roughly
     2.3 uVrms) is an order of magnitude above an ADS1299's at the same
     bandwidth. On ECG that is invisible; on a 10 uV alpha rhythm it is not.

  2. The digitiser usually decides the outcome before the analog part gets a
     vote. This script COMPUTES the AD8232 chain's input-referred LSB and its
     quantisation noise (LSB/sqrt(12)) and draws that floor on the figure.
     With gain 100 into a bare 12-bit 3.3 V ADC, one count is about 8 uV at
     the input -- the quantiser alone is noisier than the whole ADS1299
     channel, and no amount of averaging recovers what was never resolved.

So read the figure with the reference line in mind: if the AD8232 curve is
sitting on its own quantisation floor, you are measuring the ADC you chose,
not the amplifier.
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
import synth
import vizstyle


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Side-by-side comparison against an AD8232 front end.",
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    boardmod.add_common_args(p)
    p.add_argument("--seconds", type=float, default=120.0)
    p.add_argument("--condition", default="10k",
                   choices=("10k", "short", "imbalance"))
    p.add_argument("--cerelog-recording", type=Path, default=None,
                   help="reuse a saved Cerelog recording stem instead of "
                        "acquiring (e.g. out/data/01_raw_10k)")

    a = p.add_argument_group("AD8232 chain -- no defaults are guessed")
    a.add_argument("--ad8232-file", type=Path, default=None,
                   help=".csv (one column per channel) or .npz with an array "
                        "named 'data'. Omit in --synthetic mode.")
    a.add_argument("--ad8232-units", choices=("counts", "volts"),
                   default="counts",
                   help="what the file holds (default counts)")
    a.add_argument("--ad8232-fs", type=float, default=None,
                   help="AD8232 capture sample rate (defaults to --fs)")
    a.add_argument("--ad8232-total-gain", type=float, default=1100.0,
                   help="instrumentation gain x second stage (default 100x11)")
    a.add_argument("--ad8232-adc-bits", type=int, default=12)
    a.add_argument("--ad8232-adc-span", type=float, default=3.3,
                   help="digitiser full-scale span in volts (default 3.3)")
    return p


# ---------------------------------------------------------------------------

def load_ad8232(args) -> tuple[np.ndarray, float, dict]:
    """Return (input-referred volts, fs, chain metadata)."""
    fs = args.ad8232_fs or args.fs
    lsb_in = args.ad8232_adc_span / (2 ** args.ad8232_adc_bits) / args.ad8232_total_gain
    chain = {
        "device": "AD8232",
        "total_gain": args.ad8232_total_gain,
        "adc_bits": args.ad8232_adc_bits,
        "adc_span_v": args.ad8232_adc_span,
        "lsb_input_referred_uv": lsb_in * 1e6,
        "quantisation_noise_uvrms": lsb_in / math.sqrt(12.0) * 1e6,
        "fs_hz": fs,
    }

    if args.synthetic and not args.ad8232_file:
        model = synth.Ad8232Model(
            instrumentation_gain=args.ad8232_total_gain / 11.0,
            second_stage_gain=11.0,
            adc_bits=args.ad8232_adc_bits,
            adc_span_v=args.ad8232_adc_span)
        mains = synth.MainsModel(f0_hz=args.mains)
        volts, meta = synth.synth_ad8232(model, args.seconds, fs, mains,
                                         seed=args.seed + 1)
        chain.update({k: v for k, v in meta.items() if k not in chain})
        chain["synthetic"] = True
        return volts, fs, chain

    if not args.ad8232_file:
        raise SystemExit(
            "No --ad8232-file and not in --synthetic mode.\n"
            "Record the AD8232 with whatever digitiser you are using, save it "
            "as CSV or NPZ, and pass the file plus its chain constants. This "
            "script will not invent the comparison device.")

    path = Path(args.ad8232_file)
    if path.suffix == ".npz":
        with np.load(path) as z:
            key = "data" if "data" in z else list(z.keys())[0]
            raw = np.asarray(z[key], dtype=np.float64)
    else:
        try:
            raw = np.loadtxt(path, delimiter=",", ndmin=2)
        except ValueError:
            # Almost certainly a header row. Retry once rather than making
            # the person strip it by hand at the bench.
            raw = np.loadtxt(path, delimiter=",", ndmin=2, skiprows=1)
    if raw.ndim == 1:
        raw = raw.reshape(-1, 1)
    if raw.shape[0] < raw.shape[1]:
        raw = raw.T

    volts = raw * lsb_in if args.ad8232_units == "counts" else raw / args.ad8232_total_gain
    chain["source_file"] = str(path)
    chain["samples"] = int(raw.shape[0])
    return volts, fs, chain


def common_band(fs_a: float, fs_b: float) -> tuple[float, float]:
    hi = min(config.NOISE_BAND_HZ[1], 0.45 * fs_a, 0.45 * fs_b)
    return (config.NOISE_BAND_HZ[0], hi)


def analyse(volts: np.ndarray, fs: float, band: tuple[float, float],
            mains_hz: float) -> dict:
    f, pxx = dsp.welch_psd(volts, fs)
    med = np.median(pxx, axis=1) if pxx.ndim > 1 else pxx
    keep = dsp.mains_mask(f, mains_hz, f_max=float(f[-1]))
    bands = {}
    for name, (lo, hi) in config.EEG_BANDS_HZ.items():
        if hi <= band[1]:
            bands[name] = float(dsp.band_rms(f, med, (lo, hi))) * 1e6
    return {
        "f": f, "median_pxx": med,
        "band_rms_uv": float(dsp.band_rms(f, med, band)) * 1e6,
        "band_rms_no_mains_uv": float(dsp.band_rms(f, med, band, mask=keep)) * 1e6,
        "eeg_bands_uv": bands,
        "fundamental_uvrms": dsp.tone_rms_from_psd(f, med, mains_hz)[0] * 1e6,
    }


# ---------------------------------------------------------------------------

def figure(t: vizstyle.Theme, cer: dict, ad: dict, chain: dict, band, meta: dict):
    import matplotlib.pyplot as plt

    fig, (ax0, ax1) = plt.subplots(2, 1, figsize=(7.6, 7.4),
                                   height_ratios=(1.35, 1.0))

    for src, color, label in ((cer, t.color(0), "Cerelog ESP-EEG"),
                              (ad, t.color(1), "AD8232 chain")):
        f = src["f"]
        asd = dsp.amplitude_spectral_density(src["median_pxx"]) * 1e9
        ax0.loglog(f[1:], asd[1:], color=color, linewidth=vizstyle.LINE_W,
                   label=label, zorder=4)

    # Spread the quantisation noise (a total RMS) over the Nyquist band to get
    # a density comparable with the plotted curves: nVrms / sqrt(fs/2).
    q = chain["quantisation_noise_uvrms"]
    fs_ad = chain["fs_hz"]
    q_density_nv = q * 1e3 / math.sqrt(fs_ad / 2.0)
    vizstyle.reference_line(
        ax0, q_density_nv,
        f"AD8232 quantisation floor -- {chain['lsb_input_referred_uv']:.2f} uV "
        f"per count, {q:.3f} uVrms", t, x=0.5, ha="center", color=t.serious)

    ax0.set_xlabel("frequency (Hz)")
    ax0.set_ylabel("input-referred noise (nV/rtHz)")
    ratio = ad["band_rms_no_mains_uv"] / max(cer["band_rms_no_mains_uv"], 1e-12)
    vizstyle.title_block(
        ax0, "Input-referred noise density, both chains",
        f"each divided by its own gain before plotting; AD8232 is "
        f"{ratio:.1f}x noisier over {band[0]:g}-{band[1]:g} Hz")
    vizstyle.legend(ax0, t, loc="lower left")

    names = [k for k in config.EEG_BANDS_HZ if k in cer["eeg_bands_uv"]
             and k in ad["eeg_bands_uv"]]
    x = np.arange(len(names))
    w = 0.38
    vizstyle.bars(ax1, x - w / 2, [cer["eeg_bands_uv"][n] for n in names], t,
                  t.color(0), width=w, label="Cerelog ESP-EEG")
    vizstyle.bars(ax1, x + w / 2, [ad["eeg_bands_uv"][n] for n in names], t,
                  t.color(1), width=w, label="AD8232 chain")
    for i, n in enumerate(names):
        v = ad["eeg_bands_uv"][n] / max(cer["eeg_bands_uv"][n], 1e-12)
        ax1.annotate(f"{v:.0f}x", xy=(x[i], ad["eeg_bands_uv"][n]),
                     xytext=(9, 4), textcoords="offset points",
                     ha="left", fontsize=8, color=t.secondary)
    ax1.set_xticks(x)
    ax1.set_xticklabels([f"{n}\n{config.EEG_BANDS_HZ[n][0]:g}-"
                         f"{config.EEG_BANDS_HZ[n][1]:g} Hz" for n in names])
    ax1.set_ylabel("noise in band (uVrms)")
    vizstyle.title_block(
        ax1, "Noise per EEG band",
        "labels are the AD8232's multiple of the Cerelog figure")
    vizstyle.legend(ax1, t, loc="upper left", ncol=2)

    vizstyle.stamp(fig, meta, t)
    return fig


# ---------------------------------------------------------------------------

def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    artifacts.ensure_out(args.out_dir)
    boardmod.print_header("05  AD8232 COMPARISON", args)

    brd = None
    try:
        if args.cerelog_recording:
            rec = boardmod.load_recording(args.cerelog_recording)
            gainguard.inherit(rec.meta, origin=str(args.cerelog_recording))
            counts, args.fs = rec.counts, rec.fs_hz
        else:
            brd = boardmod.open_board(args, condition=args.condition)
            if args.synthetic:
                s = brd.source
                brd.set_scenario(lambda sec: s.noise_floor(
                    sec, condition=args.condition))
            else:
                input(f"\n  Wire the {args.condition} fixture on the Cerelog "
                      "board, then press Enter: ")
            print(f"\n  recording Cerelog, {args.seconds:g} s")
            counts = brd.acquire(args.seconds)
        cer_v = gainguard.counts_to_volts(counts)

        ad_v, ad_fs, chain = load_ad8232(args)
        band = common_band(args.fs, ad_fs)

        cer = analyse(cer_v, args.fs, band, args.mains)
        ad = analyse(ad_v, ad_fs, band, args.mains)

        print(f"\n  comparison band {band[0]:g}-{band[1]:g} Hz")
        print(f"\n  {'':22s}{'Cerelog':>14s}{'AD8232':>14s}{'ratio':>10s}")
        rows = []

        def emit(label: str, a: float, b: float) -> None:
            # A tone that does not clear the local floor comes back as zero.
            # Printing "0.0000" and a 0.0x ratio would read as "no mains
            # pickup", when what happened is "buried in this device's own
            # noise" -- the opposite conclusion.
            nd = "not detected above its own noise floor"
            b_s = f"{b:14.4f}" if b > 0 else f"{'n/d':>14s}"
            r_s = f"{b / max(a, 1e-12):9.1f}x" if b > 0 and a > 0 else f"{'--':>10s}"
            print(f"  {label:22s}{a:14.4f}{b_s}{r_s}")
            rows.append({"metric": label, "cerelog": round(a, 5),
                         "ad8232": round(b, 5) if b > 0 else nd,
                         "ratio": round(b / max(a, 1e-12), 3) if b > 0 else ""})

        emit("band noise (uVrms)", cer["band_rms_uv"], ad["band_rms_uv"])
        emit("band, mains excluded", cer["band_rms_no_mains_uv"],
             ad["band_rms_no_mains_uv"])
        emit(f"{args.mains:g} Hz line (uVrms)", cer["fundamental_uvrms"],
             ad["fundamental_uvrms"])
        for n in cer["eeg_bands_uv"]:
            emit(f"{n} band (uVrms)", cer["eeg_bands_uv"][n],
                 ad["eeg_bands_uv"].get(n, 0.0))
        if ad["fundamental_uvrms"] <= 0 < cer["fundamental_uvrms"]:
            print(f"\n  The {args.mains:g} Hz line is visible on the Cerelog "
                  "board and not on the AD8232. That is not better rejection "
                  "-- the AD8232's own noise is above the line level, so the "
                  "pickup is there and unmeasurable. Do not read it as a win.")

        print(f"\n  Cerelog quantisation : "
              f"{config.lsb_volts(config.PGA_GAIN) * 1e6:.5f} uV/count -> "
              f"{config.lsb_volts(config.PGA_GAIN) / math.sqrt(12) * 1e6:.5f} uVrms")
        print(f"  AD8232 quantisation  : "
              f"{chain['lsb_input_referred_uv']:.5f} uV/count -> "
              f"{chain['quantisation_noise_uvrms']:.5f} uVrms")
        if chain["quantisation_noise_uvrms"] > 0.5 * ad["band_rms_no_mains_uv"]:
            print("\n  NOTE: the AD8232's measured noise is within a factor of "
                  "two of its own quantisation floor. That figure is a "
                  "property of the digitiser you chose, not of the AD8232. "
                  "Raise the second-stage gain or use a better ADC before "
                  "quoting it as an amplifier comparison.")

        meta = boardmod.base_meta("05_ad8232", args, {
            "condition": args.condition,
            "comparison_band_hz": list(band),
            "ad8232_chain": chain,
            "cerelog": {k: v for k, v in cer.items()
                        if k not in ("f", "median_pxx")},
            "ad8232": {k: v for k, v in ad.items()
                       if k not in ("f", "median_pxx")},
            "cerelog_quantisation_uvrms":
                config.lsb_volts(config.PGA_GAIN) / math.sqrt(12) * 1e6,
        })
        artifacts.write_json(args.out_dir, "05_ad8232", meta)
        artifacts.write_csv(args.out_dir, "05_ad8232", rows)

        paths = vizstyle.render(
            lambda t: figure(t, cer, ad, chain, band, meta),
            artifacts.fig_stem(args.out_dir, "05_ad8232"),
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
