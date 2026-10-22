# 3C6 — TODO

- **Notebook updated for pydvma 2.x (2026-10-16).** Workflow: 3.1's
  stepped sine stays in the notebook widget
  (`lab_3c6.measure_stepped_sine`, now with live input level bars in
  place of the old Qt oscilloscope). From 3.2 on, one
  `dvma.launch(settings, window=..., tf_averaging=...)` web logger runs
  in a browser tab beside the notebook, and each section's settings
  cell calls `logger.apply_settings(...)`. 3.4's calibration uses the
  app's Calibrate dialog ("Transfer function" section). The lab PCs need
  pydvma 2.7.0 as re-cut with `Session.apply_settings` (pydvma commit
  `35ae762`).
- **Test on the rig before term.** So far it has only been smoke-tested
  on pydvma's mock driver, with no browser. On the PCI-6220 bench, check:
  - the stepped-sine level bars (checked on one PC on 2026-10-20: they
    update live and stop on a logger-style `start_stream`): does CLIP
    show at 95 % of ±5 V, and do they stop cleanly once the real logger
    opens its stream in 3.2;
  - ipympl is installed on all six PCs (the widget and every plot need
    `%matplotlib widget`), and Start_3C6.bat refreshes `lab_3c6.py`;
  - `apply_settings` lands in the open Edge tab in each section (toast,
    Setup values), and the 5 %-of-full-scale trigger (0.25 V) catches a
    gentle hammer tap;
  - the folder button saves into the notebook's folder, and the
    `choose_file` picker lists those files;
  - `coupled_prediction.dvma` loads in the app as three TF sets.
- **Saved files piled up deleted sets on pydvma 2.7.0 (lab, 2026-10-22).**
  The logger's tray × took a set off the screen but not out of the data,
  so each beam file in 3.5 held every earlier measurement, and
  `coupled_TF` (which took each file's FIRST transfer function) predicted
  from the wrong one. Fixed in pydvma after 2.7.0 (the tray × now
  removes the set from the saved data); upgrade the lab PCs once it is
  released. Meanwhile `lab_3c6.coupled_TF` copes with 2.7.0 files: it
  uses each file's NEWEST measurement and prints which.
- **Re-export after any notebook change:** `python make_exports.py`
  rewrites `3C6_Notebook.html`, `.pdf` and `_LAB_COPY.pdf` (needs Google
  Chrome and an internet connection for MathJax).
- **Absolute scaling check (later).** pydvma now has
  `dvma.verify_input_scaling(...)` and `dvma.RigolDG1022Z`: verification
  against a KNOWN source (NI AO→AI loopback, or the lab's Rigol DG1022Z
  over SCPI). A 3C6 wrapper could verify the whole input chain
  absolutely. SCPI notes: `additional_device_info/rigol-dg1022z-notes.md`.
