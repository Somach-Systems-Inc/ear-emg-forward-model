# Cerelog ESP-EEG characterisation suite

Bench characterisation for the Cerelog ESP-EEG (ADS1299 front end, ESP32 host),
written before the board arrives so that the day it lands is spent collecting
data rather than debugging analysis code.

Every analysis path in here has already been run end to end against a synthetic
front end with known answers. `python bench/selftest.py` executes all of it and
checks that each script recovers the number that was injected.

---

## The one rule

**The board ships at PGA gain 24. Carl runs it at 8. Those differ by exactly
3.000x, and a 3x-wrong microvolt trace looks completely normal.**

- The host-side gain is declared in exactly one place: `PGA_GAIN` in
  [`config.py`](config.py).
- There is deliberately **no `--gain` flag and no environment variable**. A
  second place to set it is a second place for it to go stale.
- Every script verifies that constant against the hardware before it records
  anything, and `gainguard.counts_to_volts()` raises if the check has not run.
  There is no path from ADC counts to a voltage in this suite that skips it.
- Recordings are stored as **raw ADC counts** with the gain in a sidecar JSON,
  so a scale-factor mistake is always recoverable. Never multiply a saved
  voltage; re-derive it from counts.

When you change the gain on the board, change that line in the same sitting.
The guard will tell you loudly if you forget:

```
GAIN MISMATCH -- REFUSING TO RECORD

  host  config.PGA_GAIN = 8   -> 0.06706 uV/count
  board CHnSET gain  = 24  -> 0.02235 uV/count
  every voltage this suite produces would be wrong by 3.000x
  ...
```

`00_gain_check.py` goes further and checks the scale factor *physically*, by
injecting a known amplitude and confirming the same number comes back. When
that fails it names the gain your data is actually consistent with.

---

## Install and verify, today, with no hardware

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r bench/requirements.txt

