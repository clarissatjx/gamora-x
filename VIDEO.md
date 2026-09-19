# Demo video plan

The plan for `demo_video.mp4`, which is submission item 1 ([spec §4.1](references/PS3_Problem_Statement.md)).
The video demos the submitted app: the web app in [`webapp/`](webapp/).

## What the video has to do

- **3:00 hard cap.** "Not more than 3 minutes." Aim for about 2:45 so the edit has some slack.
- **Show the required flow end to end:** pick a subsystem, upload or drag in a data file, see the
  result on screen, and download it. The judges check for each of these steps, so every one
  has to be visible at least once, and the drag-and-drop and download steps have to be obvious.
- **It's the main evidence for Ease of Use (§6.3):** ease of use for non-technical users,
  clarity of visuals and outputs, and usefulness of results. The narration should keep coming
  back to those three phrases.
- **It's also evidence for Problem Fit (§6.1):** coverage of all four datasets, explainability,
  UI, and fit with LTA predictive-maintenance needs. Show all four subsystems.
- **It shows the predictions came from a real pipeline (§4.1 item 2).** The on-screen results
  should match what's in `predictions.zip`. The demo files are held-out test files, so they do.

The app is live at <https://gamora-cdm-307993205824.asia-southeast1.run.app/> (the root
`Dockerfile`, deployed to Cloud Run). **Redeploy before recording** — the live service predates the latest frontend work — and record against the live
URL if it is warm and fast, since a real address bar is better evidence than `localhost`.

## Story in one line

*A maintenance engineer with no ML background drops in a raw file from any of the four train
subsystems. They get a plain-English verdict that says how urgent it is, how sure the model is
and why, then download the submission-format CSV.*

Every segment follows the same pattern, and that pattern is the pitch: **drop a file → verdict
→ evidence → download**. Four subsystems, one product.

## Demo file kit

Copy the files into one folder, e.g. `~/Desktop/demo/`, so every drag comes from the same Finder
window that stays in shot. Every result below was produced by the web app's own backend on
2026-09-19. Files marked ★ are the ones the shot list uses. The rest are spares: use them for
retakes, for a different angle, or to answer a judge's question live.

Everything under `data/` is gitignored, so each teammate needs their own copy of the organisers'
datasets. `app/samples/` has the four in-app samples as `.gz`; the ACV workbook is the only one
that isn't compressed.

### Door (`data/Door/`)

| | File | On screen |
|---|---|---|
| ★ | `Test.csv` | **"8 of 38 cycles show abnormal resistance"** · Inspect before next service · High. Worst is cycle 19: 132 % more current than a healthy cycle, turning slower |

Door has only one test stream. `Train.csv` also works in the app, but it's the training data,
so don't present it as a prediction.

### Rail Corrugation (`data/Rail_Corrugation/Test/`)

| | File | On screen |
|---|---|---|
| ★ | `Test33.csv` | **"Side I corrugation detected"** · Inspect before next service · High · 46 km/h, "where most faults have been seen" |
| ★ | `Test10.csv` | **"No corrugation detected"** · No action needed · High · 67 km/h |
| ★ | `Test13.csv` | **"Side I corrugation detected"** · Inspect *soon* · Confidence **Low** · 46 km/h. A flagged fault the app admits it's unsure about |
| ★ | `Test14.csv` | **"Side II corrugation detected"** · Inspect before next service · High · 68 km/h |
| ★ | `Test15.csv` | **"Inconclusive — train was stationary"** · Confidence: Unmeasurable · 0 km/h |
| | `Test2.csv`, `Test20.csv`, `Test31.csv` | Also stationary, so also **Inconclusive**. Spares for `Test15.csv` |
| | `Test3.csv` (8 km/h), `Test25.csv` (20 km/h) | "No corrugation detected", plus an amber **"Don't take this reading at face value"** callout, because the train is slower than any fault in the training data. A good second example of the app qualifying its own answer |
| | `Test22.csv`, `Test27.csv` | Side I. `Test26.csv`: Side II. Spare faults |

Across all 68 test files the submitted mix is 59 Normal, 5 Side I and 4 Side II. That includes
9 stationary files, which are submitted as Normal but shown as Inconclusive.

