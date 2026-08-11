# Rigol DG1022Z — Working Notes

Reference notes covering front-panel frequency entry, USB control from macOS, and a scripted-setup workflow for by-hand experiments.

---

## 1. Front panel: setting frequency

The rotary knob **edits the single digit under the cursor**, it does not scale the value as a whole. If the cursor sits on the leading digit of `1.000 000 kHz`, winding down would produce zero, which is invalid, so it stops. This is what looks like a 1 kHz floor. It isn't one.

**Option A — move the cursor.** Use the ◄ ► arrow keys to shift onto a less significant digit, then turn the knob. From `1.000 000 kHz`, move a couple of places right and you can dial down through `0.100 000 kHz` (100 Hz) and below.

**Option B — type it.** Press the *Freq* softkey (the same softkey toggles Freq/Period, so check which is showing), enter the number on the keypad, then press the unit softkey down the right-hand side: **MHz / kHz / Hz / mHz / µHz**.

- `50` → *Hz* = 50 Hz
- `5` → *mHz* = 0.005 Hz

A unit softkey must be pressed to commit. Pressing Enter alone applies the default unit.

The instrument goes down to 1 µHz on sine and square. Also confirm you're editing the intended channel — the CH1/CH2 buttons select which channel the parameters apply to.

---

## 2. USB control from macOS

The DG1022Z is a USBTMC device and macOS handles it with no Rigol driver. Rigol's UltraSigma is Windows-only, so Python is the practical route.

### Setup

```bash
brew install libusb
pip install pyvisa pyvisa-py pyusb
```

PyVISA-py is a pure-Python VISA backend, which avoids NI-VISA on macOS (patchy, particularly on Apple Silicon).

### Connecting

```python
import pyvisa

rm = pyvisa.ResourceManager('@py')
print(rm.list_resources())          # find the USB0::0x1AB1::...::INSTR string

dg = rm.open_resource('USB0::0x1AB1::0x0642::DG1ZA...::INSTR')
dg.timeout = 5000
print(dg.query('*IDN?'))
```

If `list_resources()` returns empty:

- Check the cable is in the **Device** port on the rear panel, not the Host port on the front.
- Try running once with `sudo` to rule out a permissions issue.
- If the box has been power cycled since the last session, reopen the resource.

---

## 3. Core SCPI commands

Channel is selected by the digit in `SOUR1` / `SOUR2` and `OUTP1` / `OUTP2`.

| Task | Command |
|---|---|
| Identify | `*IDN?` |
| Reset to factory state | `*RST` |
| Apply full sine config | `:SOUR1:APPL:SIN 1000,2,0,0` |
| Frequency (always Hz) | `:SOUR1:FREQ 50` |
| Amplitude | `:SOUR1:VOLT 2` |
| Amplitude units | `:SOUR1:VOLT:UNIT VPP\|VRMS\|DBM` |
| DC offset | `:SOUR1:VOLT:OFFS 0` |
| Waveform shape | `:SOUR1:FUNC SIN\|SQU\|RAMP\|PULS\|NOIS\|DC\|USER` |
| Output load | `:OUTP1:LOAD INF` (or `50`) |
| Output on/off | `:OUTP1:STAT ON\|OFF` |
| Save state to slot | `*SAV 1` |
| Recall state from slot | `*RCL 1` |
| Return front panel to user | `:SYST:LOCal` |

`:APPL:SIN` argument order is frequency (Hz), amplitude (Vpp), offset (V), phase (deg).

Every setting that can be written can also be queried, by appending `?` — e.g. `:SOUR1:FREQ?`.

---

## 4. Output modes

All scriptable, not just front-panel:

- **Waveform shape** — sine, square, ramp, pulse, noise, DC, user/arb, plus the built-in arb library.
- **Modulation** — AM, FM, PM, ASK, FSK, PSK, PWM, each with its own command subtree.
- **Sweep** — linear or log, via `:SOUR1:FREQ:STAR` and `:SOUR1:FREQ:STOP`, plus sweep time, hold and return times.
- **Burst** — N-cycle, gated, infinite.
- **Dual-channel** — channel coupling and tracking, phase alignment, sync output.

Sweep and burst both accept a **manual trigger source**, which suits by-hand experiments well: configure over USB, then press the front-panel Trigger key for each run.

---

## 5. Workflow pattern

The intended shape of a session:

1. Power on, connect USB.
2. Run a Python setup script to configure channels, levels, frequency, mode.
3. Send `:SYST:LOCal` as the final line.
4. Carry out the experiment by hand at the front panel.
5. Call a `reset()` helper to return to the standard baseline.

**Settings persist.** Anything pushed over USB stays put. The Python session can be closed and the instrument unplugged without losing the configuration.

**Baseline reset — two approaches:**

- `*RST` followed by an explicit standard config. More verbose, but self-documenting about what "normal" means.
- `*SAV 1` once to store the baseline, then `reset()` is just `*RCL 1`. Fewer lines, faster, but the definition of the baseline lives in the instrument rather than in version control.

**Worth building early:** a `dump_state()` helper that queries frequency, amplitude, offset, load, mode and output status for both channels and writes them to a timestamped file. Cheap to write, and it gives a free record of the exact instrument config per experiment.

---

## 6. Gotchas

**Remote lockout.** Sending SCPI puts the unit into remote mode and the front panel locks (remote indicator appears on screen). The Local key restores manual control, or send `:SYST:LOCal` at the end of the script. End every setup script this way if the plan is to touch the knobs afterwards.

**Output load.** If the generator is set for 50 Ω but the load is high-impedance (e.g. a 1 MΩ scope input), the measured amplitude is **double** what was requested. Set `:OUTP1:LOAD INF` for high-Z.

**Command pacing.** DG1000Z firmware can be slow digesting back-to-back writes. If behaviour looks flaky, set `dg.query_delay = 0.1` or insert short `time.sleep` calls between writes.

**Vrms constraints.** Vrms is only meaningful for periodic waveforms. dBm is rejected when the load is set to high-Z. Changing waveform shape while in Vrms recalculates the amplitude, so **set the shape first, then the level**.

---

## 7. To verify against the official programming guide

These notes are working knowledge, not transcribed from the manual. Before relying on them for anything precise, check the *DG1000Z Programming Guide* for:

- Exact frequency limits per waveform type (sine and square go to 25 MHz; ramp and pulse maxima are lower).
- Exact modulation subtree syntax, which varies more between Rigol families than the core commands do.
- The resource string format for your specific unit, which is easiest read straight off `list_resources()`.