python bench/selftest.py          # ~2 min: unit, guard and recovery tests
```

Then run the whole protocol against the synthetic front end:

```bash
python bench/00_gain_check.py    --synthetic
python bench/01_noise_floor.py   --synthetic --condition all
python bench/02_psd_mains.py     --synthetic
python bench/03_cmrr_sweep.py    --synthetic
python bench/04_bias_on_off.py   --synthetic
python bench/05_ad8232_compare.py --synthetic
python bench/06_report.py
```

Artifacts land in `bench/out/`: `data/*.json` and `*.csv`, `figures/*.png`,
`figures/06_summary_*.pdf`, and `report.md`. Every synthetic figure carries a
`SYNTHETIC` badge; that is not decoration, it is there so a modelled figure can
never be mistaken for a measurement.

Prove the guard works before you trust it:

```bash
python bench/00_gain_check.py --synthetic --synthetic-board-gain 24   # must fail
```

On hardware, replace `--synthetic` with `--port /dev/tty.usbserial-XXXX`.

---

## What you need on the bench

| Item | Why |
|---|---|
| 16 x 10 kOhm 0.1% resistors | electrode-equivalent loading, one per input leg |
| 2 x 11 kOhm 0.1% (or 1 kOhm to add in series) | the deliberate-imbalance fixture |
| 1 kOhm + 100 Ohm + 20 Ohm, all 0.1% | the CMRR injection divider |
| Analog Discovery 3 | common-mode and differential drive |
| AD8232 breakout + its digitiser | the comparison device |

Keep the resistor leads short and twisted, and keep the fixture off anything
metal and mains-powered. The fixture is part of the measurement.

**Never leave an input floating.** The ADS1299 draws a small input bias
current; with no DC return path the input drifts to a rail and the channel
reads full scale, which looks like a dead channel rather than a wiring
mistake. Every fixture below ties the common node to the board's BIAS (or to
its analog ground when BIAS is off).

---

## 01 Noise floor

### Why 10 kOhm and not a short

A shorted input measures the amplifier and nothing else. Three of the four
things that dominate a real recording scale with source impedance and vanish
at zero ohms:

1. **Input current noise** develops a voltage `i_n x R` across the source. At
   R = 0 the term is identically zero, so a shorted test reports an amplifier
   with no current noise whatever it actually has.
2. **The source's own thermal noise**, `sqrt(4kTR)`. Two 10 k legs give
   18.1 nV/rtHz differential, about 0.13 uVrms over 0.5-50 Hz -- comparable to
   the ADS1299's own noise at gain 8, and a floor no amplifier can beat. A
   skin-electrode interface has at least this much.
3. **System CMRR** is set by how well the two input paths match. A short makes
   them identical by construction, so the number you get is the amplifier's
   intrinsic CMRR, not the CMRR you will have with real electrodes.

10 kOhm because that is what a well-prepped wet electrode presents (~5-20 k),
and 0.1% because it bounds the fixture's own contribution: two 10 k 0.1% parts
differ by at most 20 Ohm, so the fixture converts at most 0.2% of common mode
into differential and cannot be mistaken for the board's limit.

The ADS1299 can short its own inputs in silicon (CHnSET MUX = 001), so the
shorted measurement is free. Take it as a **control**, not as the measurement.

### Connect

Per channel: IN+ through 10 k to the common node CN; IN- through 10 k to CN.
Tie CN to the board's BIAS pin. Repeat for all eight channels.

- `--condition short` -- amplifier alone. Either short IN+ to IN- externally
  (still tied to CN so the inputs are not floating), or set CHnSET MUX = 001
  from the firmware's own console. The script **prompts you to arrange it and
  does not set the MUX itself** -- `SerialBoard.set_mux` raises rather than
  guessing a firmware-specific command. Confirm the MUX field actually moved
  with `00_gain_check.py --dump-registers` before recording.
- `--condition 10k` -- the fixture above. **This is the number that matters.**
- `--condition imbalance` -- swap one leg for 11 k.
- `--condition all` -- all three, prompting between rewires.

```bash
python bench/01_noise_floor.py --port /dev/tty.usbserial-XXXX --condition all
```

### Expect

At gain 8, 250 SPS, over 0.5-50 Hz:

| Condition | Expected |
|---|---|
| shorted | ~0.20 uVrms (amplifier alone) |
| 10 k | ~0.24 uVrms (amplifier and 0.13 uVrms of Johnson noise in quadrature) |
| imbalance | ~the same as 10 k for noise, but more mains pickup |

The source-impedance penalty (10k / short) should land around 1.1-1.3x. The
script prints it; a shorted-input test cannot produce it at all.

### A bad result looks like

- **One channel 2x above the others.** Almost always that input's fixture --
  a cold joint or a long lead. The script names the outlier channels. Check
  the resistor before you suspect the board.
- **Noise above ~0.6 uVrms on every channel.** Either the gain is wrong (check
  `00_gain_check.py` first, always), the reference is unstable, or the fixture
  is picking up. Compare against the shorted condition: if the short is also
  bad, it is not the fixture.
- **The 10 k figure equal to the shorted figure.** Suspicious. Thermal noise of
  20 k is not optional. Either the resistors are not in circuit, or the
  amplifier's own noise is so high it swamps them -- which is itself a finding.
- **The 10 k figure BELOW the Johnson line drawn on the figure.** Physically
  impossible. Something in the chain is filtering, decimating, or averaging in
  a way the analysis does not know about.
- **A rising left edge steeper than 1/f.** Electrode drift or a thermal
  gradient across the fixture. Wait five minutes after touching it.

---

## 02 PSD with mains harmonics

### Connect

Same fixture as 01, `--condition 10k`. Or skip the recording entirely and
re-analyse one you already have:

```bash
python bench/02_psd_mains.py --from-recording bench/out/data/01_raw_10k
```

The re-analysis path inherits the gain verdict from the recording's metadata
and refuses to run if `config.PGA_GAIN` has changed since the capture.

### Expect

Mains at 60 Hz (San Francisco; pass `--mains 50` elsewhere) plus harmonics.
The script marks the comb, tabulates each harmonic's amplitude and its
prominence above the local floor, and reads the SHAPE of the comb as a hint:

| Comb shape | Usually means |
|---|---|
| fundamental only, no harmonics | magnetic coupling into a loop -- find the loop |
| strong odd harmonics (3rd, 5th, 7th) | capacitive coupling from a switching supply or dimmer |
| comb on one channel only | that input's fixture, not the board |
| comb present with inputs shorted | getting in after the input pins: supply, reference, or digital side |

This script measures; it does not notch. A notch applied before you understand
the comb removes the evidence, and its residual is indistinguishable from a
quiet front end.

### A bad result looks like

- **No comb at all.** Do not celebrate. Check that the inputs are actually
  connected to the fixture -- a genuinely floating input picks up plenty, so
  *nothing* usually means the analysis is looking at the wrong thing, or the
  capture was too short to resolve 60 Hz (needs at least a few seconds).
- **Harmonics above the 5th at large amplitude.** Something is clipping. Check
  for railing before chasing the layout.
- **The fundamental moving between captures by more than ~0.1 Hz.** Mains does
  wander, but a large jump means the capture length or sample rate is not what
  the script was told.

---

## 03 CMRR against frequency

### Connect

The divider chain, driven by AD3 W1:

```
W1 --[1k]--+--[100R]--+--[20R]-- AGND
           |          |
        tap "mid"   tap "low"       low = across the 20 R, 1/56, -34.96 dB
```

Tie the AD3's ground to the board's analog ground. Two passes:

**Pass 1, differential.** IN+ (through its 10 k) to the top of the 20 Ohm leg;
IN- (through its 10 k) to the bottom of it. 1 V peak at the generator becomes
17.9 mV at the board -- comfortably inside the +/-562 mV full scale at gain 8,
and far above the noise.

**Pass 2, common mode.** Tie IN+ and IN- together, still through their 10 k
resistors, and drive that node from W1 directly, referenced to board ground.
Start at 100 mV peak.

```bash
python bench/03_cmrr_sweep.py --port /dev/tty.usbserial-XXXX --ad3 manual
```

`--ad3 manual` (the default) prompts for each setting and needs no SDK.
`--ad3 auto` drives libdwf over ctypes; it is **untested against a real AD3**
and proves itself with an open/set/read-back before the sweep starts.

**Measure the drive amplitude with the scope at the top of the divider, and
pass that to `--ad3-amplitude`.** Do not trust the generator's dial: its output
impedance in series with a 1120 Ohm chain is a real error of order 1%, and it
drops out entirely if you measure. (0.1% resistors do not give a 0.1% ratio
either -- the 1 k part's tolerance dominates. The script prints the propagated
figure, about 0.13%.)

### Expect

- CMRR flat around 110-120 dB at low frequency, rolling off above a few tens
  of Hz. The ADS1299 datasheet figure at 50/60 Hz is around -110 dB.
- The **differential gain error** panel flat at 0 dB. This is a second,
  independent check on the voltage scale: after `counts_to_volts`, a correctly
  scaled system reports exactly the voltage that was applied.
- The **measurement ceiling** curve well above the CMRR curve.

### A bad result looks like

- **A flat offset in the differential gain error.** That is a scale-factor
  error, not a front-end property. `+9.54 dB` is exactly what a gain-24 board
  read as gain 8 looks like. Stop and re-run `00_gain_check.py`.
- **CMRR points sitting on the measurement ceiling.** Those are not
  measurements of the board -- they are measurements of how long you recorded
  for. The script flags them. Raise `--cm-amplitude` or
  `--seconds-per-point`; do not report the number.
- **CMRR far better than 120 dB.** Almost certainly the common-mode drive is
  not actually reaching the inputs. Confirm with the scope at the board's pins.
- **CMRR collapsing to 60-80 dB.** Check the fixture's matching first: an
  accidental 10% imbalance between the two legs converts a great deal of
  common mode into differential, and that is the fixture, not the board. Run
  `01 --condition imbalance` to see how much your setup is sensitive to it.
- **The differential pass clipping.** The script refuses to start if the
  computed differential drive exceeds half of full scale, but if you widen the
  amplitude by hand, a clipped sine reports a gain error that is not there.

---

## 04 BIAS drive on against off

### Connect

Identical to 02, run twice. The script toggles BIAS, then **reads CONFIG3 back
and checks the PD_BIAS bit before recording each half**. If the toggle did not
land it aborts, because two identical recordings compared against each other
produce a confident conclusion that bias does nothing.

```bash
python bench/04_bias_on_off.py --port /dev/tty.usbserial-XXXX --with-cmrr
```

`--with-cmrr` also runs the full 03 sweep in both states (two more AD3 sweeps,
and in hardware mode that means rewiring twice).

### Expect

- 20-40 dB improvement at the mains fundamental on a real subject; less on a
  bench fixture.
- **Much less improvement at the higher harmonics.** The bias loop has finite
  bandwidth. A flat improvement across all harmonics means something else
  changed between the two halves.
- **The broadband floor rising slightly.** The bias amplifier injects its own
  noise into the common-mode node. This is normal and the script reports it.

### A bad result looks like

- **No difference at all.** Not "bias does nothing" -- almost always "this
  fixture presents no common-mode mains to reject", so the comparison is
  untested rather than negative. The script says so instead of reporting 0 dB
  as a finding. Confirm from 02 that there is a comb to begin with; the
  imbalance fixture will give the loop something to work on.
- **Mains improving AND the broadband floor also falling.** Suspicious: the
  bias amplifier is not free. Look for a channel that is not actually in the
  loop, or a capture where something else changed.
- **A channel getting worse with bias on.** That channel's BIAS_SENSP/SENSN
  routing is probably wrong, so it is being driven without being sensed.
- **A beautiful CMRR improvement in the `--with-cmrr` panel, with carets on
  every point.** Bias drive routinely pushes the leaked differential below the
  detection floor, at which point the sweep is measuring its own noise. Those
  deltas are LOWER BOUNDS and the script says so, in the table and on the
  figure. Raise `--cm-amplitude` or `--cmrr-seconds-per-point` until the
  ceiling clears the curve before quoting a number.

---

## 05 Side by side against the AD8232

### Connect

Record the Cerelog board on the 10 k fixture, and the AD8232 on its own
digitiser with whatever front end you built. Then state the AD8232's chain
explicitly -- there is no default that guesses:

```bash
python bench/05_ad8232_compare.py \
    --cerelog-recording bench/out/data/01_raw_10k \
    --ad8232-file ad8232_capture.csv --ad8232-units counts \
    --ad8232-total-gain 1100 --ad8232-adc-bits 12 --ad8232-adc-span 3.3 \
    --ad8232-fs 250
```

Both devices are divided by their own chain before anything is plotted. A
comparison drawn with the wrong chain constant is not a weaker result, it is a
wrong one, and it will favour whichever device you got wrong.

### Expect

The AD8232 an order of magnitude noisier in band. Its datasheet input noise is
about 14 uV peak-to-peak over 0.5-40 Hz -- roughly 2.3 uVrms -- against the
ADS1299's ~0.24 uVrms at gain 8 with 10 k loading. That is not a criticism of
the part: it was designed for millivolt ECG on a single lead, and EEG is two
orders of magnitude smaller.

### A bad result looks like

- **The AD8232 curve sitting on its own quantisation floor** (drawn on the
  figure). Then you are measuring the ADC you chose, not the amplifier. With
  gain 100 into a bare 12-bit 3.3 V input, one count is about 8 uV at the
  input -- the quantiser alone is noisier than the entire ADS1299 channel, and
  no averaging recovers what was never resolved. Raise the second-stage gain
  or use a better digitiser.
- **The AD8232 showing LESS mains than the Cerelog board.** Not better
  rejection. Its own noise is above the line level, so the pickup is there and
  simply unmeasurable. The script prints this explicitly rather than letting
  the table imply a win.
- **A ratio near 1.0.** Check the chain constants before believing it. That is
  the number most likely to be wrong.

---

## 06 Report

```bash
python bench/06_report.py
```

Writes `out/report.md`, `out/data/summary.csv`, and the four-panel
`out/figures/06_summary_{light,dark}.{png,pdf}`.

It refuses three things rather than papering over them:

- **A missing artifact** is named along with the exact command that produces
  it, and the report is marked incomplete (`--allow-incomplete` to write it
  anyway, with the gaps stated on its face).
- **Artifacts that disagree** about gain, sample rate, mains frequency, or
  synthetic-vs-hardware are refused outright. Those runs do not describe the
  same instrument.
- **Synthetic data** is declared in the report body, on every figure, and in
  the summary CSV -- not in a footnote.

---

## Suggested order on hardware day

```bash
P=/dev/tty.usbserial-XXXX      # yours will differ

python bench/00_gain_check.py --port $P --dump-registers   # look before touching
python bench/00_gain_check.py --port $P                    # register + physical
python bench/01_noise_floor.py --port $P --condition all
python bench/02_psd_mains.py  --port $P --from-recording bench/out/data/01_raw_10k
python bench/03_cmrr_sweep.py --port $P
python bench/04_bias_on_off.py --port $P --with-cmrr
python bench/05_ad8232_compare.py --port $P --ad8232-file ad8232.csv ...
python bench/06_report.py
```

If `00` fails, stop. Nothing downstream means anything until the scale factor
is proven.

### Exit codes

| Code | Means |
|---|---|
| 0 | ran, and any pass/fail gate passed |
| 1 | a measurement failed its gate, or the gain guard refused, or the report found missing/conflicting artifacts. **Artifacts are still written** -- a failing run is data too. |
| 2 | the bench is misconfigured before anything was recorded (no `--port`, a drive amplitude that would clip, a MUX that cannot be set from here) |

`01_noise_floor.py` returning 1 means at least one channel is above its limit;
the figure and the CSV are on disk and name the channel.

---

## Files

| File | What it is |
|---|---|
| `config.py` | every constant, including **the** gain constant. Edit gain here and nowhere else. |
| `gainguard.py` | the register check, the physical check, and the latch that makes them unskippable |
| `board.py` | `SerialBoard` and `SyntheticBoard`, register parsing, recording IO |
| `synth.py` | the modelled front end and AD8232 -- every parameter is a model, not a measurement |
| `dsp.py` | Welch PSD, band RMS, mains harmonics, tone estimation, CMRR |
| `ad3.py` | Analog Discovery 3: manual, libdwf, and synthetic drivers |
| `vizstyle.py` | the figure system (validated palette, light and dark, provenance badges) |
| `artifacts.py` | artifact naming, CSV/JSON IO, provenance conflict detection |
| `selftest.py` | unit, guard and recovery tests -- run this first |

---

## What has NOT been tested against hardware

Stated plainly, because the board does not exist yet:

- **`SerialBoard`** -- the port open, the OpenBCI-dialect commands (`?`, `b`,
  `s`), and the 33-byte frame decoder. The register **parser** IS tested,
  against three dialects, in `selftest.py`. If the firmware speaks something
  else, everything protocol-specific is confined to `SerialBoard`; do not
  scatter it into the analysis scripts.
- **`WaveformsAD3`** (`--ad3 auto`) -- written from the libdwf API, never run.
  `--ad3 manual` is the default for exactly this reason, and `check()` proves
  the auto path with an open/set/read-back before a sweep begins.
- **`SerialBoard.set_mux` and `.set_bias`** -- deliberately `NotImplementedError`
  rather than a guess. Both raise with instructions to change the setting from
  the firmware's own console; `04` then confirms the change by reading CONFIG3
  back.
- **The expected-noise table** in `config.py` -- the gain-24 entry is the
  datasheet figure; the lower-gain entries are modelled from it. Replace the
  table with the noise table from your datasheet revision before quoting any
  of it. The pass/fail gate is generous (2.5x) precisely because those numbers
  are estimates; it still catches a 3x gain error.
