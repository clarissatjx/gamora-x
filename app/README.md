# The app (submission item 3)

Run from the **repository root** — the app imports the trained models from `../subsystems/`:

```bash
pip install -r requirements.txt
streamlit run app/app.py
```

No training and no raw data are needed; every model artifact is committed. The app opens on an
overview where any raw sensor file can be dropped — it detects the subsystem from the file's
contents — or a subsystem can be picked in the sidebar. Each page: upload → result banner → metrics
→ charts and evidence → results table → download of the exact submission CSV.

Files: `app.py` (shell and navigation), `theme.py` (design system), `inference/<subsystem>.py`
(pages; `acv.py` is the Streamlit-free ACV inference module the CLI also uses).
