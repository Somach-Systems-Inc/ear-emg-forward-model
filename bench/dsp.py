"""Shared signal processing. One implementation of each estimator, reused.

Two things in here are worth reading before trusting a number out of this
suite:

**Amplitudes of mains harmonics come from integrating the PSD, not from
fitting a sinusoid.** Mains is not frequency-locked to anything -- it wanders
by tens of millihertz over a two-minute capture. A least-squares fit at
exactly 60.000 Hz against a signal sitting at 60.02 Hz loses most of the
amplitude to decorrelation over a long record, and does so silently. Peak
integration does not care where inside the window the energy actually landed.

**The headline noise number is reported twice: with mains in and with mains
out.** A bench in a building is not a screened room. Quoting a broadband noise
figure that is really a measurement of the fluorescent lighting is the easiest
way to make a front end look bad, and excluding the mains bins without saying
so is the easiest way to make one look good. Both numbers, always.
"""

from __future__ import annotations

import math
from typing import Optional

import numpy as np
from scipy import signal

import config

_trapezoid = getattr(np, "trapezoid", None) or np.trapz


# ===========================================================================
# Spectra
# ===========================================================================

def welch_psd(x: np.ndarray, fs: float, nperseg: Optional[int] = None,
              overlap: float = config.WELCH_OVERLAP
              ) -> tuple[np.ndarray, np.ndarray]:
    """One-sided power spectral density, V^2/Hz.

    ``x`` may be (n,) or (n, n_channels); the returned PSD matches.
    """
    x = np.asarray(x, dtype=np.float64)
    n = x.shape[0]
    nperseg = int(nperseg or min(config.WELCH_NPERSEG, n))
    if nperseg > n:
        nperseg = n
    noverlap = int(nperseg * overlap)
    f, pxx = signal.welch(x, fs=fs, window="hann", nperseg=nperseg,
                          noverlap=noverlap, detrend="constant",
                          scaling="density", axis=0)
    return f, pxx


def amplitude_spectral_density(pxx: np.ndarray) -> np.ndarray:
    """V/sqrt(Hz) -- the natural unit for an amplifier noise plot."""
    return np.sqrt(np.maximum(pxx, 0.0))


def band_rms(f: np.ndarray, pxx: np.ndarray,
             band: tuple[float, float] = config.NOISE_BAND_HZ,
             mask: Optional[np.ndarray] = None) -> np.ndarray:
    """Integrate a PSD over a band -> Vrms. Returns a scalar or per-channel.

    ``mask`` marks which frequency bins to keep (e.g. everything except the
    mains harmonics). The excluded bins are not dropped from the integral --
    they are REPLACED by interpolation from the surviving neighbours, so the
    notched region contributes its own local broadband floor and the integral
    still covers the whole band.

    Dropping them instead would be wrong in two different directions at once:
    the bandwidth would silently shrink, and a notch at the band edge would
    shrink it by a different amount than a notch in the middle, so two
    supposedly comparable numbers would not be comparable.
    """
    lo, hi = band
    sel = (f >= lo) & (f <= hi)
    if not np.any(sel):
        raise ValueError(f"no frequency bins in band {band}")
    fsel = f[sel]
    psel = np.asarray(pxx[sel] if pxx.ndim == 1 else pxx[sel, :],
                      dtype=np.float64)

    if mask is not None:
        keep = np.asarray(mask, dtype=bool)[sel]
        if not keep.any():
            raise ValueError(
                f"the mask excluded every bin in band {band}. Either the "
                "mains halfwidth is too wide or the band is too narrow to "
                "hold anything but harmonics.")
        if not keep.all():
            if psel.ndim == 1:
                psel = np.interp(fsel, fsel[keep], psel[keep])
            else:
                psel = np.column_stack([
                    np.interp(fsel, fsel[keep], psel[keep, c])
                    for c in range(psel.shape[1])])

    power = _trapezoid(psel, fsel, axis=0)
    return np.sqrt(np.maximum(power, 0.0))


def band_rms_of_signal(x: np.ndarray, fs: float,
                       band: tuple[float, float] = config.NOISE_BAND_HZ
                       ) -> np.ndarray:
    f, pxx = welch_psd(x, fs)
    return band_rms(f, pxx, band)


# ===========================================================================
# Mains
# ===========================================================================

def mains_harmonics(f0: float, f_max: float,
                    n_harmonics: int = config.MAINS_N_HARMONICS
                    ) -> list[float]:
    return [f0 * k for k in range(1, n_harmonics + 1) if f0 * k < f_max]


