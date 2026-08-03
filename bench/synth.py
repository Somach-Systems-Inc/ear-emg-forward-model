"""Synthetic signal generator -- the reason this suite works on day one.

The hardware lands on 6 August. Every analysis path in this repo has already
been exercised end to end against signals generated here, with known answers,
so that day is spent collecting data rather than discovering that the CMRR
maths had a sign error.

Everything below is a MODEL. The parameters are chosen to be plausible for an
ADS1299 front end and an AD8232, but no number here is a measurement and none
of it should ever be quoted as one. Its only job is to have known ground
truth: the noise floor is what ``NoiseModel`` says it is, the CMRR is what
``cmrr_db()`` says it is, and ``selftest.py`` asserts that each analysis
script recovers those values from the synthetic stream. If an analysis is
wrong, the recovered number will not match the injected one and the selftest
fails.

Every figure produced from this generator is stamped SYNTHETIC. A synthetic
figure that could be mistaken for a measurement is worse than no figure.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict

import numpy as np

import config


# ===========================================================================
# Model parameters
# ===========================================================================

@dataclass
class NoiseModel:
    """Input-referred noise of the modelled front end."""

    white_density_v_rthz: float = 25e-9
    """Broadband voltage-noise density of the amplifier alone. The datasheet's
    gain-24 figure, 0.14 uVrms over a 65 Hz bandwidth, works out at about
    17 nV/sqrt(Hz); 25 nV/sqrt(Hz) is the same part at gain 8, and integrating
    it with the flicker tail over 0.5-50 Hz gives ~0.19 uVrms, which is where
    the gain-8 entry in ``config.EXPECTED_INPUT_NOISE_URMS`` sits. The model is
    calibrated to the expectation on purpose: the selftest can then check that
    the analysis recovers a number the pass/fail gate agrees with."""

    flicker_corner_hz: float = 2.0
    """1/f corner. The ADS1299 is not chopper-stabilised, so it has one."""

    current_noise_a_rthz: float = 0.0
    """Input current noise. Set non-zero to make the 10 k source condition
    differ from the shorted condition by more than thermal noise alone --
    which is precisely the effect a shorted-input measurement cannot see."""


@dataclass
class MainsModel:
    f0_hz: float = config.MAINS_HZ
    amplitude_v: float = 1.5e-6
    """Differential mains amplitude at the fundamental, volts peak, with bias
    drive off and a 10 k source. Bench-plausible, not measured."""

    harmonic_decay: float = 0.45
    """Amplitude of harmonic n relative to n-1. Odd harmonics dominate real
    mains; this model keeps all of them and weights odd ones higher."""

    n_harmonics: int = config.MAINS_N_HARMONICS
    odd_boost: float = 2.2
    frequency_drift_hz: float = 0.02


@dataclass
class CmrrModel:
    cmrr0_db: float = 120.0
    """Low-frequency system CMRR."""

    corner_hz: float = 30.0
    """Above this the CMRR falls at 20 dB/decade, as the input-path impedance
    imbalance stops being negligible against the amplifier's own rejection."""

    def cmrr_db(self, f_hz: float | np.ndarray) -> np.ndarray:
        f = np.asarray(f_hz, dtype=float)
        return self.cmrr0_db - 20.0 * np.log10(np.sqrt(1.0 + (f / self.corner_hz) ** 2))


@dataclass
class BiasModel:
    """Right-leg / BIAS drive as a common-mode feedback loop."""

    dc_loop_gain_db: float = 26.0
    """Extra common-mode rejection the loop provides at DC."""

    corner_hz: float = 45.0
    """Loop bandwidth. Above it the benefit falls away, which is why the
    improvement at the 3rd mains harmonic is much smaller than at 60 Hz."""

    added_noise_density_v_rthz: float = 30e-9
    """The bias amplifier is not free -- it injects its own noise into the
    common-mode node. A real bias-on/off comparison should show mains dropping
    AND the broadband floor rising slightly. If your measurement shows only
    the first, look for a channel that is not actually in the loop."""

    def benefit_db(self, f_hz: float | np.ndarray) -> np.ndarray:
        f = np.asarray(f_hz, dtype=float)
        return self.dc_loop_gain_db - 20.0 * np.log10(
            np.sqrt(1.0 + (f / self.corner_hz) ** 2))


