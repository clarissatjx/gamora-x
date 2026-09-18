---
name: streamlit-inference-app
description: Use when building the compulsory shared PS3 app — one Streamlit app covering every subsystem attempted, letting a non-technical user upload a raw data file and get a prediction back on screen with a download option. This is the item judged for Ease of Use, scored from the demo video and the app itself.
---

# Shared Streamlit app for PS3 (all subsystems, one app)

The spec requires **one app covering every subsystem attempted**, not one app per subsystem —
submitted once at the team-root level (`app/`). This app is also what must actually produce the
`*_predictions.csv` files you zip and submit (Section 4.1 items 2 and 3 are linked: run the
held-out test files through this same app to generate your predictions).

## Structure

```
app/
├── app.py            # subsystem picker (tabs or st.selectbox) + uploader + results panel
├── models/           # one trained artifact per subsystem, loaded once (st.cache_resource)
├── inference/
│   ├── door.py        # raw stream -> segments -> labels -> DataFrame(start_time,end_time,prediction)
│   ├── acv.py          # raw telemetry -> ranked car list -> DataFrame(file_id,ranked_cars)
│   ├── rail.py         # raw vibration file -> label -> DataFrame(file_id,prediction)
│   └── shm.py           # raw stress series -> damage value -> DataFrame(file_id,prediction)
└── requirements.txt
```

Each `inference/<subsystem>.py` function should be the **single source of truth** used both by
the app and by any batch script that generates the final submission CSVs — don't duplicate the
inference logic in two places, since divergence between "what the app shows" and "what got
submitted" would undercut the demo video as evidence of a real pipeline.

## Per-subsystem UI flow (keep consistent across tabs for a clean demo video)
1. `st.selectbox`/tabs to pick the subsystem.
2. `st.file_uploader` accepting that subsystem's native raw format (`.csv` for Door/Rail/SHM,
   `.xlsx` for ACV) — do not require a pre-processed format from the user, the whole point is a
   non-technical user drags in the raw file they were given.
3. Run that subsystem's `inference/*.py` on upload; render the result:
   - Door: table of predicted segments + a chart overlaying predicted segment boundaries on the
     raw signal (e.g. current/back-EMF trace) so a viewer can visually sanity-check it
   - ACV: the ranked car list, most-likely first, ideally with a bar chart of per-car anomaly
     score if available
   - Rail: predicted class, ideally with per-class confidence if the model exposes it
   - SHM: predicted damage value, ideally with context (e.g. where it falls vs. training
     distribution)
4. `st.download_button` exporting exactly the required `*_predictions.csv` schema for that
   subsystem — see `prediction-submission-packager` for the exact column spec per subsystem.

## Ease-of-Use considerations (this is literally graded, Section 6.3)
- Handle malformed/wrong-format uploads gracefully (clear error message, not a raw traceback).
- Label things in plain language — a non-technical user shouldn't need to know what "IoU" or
  "macro F1" mean to use the app; save that language for the write-up.
- Keep the four subsystem flows visually consistent (same layout pattern) so the demo video reads
  as one coherent product, not four bolted-together scripts.
