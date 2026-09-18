# The app (submission item 3)

Run from the **repository root** — the app imports the trained models from `../subsystems/`:

```bash
pip install -r requirements.txt
streamlit run app/app.py
```

No training and no raw data are needed; every model artifact is committed, and one held-out
sample file per subsystem is bundled in `samples/` behind a **Sample** button on each page and
each overview card. The app opens on an overview where any raw sensor file can be dropped — it
detects the subsystem from the file's contents — or a subsystem can be picked in the sidebar
(`?view=door|acv|rail|shm` deep-links to a page). Each page: upload → result banner → metrics
→ charts and evidence → results table → download of the exact submission CSV. Batch mode scores
several files and lets you pick which one the charts follow; the overview collects everything
scored in the session into a submission-shaped `predictions.zip`.

Files: `app.py` (shell, navigation, URL sync), `theme.py` (design system), `session.py` (samples,
session results, batch picker), `inference/<subsystem>.py` (pages; `acv.py` is the
Streamlit-free ACV inference module the CLI also uses).
