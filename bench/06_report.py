#!/usr/bin/env python3
"""06 -- one report: a single coherent figure set plus the numbers.

Reads whatever the measurement scripts left in out/data, checks that the
pieces actually belong together, and writes:

    out/report.md                     the numbers, with provenance at the top
    out/data/summary.csv              every headline figure, one per row
    out/figures/06_summary_*.png/pdf  the four-panel overview

It refuses to paper over three things:

  * A MISSING ARTIFACT is named, along with the exact command that produces
    it, and the report is marked incomplete. A report with a silently absent
    panel is how a measurement nobody made becomes a measurement everybody
    assumes was made.

  * ARTIFACTS THAT DISAGREE about gain, sample rate, mains frequency, or
    whether the data is synthetic are refused outright. Stitching a gain-8 run
    together with a gain-24 run produces a figure set whose panels are not
    comparable -- the same class of error the gain guard exists to prevent,
    one level up.

  * SYNTHETIC DATA is declared in the title, in the first line of the report,
    on every figure, and in the summary CSV. Not in a footnote.
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np

import artifacts
import config
import vizstyle

SHORT_LABELS = {"short": "shorted", "10k": "10 k / 10 k",
                "imbalance": "10 k / 11 k"}

REQUIRED = ["01_noise_floor_10k", "02_psd_mains", "03_cmrr", "05_ad8232"]
OPTIONAL = ["00_gain_check", "01_noise_floor_short", "01_noise_floor_imbalance",
            "04_bias"]


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Assemble the bench report from the measurement artifacts.",
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    p.add_argument("--out-dir", type=Path, default=config.OUT_DIR)
    p.add_argument("--theme", default="both", choices=("light", "dark", "both"))
    p.add_argument("--allow-incomplete", action="store_true",
                   help="write the report even when required artifacts are "
                        "missing. It will say so on its face.")
    return p


# ---------------------------------------------------------------------------

def load_all(out_dir: Path) -> dict[str, dict]:
    found = {}
    for name in REQUIRED + OPTIONAL:
        d = artifacts.read_json(out_dir, name)
        if d:
            found[name] = d
    return found


def summary_rows(found: dict) -> list[dict]:
    rows: list[dict] = []

    def add(section, metric, value, unit, note=""):
        rows.append({"section": section, "metric": metric,
                     "value": (round(value, 5) if isinstance(value, float)
                               else value),
                     "unit": unit, "note": note})

    gain_src = next(iter(found.values()), {})
    add("configuration", "host PGA gain", gain_src.get("host_pga_gain"), "",
        "config.PGA_GAIN")
    add("configuration", "scale factor",
        (gain_src.get("lsb_volts") or 0) * 1e6, "uV/count", "")
    add("configuration", "gain verified",
        str(gain_src.get("gain_verified")), "", gain_src.get("gain_check_method", ""))
    add("configuration", "data source", gain_src.get("source"), "", "")

    for cond in ("short", "10k", "imbalance"):
        d = found.get(f"01_noise_floor_{cond}")
        if not d:
            continue
        pc = d["per_channel"]["band_rms_uv"]
        add("noise floor", f"{cond}: median {config.NOISE_BAND_HZ[0]:g}-"
            f"{config.NOISE_BAND_HZ[1]:g} Hz", float(np.median(pc)), "uVrms",
            d["condition_label"])
        add("noise floor", f"{cond}: worst channel", float(np.max(pc)), "uVrms",
            f"ch{int(np.argmax(pc)) + 1}")
        add("noise floor", f"{cond}: expected",
            d["expected"]["expected_total_uv"], "uVrms",
            "thermal + datasheet estimate")
        add("noise floor", f"{cond}: verdict",
            "PASS" if d["verdict"]["pass"] else "FAIL", "", "")
    if ("01_noise_floor_10k" in found) and ("01_noise_floor_short" in found):
        a = np.median(found["01_noise_floor_10k"]["per_channel"]["band_rms_uv"])
        b = np.median(found["01_noise_floor_short"]["per_channel"]["band_rms_uv"])
        add("noise floor", "source-impedance penalty (10k / short)",
            float(a / b), "x", "invisible to a shorted-input test")

    d = found.get("02_psd_mains")
    if d:
        add("mains", "harmonics above floor", str(d["harmonics_present"]), "",
            f"threshold {d['prominence_threshold_db']:g} dB")
        for r in d["harmonics"]:
            add("mains", f"harmonic {r['harmonic']} ({r['frequency_hz']:.0f} Hz)",
                r["amplitude_uvrms"], "uVrms",
                f"{r['prominence_db']:.1f} dB above local floor")
        add("mains", "coupling hint", d["coupling_hint"], "", "")

    d = found.get("03_cmrr")
    if d:
        for r in d["rows"]:
            note = ("AT MEASUREMENT CEILING -- not a board measurement"
                    if r["at_measurement_ceiling"] else "")
            add("cmrr", f"{r['frequency_hz']:g} Hz", r["cmrr_median_db"], "dB",
                note)
        add("cmrr", "differential gain error",
            d["differential_gain_error_db"], "dB", d["differential_gain_note"])

    d = found.get("04_bias")
    if d:
        c = d["comparison"]
        add("bias", "fundamental improvement",
            c["fundamental_improvement_db"], "dB", c["note"])
        add("bias", "broadband change (mains excluded)",
            c["broadband_change_db"], "dB",
            "bias amplifier noise; a fall here is suspicious")
        for r in c["harmonics"]:
            add("bias", f"harmonic {r['harmonic']} improvement",
                r["improvement_db"], "dB", "")

    d = found.get("05_ad8232")
    if d:
        cer, ad = d["cerelog"], d["ad8232"]
        add("comparison", "Cerelog band noise", cer["band_rms_no_mains_uv"],
            "uVrms", f"{d['comparison_band_hz'][0]:g}-"
                     f"{d['comparison_band_hz'][1]:g} Hz, mains excluded")
        add("comparison", "AD8232 band noise", ad["band_rms_no_mains_uv"],
            "uVrms", "same band and analysis")
        add("comparison", "ratio",
            float(ad["band_rms_no_mains_uv"] /
                  max(cer["band_rms_no_mains_uv"], 1e-12)), "x", "")
        add("comparison", "AD8232 input-referred LSB",
            d["ad8232_chain"]["lsb_input_referred_uv"], "uV/count",
            f"gain {d['ad8232_chain']['total_gain']:g}, "
            f"{d['ad8232_chain']['adc_bits']}-bit")
        add("comparison", "AD8232 quantisation noise",
            d["ad8232_chain"]["quantisation_noise_uvrms"], "uVrms",
            "floor set by the digitiser, not the amplifier")
    return rows


# ---------------------------------------------------------------------------

def summary_figure(t: vizstyle.Theme, found: dict, meta: dict):
    """Four panels built entirely from the stored numbers.

    Deliberately not from raw spectra: the report must be reproducible from
    the artifacts alone, so a panel can never show something the numbers do
    not also say.
    """
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(2, 2, figsize=(12.6, 8.4))
    (axA, axB), (axC, axD) = axes

    # A -- per-channel noise, one bar series per condition
    conds = [c for c in ("short", "10k", "imbalance")
             if f"01_noise_floor_{c}" in found]
    if conds:
        width = 0.8 / len(conds)
        for i, c in enumerate(conds):
            d = found[f"01_noise_floor_{c}"]
            pc = np.asarray(d["per_channel"]["band_rms_uv"])
            x = np.arange(1, len(pc) + 1) + (i - (len(conds) - 1) / 2) * width
            vizstyle.bars(axA, x, pc, t, t.color(i), width=width,
                          label=SHORT_LABELS.get(c, c))
        lim = found[f"01_noise_floor_{conds[-1]}"]["expected"]["limit_uv"]
        vizstyle.reference_line(axA, lim, f"limit {lim:.2f} uV", t,
                                color=t.serious)
        axA.set_ylim(0, max(axA.get_ylim()[1] * 1.32, lim * 1.25))
        axA.set_xticks(np.arange(1, config.N_CHANNELS + 1))
        axA.set_xlabel("channel")
        axA.set_ylabel(f"{config.NOISE_BAND_HZ[0]:g}-"
                       f"{config.NOISE_BAND_HZ[1]:g} Hz noise (uVrms)")
        if len(conds) >= 2:
            vizstyle.legend(axA, t, loc="upper left", ncol=len(conds))
    vizstyle.title_block(axA, "A  Noise floor per channel",
                         "10 k loading is the number that predicts recordings")

    # B -- mains harmonics, bias off vs on when available
    d4, d2 = found.get("04_bias"), found.get("02_psd_mains")
    if d4:
        rows = d4["comparison"]["harmonics"]
        ks = np.array([r["harmonic"] for r in rows])
        vizstyle.bars(axB, ks - 0.13, [r["amplitude_bias_off_uvrms"] for r in rows],
                      t, t.color(0), width=0.26, label="BIAS off")
        vizstyle.bars(axB, ks + 0.13, [r["amplitude_bias_on_uvrms"] for r in rows],
                      t, t.color(1), width=0.26, label="BIAS on")
        vizstyle.category_axis(axB, ks)
        vizstyle.legend(axB, t, loc="upper right")
        sub = d4["comparison"]["note"]
    elif d2:
        rows = d2["harmonics"]
        ks = np.array([r["harmonic"] for r in rows])
        vizstyle.bars(axB, ks, [r["amplitude_uvrms"] for r in rows], t,
                      t.color(0), width=0.34)
        vizstyle.category_axis(axB, ks)
        sub = d2["coupling_hint"]
    else:
        sub = "no mains artifact"
    axB.set_xlabel(f"harmonic of {meta['mains_hz']:.0f} Hz")
    axB.set_ylabel("amplitude (uVrms)")
    vizstyle.title_block(axB, "B  Mains harmonics", sub[:96])

    # C -- CMRR with its measurement ceiling
    d3 = found.get("03_cmrr")
    if d3:
        f = np.array([r["frequency_hz"] for r in d3["rows"]])
        med = np.array([r["cmrr_median_db"] for r in d3["rows"]])
        ceil = np.array([r["measurement_ceiling_db"] for r in d3["rows"]])
        axC.semilogx(f, med, color=t.color(0), linewidth=vizstyle.LINE_W,
                     zorder=4)
        axC.semilogx(f, ceil, color=t.serious,
                     linewidth=vizstyle.HAIRLINE_W * 1.6, zorder=3)
        vizstyle.dot(axC, f[-1], med[-1], t, t.color(0))
        vizstyle.end_label(axC, f[-1], med[-1], f"{med[-1]:.0f} dB", t)
        vizstyle.legend(axC, t, handles=[
            vizstyle.key_handle("CMRR (median channel)", t.color(0)),
            vizstyle.key_handle("measurement ceiling", t.serious)],
            loc="lower left")
        at_mains = [r for r in d3["rows"]
                    if abs(r["frequency_hz"] - meta["mains_hz"]) < 1e-6]
        sub = (f"{at_mains[0]['cmrr_median_db']:.1f} dB at "
               f"{meta['mains_hz']:.0f} Hz" if at_mains
               else "no point at the mains frequency")
    else:
        sub = "no CMRR artifact"
    axC.set_xlabel("frequency (Hz)")
    axC.set_ylabel("CMRR (dB)")
    vizstyle.title_block(axC, "C  Common-mode rejection", sub)

    # D -- device comparison per EEG band
    d5 = found.get("05_ad8232")
    if d5:
        cer = d5["cerelog"]["eeg_bands_uv"]
        ad = d5["ad8232"]["eeg_bands_uv"]
        names = [n for n in config.EEG_BANDS_HZ if n in cer and n in ad]
        x = np.arange(len(names))
        vizstyle.bars(axD, x - 0.19, [cer[n] for n in names], t, t.color(0),
                      width=0.38, label="Cerelog ESP-EEG")
        vizstyle.bars(axD, x + 0.19, [ad[n] for n in names], t, t.color(1),
                      width=0.38, label="AD8232 chain")
        axD.set_xticks(x)
        axD.set_xticklabels(names)
        vizstyle.legend(axD, t, loc="upper left")
        ratio = (d5["ad8232"]["band_rms_no_mains_uv"] /
                 max(d5["cerelog"]["band_rms_no_mains_uv"], 1e-12))
        sub = f"AD8232 is {ratio:.1f}x noisier in band; each divided by its own chain"
    else:
        sub = "no comparison artifact"
    axD.set_ylabel("noise in band (uVrms)")
    vizstyle.title_block(axD, "D  Against the AD8232", sub)

    # fig.text rather than suptitle: constrained_layout reserves a generous
    # band for a suptitle and the panels ended up floating a long way below it.
    fig.text(0.006, 0.985, "Cerelog ESP-EEG characterisation summary",
             fontsize=13, fontweight="bold", ha="left", va="top", color=t.ink)
    vizstyle.stamp(fig, meta, t, top=0.955)
    return fig


# ---------------------------------------------------------------------------

def md_table(rows: list[dict], fields: list[str]) -> str:
    if not rows:
        return "_no data_\n"
    out = ["| " + " | ".join(fields) + " |",
           "|" + "|".join("---" for _ in fields) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(r.get(f, "")) for f in fields) + " |")
    return "\n".join(out) + "\n"


def write_report(out_dir: Path, found: dict, rows: list[dict],
                 missing: list[tuple[str, str]], figures: list[Path]) -> Path:
    meta = next(iter(found.values()), {})
    synthetic = any(d.get("synthetic") for d in found.values())
    unverified = [n for n, d in found.items() if not d.get("gain_verified")]

    L: list[str] = []
    L.append("# Cerelog ESP-EEG characterisation report\n")
    if synthetic:
        L.append("> **SYNTHETIC DATA.** Every number below came from the model "
                 "in `bench/synth.py`, not from hardware. It is here to prove "
                 "the analysis runs end to end; it is not a measurement of "
                 "anything physical.\n")
    if unverified:
        L.append("> **GAIN NOT VERIFIED** for: " + ", ".join(sorted(unverified)) +
                 ". Every voltage in those sections is provisional.\n")
    if missing:
        L.append("> **INCOMPLETE.** Missing artifacts:\n>\n" +
                 "\n".join(f"> - `{n}` -- produce with `{cmd}`"
                           for n, cmd in missing) + "\n")

    L.append("## Configuration\n")
    L.append(f"- Host PGA gain: **{meta.get('host_pga_gain')}** "
             f"(`config.PGA_GAIN`, the only declaration in the repo)")
    L.append(f"- Scale factor: **{(meta.get('lsb_volts') or 0) * 1e6:.5f} "
             f"uV/count** at VREF {meta.get('vref_v')} V")
    L.append(f"- Board reported gain: {meta.get('board_pga_gain')} "
             f"(via {meta.get('gain_check_method')})")
    L.append(f"- Sample rate: {meta.get('fs_hz')} SPS   ")
    L.append(f"- Mains: {meta.get('mains_hz')} Hz")
    L.append(f"- Source: {meta.get('source')}")
    L.append(f"- Suite {meta.get('suite_version')}, git "
             f"`{meta.get('git_revision')}`")
    L.append(f"- Written {datetime.now(timezone.utc).isoformat(timespec='seconds')}\n")

    for section, heading in (
            ("noise floor", "## 01 Noise floor (electrode-equivalent loading)"),
            ("mains", "## 02 Mains harmonics"),
            ("cmrr", "## 03 CMRR against frequency"),
            ("bias", "## 04 BIAS drive on against off"),
            ("comparison", "## 05 Against the AD8232")):
        sec = [r for r in rows if r["section"] == section]
        if not sec:
            continue
        L.append(heading + "\n")
        L.append(md_table(sec, ["metric", "value", "unit", "note"]))

    L.append("## Figures\n")
    for p in sorted(figures):
        L.append(f"- `{p.relative_to(out_dir.parent) if out_dir.parent in p.parents else p.name}`")
    L.append("")

    L.append("## How to read these numbers\n")
    L.append("- The noise floor under **10 k loading** is the one that "
             "predicts real recordings. The shorted figure is the amplifier "
             "alone and is always better; the gap between them is the "
             "source-impedance penalty.")
    L.append("- A **CMRR point sitting at the measurement ceiling** is a "
             "measurement of the capture length, not of the board. Raise the "
             "common-mode drive or record longer.")
    L.append("- The **differential gain error** in section 03 is an "
             "independent check on the voltage scale. A flat offset of "
             "+9.54 dB means the board is at gain 24 while the host is "
             "scaling as gain 8.")
    L.append("- **BIAS improving mains while the broadband floor also falls** "
             "is suspicious: the bias amplifier adds noise, so the floor "
             "normally rises a little.")
    L.append("- In the AD8232 comparison, check the **quantisation floor** "
             "before crediting or blaming the amplifier.\n")

    path = out_dir / "report.md"
    path.write_text("\n".join(L))
    print(f"  wrote {path}")
    return path


# ---------------------------------------------------------------------------

def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    artifacts.ensure_out(args.out_dir)
    print(f"\n{'-' * 74}\n06  REPORT\n  reading {args.out_dir}\n{'-' * 74}")

    found = load_all(args.out_dir)
    if not found:
        print("\n  Nothing to report on. Run the measurement scripts first:\n" +
              "\n".join(f"    {c}" for c in artifacts.PRODUCERS.values()),
              file=sys.stderr)
        return 1

    conflicts = artifacts.provenance_conflicts(found.values())
    hard = [c for c in conflicts if not c.startswith("gain was never verified")]
    if hard:
        print("\n  REFUSING TO BUILD ONE REPORT OUT OF THESE ARTIFACTS:\n" +
              "\n".join(f"    - {c}" for c in conflicts) +
              "\n\n  These runs do not describe the same instrument. Delete or "
              "move the stale ones out of out/data and re-run the affected "
              "scripts, so every panel is measuring the same thing.",
              file=sys.stderr)
        return 1
    for c in conflicts:
        print(f"  note: {c}")

    missing = artifacts.missing(args.out_dir, REQUIRED)
    if missing and not args.allow_incomplete:
        print("\n  MISSING REQUIRED ARTIFACTS:\n" +
              "\n".join(f"    {n}\n      produce with: {cmd}"
                        for n, cmd in missing) +
              "\n\n  Re-run those, or pass --allow-incomplete to write a "
              "report that says on its face what is absent.", file=sys.stderr)
        return 1

    rows = summary_rows(found)
    with (Path(args.out_dir) / "data" / "summary.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["section", "metric", "value",
                                           "unit", "note"])
        w.writeheader()
        w.writerows(rows)
    print(f"  wrote {Path(args.out_dir) / 'data' / 'summary.csv'}")

    meta = dict(next(iter(found.values())))
    meta["script"] = "06_report"
    figs = vizstyle.render(
        lambda t: summary_figure(t, found, meta),
        artifacts.fig_stem(args.out_dir, "06_summary"),
        vizstyle.resolve_themes(args.theme), also_pdf=True)
    vizstyle.log_written(figs)

    all_figs = sorted((Path(args.out_dir) / "figures").glob("*.png")) + list(figs)
    write_report(args.out_dir, found, rows, missing, sorted(set(all_figs)))

    print(f"\n  {len(found)} artifacts, {len(rows)} numbers, "
          f"{len(set(all_figs))} figures."
          + (f"  INCOMPLETE: {len(missing)} missing." if missing else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
