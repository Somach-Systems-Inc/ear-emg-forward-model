#!/usr/bin/env python3
"""04 -- BIAS drive on against off, same protocol both times.

The comparison is only worth anything if the two halves are identical in every
respect except the bias loop. This script therefore:

  * uses the same fixture, the same capture length, the same analysis, and
    the same random seed in synthetic mode;
  * runs the two halves back to back rather than on different days;
  * CONFIRMS THE TOGGLE BY READING CONFIG3 BACK. A prompt that says "turn
    bias on now" and then trusts the answer produces two identical recordings
    and a confident conclusion that bias does nothing. The PD_BIAS bit is
    checked before each half records, and the run aborts if it did not move.

WHAT TO EXPECT

The bias amplifier drives the inverse of the measured common mode back into
the subject (here, into the common node of the fixture), which reduces the
common-mode voltage the inputs actually see. On a real head that is typically
worth 20-40 dB at the mains fundamental. It is a feedback loop with finite
bandwidth, so the benefit falls away at the higher harmonics -- expect much
less improvement at the 3rd than at the 1st.

It is not free. The bias amplifier injects its own noise into the common-mode
node, so the broadband floor usually rises slightly. A result showing mains
dropping AND the broadband floor dropping is suspicious; look for a channel
that is not actually in the loop, or a capture that changed something else.

WHAT A NULL RESULT MEANS

On a bench fixture of resistors sitting on a desk there may be almost no
common-mode mains to reject, in which case bias on and bias off look the same.
That is not "bias does not work" -- it is "this fixture does not test bias".
The script says so rather than reporting 0 dB as a finding. To make the test
meaningful, give it something to reject: run the imbalance fixture, or route
the common node near a mains lead, and confirm from 02 that there is a comb to
begin with.
"""

from __future__ import annotations

import argparse
import subprocess
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

NULL_RESULT_DB = 1.5


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="BIAS drive on vs off, identical protocol.",
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    boardmod.add_common_args(p)
    p.add_argument("--seconds", type=float, default=120.0)
    p.add_argument("--condition", default="10k",
                   choices=("10k", "short", "imbalance"))
    p.add_argument("--with-cmrr", action="store_true",
                   help="also run the full 03 CMRR sweep in both states "
                        "(adds two AD3 sweeps; in hardware mode that means "
                        "rewiring twice)")
    p.add_argument("--cmrr-seconds-per-point", type=float, default=10.0)
    return p


# ---------------------------------------------------------------------------

def set_bias_confirmed(brd, enabled: bool, synthetic: bool) -> dict:
    """Change the bias state and PROVE it changed before recording."""
    want = "ON" if enabled else "OFF"
    try:
        brd.set_bias(enabled)
    except NotImplementedError:
        input(f"\n  Turn BIAS drive {want} on the board now, then press "
              "Enter (CONFIG3 will be read back to confirm): ")

    regs = {}
    if hasattr(brd, "read_named_registers"):
        regs = brd.read_named_registers()
    cfg3 = regs.get("CONFIG3")
    if cfg3 is None:
        raise RuntimeError(
            "Could not read CONFIG3 back, so the bias state is unconfirmed.\n"
            "This script refuses to run on an unconfirmed toggle: if the "
            "write did not land, both halves record the same thing and the "
            "comparison silently reports that bias does nothing.\n"
            "Fix the register dump path in board.py, or run the two halves as "
            "separate 02_psd_mains.py invocations and compare them by hand, "
            "knowing that is what you are doing.")
    actual = bool(cfg3 & config.CONFIG3_PD_BIAS_BIT)
    if actual != enabled:
        raise RuntimeError(
            f"BIAS is still {'ON' if actual else 'OFF'} after asking for "
            f"{want}. CONFIG3 = 0x{cfg3:02X}, PD_BIAS bit "
            f"(0x{config.CONFIG3_PD_BIAS_BIT:02X}) reads "
            f"{int(actual)}.\nAborting rather than recording two identical "
            "halves and calling it a comparison.")
    print(f"  BIAS confirmed {want}  (CONFIG3 = 0x{cfg3:02X})")
    return {"config3": cfg3, "pd_bias": actual}