@dataclass
class SynthConfig:
    fs_hz: float = config.FS_HZ
    n_channels: int = config.N_CHANNELS
    seed: int = 20260806
    noise: NoiseModel = field(default_factory=NoiseModel)
    mains: MainsModel = field(default_factory=MainsModel)
    cmrr: CmrrModel = field(default_factory=CmrrModel)
    bias: BiasModel = field(default_factory=BiasModel)

    channel_noise_spread: float = 0.12
    """Fractional channel-to-channel variation in noise density, so the
    per-channel bar chart has something to show and an outlier-detection path
    gets exercised."""

    def as_meta(self) -> dict:
        return asdict(self)


# ===========================================================================
# Primitives
# ===========================================================================

def white(density_v_rthz: float, n: int, fs: float, rng) -> np.ndarray:
    """White noise of the given one-sided density, volts."""
    sigma = density_v_rthz * math.sqrt(fs / 2.0)
    return rng.normal(0.0, sigma, n)


def flicker_shaped(density_v_rthz: float, corner_hz: float, n: int,
                   fs: float, rng) -> np.ndarray:
    """Noise with density ``d * sqrt(1 + fc/f)`` -- white plus a 1/f tail."""
    x = white(density_v_rthz, n, fs, rng)
    spec = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1.0 / fs)
    shape = np.ones_like(f)
    shape[1:] = np.sqrt(1.0 + corner_hz / f[1:])
    shape[0] = shape[1] if len(shape) > 1 else 1.0
    return np.fft.irfft(spec * shape, n)


def mains_waveform(model: MainsModel, n: int, fs: float, rng,
                   scale: float = 1.0) -> np.ndarray:
    """Mains fundamental plus harmonics, volts."""
    t = np.arange(n) / fs
    f0 = model.f0_hz + rng.normal(0.0, model.frequency_drift_hz)
    out = np.zeros(n)
    nyq = fs / 2.0
    for k in range(1, model.n_harmonics + 1):
        f = f0 * k
        if f >= nyq * 0.98:
            break
        amp = model.amplitude_v * (model.harmonic_decay ** (k - 1))
        if k % 2 == 1 and k > 1:
            amp *= model.odd_boost
        phase = rng.uniform(0, 2 * math.pi)
        out += scale * amp * np.sin(2 * math.pi * f * t + phase)
    return out


# ===========================================================================
# The source
# ===========================================================================

SOURCE_CONDITIONS = ("10k", "short", "imbalance")


