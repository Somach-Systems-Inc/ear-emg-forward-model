"""Cerelog ESP-EEG bench suite -- the single source of truth.

Every constant that could silently corrupt a voltage lives here and NOWHERE
ELSE. Import it; never re-declare it.

===========================================================================
 THE ONE NUMBER THAT MATTERS
===========================================================================

The board ships configured for PGA gain 24 and most host software assumes 24
when it scales counts to volts. Carl intends to run it at 8. Those two gains
differ by exactly 3.000x, and nothing about a 3x-wrong EEG trace *looks*
wrong -- amplitudes in microvolts are unfamiliar enough that a wrong one
passes the eyeball test every time. It shows up months later as a noise floor
that will not reconcile with the datasheet, or a paper figure with the wrong
y-axis.

So:

  * ``PGA_GAIN`` below is the only host-side declaration of gain in the repo.
  * There is deliberately NO ``--gain`` command-line flag and NO environment
    variable override. A second place to set it is a second place for it to
    go stale. Editing one line in one file is the entire interface.
  * ``gainguard.verify_gain()`` reads the gain actually programmed into the
    ADS1299 at the start of every run and refuses to continue if it disagrees.
  * ``gainguard.counts_to_volts()`` raises unless that check has run. You
    cannot produce a voltage in this suite without having proven the scale
    factor first.

When you change the gain on the board, change the line below in the same
commit. The guard will tell you loudly if you forget.
"""

from __future__ import annotations

import math
import subprocess
from pathlib import Path

# ===========================================================================
# THE GAIN CONSTANT -- edit here, nowhere else
# ===========================================================================

PGA_GAIN: int = 8
"""ADS1299 PGA gain the board is programmed for.

History (demote, never overwrite -- see the vault convention):
  - 24  factory default as shipped; assumed by stock host software.
  - 8   intended bench configuration, 2026-08 (headroom for electrode
        offset at the cost of ~1.4x more input-referred noise).
"""

# ===========================================================================
# ADS1299 analog front end
# ===========================================================================

VREF_V: float = 4.5
"""Internal reference, volts. The count->volt scale factor is
``VREF_V / (gain * (2**23 - 1))``; at gain 24 that is 0.02235 uV/count, the
number OpenBCI-lineage firmware hard-codes. Confirm against CONFIG3 if the
firmware ever selects the 4.0 V reference option -- a 4.5 -> 4.0 change is a
silent 11% error and this constant is where it would be caught."""

ADC_BITS: int = 24
ADC_FULL_SCALE_COUNTS: int = 2 ** 23 - 1  # 8388607, positive full scale

VALID_GAINS: tuple[int, ...] = (1, 2, 4, 6, 8, 12, 24)

GAIN_CODES: dict[int, int] = {1: 0b000, 2: 0b001, 4: 0b010, 6: 0b011,
                              8: 0b100, 12: 0b101, 24: 0b110}
"""CHnSET[6:4] GAIN field encoding (ADS1299 datasheet, channel settings
register). 0b111 is reserved."""

CHNSET_GAIN_SHIFT = 4
CHNSET_GAIN_MASK = 0b111 << CHNSET_GAIN_SHIFT
CHNSET_MUX_MASK = 0b111

MUX_CODES: dict[str, int] = {
    "normal": 0b000,       # external electrode input
    "shorted": 0b001,      # inputs shorted internally -- amplifier alone
    "bias_meas": 0b010,
    "mvdd": 0b011,
    "temp": 0b100,
    "test": 0b101,         # internal square-wave test signal
    "bias_drp": 0b110,
    "bias_drn": 0b111,
}

TEST_SIGNAL_DIVISOR: float = 2400.0
"""Internal test signal amplitude is +/- (VREFP - VREFN) / 2400 with
CONFIG2.TEST_AMP = 0 (and /1200 with TEST_AMP = 1). At VREF 4.5 V that is
+/-1.875 mV, i.e. 3.75 mV peak-to-peak.

Verify against your datasheet revision -- but note the gain check does not
depend on this being exact. It flags errors of 1.5x and larger; a few percent
of uncertainty in this divisor cannot mask a 3x gain mistake."""