def capture(brd, args, bias_on: bool) -> dict:
    if args.synthetic:
        src = brd.source
        brd.set_scenario(lambda s: src.noise_floor(
            s, condition=args.condition, bias_on=bias_on))
    else:
        input(f"\n  Ready to record {args.seconds:g} s with BIAS "
              f"{'ON' if bias_on else 'OFF'}. Press Enter: ")
    counts = brd.acquire(args.seconds)
    volts = gainguard.counts_to_volts(counts)
    f, pxx = dsp.welch_psd(volts, args.fs)
    med = np.median(pxx, axis=1)
    keep = dsp.mains_mask(f, args.mains, f_max=float(f[-1]))
    wide = (config.NOISE_BAND_HZ[0], 0.45 * args.fs)
    return {
        "f": f, "pxx": pxx, "median_pxx": med,
        "harmonics": dsp.harmonic_table(f, med, args.mains),
        "band_rms_uv": float(np.median(dsp.band_rms(f, pxx))) * 1e6,
        "wide_rms_uv": float(np.median(dsp.band_rms(f, pxx, wide))) * 1e6,
        "wide_rms_no_mains_uv": float(
            np.median(dsp.band_rms(f, pxx, wide, mask=keep))) * 1e6,
    }


def compare(off: dict, on: dict) -> dict:
    by_k_off = {r["harmonic"]: r for r in off["harmonics"]}
    rows = []
    for r in on["harmonics"]:
        o = by_k_off.get(r["harmonic"])
        if not o:
            continue
        a_off, a_on = o["amplitude_uvrms"], r["amplitude_uvrms"]
        imp = (20.0 * np.log10(a_off / a_on)
               if a_off > 0 and a_on > 0 else float("nan"))
        rows.append({
            "harmonic": r["harmonic"],
            "frequency_hz": r["frequency_hz"],
            "amplitude_bias_off_uvrms": a_off,
            "amplitude_bias_on_uvrms": a_on,
            "improvement_db": float(imp),
        })
    broadband_change = 20.0 * np.log10(
        max(on["wide_rms_no_mains_uv"], 1e-12) /
        max(off["wide_rms_no_mains_uv"], 1e-12))
    fundamental = rows[0]["improvement_db"] if rows else float("nan")
    if not np.isfinite(fundamental) or abs(fundamental) < NULL_RESULT_DB:
        note = (f"no meaningful difference at the fundamental "
                f"({fundamental:+.2f} dB). This fixture is not presenting the "
                "bias loop with common-mode mains to reject, so the "
                "comparison is untested rather than negative. Check 02 shows "
                "a comb at all before concluding anything.")
    else:
        note = (f"bias improves the fundamental by {fundamental:.1f} dB and "
                f"changes the mains-free broadband floor by "
                f"{broadband_change:+.2f} dB")
    return {"harmonics": rows, "broadband_change_db": float(broadband_change),
            "fundamental_improvement_db": float(fundamental), "note": note}


def run_cmrr(args, bias_on: bool) -> dict | None:
    """Delegate to 03 rather than reimplementing the sweep."""
    tag = f"04_cmrr_bias_{'on' if bias_on else 'off'}"
    cmd = [sys.executable, str(Path(__file__).with_name("03_cmrr_sweep.py")),
           "--tag", tag, "--fs", str(args.fs), "--mains", str(args.mains),
           "--seconds-per-point", str(args.cmrr_seconds_per_point),
           "--out-dir", str(args.out_dir), "--theme", args.theme,
           "--seed", str(args.seed)]
    if args.synthetic:
        cmd.append("--synthetic")
        if args.synthetic_board_gain:
            cmd += ["--synthetic-board-gain", str(args.synthetic_board_gain)]
    else:
        cmd += ["--port", args.port]
    if bias_on:
        cmd.append("--bias")
    print(f"\n  running CMRR sweep with bias {'ON' if bias_on else 'OFF'}")
    r = subprocess.run(cmd)
    if r.returncode != 0:
        raise RuntimeError(
            f"The CMRR sweep failed (exit {r.returncode}) with bias "
            f"{'on' if bias_on else 'off'}. Not continuing with a half-built "
            "comparison -- read its message above.")
    return artifacts.read_json(args.out_dir, tag)


# ---------------------------------------------------------------------------