class SyntheticSource:
    """Generates input-referred volts for every measurement in the suite."""

    def __init__(self, cfg: SynthConfig | None = None):
        self.cfg = cfg or SynthConfig()
        self._rng = np.random.default_rng(self.cfg.seed)
        spread = self._rng.normal(1.0, self.cfg.channel_noise_spread,
                                  self.cfg.n_channels)
        self.channel_scale = np.clip(spread, 0.7, 1.5)

    # -- source impedance ---------------------------------------------------

    @staticmethod
    def source_resistance(condition: str) -> tuple[float, float]:
        """(R_plus, R_minus) in ohms for a named fixture condition."""
        if condition == "short":
            return 0.0, 0.0
        if condition == "10k":
            return config.SOURCE_R_OHM, config.SOURCE_R_OHM
        if condition == "imbalance":
            # Deliberate 10% mismatch: the condition that exposes how much of
            # your system CMRR is really source-impedance matching.
            return config.SOURCE_R_OHM, config.SOURCE_R_OHM * 1.10
        raise ValueError(f"unknown source condition {condition!r}; "
                         f"expected one of {SOURCE_CONDITIONS}")

    def thermal_and_current_noise(self, condition: str, n: int,
                                  ch_scale: float) -> np.ndarray:
        """Noise contributed by the SOURCE, not the amplifier.

        This term is identically zero for a short, which is the entire reason
        the noise-floor protocol does not use one.
        """
        rp, rm = self.source_resistance(condition)
        fs = self.cfg.fs_hz
        v = np.zeros(n)
        for r in (rp, rm):
            if r <= 0:
                continue
            v += white(config.johnson_noise_density(r), n, fs, self._rng)
            i_n = self.cfg.noise.current_noise_a_rthz
            if i_n > 0:
                v += white(i_n * r, n, fs, self._rng)
        return v * ch_scale

    def amplifier_noise(self, n: int, ch_scale: float) -> np.ndarray:
        nm = self.cfg.noise
        return flicker_shaped(nm.white_density_v_rthz * ch_scale,
                              nm.flicker_corner_hz, n, self.cfg.fs_hz, self._rng)

    # -- whole recordings ---------------------------------------------------

    def noise_floor(self, seconds: float, condition: str = "10k",
                    bias_on: bool = False, with_mains: bool = True
                    ) -> np.ndarray:
        """(n_samples, n_channels) of input-referred volts."""
        n = int(round(seconds * self.cfg.fs_hz))
        out = np.empty((n, self.cfg.n_channels))
        # The bias loop's benefit is applied PER HARMONIC inside
        # _mains_with_harmonic_bias, not as one scale factor here. Flattening
        # it would make the bias comparison in 04 look better than reality,
        # because the loop rolls off and rejects the 3rd harmonic far less
        # than the fundamental.
        for ch in range(self.cfg.n_channels):
            s = float(self.channel_scale[ch])
            v = self.amplifier_noise(n, s)
            v = v + self.thermal_and_current_noise(condition, n, s)
            if bias_on:
                v = v + white(self.cfg.bias.added_noise_density_v_rthz, n,
                              self.cfg.fs_hz, self._rng)
            if with_mains:
                v = v + self._mains_with_harmonic_bias(n, bias_on, condition)
            out[:, ch] = v
        return out

    def _mains_with_harmonic_bias(self, n: int, bias_on: bool,
                                  condition: str) -> np.ndarray:
        """Mains pickup, with the bias loop's benefit applied per harmonic.

        The loop rolls off, so the 3rd harmonic is rejected far less than the
        fundamental. Flattening that into a single scale factor would make the
        bias comparison script look better than reality.
        """
        m = self.cfg.mains
        t = np.arange(n) / self.cfg.fs_hz
        rng = self._rng
        f0 = m.f0_hz + rng.normal(0.0, m.frequency_drift_hz)
        # An impedance imbalance converts common mode to differential, so the
        # imbalance fixture picks up more mains. A short picks up almost none,
        # which is the second reason not to test with one.
        cond_scale = {"short": 0.05, "10k": 1.0, "imbalance": 3.2}[condition]
        out = np.zeros(n)
        nyq = self.cfg.fs_hz / 2.0
        for k in range(1, m.n_harmonics + 1):
            f = f0 * k
            if f >= nyq * 0.98:
                break
            amp = m.amplitude_v * (m.harmonic_decay ** (k - 1))
            if k % 2 == 1 and k > 1:
                amp *= m.odd_boost
            if bias_on:
                amp *= 10 ** (-float(self.cfg.bias.benefit_db(f)) / 20.0)
            out += cond_scale * amp * np.sin(
                2 * math.pi * f * t + rng.uniform(0, 2 * math.pi))
        return out

    def tone(self, seconds: float, freq_hz: float, amplitude_v: float,
             mode: str, bias_on: bool = False,
             condition: str = "10k") -> np.ndarray:
        """A single-frequency segment for the CMRR sweep.

        ``mode="differential"``: ``amplitude_v`` is the differential amplitude
        actually presented to the inputs (i.e. already through the divider).
        The channel should see it essentially unattenuated.

        ``mode="common"``: ``amplitude_v`` is the common-mode amplitude on both
        inputs together. What reaches the differential output is that amplitude
        divided by the system CMRR at this frequency -- the thing being
        measured.
        """
        n = int(round(seconds * self.cfg.fs_hz))
        t = np.arange(n) / self.cfg.fs_hz
        out = np.empty((n, self.cfg.n_channels))

        if mode == "differential":
            leak_db = 0.0
        elif mode == "common":
            leak_db = float(self.cfg.cmrr.cmrr_db(freq_hz))
            if bias_on:
                leak_db += float(self.cfg.bias.benefit_db(freq_hz))
        else:
            raise ValueError(f"mode must be 'differential' or 'common', got {mode!r}")

        seen = amplitude_v * 10 ** (-leak_db / 20.0)
        for ch in range(self.cfg.n_channels):
            s = float(self.channel_scale[ch])
            v = self.amplifier_noise(n, s)
            v = v + self.thermal_and_current_noise(condition, n, s)
            if bias_on:
                v = v + white(self.cfg.bias.added_noise_density_v_rthz, n,
                              self.cfg.fs_hz, self._rng)
            phase = 0.31 * ch
            # Per-channel spread: real boards do not have identical CMRR on
            # every channel, and a sweep that hides that is not useful.
            ch_leak = seen * (1.0 + 0.06 * (s - 1.0) / max(self.cfg.channel_noise_spread, 1e-9))
            v = v + ch_leak * np.sin(2 * math.pi * freq_hz * t + phase)
            out[:, ch] = v
        return out

    def test_signal(self, seconds: float, amp_2x: bool = False,
                    freq_hz: float = 7.8125) -> np.ndarray:
        """The ADS1299 internal square-wave test signal, input-referred.

        Default frequency is fCLK / 2^21 with the internal oscillator, which
        lands near 7.8 Hz -- low enough that the 0.5-50 Hz analysis band sees
        several full cycles in a short capture.
        """
        n = int(round(seconds * self.cfg.fs_hz))
        t = np.arange(n) / self.cfg.fs_hz
        amp = config.test_signal_amplitude_v(amp_2x)
        square = amp * np.sign(np.sin(2 * math.pi * freq_hz * t))
        out = np.empty((n, self.cfg.n_channels))
        for ch in range(self.cfg.n_channels):
            s = float(self.channel_scale[ch])
            out[:, ch] = square + self.amplifier_noise(n, s)
        return out