CONFIG3_PD_BIAS_BIT = 1 << 2
"""CONFIG3[2] PD_BIAS: 0 = bias buffer powered down, 1 = bias buffer enabled.
Inverted sense -- 'PD' is power-down, so 1 means ON."""

# ===========================================================================
# Acquisition defaults
# ===========================================================================

FS_HZ: float = 250.0
VALID_SAMPLE_RATES: tuple[float, ...] = (250.0, 500.0, 1000.0, 2000.0,
                                         4000.0, 8000.0, 16000.0)

N_CHANNELS: int = 8
ACTIVE_CHANNELS: tuple[int, ...] = tuple(range(N_CHANNELS))

SERIAL_BAUD: int = 115200
SERIAL_TIMEOUT_S: float = 3.0

MAINS_HZ: float = 60.0
"""San Francisco. Pass --mains 50 if the board ever travels."""

MAINS_N_HARMONICS: int = 8

# ===========================================================================
# Bench fixtures -- the physical parts on the desk
# ===========================================================================

SOURCE_R_OHM: float = 10_000.0
"""Electrode-equivalent series resistance, one per input. 0.1% tolerance.
See ``01_noise_floor.py`` for why this is not a short."""

SOURCE_R_TOL: float = 0.001

DIVIDER_R_OHM: tuple[float, float, float] = (1000.0, 100.0, 20.0)
"""Precision divider chain driven by the Analog Discovery 3 W1 output:

    W1 --[R1 1k]--+--[R2 100R]--+--[R3 20R]-- AGND
                  |             |
                tap A         tap B

  tap B (across R3):        20 / 1120 = 1/56.0    = -34.96 dB
  tap A (across R2 + R3):  120 / 1120 = 1/9.333   = -19.42 dB

All three 0.1%. Use ``divider_ratio()`` rather than the numbers above so the
value tracks the resistors you actually soldered."""

DIVIDER_R_TOL: float = 0.001

TEMPERATURE_K: float = 295.15  # 22 C, lab ambient
BOLTZMANN: float = 1.380649e-23

# ===========================================================================
# Analysis bands
# ===========================================================================

NOISE_BAND_HZ: tuple[float, float] = (0.5, 50.0)
"""Integration band for the headline noise number. 0.5 Hz excludes electrode
drift, which is a fixture property, not an amplifier property. 50 Hz is the
top of usable EEG for most work and sits below the 60 Hz mains line so the
number is not dominated by pickup."""

EEG_BANDS_HZ: dict[str, tuple[float, float]] = {
    "delta": (0.5, 4.0),
    "theta": (4.0, 8.0),
    "alpha": (8.0, 13.0),
    "beta": (13.0, 30.0),
    "gamma": (30.0, 50.0),
}

WELCH_NPERSEG: int = 2048
WELCH_OVERLAP: float = 0.5

CMRR_FREQS_HZ: tuple[float, ...] = (1.0, 2.0, 5.0, 10.0, 20.0, 30.0, 40.0,
                                    50.0, 60.0, 80.0, 100.0)
"""Capped at 0.4 * FS_HZ = 100 Hz for the default 250 SPS. Includes both 50
and 60 so the same sweep is valid in either mains region."""

CMRR_SECONDS_PER_POINT: float = 10.0
CMRR_CM_AMPLITUDE_V: float = 0.100
"""Common-mode drive amplitude, volts peak. Start here, not at 1 V: at PGA
gain 24 the ADS1299 input common-mode range is narrow and a large CM drive
clips before it tells you anything. Raise it only after confirming the
channels are not railing."""

# ===========================================================================
# Paths
# ===========================================================================