### ACV

| | File | On screen |
|---|---|---|
| ★ | `acv_synthetic_test_case.xlsx` (`data/ACV/Demo/`) | Not a held-out file and not in `predictions.zip`. **"Car 05 most likely faulty"** · Inspect before next service · High. Car 05 runs **+2.18 °C** above its cooling setpoint, 2.86 clear of car 01. Ranking 05 › 01 › 03 › 06 › 08 › 04 › 07 › 02. 8 cars over 6.0 h |
| ★ | `acv_test_case.xlsx` (`data/ACV/Test/`) | The held-out file. **"Car 01 most likely faulty"** · Monitor · Confidence **Low**. Car 01 is only +0.12 °C above setpoint, 0.23 clear of car 04. Ranking 01 › 04 › 03 › 07 › 08 › 06 › 02 › 05. Also the in-app sample |

The two workbooks make a good pair: the same app is confident on one and says it isn't sure on
the other. The six labelled training workbooks (`data/ACV/Train/acv_case_01–06.xlsx`) all put
the known faulty car first (01, 02, 03, 01, 04, 06). Those are useful to show a judge that the
ranking matches the answer key. `acv_case_04.xlsx` is 34 MB and slow to parse, so skip it on
camera.

### SHM (`data/SHM/Test/`)

| | File | On screen |
|---|---|---|
| ★ | `test02.csv` | **"Damage 0.827631 of 1.0"** · Inspect before next service · High. Likely 0.751–0.905. The worst of the 16 |
| | `test14.csv` (0.494), `test03.csv` (0.457), `test06.csv` (0.446), `test13.csv` (0.433) | **Monitor** · Medium |
| | `test04.csv` | **"Damage 0.028829 of 1.0"** · No action needed. The healthiest of the 16, for contrast |
| | All 16 `test*.csv` | Batch upload triages them into 1 Inspect, 4 Monitor, 11 No action needed. A quick way to show batch mode on a second subsystem |

### Wrong-file test

Drop `test02.csv` (the SHM file) on the **Door** page. It gets a clean rejection: *"This doesn't
look like a Door data file. Missing columns: Datetime, Motor current(mA), …"*. Don't drop an ACV
workbook on a CSV page (Rail, SHM or Door) for this. That error comes through as a raw
`utf-8 codec` message and looks like a bug.

## Before recording

1. **Start fresh.** Use the redeployed Cloud Run URL. As a fallback, run it locally: the backend
   (`uvicorn webapp.backend.main:app --port 8000`) and frontend (`cd webapp/frontend && npm run dev`).
2. **Warm the models.** Run every file above through the app once before you hit record. The
   first rail prediction can trigger the retrain fallback (a couple of seconds), and the ACV
   workbook parse takes about 7 s. You don't want either happening on camera. On Cloud Run the
   service scales to zero when idle, so warm it up within a few minutes of recording.