def figure(t: vizstyle.Theme, off: dict, on: dict, cmp_: dict,
           cmrr: tuple | None, meta: dict):
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    n_panels = 3 if cmrr else 2
    heights = (1.35, 1.0, 1.1)[:n_panels]
    fig, axes = plt.subplots(n_panels, 1, figsize=(7.6, 3.4 * n_panels),
                             height_ratios=heights)
    ax0, ax1 = axes[0], axes[1]

    # -- panel A: two series, legend present, both direct-labelled
    f = off["f"]
    a_off = dsp.amplitude_spectral_density(off["median_pxx"]) * 1e9
    a_on = dsp.amplitude_spectral_density(on["median_pxx"]) * 1e9
    ax0.loglog(f[1:], a_off[1:], color=t.color(0), linewidth=vizstyle.LINE_W,
               label="BIAS off", zorder=3)
    ax0.loglog(f[1:], a_on[1:], color=t.color(1), linewidth=vizstyle.LINE_W,
               label="BIAS on", zorder=4)
    harm = dsp.mains_harmonics(meta["mains_hz"], float(f[-1]))
    vizstyle.vertical_marks(
        ax0, harm, t,
        labels=[f"{meta['mains_hz']:.0f} Hz", "2nd", "3rd"][:len(harm)])
    ax0.set_xlim(max(f[1], 0.3), float(f[-1]))
    ax0.set_xlabel("frequency (Hz)")
    ax0.set_ylabel("input-referred noise (nV/rtHz)")
    vizstyle.title_block(ax0, "Noise density, BIAS off against BIAS on",
                         cmp_["note"])
    vizstyle.legend(ax0, t, loc="lower left")

    # -- panel B: improvement per harmonic. Polarity -> diverging colors.
    rows = cmp_["harmonics"]
    ks = [r["harmonic"] for r in rows]
    imp = [r["improvement_db"] for r in rows]
    pos, neg = t.diverging[0], t.diverging[2]
    colors = [pos if v >= 0 else neg for v in imp]
    ax1.bar(ks, imp, width=0.34, color=colors, edgecolor="none", zorder=3)
    ax1.axhline(0.0, color=t.baseline, linewidth=vizstyle.HAIRLINE_W, zorder=2)
    if imp:
        i = int(np.argmax(np.abs(imp)))
        ax1.annotate(f"{imp[i]:+.1f} dB",
                     xy=(ks[i], imp[i]),
                     xytext=(0, 7 if imp[i] >= 0 else -14),
                     textcoords="offset points", ha="center", fontsize=8.5,
                     color=t.secondary)
        span = max(abs(min(imp)), abs(max(imp)), 1.0) * 1.4
        ax1.set_ylim(-span, span)
    vizstyle.category_axis(ax1, ks)
    ax1.set_xlabel(f"harmonic of {meta['mains_hz']:.0f} Hz")
    ax1.set_ylabel("improvement with BIAS (dB)")
    vizstyle.title_block(
        ax1, "Mains rejection gained by enabling BIAS",
        "above zero is better with bias; the loop rolls off, so expect less "
        "at the higher harmonics")

    # -- panel C: CMRR overlay
    if cmrr:
        ax2 = axes[2]
        c_off, c_on = cmrr
        any_limited = False
        handles = []
        for src, color, label in ((c_off, t.color(0), "BIAS off"),
                                  (c_on, t.color(1), "BIAS on")):
            fr = np.array([r["frequency_hz"] for r in src["rows"]])
            md = np.array([r["cmrr_median_db"] for r in src["rows"]])
            lim = np.array([bool(r["at_measurement_ceiling"])
                            for r in src["rows"]])
            ax2.semilogx(fr, md, color=color, linewidth=vizstyle.LINE_W,
                         label=label, zorder=4)
            vizstyle.dot(ax2, fr[-1], md[-1], t, color)
            handles.append(vizstyle.key_handle(label, color))
            if lim.any():
                any_limited = True
                # Caret = "at least this". Bias drive routinely pushes the
                # leaked differential below the detection floor, and a curve
                # drawn through those points is a plot of the capture length,
                # not of the board. Marking them is the difference between a
                # lower bound and a measurement.
                ax2.plot(fr[lim], md[lim], marker="^", linestyle="none",
                         color=t.serious, markersize=vizstyle.MARKER_SIZE,
                         markeredgecolor=t.surface,
                         markeredgewidth=vizstyle.RING_W, zorder=6)
        if any_limited:
            handles.append(Line2D([0], [0], marker="^", linestyle="none",
                                  color=t.serious,
                                  label="at measurement ceiling (lower bound)"))
        ax2.set_xlabel("frequency (Hz)")
        ax2.set_ylabel("CMRR (dB)")
        vizstyle.title_block(
            ax2, "CMRR, both states",
            "carets sit at the measurement ceiling: true CMRR is AT LEAST "
            "that, not equal to it" if any_limited else
            "same sweep, same divider, bias the only change")
        vizstyle.legend(ax2, t, loc="lower left", handles=handles)

    vizstyle.stamp(fig, meta, t)
    return fig