def mains_mask(f: np.ndarray, f0: float, f_max: Optional[float] = None,
               n_harmonics: int = config.MAINS_N_HARMONICS,
               halfwidth_hz: float = 1.0) -> np.ndarray:
    """Boolean mask that is False inside +/- halfwidth of every harmonic."""
    f_max = f_max if f_max is not None else float(f[-1])
    keep = np.ones_like(f, dtype=bool)
    for fh in mains_harmonics(f0, f_max, n_harmonics):
        keep &= np.abs(f - fh) > halfwidth_hz
    return keep


def tone_rms_from_psd(f: np.ndarray, pxx: np.ndarray, f_center: float,
                      halfwidth_hz: float = 0.6,
                      floor_window_hz: float = 4.0) -> tuple[float, float]:
    """(tone Vrms, local floor V/sqrt(Hz)) for a peak near ``f_center``.

    Integrates the PSD across the peak, subtracts the local broadband floor
    (median of nearby bins outside the peak) times the integration bandwidth,
    and returns the residual as an RMS. Robust to the tone sitting a fraction
    of a bin away from where it was expected.
    """
    pxx = np.asarray(pxx, dtype=np.float64)
    peak = np.abs(f - f_center) <= halfwidth_hz
    near = (np.abs(f - f_center) <= floor_window_hz) & ~peak
    if not np.any(peak):
        return 0.0, 0.0
    floor_psd = float(np.median(pxx[near])) if np.any(near) else 0.0
    bw = float(f[peak][-1] - f[peak][0]) or float(f[1] - f[0])
    power = float(_trapezoid(pxx[peak], f[peak])) - floor_psd * bw
    return math.sqrt(max(power, 0.0)), math.sqrt(max(floor_psd, 0.0))


def harmonic_table(f: np.ndarray, pxx: np.ndarray, f0: float,
                   n_harmonics: int = config.MAINS_N_HARMONICS,
                   halfwidth_hz: float = 0.6) -> list[dict]:
    """Per-harmonic amplitude and prominence above the local floor."""
    rows = []
    for k in range(1, n_harmonics + 1):
        fh = f0 * k
        if fh >= f[-1]:
            break
        rms, floor_asd = tone_rms_from_psd(f, pxx, fh, halfwidth_hz)
        floor_rms = floor_asd * math.sqrt(2 * halfwidth_hz)
        snr_db = (20.0 * math.log10(rms / floor_rms)
                  if rms > 0 and floor_rms > 0 else float("nan"))
        rows.append({
            "harmonic": k,
            "frequency_hz": fh,
            "amplitude_uvrms": rms * 1e6,
            "local_floor_nv_rthz": floor_asd * 1e9,
            "prominence_db": snr_db,
        })
    return rows


# ===========================================================================
# Single-tone estimation (for the CMRR sweep, where we set the frequency)
# ===========================================================================

def refine_tone_frequency(x: np.ndarray, fs: float, f_guess: float,
                          search_hz: float = 0.25,
                          n_grid: int = 81) -> float:
    """Locate a tone near ``f_guess`` by maximising the DFT magnitude.

    A generator's frequency is accurate but not exact, and the least-squares
    amplitude estimator below decorrelates if the frequency is off by more
    than roughly 1/(4T). Refining first costs microseconds and removes the
    whole failure mode.
    """
    x = np.asarray(x, dtype=np.float64)
    x = x - x.mean()
    n = x.size
    t = np.arange(n) / fs
    grid = np.linspace(f_guess - search_hz, f_guess + search_hz, n_grid)
    grid = grid[grid > 0]
    mags = np.array([abs(np.sum(x * np.exp(-2j * math.pi * fg * t))) for fg in grid])
    i = int(np.argmax(mags))
    if 0 < i < len(grid) - 1:  # parabolic refinement on the log-magnitude
        y0, y1, y2 = np.log(mags[i - 1:i + 2] + 1e-300)
        denom = (y0 - 2 * y1 + y2)
        delta = 0.5 * (y0 - y2) / denom if denom != 0 else 0.0
        delta = float(np.clip(delta, -1.0, 1.0))
        step = grid[1] - grid[0]
        return float(grid[i] + delta * step)
    return float(grid[i])


def tone_amplitude(x: np.ndarray, fs: float, f_hz: float,
                   refine: bool = True) -> tuple[float, float]:
    """(amplitude volts peak, frequency used) by least squares.

    The design matrix carries a constant and a linear ramp alongside the
    quadrature pair, so DC offset and slow electrode drift are projected out
    rather than leaking into the amplitude.
    """
    x = np.asarray(x, dtype=np.float64).ravel()
    n = x.size
    t = np.arange(n) / fs
    if refine:
        f_hz = refine_tone_frequency(x, fs, f_hz)
    A = np.column_stack([np.cos(2 * math.pi * f_hz * t),
                         np.sin(2 * math.pi * f_hz * t),
                         np.ones(n), t / t[-1] if t[-1] > 0 else t])
    coef, *_ = np.linalg.lstsq(A, x, rcond=None)
    return float(math.hypot(coef[0], coef[1])), float(f_hz)