BENCH_DIR: Path = Path(__file__).resolve().parent
OUT_DIR: Path = BENCH_DIR / "out"
DATA_DIR: Path = OUT_DIR / "data"
FIG_DIR: Path = OUT_DIR / "figures"

SUITE_VERSION = "1.0.0"


# ===========================================================================
# Derived quantities -- functions, so they can never drift from the constants
# ===========================================================================

def lsb_volts(gain: int) -> float:
    """Volts per ADC count at ``gain``. The whole suite's scale factor."""
    return VREF_V / (gain * ADC_FULL_SCALE_COUNTS)


def full_scale_input_volts(gain: int) -> float:
    """Differential input that saturates the ADC, volts peak."""
    return VREF_V / gain


def gain_from_code(code: int) -> int:
    """Decode a CHnSET GAIN field (already shifted down to bits [2:0])."""
    for gain, c in GAIN_CODES.items():
        if c == code:
            return gain
    raise ValueError(
        f"CHnSET gain code 0b{code:03b} is reserved on the ADS1299. "
        "Either the register read is misaligned or the part is not an "
        "ADS1299. Do not guess a gain from this."
    )


def gain_from_chnset(reg: int) -> int:
    """Decode gain from a whole CHnSET register byte."""
    return gain_from_code((reg & CHNSET_GAIN_MASK) >> CHNSET_GAIN_SHIFT)


def mux_from_chnset(reg: int) -> str:
    code = reg & CHNSET_MUX_MASK
    for name, c in MUX_CODES.items():
        if c == code:
            return name
    return f"unknown(0b{code:03b})"


def test_signal_amplitude_v(amp_2x: bool = False) -> float:
    """Internal test-signal amplitude in volts peak (half of peak-to-peak)."""
    divisor = TEST_SIGNAL_DIVISOR / (2.0 if amp_2x else 1.0)
    return VREF_V / divisor


def johnson_noise_density(resistance_ohm: float,
                          temperature_k: float = TEMPERATURE_K) -> float:
    """Thermal noise voltage density of a resistor, V/sqrt(Hz).

    sqrt(4 k T R). This is physics, not a datasheet claim, so the noise-floor
    script can use it as a hard lower bound: no amplifier can measure a 10 k
    source and report less noise than this.
    """
    return math.sqrt(4.0 * BOLTZMANN * temperature_k * resistance_ohm)


def johnson_noise_rms(resistance_ohm: float,
                      band_hz: tuple[float, float] = NOISE_BAND_HZ,
                      temperature_k: float = TEMPERATURE_K) -> float:
    """Thermal noise of a resistor integrated over ``band_hz``, Vrms."""
    lo, hi = band_hz
    return johnson_noise_density(resistance_ohm, temperature_k) * math.sqrt(hi - lo)


def differential_source_resistance(single_ended_r: float = SOURCE_R_OHM) -> float:
    """Resistance seen across the differential input pair.

    Two independent resistors in the two input legs are uncorrelated noise
    sources, so their powers add: the differential thermal noise equals that
    of a single resistor of value R1 + R2.
    """
    return 2.0 * single_ended_r


def divider_ratio(resistors: tuple[float, float, float] = DIVIDER_R_OHM,
                  tap: str = "low",
                  source_impedance_ohm: float = 0.0) -> float:
    """Attenuation of the precision divider, output/input.

    ``tap="low"`` takes the output across R3 alone; ``tap="mid"`` takes it
    across R2 + R3.

    ``source_impedance_ohm`` is the generator's own output resistance in
    series with R1. It defaults to 0, which is optimistic: 10 ohms of unmodelled
    source impedance is a 0.9% amplitude error on this chain. The protocol in
    README.md tells you to measure the voltage at the top of R1 with the AD3
    scope instead of trusting the generator's amplitude setting, which makes
    this term drop out entirely.
    """
    r1, r2, r3 = resistors
    total = source_impedance_ohm + r1 + r2 + r3
    if tap == "low":
        return r3 / total
    if tap == "mid":
        return (r2 + r3) / total
    raise ValueError(f"tap must be 'low' or 'mid', got {tap!r}")