# ---------------------------------------------------------------------------

def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    artifacts.ensure_out(args.out_dir)
    boardmod.print_header("04  BIAS ON vs OFF", args)

    brd = boardmod.open_board(args, condition=args.condition)
    try:
        print("\n  half 1 of 2: BIAS OFF")
        state_off = set_bias_confirmed(brd, False, args.synthetic)
        off = capture(brd, args, bias_on=False)

        print("\n  half 2 of 2: BIAS ON")
        state_on = set_bias_confirmed(brd, True, args.synthetic)
        on = capture(brd, args, bias_on=True)

        cmp_ = compare(off, on)

        print("\n   harmonic   freq      bias off      bias on   improvement")
        for r in cmp_["harmonics"]:
            print(f"   {r['harmonic']:<8d} {r['frequency_hz']:6.1f} Hz "
                  f"{r['amplitude_bias_off_uvrms']:10.4f} "
                  f"{r['amplitude_bias_on_uvrms']:12.4f} uVrms "
                  f"{r['improvement_db']:+9.2f} dB")
        print(f"\n  broadband (mains excluded)  off "
              f"{off['wide_rms_no_mains_uv']:.3f} -> on "
              f"{on['wide_rms_no_mains_uv']:.3f} uVrms "
              f"({cmp_['broadband_change_db']:+.2f} dB)")
        print(f"\n  {cmp_['note']}")

        cmrr = None
        if args.with_cmrr:
            brd.close()
            c_off = run_cmrr(args, bias_on=False)
            c_on = run_cmrr(args, bias_on=True)
            cmrr = (c_off, c_on) if c_off and c_on else None
            if cmrr:
                print("\n   CMRR gain from BIAS:")
                n_limited = 0
                for a, b in zip(c_off["rows"], c_on["rows"]):
                    delta = b["cmrr_median_db"] - a["cmrr_median_db"]
                    lim = a["at_measurement_ceiling"] or b["at_measurement_ceiling"]
                    n_limited += bool(lim)
                    print(f"     {a['frequency_hz']:7.2f} Hz  {delta:+7.2f} dB"
                          + ("   (>= : at the measurement ceiling)" if lim else ""))
                if n_limited:
                    print(f"\n   {n_limited} of {len(c_off['rows'])} points are "
                          "limited by the measurement, not by the board. Those "
                          "deltas are LOWER BOUNDS: the real improvement is at "
                          "least that large and cannot be read off this sweep.\n"
                          "   To turn them into measurements, raise "
                          "--cm-amplitude or --cmrr-seconds-per-point until "
                          "the ceiling clears the curve.")
            brd = boardmod.open_board(args, condition=args.condition)

        meta = boardmod.base_meta("04_bias", args, {
            "condition": args.condition,
            "seconds": args.seconds,
            "config3_bias_off": state_off,
            "config3_bias_on": state_on,
            "bias_off": {k: off[k] for k in
                         ("band_rms_uv", "wide_rms_uv", "wide_rms_no_mains_uv",
                          "harmonics")},
            "bias_on": {k: on[k] for k in
                        ("band_rms_uv", "wide_rms_uv", "wide_rms_no_mains_uv",
                         "harmonics")},
            "comparison": cmp_,
            "cmrr_included": bool(cmrr),
        })
        artifacts.write_json(args.out_dir, "04_bias", meta)
        artifacts.write_csv(args.out_dir, "04_bias", [
            {k: (round(v, 5) if isinstance(v, float) else v)
             for k, v in r.items()} for r in cmp_["harmonics"]])

        paths = vizstyle.render(
            lambda t: figure(t, off, on, cmp_, cmrr, meta),
            artifacts.fig_stem(args.out_dir, "04_bias"),
            vizstyle.resolve_themes(args.theme))
        vizstyle.log_written(paths)
        return 0
    finally:
        brd.close()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except gainguard.GainMismatch as exc:
        print(f"\n{'=' * 74}\n{exc}\n{'=' * 74}\n", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as exc:
        print(f"\n{'=' * 74}\n{exc}\n{'=' * 74}\n", file=sys.stderr)
        sys.exit(1)