def tone_amplitude_multichannel(x: np.ndarray, fs: float, f_hz: float
                                ) -> tuple[np.ndarray, float]:
    """Per-channel tone amplitude, all channels sharing one refined frequency.

    Sharing the frequency matters: the channels are looking at the same
    generator, so letting each pick its own peak lets a noisy channel wander
    off and invent an amplitude.
    """
    x = np.asarray(x, dtype=np.float64)
    if x.ndim == 1:
        x = x.reshape(-1, 1)
    if x.ndim != 2:
        raise ValueError(f"expected (n_samples,) or (n_samples, n_channels), "
                         f"got shape {x.shape}")
    f_ref = refine_tone_frequency(x[:, 0], fs, f_hz)
    amps = np.array([tone_amplitude(x[:, c], fs, f_ref, refine=False)[0]
                     for c in range(x.shape[1])])
    return amps, f_ref


# ===========================================================================
# Amplitude statistics
# ===========================================================================

def highpass(x: np.ndarray, fs: float, cutoff_hz: float, order: int = 2
             ) -> np.ndarray:
    sos = signal.butter(order, cutoff_hz, btype="highpass", fs=fs, output="sos")
    return signal.sosfiltfilt(sos, np.asarray(x, dtype=np.float64), axis=0)


def bandpass(x: np.ndarray, fs: float, band: tuple[float, float],
             order: int = 4) -> np.ndarray:
    lo, hi = band
    hi = min(hi, 0.45 * fs)
    sos = signal.butter(order, (lo, hi), btype="bandpass", fs=fs, output="sos")
    return signal.sosfiltfilt(sos, np.asarray(x, dtype=np.float64), axis=0)


def robust_peak_to_peak(x: np.ndarray, percentile: float = 99.9) -> np.ndarray:
    """Peak-to-peak with the outermost 0.1% trimmed off each tail.

    True min-to-max on a 30000-sample record is an estimate of the single
    worst sample, which is dominated by whatever transient happened once. The
    trimmed version is what people mean when they quote a peak-to-peak noise
    figure.
    """
    x = np.asarray(x, dtype=np.float64)
    lo = np.percentile(x, 100.0 - percentile, axis=0)
    hi = np.percentile(x, percentile, axis=0)
    return hi - lo


# ===========================================================================
# CMRR
# ===========================================================================

def cmrr_db(cm_applied_v: float, differential_seen_v: np.ndarray | float
            ) -> np.ndarray:
    """20 log10(applied common mode / differential signal it produced).

    Both arguments must be the same kind of amplitude (both peak, or both
    RMS). The suite uses peak throughout.
    """
    d = np.asarray(differential_seen_v, dtype=np.float64)
    with np.errstate(divide="ignore", invalid="ignore"):
        out = 20.0 * np.log10(np.where(d > 0, cm_applied_v / np.maximum(d, 1e-30),
                                       np.nan))
    return out


def differential_gain_error_db(measured_v: np.ndarray, applied_v: float
                               ) -> np.ndarray:
    """Deviation of the differential path from unity, in dB.

    After ``counts_to_volts`` a correctly scaled system reports exactly the
    voltage that was applied, so this should sit at 0 dB across the band. A
    flat offset here is a scale-factor error; a slope is the front end's
    frequency response.
    """
    m = np.asarray(measured_v, dtype=np.float64)
    with np.errstate(divide="ignore", invalid="ignore"):
        return 20.0 * np.log10(np.maximum(m, 1e-30) / applied_v)


# ===========================================================================
# Small helpers used by more than one script
# ===========================================================================

def summarise_channels(values: np.ndarray, unit: str) -> dict:
    v = np.asarray(values, dtype=np.float64)
    return {
        f"median_{unit}": float(np.median(v)),
        f"min_{unit}": float(np.min(v)),
        f"max_{unit}": float(np.max(v)),
        "worst_channel": int(np.argmax(v)) + 1,
        "spread_ratio": float(np.max(v) / max(np.min(v), 1e-30)),
    }


def outlier_channels(values: np.ndarray, factor: float = 2.0) -> list[int]:
    """1-based channels sitting more than ``factor`` above the median.

    On a resistor-loaded board every channel sees the same fixture, so a
    channel that stands out is a hardware fault, not biology. Naming it here
    saves an hour of staring at an eight-line spaghetti plot.
    """
    v = np.asarray(values, dtype=np.float64)
    med = float(np.median(v))
    return [int(i) + 1 for i in np.where(v > factor * med)[0]]
