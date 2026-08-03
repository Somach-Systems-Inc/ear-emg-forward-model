#!/usr/bin/env python3
"""Self-test: run every analysis path against synthetic input with known answers.

This is the file that makes the claim "it will work on 6 August" checkable
rather than hopeful. It does three kinds of test:

  UNIT      the arithmetic that everything else rests on -- scale factors,
            divider ratios, Johnson noise, the register-dump parser, the
            tone and band estimators.

  RECOVERY  every measurement script is run end to end in --synthetic mode
            and the number it reports is compared against the number that was
            injected. A CMRR analysis that is subtly wrong still produces a
            plausible-looking curve; the only way to catch it is to know the
            answer in advance.

  GUARD     the gain guard is made to fire. A guard nobody has seen fire is
            not known to work. Failing to fire is a test failure here.

    python bench/selftest.py            run everything
    python bench/selftest.py --quick    unit and guard tests only

Exit 0 means every path ran and every recovered number matched.
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path

BENCH = Path(__file__).resolve().parent
sys.path.insert(0, str(BENCH))

import numpy as np

import board as boardmod
import config
import dsp
import gainguard
import synth

PASS, FAIL = [], []


def check(name: str, condition: bool, detail: str = "") -> None:
    (PASS if condition else FAIL).append(name)
    mark = "ok  " if condition else "FAIL"
    print(f"  [{mark}] {name}" + (f"   {detail}" if detail else ""))


def close(name: str, got: float, want: float, tol: float, unit: str = "") -> None:
    ok = abs(got - want) <= tol
    check(name, ok, f"got {got:.5g}{unit}, want {want:.5g}{unit} "
                    f"(+/-{tol:.3g}{unit})")


def section(title: str) -> None:
    print(f"\n{title}\n{'-' * len(title)}")


# ===========================================================================
# UNIT
# ===========================================================================

def unit_tests() -> None:
    section("UNIT -- the arithmetic everything else rests on")

    close("gain 24 scale factor is the familiar 0.02235 uV/count",
          config.lsb_volts(24) * 1e6, 0.02235, 0.00002, " uV")
    close("gain 8 / gain 24 scale factors differ by exactly 3",
          config.lsb_volts(8) / config.lsb_volts(24), 3.0, 1e-9, "x")
    check("every legal gain has a distinct CHnSET code",
          len(set(config.GAIN_CODES.values())) == len(config.VALID_GAINS))
    check("gain round-trips through the CHnSET encoding",
          all(config.gain_from_chnset(config.GAIN_CODES[g] << 4) == g
              for g in config.VALID_GAINS))
    try:
        config.gain_from_code(0b111)
        check("reserved gain code 0b111 is rejected", False)
    except ValueError:
        check("reserved gain code 0b111 is rejected", True)

    close("divider low tap is 20/1120", config.divider_ratio(tap="low"),
          20.0 / 1120.0, 1e-12)
    close("divider mid tap is 120/1120", config.divider_ratio(tap="mid"),
          120.0 / 1120.0, 1e-12)
    # 0.13%, not 0.1%: the 1 k resistor's 0.1% is 1 ohm against a 1120 ohm
    # chain, and that absolute error dominates. Worth stating, because
    # "0.1% parts" is routinely misread as "0.1% ratio".
    close("divider ratio uncertainty", config.divider_ratio_uncertainty() * 100,
          0.133, 0.01, "%")
    check("divider ratio uncertainty stays well under the CMRR error budget",
          config.divider_ratio_uncertainty() < 2e-3,
          f"{config.divider_ratio_uncertainty() * 100:.4f}% = "
          f"{20 * math.log10(1 + config.divider_ratio_uncertainty()):.4f} dB")
    check("board input impedance does not load the divider",
          config.divider_loading_error() < 1e-5,
          f"{config.divider_loading_error() * 100:.7f}%")
    close("10 k Johnson noise density at 22 C",
          config.johnson_noise_density(10_000.0) * 1e9, 12.76, 0.15, " nV/rtHz")
    close("differential 10 k + 10 k Johnson density",
          config.johnson_noise_density(
              config.differential_source_resistance()) * 1e9,
          18.05, 0.2, " nV/rtHz")
    close("internal test signal is VREF/2400",
          config.test_signal_amplitude_v() * 1e3, 1.875, 0.001, " mV")

    # --- register dump parser, three dialects
    dumps = {
        "OpenBCI style": "ADS1299 Registers\nCH1SET, 05, 60, 01100000\n"
                         "CH2SET, 06, 60, 01100000\n",
        "hex assignment": "CH1SET = 0x60\nCH2SET = 0x60\n",
        "colon decimal-hex": "CH1SET: 60\nCH2SET: 60\n",
    }
    for label, text in dumps.items():
        regs = boardmod.parse_register_dump(text)
        ok = (len(regs) == 2 and
              all(config.gain_from_chnset(v) == 24 for v in regs.values()))
        check(f"register parser handles {label}", ok, str(regs))
    check("register parser ignores lines with no CHnSET",
          boardmod.parse_register_dump("CONFIG1, 01, 96\nnoise\n") == {})
    named = boardmod.parse_named_registers(
        "CONFIG3, 03, E4, 11100100\nCONFIG1, 01, 96, 10010110\n")
    check("named register parser finds CONFIG3",
          named.get("CONFIG3") == 0xE4, f"{named}")
    check("CONFIG3 0xE4 decodes as BIAS enabled",
          bool(named.get("CONFIG3", 0) & config.CONFIG3_PD_BIAS_BIT))

    # --- estimators, against signals whose answer is known exactly
    fs = 250.0
    n = int(fs * 40)
    t = np.arange(n) / fs
    amp, f0 = 3.7e-6, 17.3
    x = amp * np.sin(2 * math.pi * f0 * t + 0.9) + 1e-4  # plus a DC offset
    got, f_used = dsp.tone_amplitude(x, fs, f0 * 1.0004)
    close("tone amplitude recovered from a clean sine", got * 1e6, amp * 1e6,
          amp * 1e6 * 0.01, " uV")
    close("tone frequency refined onto the true frequency", f_used, f0, 0.01,
          " Hz")

    rng = np.random.default_rng(7)
    density = 40e-9
    w = synth.white(density, n, fs, rng)
    band = (1.0, 100.0)
    want = density * math.sqrt(band[1] - band[0])
    close("band RMS of white noise matches density x sqrt(BW)",
          float(dsp.band_rms_of_signal(w, fs, band)) * 1e6, want * 1e6,
          want * 1e6 * 0.08, " uV")

    y = w + amp * np.sin(2 * math.pi * 60.0 * t)
    f, pxx = dsp.welch_psd(y, fs)
    rms, _ = dsp.tone_rms_from_psd(f, pxx, 60.0)
    close("tone RMS recovered from the PSD peak", rms * 1e6,
          amp / math.sqrt(2) * 1e6, amp / math.sqrt(2) * 1e6 * 0.05, " uV")

    keep = dsp.mains_mask(f, 60.0, f_max=float(f[-1]))
    masked = float(dsp.band_rms(f, pxx, band, mask=keep))
    check("masking the mains bins removes the tone from the band RMS",
          masked < float(dsp.band_rms(f, pxx, band)) and
          abs(masked - want) / want < 0.12,
          f"{masked * 1e6:.4f} vs unmasked "
          f"{float(dsp.band_rms(f, pxx, band)) * 1e6:.4f} uVrms")

    close("CMRR arithmetic", float(dsp.cmrr_db(1.0, 1e-6)), 120.0, 1e-9, " dB")


# ===========================================================================
# GUARD
# ===========================================================================

def guard_tests() -> None:
    section("GUARD -- the gain guard must actually fire")

    gainguard.reset()
    try:
        gainguard.counts_to_volts(np.array([1, 2, 3]))
        check("counts_to_volts refuses before the gain is checked", False)
    except gainguard.GainNotVerified:
        check("counts_to_volts refuses before the gain is checked", True)

    gainguard.reset()
    good = boardmod.SyntheticBoard(board_gain=config.PGA_GAIN)
    v = gainguard.verify_gain(good)
    check("matching board passes the register check",
          v.verified and v.board_gain == config.PGA_GAIN)
    close("verified scale factor equals config.lsb_volts",
          v.lsb_volts, config.lsb_volts(config.PGA_GAIN), 1e-18)

    gainguard.reset()
    bad = boardmod.SyntheticBoard(board_gain=24 if config.PGA_GAIN != 24 else 8)
    try:
        gainguard.verify_gain(bad)
        check("mismatched board is REFUSED", False)
    except gainguard.GainMismatch as exc:
        msg = str(exc)
        check("mismatched board is REFUSED", True)
        check("the refusal names both gains",
              str(config.PGA_GAIN) in msg and str(bad.board_gain) in msg)
        check("the refusal states the error factor",
              "wrong by" in msg)
        check("the refusal says what to check, not just that it failed",
              "WHAT TO CHECK" in msg)

    gainguard.reset()
    mixed = boardmod.SyntheticBoard(board_gain=config.PGA_GAIN)
    real = mixed.read_channel_registers
    mixed.read_channel_registers = lambda: {
        **real(), 3: (config.GAIN_CODES[24] << 4)}
    try:
        gainguard.verify_gain(mixed)
        check("channels at different gains are REFUSED", False)
    except gainguard.GainMismatch as exc:
        check("channels at different gains are REFUSED",
              "DIFFERENT GAINS" in str(exc))

    gainguard.reset()

    class Silent:
        def describe(self):
            return {"kind": "test", "detail": "silent firmware"}

        def read_channel_registers(self):
            return {}

    try:
        gainguard.verify_gain(Silent())
        check("a board that reports no registers is REFUSED", False)
    except gainguard.GainMismatch as exc:
        check("a board that reports no registers is REFUSED",
              "NO REGISTERS" in str(exc))

    # Physical check: a 3x-wrong scale must be named as gain 24.
    gainguard.reset()
    gainguard.mark_unverified("selftest")
    expected = config.test_signal_amplitude_v()
    try:
        gainguard.verify_gain_physically(expected * 3.0, expected)
        check("physical check catches a 3x scale error", False)
    except gainguard.GainMismatch as exc:
        msg = str(exc)
        check("physical check catches a 3x scale error", True)
        check("physical check NAMES the gain the data implies",
              "CONSISTENT WITH GAIN 24" in msg,
              [l for l in msg.splitlines() if "CONSISTENT" in l])

    gainguard.reset()
    gainguard.mark_unverified("selftest")
    v = gainguard.verify_gain_physically(expected * 1.02, expected)
    check("physical check passes within tolerance", v.verified)

    gainguard.reset()
    v = gainguard.mark_unverified("no register query on this firmware")
    check("mark_unverified leaves the verdict unverified", not v.verified)
    check("the unverified reason survives into metadata",
          "no register query" in v.as_meta()["unverified_reason"])

    gainguard.reset()
    try:
        gainguard.inherit({"host_pga_gain": config.PGA_GAIN + 100})
        check("re-analysing a recording made at another gain is REFUSED", False)
    except gainguard.GainMismatch:
        check("re-analysing a recording made at another gain is REFUSED", True)

    gainguard.reset()


# ===========================================================================
# RECOVERY -- run the real scripts, compare against what was injected
# ===========================================================================

def run(script: str, *args: str, out: Path, expect: int = 0) -> tuple[int, str]:
    cmd = [sys.executable, str(BENCH / script), "--synthetic",
           "--out-dir", str(out), "--theme", "light", *args]
    r = subprocess.run(cmd, capture_output=True, text=True)
    ok = r.returncode == expect
    check(f"{script} exits {expect}", ok,
          "" if ok else (r.stderr or r.stdout)[-400:])
    return r.returncode, r.stdout + r.stderr


def load(out: Path, name: str) -> dict:
    p = out / "data" / f"{name}.json"
    return json.loads(p.read_text()) if p.exists() else {}


def recovery_tests(out: Path) -> None:
    model = synth.SynthConfig()
    section("RECOVERY -- every script, end to end, against known answers")

    # -- 00 gain check
    run("00_gain_check.py", out=out)
    d = load(out, "00_gain_check")
    check("00 wrote a gain-check artifact", bool(d))
    if d:
        close("00 recovers the internal test-signal amplitude",
              d["measured_amplitude_v"] * 1e6,
              config.test_signal_amplitude_v() * 1e6, 5.0, " uV")
        check("00 marks the run gain-verified", d["gain_verified"])

    rc, msg = run("00_gain_check.py", "--synthetic-board-gain",
                  "24" if config.PGA_GAIN != 24 else "8", out=out, expect=1)
    check("00 refuses a board whose gain disagrees with config.py",
          "GAIN MISMATCH" in msg)

    # -- 01 noise floor, all three fixtures
    run("01_noise_floor.py", "--condition", "all", "--seconds", "60", out=out)
    short = load(out, "01_noise_floor_short")
    tenk = load(out, "01_noise_floor_10k")
    if short and tenk:
        s = float(np.median(short["per_channel"]["band_rms_uv"]))
        k = float(np.median(tenk["per_channel"]["band_rms_uv"]))
        exp_amp = config.EXPECTED_INPUT_NOISE_URMS[config.PGA_GAIN]
        close("01 shorted noise lands on the modelled amplifier noise",
              s, exp_amp, exp_amp * 0.25, " uVrms")
        want_10k = math.hypot(exp_amp, tenk["expected"]["thermal_rms_uv"])
        close("01 10 k noise equals amplifier + Johnson in quadrature",
              k, want_10k, want_10k * 0.25, " uVrms")
        check("01 shows a source-impedance penalty a short cannot show",
              k > s * 1.05, f"10k/short = {k / s:.3f}x")
        check("01 passes its own limit on synthetic data",
              tenk["verdict"]["pass"] and short["verdict"]["pass"])
        check("01 stores raw counts alongside the metadata",
              (out / "data" / "01_raw_10k.npz").exists())

    # -- 02 mains harmonics
    run("02_psd_mains.py", "--seconds", "120", out=out)
    d = load(out, "02_psd_mains")
    if d and d["harmonics"]:
        want = model.mains.amplitude_v / math.sqrt(2) * 1e6
        got = d["harmonics"][0]["amplitude_uvrms"]
        close("02 recovers the injected mains fundamental", got, want,
              want * 0.05, " uVrms")
        k2 = [r for r in d["harmonics"] if r["harmonic"] == 2]
        if k2:
            want2 = want * model.mains.harmonic_decay
            close("02 recovers the 2nd harmonic", k2[0]["amplitude_uvrms"],
                  want2, want2 * 0.08, " uVrms")
        check("02 flags the fundamental as present",
              1 in d["harmonics_present"])

    # -- 02 re-analysis path
    run("02_psd_mains.py", "--from-recording",
        str(out / "data" / "01_raw_10k"), out=out)

    # -- 03 CMRR
    run("03_cmrr_sweep.py", "--seconds-per-point", "8", out=out)
    d = load(out, "03_cmrr")
    if d:
        worst = 0.0
        for r in d["rows"]:
            want = float(model.cmrr.cmrr_db(r["frequency_hz"]))
            worst = max(worst, abs(r["cmrr_median_db"] - want))
        check("03 recovers the injected CMRR curve at every frequency",
              worst < 1.5, f"worst error {worst:.2f} dB")
        check("03 finds no scale error on a correctly scaled board",
              abs(d["differential_gain_error_db"]) < 1.0,
              f"{d['differential_gain_error_db']:+.3f} dB")
        check("03 reports a measurement ceiling above the measurement",
              all(r["measurement_ceiling_db"] > r["cmrr_median_db"]
                  for r in d["rows"]))

    # With BIAS on, the leaked differential drops below the detection floor,
    # so the sweep MUST report those points as ceiling-limited rather than as
    # a spectacular CMRR. A ceiling detector that never fires is not a
    # detector.
    run("03_cmrr_sweep.py", "--bias", "--tag", "03_cmrr_bias",
        "--seconds-per-point", "6", out=out)
    d = load(out, "03_cmrr_bias")
    if d:
        check("03 flags CMRR points limited by the measurement, not the board",
              bool(d["points_at_ceiling"]),
              f"{len(d['points_at_ceiling'])} of {len(d['rows'])} points")

    # -- 04 bias
    run("04_bias_on_off.py", "--seconds", "90", out=out)
    d = load(out, "04_bias")
    if d:
        want = float(model.bias.benefit_db(model.mains.f0_hz))
        got = d["comparison"]["fundamental_improvement_db"]
        close("04 recovers the injected bias benefit at the fundamental",
              got, want, 2.0, " dB")
        check("04 confirmed the bias toggle from CONFIG3",
              d["config3_bias_on"]["pd_bias"] is True and
              d["config3_bias_off"]["pd_bias"] is False)
        check("04 shows the broadband floor RISING with bias, as modelled",
              d["comparison"]["broadband_change_db"] > 0,
              f"{d['comparison']['broadband_change_db']:+.2f} dB")

    # -- 05 AD8232
    run("05_ad8232_compare.py", "--seconds", "90", out=out)
    d = load(out, "05_ad8232")
    if d:
        ratio = (d["ad8232"]["band_rms_no_mains_uv"] /
                 d["cerelog"]["band_rms_no_mains_uv"])
        check("05 shows the AD8232 chain as the noisier of the two",
              ratio > 5.0, f"{ratio:.1f}x")
        close("05 computes the AD8232 input-referred LSB",
              d["ad8232_chain"]["lsb_input_referred_uv"],
              3.3 / 4096 / 1100 * 1e6, 1e-4, " uV")
        check("05 normalises both devices to input-referred volts",
              d["cerelog"]["band_rms_no_mains_uv"] < 1.0,
              f"cerelog {d['cerelog']['band_rms_no_mains_uv']:.4f} uVrms")

    # -- 06 report
    rc, _ = subprocess.run(
        [sys.executable, str(BENCH / "06_report.py"), "--out-dir", str(out),
         "--theme", "light"], capture_output=True, text=True).returncode, None
    check("06_report.py exits 0", rc == 0)
    report = out / "report.md"
    check("06 wrote report.md", report.exists())
    if report.exists():
        text = report.read_text()
        check("06 declares synthetic data in the report body",
              "SYNTHETIC DATA" in text)
        check("06 states the gain and scale factor",
              f"gain: **{config.PGA_GAIN}**" in text)
    check("06 wrote the summary CSV",
          (out / "data" / "summary.csv").exists())
    check("06 wrote the summary figure",
          (out / "figures" / "06_summary_light.png").exists())

    n_figs = len(list((out / "figures").glob("*.png")))
    check("every script produced a figure", n_figs >= 6, f"{n_figs} PNGs")

    # -- 06 must refuse artifacts that disagree about the gain
    mixed = out / "mixed"
    shutil.copytree(out / "data", mixed / "data")
    (mixed / "figures").mkdir(parents=True, exist_ok=True)
    p = mixed / "data" / "02_psd_mains.json"
    j = json.loads(p.read_text())
    j["host_pga_gain"] = config.PGA_GAIN + 4
    p.write_text(json.dumps(j))
    r = subprocess.run([sys.executable, str(BENCH / "06_report.py"),
                        "--out-dir", str(mixed)], capture_output=True, text=True)
    check("06 refuses to merge artifacts recorded at different gains",
          r.returncode != 0 and "REFUSING" in (r.stderr + r.stdout))

    # -- 06 must name what is missing rather than quietly omitting it
    sparse = out / "sparse"
    (sparse / "data").mkdir(parents=True, exist_ok=True)
    shutil.copy(out / "data" / "02_psd_mains.json", sparse / "data")
    r = subprocess.run([sys.executable, str(BENCH / "06_report.py"),
                        "--out-dir", str(sparse)], capture_output=True, text=True)
    out_txt = r.stderr + r.stdout
    check("06 refuses an incomplete report by default",
          r.returncode != 0 and "MISSING REQUIRED" in out_txt)
    check("06 names the command that produces each missing artifact",
          "01_noise_floor.py" in out_txt)


# ===========================================================================

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--quick", action="store_true",
                    help="unit and guard tests only, no subprocess runs")
    ap.add_argument("--keep", action="store_true",
                    help="keep the temporary output directory")
    args = ap.parse_args(argv)

    print(f"\nbench selftest -- suite {config.SUITE_VERSION}, "
          f"config.PGA_GAIN = {config.PGA_GAIN}")

    tmp = Path(tempfile.mkdtemp(prefix="bench-selftest-"))
    try:
        unit_tests()
        guard_tests()
        if not args.quick:
            recovery_tests(tmp)
        else:
            print("\n  (--quick: skipped the end-to-end recovery tests)")
    except Exception:
        traceback.print_exc()
        FAIL.append("selftest crashed")
    finally:
        if args.keep:
            print(f"\n  output kept in {tmp}")
        else:
            shutil.rmtree(tmp, ignore_errors=True)

    print(f"\n{'=' * 74}")
    if FAIL:
        print(f"{len(FAIL)} FAILED, {len(PASS)} passed\n")
        for f in FAIL:
            print(f"  FAILED: {f}")
        print(f"{'=' * 74}\n")
        return 1
    print(f"all {len(PASS)} checks passed\n{'=' * 74}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
