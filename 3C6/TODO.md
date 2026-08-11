# 3C6 — TODO

- **Notebook needs a pydvma 2.x update — DO NOT update yet.** The
  notebook still calls `dvma.Logger(...)`, which was the Qt desktop
  GUI, removed in pydvma 2.0 (last Qt version: the `qt-final` git tag
  in the pydvma repo). On pydvma 2.x those cells raise an actionable
  tombstone error. Hold the update until the new workflow is decided
  (below); meanwhile the lab machines must pin pydvma 1.x, or the
  notebook stays as-is with the old install.
- **New workflow (Tore, undecided).** The old pattern was
  notebook-calls-Qt-GUI per experiment stage. Likely replacement: the
  pydvma **web logger in a right-hand browser tab** with the notebook
  on the left (the web UI has a narrow-viewport layout for exactly
  this split-screen use). Decide, then rework the notebook stages
  around it.
- **Calibrate `check_setup` targets.** `lab_3c6.check_setup(settings)`
  is the new live noise-level meter (advisory red/amber/green bars).
  Its `NOISE_TARGET_RMS = 0.2` V rms (±5%) is a PLACEHOLDER — measure
  the correct per-channel levels on the real cantilever rig and set
  them (per-channel values supported via `target_rms=[...]`). Then
  wire the check into the notebook's setup stage once the workflow is
  decided.
- **Absolute scaling check (later).** pydvma is gaining
  `verify_input_scaling(...)` — verification against a KNOWN source
  (NI AO→AI loopback, or the lab's Rigol DG1022Z over SCPI). Once
  released, a 3C6 wrapper could verify the whole input chain
  absolutely, not just that levels sit in a band. SCPI notes:
  `additional_device_info/rigol-dg1022z-notes.md`.