def divider_ratio_uncertainty(resistors: tuple[float, float, float] = DIVIDER_R_OHM,
                              tap: str = "low",
                              tol: float = DIVIDER_R_TOL) -> float:
    """Relative 1-sigma uncertainty of ``divider_ratio``, propagated properly.

    Partial derivatives of ratio = Rnum / Rtot with respect to each resistor,
    combined in quadrature with each resistor's tolerance treated as 1 sigma.
    """
    r1, r2, r3 = resistors
    total = r1 + r2 + r3
    num = r3 if tap == "low" else (r2 + r3)
    # d(ratio)/dRi = (delta_i,num * total - num) / total^2
    var = 0.0
    in_num = {"low": (False, False, True), "mid": (False, True, True)}[tap]
    for r, member in zip((r1, r2, r3), in_num):
        d = ((total if member else 0.0) - num) / total ** 2
        var += (d * r * tol) ** 2
    ratio = num / total
    return math.sqrt(var) / ratio


def divider_loading_error(resistors: tuple[float, float, float] = DIVIDER_R_OHM,
                          load_ohm: float = 1e9) -> float:
    """Relative error from the board's finite input impedance loading the tap.

    With a 20 ohm bottom leg and an ADS1299 input impedance in the gigaohms,
    this is ~2e-8 -- i.e. the divider is not the problem. Computed rather than
    asserted so a change of parts re-checks itself.
    """
    r1, r2, r3 = resistors
    unloaded = r3 / (r1 + r2 + r3)
    r3_eff = (r3 * load_ohm) / (r3 + load_ohm)
    loaded = r3_eff / (r1 + r2 + r3_eff)
    return abs(loaded - unloaded) / unloaded


def git_revision() -> str:
    """Short git rev of the worktree, or 'unknown'. Stamped into every output."""
    try:
        out = subprocess.run(
            ["git", "-C", str(BENCH_DIR), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5, check=False)
        rev = out.stdout.strip()
        return rev if rev else "unknown"
    except Exception:
        return "unknown"


def ensure_dirs() -> None:
    for d in (OUT_DIR, DATA_DIR, FIG_DIR):
        d.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Expected input-referred noise, ADS1299, 250 SPS.
#
# PROVENANCE MATTERS HERE. These are the commonly cited datasheet figures for
# gain 24 (0.14 uVrms / ~1.0 uVpp at 250 SPS); the lower-gain entries are
# scaled from that using the standard model in which the PGA's own noise
# dominates above gain ~6 and the ADC's noise adds in quadrature below it.
# They are ESTIMATES used only to decide whether a measurement is roughly
# where it should be -- never as a spec you can quote.
#
# Before the board arrives, replace this table with the noise table from the
# datasheet revision you actually have, and set ``source`` accordingly.
# ---------------------------------------------------------------------------

EXPECTED_INPUT_NOISE_URMS: dict[int, float] = {
    24: 0.14,
    12: 0.16,
    8: 0.20,
    6: 0.24,
    4: 0.33,
    2: 0.63,
    1: 1.20,
}

EXPECTED_NOISE_SOURCE = (
    "ADS1299 datasheet input-referred noise, 250 SPS, shorted input; "
    "gain-24 entry is the datasheet figure, lower gains are modelled. "
    "ESTIMATE -- replace with your datasheet revision before quoting."
)

NOISE_PASS_FACTOR: float = 2.5
"""How far above the expected figure a measurement may sit before the script
calls it a failure. Generous on purpose: a 10 k source, real cabling, and a
bench that is not a screened room all legitimately add noise. A 3x gain error
moves the number by 3x, which this still catches."""
