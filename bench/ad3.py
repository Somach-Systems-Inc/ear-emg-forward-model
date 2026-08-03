"""Analog Discovery 3 waveform generator, three ways.

The CMRR sweep needs a sine at each of eleven frequencies, twice (differential
pass and common-mode pass). That is 22 generator settings per protocol, and
doing it by hand is where a sweep quietly acquires a wrong amplitude.

``ManualAD3``   prompts for every setting and makes you confirm. Slow, but it
                will work on 6 August with no SDK installed. THE DEFAULT.
``WaveformsAD3`` drives libdwf over ctypes. Faster, and UNTESTED -- no AD3 was
                attached while this was written. It proves itself before the
                sweep starts rather than failing halfway through.
``SyntheticAD3`` records what was asked for so the synthetic source can
                produce it. Used by every --synthetic run.

Amplitude convention throughout this suite: VOLTS PEAK, at the point named.
``set_output(f, amplitude_v)`` means "amplitude_v volts peak at the generator
terminal", i.e. at the top of the divider chain.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Setting:
    frequency_hz: float
    amplitude_v: float
    note: str = ""


class SyntheticAD3:
    kind = "synthetic"

    def __init__(self):
        self.history: list[Setting] = []
        self.current: Setting | None = None

    def check(self) -> None:
        pass

    def set_output(self, frequency_hz: float, amplitude_v: float,
                   note: str = "") -> None:
        self.current = Setting(frequency_hz, amplitude_v, note)
        self.history.append(self.current)

    def off(self) -> None:
        self.current = None

    def describe(self) -> dict:
        return {"kind": self.kind, "settings": len(self.history)}


class ManualAD3:
    """You are the driver. Every setting is confirmed before anything records."""

    kind = "manual"

    def __init__(self, confirm: bool = True):
        self.confirm = confirm
        self.history: list[Setting] = []

    def check(self) -> None:
        print("\n  AD3 in MANUAL mode. You will be prompted for each setting.\n"
              "  Before starting, confirm on the AD3 scope that the amplitude\n"
              "  at the TOP of the divider is what you think it is. The\n"
              "  generator's amplitude dial is not a measurement -- its output\n"
              "  impedance in series with a 1120 ohm chain is a real error.\n")

    def set_output(self, frequency_hz: float, amplitude_v: float,
                   note: str = "") -> None:
        self.history.append(Setting(frequency_hz, amplitude_v, note))
        prompt = (f"\n  Set W1 to {frequency_hz:>8.3f} Hz, "
                  f"{amplitude_v:.4f} V peak sine")
        if note:
            prompt += f"  [{note}]"
        input(prompt + "\n  Press Enter when the scope confirms it: ")

    def off(self) -> None:
        input("\n  Turn W1 OFF, then press Enter: ")

    def describe(self) -> dict:
        return {"kind": self.kind, "settings": len(self.history)}


class WaveformsAD3:
    """ctypes binding to Digilent's libdwf.

    NOT TESTED AGAINST HARDWARE. It is written to fail immediately and
    obviously if anything is wrong, and ``check()`` runs a full open / set /
    read-back before the sweep begins, so a broken SDK costs you one second
    rather than a half-finished dataset.
    """

    kind = "waveforms"

    _LIB_CANDIDATES = (
        "/Library/Frameworks/dwf.framework/dwf",
        "libdwf.dylib", "libdwf.so", "libdwf.so.3", "dwf.dll",
    )

    # DwfAnalogOutNode / func constants from dwfconstants.py
    _AnalogOutNodeCarrier = 0
    _funcSine = 1

    def __init__(self, channel: int = 0):
        import ctypes  # noqa: PLC0415
        self.ctypes = ctypes
        self.channel = channel
        self.dwf = None
        self.hdwf = None
        self.history: list[Setting] = []
        last = None
        for name in self._LIB_CANDIDATES:
            try:
                self.dwf = ctypes.cdll.LoadLibrary(name)
                break
            except OSError as exc:
                last = exc
        if self.dwf is None:
            raise RuntimeError(
                "Could not load Digilent's libdwf, so --ad3 auto is not "
                f"available (last error: {last}).\n"
                "Install the WaveForms runtime, or use --ad3 manual, which "
                "needs nothing installed and is the default for exactly this "
                "reason.")

    def _err(self) -> str:
        buf = self.ctypes.create_string_buffer(512)
        try:
            self.dwf.FDwfGetLastErrorMsg(buf)
        except Exception:
            return "unknown"
        return buf.value.decode(errors="replace").strip()

    def check(self) -> None:
        ct = self.ctypes
        hdwf = ct.c_int()
        if self.dwf.FDwfDeviceOpen(ct.c_int(-1), ct.byref(hdwf)) == 0 or hdwf.value == 0:
            raise RuntimeError(
                "libdwf loaded but no Analog Discovery could be opened: "
                f"{self._err()}\n"
                "Is WaveForms itself still running and holding the device? "
                "Close it, or use --ad3 manual.")
        self.hdwf = hdwf
        self.set_output(100.0, 0.01, note="self-check")
        self.off()
        print("  AD3 opened and accepted a setting. Proceeding.")

    def set_output(self, frequency_hz: float, amplitude_v: float,
                   note: str = "") -> None:
        ct = self.ctypes
        ch = ct.c_int(self.channel)
        node = ct.c_int(self._AnalogOutNodeCarrier)
        ok = all([
            self.dwf.FDwfAnalogOutNodeEnableSet(self.hdwf, ch, node, ct.c_bool(True)),
            self.dwf.FDwfAnalogOutNodeFunctionSet(self.hdwf, ch, node,
                                                  ct.c_ubyte(self._funcSine)),
            self.dwf.FDwfAnalogOutNodeFrequencySet(self.hdwf, ch, node,
                                                   ct.c_double(frequency_hz)),
            self.dwf.FDwfAnalogOutNodeAmplitudeSet(self.hdwf, ch, node,
                                                   ct.c_double(amplitude_v)),
            self.dwf.FDwfAnalogOutConfigure(self.hdwf, ch, ct.c_bool(True)),
        ])
        if not ok:
            raise RuntimeError(
                f"AD3 rejected {frequency_hz} Hz / {amplitude_v} V: {self._err()}")
        self.history.append(Setting(frequency_hz, amplitude_v, note))

    def off(self) -> None:
        ct = self.ctypes
        self.dwf.FDwfAnalogOutConfigure(self.hdwf, ct.c_int(self.channel),
                                        ct.c_bool(False))

    def close(self) -> None:
        if self.hdwf is not None:
            self.off()
            self.dwf.FDwfDeviceClose(self.hdwf)
            self.hdwf = None

    def describe(self) -> dict:
        return {"kind": self.kind, "settings": len(self.history)}


def open_generator(mode: str, synthetic: bool):
    if synthetic:
        gen = SyntheticAD3()
    elif mode == "auto":
        gen = WaveformsAD3()
    elif mode == "manual":
        gen = ManualAD3()
    else:
        raise ValueError(f"unknown AD3 mode {mode!r}")
    gen.check()
    return gen


def add_ad3_args(parser) -> None:
    g = parser.add_argument_group("signal generator")
    g.add_argument("--ad3", choices=("manual", "auto"), default="manual",
                   help="how the AD3 is driven in hardware mode. 'manual' "
                        "prompts for each setting and needs no SDK (default); "
                        "'auto' drives libdwf and is untested against a real "
                        "AD3.")
    g.add_argument("--divider-tap", choices=("low", "mid"), default="low",
                   help="divider tap feeding the differential pass "
                        "(low = across the 20 R, 1/56)")
    g.add_argument("--ad3-amplitude", type=float, default=1.0,
                   help="generator amplitude for the differential pass, volts "
                        "peak MEASURED at the top of the divider")
