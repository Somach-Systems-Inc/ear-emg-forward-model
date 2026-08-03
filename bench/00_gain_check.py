#!/usr/bin/env python3
"""00 -- prove the voltage scale factor before trusting any other number.

Run this first, every session, before the board has been touched. It is the
only script whose entire output is "yes, a volt is a volt".

Two independent checks:

  REGISTER  Read CHnSET out of the ADS1299 and decode bits [6:4]. Catches a
            stale config.PGA_GAIN or a board that quietly returned to its
            factory gain of 24 after a power cycle.

  PHYSICAL  Put a known amplitude in, confirm the same number comes out.
            Catches everything the register check catches, plus a firmware
            that reports a gain it did not program, a VREF that is 4.0 V
            rather than 4.5 V, and a host scale factor that is wrong for some
            reason nobody has thought of yet.

The physical check has two sources:

  --source internal   The ADS1299's own test signal (CHnSET MUX = 101), a
                      square wave of +/-VREF/2400 = +/-1.875 mV. Needs NO
                      external hardware, so there is no excuse for skipping
                      it. This is the default.

  --source external   The Analog Discovery 3 driving the 1k/100R/20R divider,
                      which also validates the injection path the CMRR sweep
                      depends on.

Exit codes: 0 both checks pass. 1 a check failed -- read the message, it names
the gain your data is actually consistent with. 2 the bench is misconfigured.
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
        description="Verify the host gain constant against the hardware.",
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    boardmod.add_common_args(p)
    p.add_argument("--dump-registers", action="store_true",
                   help="print the decoded channel registers and exit")
    p.add_argument("--source", choices=("internal", "external", "none"),
                   default="internal",
                   help="physical check source (default internal test signal)")
    p.add_argument("--seconds", type=float, default=4.0,
                   help="capture length for the physical check")
    p.add_argument("--ad3-amplitude", type=float, default=1.0,
                   help="AD3 amplitude at the TOP of the divider, volts peak, "
                        "as MEASURED with the scope -- not as set on the "
                        "generator dial (--source external)")
    p.add_argument("--ad3-frequency", type=float, default=10.0,
                   help="AD3 frequency, Hz (--source external)")
    p.add_argument("--divider-tap", choices=("low", "mid"), default="low",
                   help="which divider tap feeds the board (--source external)")
    p.add_argument("--tolerance", type=float, default=0.10,
                   help="fractional tolerance on the physical check")
    return p


def dump_registers(brd) -> int:
    regs = brd.read_channel_registers()
    if not regs:
        print("No CHnSET registers came back. See the guard's message above.",
              file=sys.stderr)
        return 1
    print("\n  ch   CHnSET   gain   mux")
    print("  " + "-" * 34)
    for ch, reg in sorted(regs.items()):
        try:
            g = str(config.gain_from_chnset(reg))
        except ValueError:
            g = "RESERVED"
        print(f"  {ch + 1:<4} 0x{reg:02X}     {g:<6} {config.mux_from_chnset(reg)}")
    print(f"\n  config.PGA_GAIN = {config.PGA_GAIN} "
          f"({config.lsb_volts(config.PGA_GAIN) * 1e6:.5f} uV/count)\n")
    return 0


def measure_square_amplitude(volts: np.ndarray) -> np.ndarray:
    """Amplitude (volts peak) of a symmetric square wave, per channel.

    Uses the 25th/75th percentiles rather than min/max. A 50% duty square wave
    puts half its samples at each level, so those percentiles land on the two
    plateaus and are immune to the single worst noise sample -- which is what
    min/max would actually be measuring.
    """
    p25 = np.percentile(volts, 25, axis=0)
    p75 = np.percentile(volts, 75, axis=0)
    return (p75 - p25) / 2.0


def figure(t: vizstyle.Theme, trace_s, trace_v, expected_v, per_ch, meta,
           source_label: str):
    import matplotlib.pyplot as plt

    fig, (ax0, ax1) = plt.subplots(
        2, 1, figsize=(7.4, 6.2), height_ratios=(1.25, 1.0))

    # -- panel 1: the injected waveform, one channel, one series -> no legend
    ax0.plot(trace_s, trace_v * 1e3, color=t.color(0), linewidth=vizstyle.LINE_W)
    vizstyle.title_block(
        ax0, f"Injected {source_label}, channel 1",
        "host-scaled voltage against the amplitude that was applied")
    vizstyle.reference_line(ax0, expected_v * 1e3,
                            f"expected +{expected_v * 1e3:.3f} mV", t)
    vizstyle.reference_line(ax0, -expected_v * 1e3,
                            f"expected -{expected_v * 1e3:.3f} mV", t, va="top")
    ax0.set_xlabel("time (s)")
    ax0.set_ylabel("input-referred (mV)")

    # -- panel 2: per-channel recovered amplitude, one series -> no legend
    chans = np.arange(1, len(per_ch) + 1)
    ax1.bar(chans, per_ch * 1e3, width=0.55, color=t.color(0),
            edgecolor="none", zorder=3)
    vizstyle.reference_line(ax1, expected_v * 1e3, "expected", t)
    worst = int(np.argmax(np.abs(per_ch - expected_v)))
    err = (per_ch[worst] / expected_v - 1.0) * 100.0
    ax1.annotate(f"worst ch{worst + 1}  {err:+.2f}%",
                 xy=(chans[worst], per_ch[worst] * 1e3),
                 xytext=(0, 7), textcoords="offset points",
                 ha="center", fontsize=8.5, color=t.secondary)
    vizstyle.title_block(ax1, "Recovered amplitude per channel",
                         "a flat offset here is a scale-factor error; "
                         "one odd channel is a hardware fault")
    ax1.set_xlabel("channel")
    ax1.set_ylabel("amplitude (mV peak)")
    ax1.set_xticks(chans)

    vizstyle.stamp(fig, meta, t)
    return fig


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    artifacts.ensure_out(args.out_dir)
    boardmod.print_header("00  GAIN CHECK", args)

    if args.dump_registers:
        # Deliberately bypasses open_board(): the whole point is to see what
        # the board says when the host constant is wrong.
        if args.synthetic:
            brd = boardmod.SyntheticBoard(
                board_gain=args.synthetic_board_gain or config.PGA_GAIN,
                synth_cfg=boardmod.resolve_synth_config(args))
        else:
            if not args.port:
                print("--dump-registers needs --port or --synthetic",
                      file=sys.stderr)
                return 2
            brd = boardmod.SerialBoard(args.port, fs_hz=args.fs,
                                       n_channels=args.channels)
        try:
            return dump_registers(brd)
        finally:
            brd.close()

    brd = boardmod.open_board(args)
    try:
        if args.source == "none":
            print("\n  Register check only (--source none). The physical check "
                  "is what catches a firmware that lies about its own gain; "
                  "skipping it is a choice, not a default.")
            expected = measured = float("nan")
            per_ch = np.array([])
            trace_s = trace_v = np.array([])
            source_label = "nothing (register check only)"
        else:
            if args.source == "internal":
                source_label = "internal test signal"
                expected = config.test_signal_amplitude_v()
                if hasattr(brd, "set_mux"):
                    try:
                        brd.set_mux("test")
                    except NotImplementedError as exc:
                        print(f"\n  {exc}\n", file=sys.stderr)
                        return 2
                counts = brd.acquire(args.seconds)
                volts = gainguard.counts_to_volts(counts)
                per_ch = measure_square_amplitude(volts)
            else:
                source_label = (f"AD3 {args.ad3_frequency:g} Hz through the "
                                f"{args.divider_tap} divider tap")
                ratio = config.divider_ratio(tap=args.divider_tap)
                unc = config.divider_ratio_uncertainty(tap=args.divider_tap)
                expected = args.ad3_amplitude * ratio
                print(f"  divider ratio  1/{1 / ratio:.4f}  "
                      f"(+/-{unc * 100:.3f}% from 0.1% resistors)")
                print(f"  loading error  {config.divider_loading_error() * 100:.6f}% "
                      "(board input impedance vs the 20 R bottom leg)")
                print(f"  expected       {expected * 1e6:.2f} uV peak")
                if args.synthetic:
                    src = brd.source
                    brd.set_scenario(lambda s: src.tone(
                        s, args.ad3_frequency, expected, "differential"))
                else:
                    input(f"\n  Set the AD3 to {args.ad3_frequency:g} Hz, "
                          f"{args.ad3_amplitude:g} V peak into the divider, "
                          "confirm the amplitude on the scope, then press "
                          "Enter: ")
                counts = brd.acquire(args.seconds)
                volts = gainguard.counts_to_volts(counts)
                per_ch, _ = dsp.tone_amplitude_multichannel(
                    volts, args.fs, args.ad3_frequency)

            measured = float(np.median(per_ch))
            trace_n = min(len(counts), int(args.fs * 0.6))
            trace_s = np.arange(trace_n) / args.fs
            trace_v = volts[:trace_n, 0]

            print(f"\n  expected  {expected * 1e6:12.3f} uV")
            print(f"  measured  {measured * 1e6:12.3f} uV  "
                  f"(median of {len(per_ch)} channels)")
            print(f"  error     {(measured / expected - 1) * 100:+12.2f} %")

            gainguard.verify_gain_physically(
                measured, expected, tolerance=args.tolerance,
                source=source_label)

        meta = boardmod.base_meta("00_gain_check", args, {
            "physical_check_source": source_label,
            "expected_amplitude_v": None if np.isnan(expected) else expected,
            "measured_amplitude_v": None if np.isnan(measured) else measured,
            "per_channel_amplitude_uv": (per_ch * 1e6).tolist(),
            "tolerance": args.tolerance,
            "board": brd.describe(),
        })
        artifacts.write_json(args.out_dir, "00_gain_check", meta)

        if per_ch.size:
            paths = vizstyle.render(
                lambda t: figure(t, trace_s, trace_v, expected, per_ch, meta,
                                 source_label),
                artifacts.fig_stem(args.out_dir, "00_gain_check"),
                vizstyle.resolve_themes(args.theme))
            vizstyle.log_written(paths)

        print("\n  GAIN CHECK PASSED. Voltages from this session are trustworthy.\n")
        return 0
    finally:
        brd.close()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except gainguard.GainMismatch as exc:
        print(f"\n{'=' * 74}\n{exc}\n{'=' * 74}\n", file=sys.stderr)
        sys.exit(1)
