# EMG: maps, processing, normalisation

{py:mod}`bioscout.emg`

* **emg_map** (session.yaml) — analog channel → model muscles it stands for.
  It is the only statement of which electrode is which; channel names are
  validated against the c3d's labels (a mapped channel that does not exist is
  a hard error). `python -m bioscout.emg.channels TRIAL.c3d --yaml` writes a
  stub.
* **processing** — band-pass (20–95 Hz), rectification, low-pass envelope
  (6 Hz) by default ({py:func}`bioscout.emg.emg.emg_processing_file`); data that
  is already an envelope (`pre_enveloped`) is only normalised.
* **normalisation** — {py:meth}`bioscout.session.iteration.Iteration.run_emg_normalise`:
  per channel, the maximum of the envelope over **every** session trial with
  `emg_normalisation: true` (stored in `2_experimental/maxemg.txt`, with the
  trial and instant that set it); each trial's
  `emg_filtered_normalised.mot` = envelope / that max, in [0, 1]. Adding
  trials can raise the max and rescale every trial; correlation-based
  comparisons (r) are unaffected, amplitude ones are not.
* **figure** — `emg_processing.png` per trial: poses + vGRF + hip/knee/ankle
  angles on top, then one row per channel coloured by the side of its mapped
  muscles ({py:mod}`bioscout.plot.emg_figure`).
* **use** — CEINMS excitations; comparison with SO activations (mean
  activation of the mapped muscles vs the channel).