3. **Clear state.** Open the app in a **new incognito window** (or a fresh browser profile) so
   history, the Saved list and the sidebar state are empty. Delete any test notes from
   `webapp/backend/notes.db` (or via the Notes panel's Remove), or the Notes panel will show
   leftovers.
4. **Screen setup.** Use 1920×1080 at 100–110 % browser zoom so the chart labels are readable
   at 1080p. Use light or dark theme, whichever reads better on the charts, and keep it for the
   whole video. Hide the bookmarks bar and extensions, turn on Do Not Disturb, close everything
   else. Have the Finder window with `~/Desktop/demo/` beside the browser, and set the browser to
   show downloads in its toolbar.
5. **Cursor.** Use a cursor highlight or click visualiser if your recorder has one (Screen
   Studio, CleanShot, or OBS with a cursor plugin). Hover deliberately and pause about 1 s on
   every tooltip you want read.

## Shot list and narration

Target times are cumulative. The narration is about 420 words, which is roughly 2:50 at a calm
150 wpm. **Bold** in the narration is the rubric language, so say it as written.

### 1 · Open on Get started (0:00 – 0:15)

**Screen:** Get started page, sidebar visible. Slowly point at the 1-2-3 steps, then the four
subsystem tiles.

> "This is Gamora, our condition-monitoring app for PS3. It's built for a maintenance engineer
> who's never trained a model. Pick a subsystem, drop in the raw sensor file, and get a verdict
> in plain English: how urgent it is, how sure the model is, and why. One app, all four
> subsystems."

### 2 · Door: the full flow (0:15 – 0:55)

**Screen:**
1. On the **Door** tile, click **Upload CSV**, or open Door and **drag `Test.csv`** from Finder
   onto the dropzone. Dragging is better: the spec names drag-and-drop.
2. The result lands. Hold on the banner and the **verdict card**: *8 of 38 cycles show abnormal
   resistance · Inspect before next service · Confidence: High.*
3. Hover a red band in the **motor-current chart** so its cycle tooltip shows.
4. Scroll to **"Why cycle 19 was flagged"**. Hover the underlined **back-EMF** term so the
   glossary tooltip appears.
5. Scroll past the table (`door_predictions.csv · 38 rows`), click **⬇ Download CSV**, and show
   `door_predictions.csv` arrive in the downloads tray.

> "Door first. This file is one continuous recording, with dozens of doors opening and closing
> back to back and no markers between them. The app finds the cycles itself: 38 of them, and 8
> show abnormal resistance. That's a red 'inspect before next service', with high confidence.
> The chart shows exactly where they are, and for the worst one, cycle 19, it says why: 132 %
> more motor current than a healthy cycle, turning slower. Any technical term is underlined;
> hover it and you get a plain-language definition. Then one click downloads the result in the
> exact submission format."

### 3 · Rail Corrugation: honest verdicts and batch mode (0:55 – 1:40)

**Screen:**
1. Sidebar → **Rail Corrugation**. **Drag `Test33.csv`** onto the dropzone.
2. Hold on the verdict: *Side I corrugation detected · Inspect before next service · High.*
   Hover **"How reliable is this?"** for about 2 s.
3. Point at the **Recording speed** metric (46 km/h, "where most faults have been seen") and
   the side-asymmetry gauge.
4. Click **Reset**, switch to **Batch upload**, and **multi-select drag** `Test10`, `Test13`,
   `Test14` and `Test15` in one go. Let the triage table fill in: Normal / Side I / Side II /
   **Inconclusive**.
5. Click **View** on the Inconclusive row for a beat, then **⬇ Download all CSV**.

> "Rail corrugation: a one-second vibration recording from 64 axle boxes. This one is Side I
> corrugation. The app doesn't just give a label, it says how far to trust it. 'How reliable is
> this?' gives this model's real track record, including what it tends to miss. It also flags
> recording speed, because that changes how reliable a call is.
>
> Engineers rarely have just one file, so here's batch mode: four recordings at once, triaged
> into one table. Normal, Side I, Side II… and this one says Inconclusive. The train was
> standing still, and a stationary train can't produce a corrugation signature. We could have
> shown a green 'Normal' and technically been right. We'd rather not tell an engineer the track
> is healthy when the data can't show it. The whole batch downloads as one CSV."

### 4 · ACV: ranking, and saying when it's unsure (1:40 – 2:05)

**Screen:**
1. Sidebar → **ACV**, switch to **Batch upload**, and **drag both workbooks**
   (`acv_synthetic_test_case.xlsx` and `acv_test_case.xlsx`) in one go. Trim the parse wait in
   the edit. The table shows car 05 as *Inspect before next service* and car 01 as *Monitor*.
2. Click **View** on the synthetic case: *Car 05 most likely faulty · Inspect before next
   service · High.* Show the **ranked-cars bars** with 05 at the top, then the cabin-temperature
   chart with car 05 well above the dashed setpoint.
3. Click **View** on `acv_test_case.xlsx`: *Car 01 most likely faulty · Monitor · Confidence:
   Low.*

> "Air-con: which of eight cars is leaking refrigerant. A leaking unit can't pull its cabin down
> to the cooling setpoint. In this train, car 05 runs more than two degrees warm while the
> others hold, so it's ranked first with high confidence. The second train is a closer call:
> car 01 is only just ahead, and the app says *Low* confidence instead of hiding it. The
> engineer knows which car to check first, and how much to trust that call."

### 5 · SHM: a number with context (2:05 – 2:25)

**Screen:**
1. Sidebar → **SHM**. **Drag `test02.csv`**.
2. The verdict: *Damage 0.827631 of 1.0 · Inspect before next service*. Point at the "likely
   between 0.751 and 0.905" sentence.
3. Scroll the **stress chart** (amber rings on the biggest swings) and the **cumulative-damage
   curve** climbing through the shaded urgency bands.

> "Structural health: how much of a component's fatigue life is used up. This point is at
> 0.83, where 1.0 means life fully used, and the app gives the realistic range, 0.75 to 0.9,
> not a falsely precise number. The rings mark the handful of big stress swings that cause
> most of the damage, and the curve shows it building up into the 'inspect' zone."

### 6 · Wrong file, clear message (2:25 – 2:35)

**Screen:** Sidebar → **Door**. Click **Reset** if a result is showing, then **drag `test02.csv`**
(the SHM file) onto the Door dropzone. Hold on the red alert.

> "And if someone drops the wrong file? No crash and no confident-looking nonsense. It tells
> them exactly what's wrong."

### 7 · Built for a team, and under the hood (2:35 – 2:50)

**Screen:**
1. Click the **›** arrow next to Rail in the sidebar so the run history opens with this
   session's runs. Click a run name and rename it, e.g. "Depot line 3 – morning".
2. On a result, type a quick **note** ("Check car 01 at next depot visit") and post it.
3. Click **Under the hood**: a slow scroll past the four scores (1.000 / 1.000 / 0.888 / 0.974).

> "Every run is kept in a per-subsystem history you can rename and re-download, results can be
> saved, and the team can leave notes on a file. For anyone who wants the detail, 'Under the
> hood' explains each model and how it was validated."

### 8 · Close (2:50 – 2:58)

**Screen:** Back to **Get started**, or a title card with the team name and the score table.

> "Four subsystems, one app, and every answer comes with its urgency, its confidence and its
> reason. That's Gamora, from team gamora-x."

## If you're running long

Cut in this order until you're under 3:00:

1. Segment 7's notes and rename (keep a 3 s flash of the history panel).
2. ACV: drop the batch and show `acv_synthetic_test_case.xlsx` on its own. Keep the Low-confidence line as narration only.
3. Segment 6 (wrong file). It's valuable, but a judge can find it in the app.
4. Trim the rail batch to three files. Keep the Inconclusive one, since it's the best
   "usefulness of results" moment in the video.

**Never cut:** a visible drag-and-drop, a visible download landing, and at least a glimpse of
all four subsystems. These are the spec's literal requirements.

## Recording and editing

- **Record each segment as its own take** and join them in the edit. Retakes stay cheap, and
  you can cut load spinners out at the joins.
- **Record narration separately** (voice-over on the finished screen edit) unless someone is
  very comfortable talking and clicking at once. A USB mic or AirPods in a quiet room is enough.
  Normalise the audio.
- **Add captions and burn them in.** Judges often watch muted. At minimum, add a lower-third
  label per segment ("Door · segment + classify", "Rail · batch triage", …).
- **Zoom in during the edit** on the verdict card, the tooltips and the download tray. The text
  is small at full-screen 1080p.
- **Export** as H.264 MP4 at 1080p30, ideally under 100 MB. Name it `demo_video.mp4` at the repo
  root, which is where the README already points.

## Final checks

- [ ] Runtime ≤ 3:00 (check the exported file, not the timeline)
- [ ] Drag-and-drop visible, a download landing visible, and all four subsystems shown
- [ ] On-screen results match `predictions.zip` (Door 8/38 abnormal, Rail Test33 = Side I,
      ACV `acv_test_case.xlsx` = 01 first, SHM test02 = 0.827631). The synthetic ACV workbook
      isn't in the zip, so don't describe it as a submitted prediction. The zip was
      regenerated on 2026-09-19. The old one had the v1 ACV ranking (`04|01|…`), so if the
      app ever shows 04 first, someone has restored a stale zip.
- [ ] No terminal windows, stack traces, notifications, personal tabs or leftover test notes
      in frame
- [ ] Cloud Run redeployed from `main`, and the live URL shows the same UI as the video
- [ ] `demo_video.mp4` committed at the repo root and on `main`