# ===========================================================================
# The comparison device
# ===========================================================================

@dataclass
class Ad8232Model:
    """A single-lead ECG front end, modelled as the comparison device.

    The point of the comparison is not that the AD8232 is bad -- it is a good
    part for what it was designed for. The point is that its noise floor and
    its typical 12-bit digitiser are sized for millivolt ECG, and EEG is two
    orders of magnitude smaller. The quantisation term below is computed, not
    asserted, and it is usually the headline of the comparison.
    """

    instrumentation_gain: float = 100.0
    second_stage_gain: float = 11.0
    input_noise_density_v_rthz: float = 366e-9
    """~14 uV p-p over 0.5-40 Hz from the datasheet, converted: 14 uVpp is
    about 2.3 uVrms, over a 39.5 Hz band that is 366 nV/sqrt(Hz)."""

    flicker_corner_hz: float = 6.0
    hpf_hz: float = 0.5
    cmrr_db_at_60hz: float = 80.0
    adc_bits: int = 12
    adc_span_v: float = 3.3
    """A bare ESP32 ADC. Change if you digitise it some other way -- and note
    that this single line moves the comparison's conclusion more than any
    analog parameter does."""

    @property
    def total_gain(self) -> float:
        return self.instrumentation_gain * self.second_stage_gain

    @property
    def lsb_input_referred_v(self) -> float:
        return self.adc_span_v / (2 ** self.adc_bits) / self.total_gain

    @property
    def quantisation_noise_v_rms(self) -> float:
        """LSB / sqrt(12), input-referred. Uniform quantisation error."""
        return self.lsb_input_referred_v / math.sqrt(12.0)


def synth_ad8232(model: Ad8232Model, seconds: float, fs_hz: float,
                 mains: MainsModel, seed: int = 4242,
                 with_mains: bool = True) -> tuple[np.ndarray, dict]:
    """Input-referred volts from a modelled AD8232 chain, already quantised.

    Returns (volts, meta). The signal is generated at the input, amplified,
    quantised at the ADC, then divided back down -- the same order the real
    chain does it in, so the quantisation floor lands where it really would.
    """
    rng = np.random.default_rng(seed)
    n = int(round(seconds * fs_hz))
    v = flicker_shaped(model.input_noise_density_v_rthz,
                       model.flicker_corner_hz, n, fs_hz, rng)
    if with_mains:
        # Worse CMRR than the ADS1299 -> more mains gets through.
        leak = 10 ** (-(model.cmrr_db_at_60hz - 60.0) / 20.0)
        v = v + mains_waveform(mains, n, fs_hz, rng, scale=leak)

    # Single-pole high-pass at hpf_hz, applied in the frequency domain.
    spec = np.fft.rfft(v)
    f = np.fft.rfftfreq(n, 1.0 / fs_hz)
    h = np.zeros_like(f, dtype=complex)
    nz = f > 0
    jw = 1j * f[nz] / model.hpf_hz
    h[nz] = jw / (1.0 + jw)
    v = np.fft.irfft(spec * h, n)

    out_v = np.clip(v * model.total_gain, -model.adc_span_v / 2,
                    model.adc_span_v / 2)
    lsb = model.adc_span_v / (2 ** model.adc_bits)
    codes = np.round(out_v / lsb)
    v_quantised = codes * lsb / model.total_gain

    meta = {
        "device": "AD8232 (model)",
        "total_gain": model.total_gain,
        "adc_bits": model.adc_bits,
        "adc_span_v": model.adc_span_v,
        "lsb_input_referred_uv": model.lsb_input_referred_v * 1e6,
        "quantisation_noise_uvrms": model.quantisation_noise_v_rms * 1e6,
        "hpf_hz": model.hpf_hz,
        "cmrr_db_at_60hz": model.cmrr_db_at_60hz,
        "synthetic": True,
    }
    return v_quantised.reshape(-1, 1), meta
