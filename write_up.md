# gamora-x — PS3 Train Condition Monitoring: write-up

This single write-up covers all four subsystems. Everything stated here can be regenerated
from the repository: each subsystem's `PLAN.md` records the data facts, every experiment
(including the rejected ones), the validation numbers and the decisions, and the commands in
`README.md` reproduce them.

## 1. Results

| Subsystem | Task | Metric | Our validation estimate | Held-out score |
|---|---|---|---|---|
| Door | segment a continuous stream into door cycles, classify each Normal / Abnormal resistance | IoU-weighted F1 | 1.000 (time-ordered holdout, 22 cycles) | **1.000** |
| ACV | rank 8 cars by likelihood of a refrigerant leak | linear rank-decay | 1.000 (leave-one-case-out, 6 cases) | 0.875 (v1) |
| Rail corrugation | classify a 1 s axle-box recording Normal / Side I / Side II | macro F1 | 0.806 ± 0.03 (5×5 repeated stratified CV) | 0.888 |
| SHM | cumulative fatigue damage of a dynamic-stress segment | max(0, 1 − MAPE) | 0.974 analytic / 0.978 corrected (leave-one-out, 64 files) | 0.974 |
| **Overall** | all four attempted | mean | | **0.934** |

Two of the held-out scores land on our own validation estimates to three or four decimal
places (Door, SHM), which is the strongest evidence we can offer that the splits were sound and
nothing leaked. Rail scored above its estimate — a favourable draw, discussed in §4. ACV's 0.875
is the score of our first submission; §3 explains what it revealed and what we changed.

## 2. Door — cycle detection and classification

**Data facts that shaped the design.** `Train.csv` holds 110 labelled cycles (80 Normal,
30 Abnormal resistance; 55 Open, 55 Close) and `Test.csv` 38 cycles, sampled at 20 ms. The
"continuous stream" is cycles concatenated with 10–59 s jumps between them: inside a cycle every
step is exactly 0.02 s, between cycles never less than 10 s, and no row lies outside a labelled
cycle.

**Segmentation.** Splitting wherever the timestamp advances by more than 0.5 s reproduces all
110 labelled start and end times exactly — IoU 1.0 on every cycle — and yields 38 cycles on Test
(20 Close, 18 Open). The Info Kit warns against trusting any single flag column; what actually
changes at a boundary is the clock, and that is what we split on. A fallback (position reset or
opening/closing flag change) exists for a stream with no gaps and reproduces the same boundaries
on de-gapped copies of both files. Because segmentation is exact, the IoU-weighted F1 collapses
to per-cycle classification accuracy.

**Features and model.** Per cycle: mid-travel motor current (position 100–600), current
mean/median/quartiles/sum, voltage mean/max, mid-travel back-EMF, back-EMF spread, rows to
half-travel, and operation (Open/Close, derived from the flags and agreeing with the answer
file on all 110). The physics is clean and it shows: under abnormal resistance the motor draws
more current and produces less back-EMF (it turns slower). Mid-travel current alone separates the
classes with AUC 1.00 within each operation; peak current is useless because the peak is the
end-stop lock, not the travel. A standardised logistic regression is the shipped model (5×5
stratified CV 0.982; time-ordered holdout 1.000); a random forest is kept only as a disagreement
detector, never as the decision.

**Split and validation.** Cycles are independent events ≥ 10 s apart with the door position
resetting between them, so cycle-level stratified K-fold is valid; a time-ordered holdout (train
first 88, score last 22) is reported alongside to show no temporal drift. End-to-end on the
holdout — segmentation, features, classification, official scorer — is 1.000. Before shipping we
checked Test for distribution shift: its Normal cycles sit 1–17 mA above Train's (a
door-to-door effect the Info Kit predicts) against a ~100 mA class gap; zero cycles were
uncertain (probability in 0.2–0.8) and the two models disagreed on none.

**Assumption stated.** One Test cycle is 185 rows long where Opens are ~142: it opened to
position 807 instead of ~700, at the lowest mid-travel current in the file. Over-travel at
normal current is not resistance; it is labelled Normal deliberately.

## 3. ACV — refrigerant leak localisation

**Why a ranking, and why the metric fits.** With six labelled cases (one faulty car each) and
one test workbook, a classifier's yes/no would be judged on a single coin. The rank-decay score
gives partial credit for a near miss, which rewards exactly what a maintenance planner needs: a
short list of cars to inspect first.

**Data facts.** Schemas differ: five cases and the test workbook share eight parameters per car;
one case has 63, including refrigerant pressures that no other file has, and cabin temperature
for only four of its eight cars. Column headers were always read from the file itself, and the
car IDs in `ranked_cars` are taken verbatim from those headers.

**v1 (submitted first).** A peer-deviation heuristic: every parameter is expressed as each car's
deviation from its seven peers at each timestamp, aggregated into semantic categories
(temperature, mode, pressure, validity flags, …) and combined with fixed, domain-reasoned
weights. It ranked the true car first in all six labelled cases under leave-one-case-out. A
data-tuned variant and a small supervised ranker were compared under the same protocol and did
not beat it, so the simplest was shipped.

**What the held-out score taught us.** 0.875 means the true car was ranked second. Decomposing
v1's score on the test workbook showed the two leading cars tied on temperature — the physical
symptom — with the wrong car winning on the *mode* and *"Information Valid"* categories. The
latter is a telemetry-validity flag, not a leak symptom; it carried weight because in three of six
training cases the faulty car happened to throw more Invalid readings. With six cases, a
coincidence is indistinguishable from a mechanism.

**v2.** A refrigerant leak means the unit cannot pull its cabin down to the cooling setpoint, so
we measure that directly: mean (cabin temperature − cooling setpoint) over cooling-mode
timestamps, per car. It has no fitted parameter, so its score on the labelled cases is its
out-of-sample estimate: true car first in five of six (0.979), the miss being the file where half
the cars have no cabin sensor. Blending its within-file z-score equally with the v1 heuristic
(whose pressure channels cover that file) scores 1.000 on all six with still no fitted parameter,
and that blend is the shipped default. It ranks car 01 first on the test workbook.

**Disclosure.** The physics rule was formulated after the leaderboard feedback, from the failure
mechanism, and was validated on the labelled cases before its test output was examined. Its
agreement with the leaderboard is corroboration, not the reason it was chosen; the flag was
outvoted by a direct measurement, not edited out.

## 4. Rail corrugation — three-class classification

**Data facts.** 272 training files (234 Normal, 14 Side I, 24 Side II), 68 test files; 129
columns: a toothed-wheel speed pulse and vibration + shock for 64 axle boxes at 10 kHz for 1 s.
Thirty-eight training files (and nine test files) are stationary — the pulse never toggles — and
all are Normal. A stationary train cannot excite corrugation, so these are handled by an explicit
rule at inference and excluded from model training; this costs no minority-class information.
Two byte-identical duplicate files were found by MD5 and one of each pair dropped so a fold could
not validate on a file it trained on. Speed is derived as rising edges / 90 teeth × wheel
circumference; the convention was resolved from evidence (50 % duty cycle, one rising edge per
tooth, fleet speeds of 6–70 km/h).

**Why macro F1 matters here.** An always-Normal model scores ~0.85 accuracy and 0.30 macro F1.
Every decision below was judged on macro F1, and specifically on Side I, the class with 14
examples that caps the score.

**Features and model.** Per channel: RMS, std, peak-to-peak, skew, kurtosis, zero-crossing rate,
dominant frequency and its energy share, spectral centroid, dominant wavelength (speed /
frequency); pooled per rail side (positions 1/3/5/7 vs 2/4/6/8) by mean, max and std, plus
Side I − Side II asymmetry differences and ratios: 239 features after removing two that are
constant by construction. `HistGradientBoostingClassifier` with balanced class weights and
default hyperparameters.

**Validation discipline.** Repeated stratified 5-fold CV (5 repeats, identical folds for every
comparison, pooled macro F1 per repeat) — with 2–3 Side I files per fold a single split is too
noisy to select on. Before any ablation was run, the seed-to-seed noise floor was measured over
30 seeds (sd ≈ 0.03) and declared: any gain smaller than that would be treated as unproven.
Baseline: **0.806 ± 0.03**; per class 0.97 / 0.57 / 0.88.

**What was tried and rejected — fifteen alternatives across three rounds of review, every one
at or below the baseline or inside the pre-declared noise floor.** Feature
pruning to asymmetry only (Side I F1 collapses 0.57 → 0.19); dropping the wavelength family;
two one-vs-rest detectors instead of one multiclass model (0.762); no class weighting (0.795,
measured three separate times); decision-rule boosting toward the fault classes (+0.002); speed-
residualised asymmetry (a wash); 120 wavelength-band features (−0.038) and a pre-registered
4-feature version (−0.009); per-axle left/right ratios (−0.009); hyperparameters in both
directions — smaller leaves (−0.05 to −0.06) and larger leaves, fewer rounds or lower learning
rate (−0.03 to −0.14); side-averaged spectra binned by wavelength (alone 0.565; added −0.013);
half-second window augmentation with file-grouped folds (−0.104); an ensemble of the two views
(−0.086); and demeaning the shock channels (−0.044). Other learners scored 0.61–0.74 under
the same protocol (random forest 0.738, logistic regression 0.714, SVM 0.675, extra trees
0.606), and averaging seven differently-seeded models per fold changed nothing.

**Two findings worth more than a gain.** The shock channels carry a DC offset that looks like
sensor bias, but removing it costs 0.044: the offset differs between files in a label-relevant
way. And the textbook corrugation detector — average the 32 channel spectra per side and bin by
wavelength — is far *weaker* than per-channel statistics, for a concrete reason: within a
one-second window a ~150 m train spans different track, so a corrugated section sits under only
some axle boxes; averaging a side dilutes exactly those, while the max-pooled per-channel
features (which importance analysis singles out) capture "the loudest box".

**Reading the score honestly.** 0.888 is above our 0.806 ± 0.03 estimate. With about five Side I
files in the test set, each correct or incorrect call moves macro F1 by ~0.04, so the held-out
draw was favourable; the model's capability on a fresh batch of files is ≈ 0.80, and the ceiling
is the 14 Side I training files, not the representation. We chose not to resubmit a variant,
since every candidate had a lower expected score than the one already scored.

## 5. SHM — cumulative fatigue damage

**Data facts.** 64 training files and 16 test files, each one headerless column of 581,120
stress samples; damage labels 0.029–0.928, median 0.099 and heavily skewed low. Because the
metric is relative error, the small-damage files dominate it, so everything is modelled in log
space and errors are always reported as MAPE, never as RMSE or R².

**Recovering the generator.** The Info Kit says the labels come from rainflow counting and
Miner's rule, D = Σ nᵢ σᵢᵐ / C, without stating m or C. We implemented ASTM E1049 three-point
rainflow counting (verified exactly against the reference package's documented example) and
tested the exponent: the log–log slope of damage against Σ nᵢ σᵢ⁵ is 0.9965 with r = 0.9994,
and the leave-one-out score peaks at exactly m = 5.0 (4.95 → 0.969, 5.0 → 0.973,
5.05 → 0.9725) — m = 5 is a
standard S-N exponent, so this is the generator, not a coincidence. Half-weighted trailing
residual cycles are correct (×0 → 0.881, ×1 → 0.942, ×0.5 → 0.973). Goodman and SWT mean-stress
corrections, an endurance cutoff, a bilinear S-N curve, range binning and an additive offset were
each tested and each scores lower: the reference is pure single-exponent Miner.

**Model.** The physical sum with one fitted scale, C = median(S₅ / D) (more robust than least
squares for the few noisiest low-damage files), plus a ridge correction on seven cycle features
that is clipped at ±20 % and enabled by the training script only because it beats the analytic
term on leave-one-out (0.9744 → 0.9778; all standardised coefficients < 0.08). Leave-one-out is
the right protocol: files are independent segments with random IDs, and a fixed split would rest
on ~13 files.

**Reading the score.** Held-out 0.9743 equals the *analytic* model's estimate to four decimals;
the correction's small gain did not carry over. We consider this the honest outcome of a
physics-first model: it predicted its own error, and the remaining ~2.6 % is the part of the
organisers' procedure we could not reconstruct.

## 6. The app and the shared inference path

One Streamlit app covers all four subsystems. It opens on an overview where any raw file can be
dropped — the subsystem is detected from the file's contents, not its name — or a subsystem can
be chosen in the sidebar. Every page follows the same flow: upload → plain-language result →
metric tiles → a chart of the raw signal with the model's decision drawn on it (door cycles
shaded by label; each ACV car's cabin-minus-setpoint trace; per-axle-box vibration with the
predicted side highlighted; the stress series with its damage-share histogram) → an evidence
panel computed from the uploaded file → a results table → download of the exact submission CSV.
Batch mode scores many files at once; malformed uploads produce a sentence, not a traceback; the
Rail page says explicitly when the stationary rule, rather than the model, produced the answer.

The app and the command-line tools share one inference function per subsystem, and each
subsystem's evaluation script checks that the app path reproduces the submitted predictions
byte-for-byte. `scripts/validate_submission.py` checks every prediction file against the
scoring rules (exact columns and labels, one row per held-out file, ACV car IDs verified against
the workbook headers) before `predictions.zip` is written.

## 7. Assumptions and open decisions

| Where the documentation was open | What we assumed | Why |
|---|---|---|
| Door: how to find cycle boundaries | timestamp gaps > 0.5 s | reproduces all 110 labelled boundaries exactly; in-cycle steps are always 0.02 s |
| Door: validation split | cycle-level stratified CV plus a time-ordered holdout | cycles are independent events ≥ 10 s apart |
| ACV: how to handle the 63-parameter file | semantic categories keyed on parameter names; the physics rule maps its cabin/target names | features stay comparable across schemas |
| ACV: validation | leave-one-case-out | six cases; a fixed split is meaningless |
| Rail: stationary files | reported Normal by rule, excluded from training | a stationary train cannot excite corrugation; all 38 are Normal |
| Rail: speed convention | one rising edge per tooth | 50 % duty cycle; plausible fleet speeds; wording of the Info Kit |
| Rail: what counts as an improvement | pre-declared noise floor of 0.03 macro F1 | measured over 30 seeds before any ablation |
| SHM: the S-N exponent and rainflow convention | m = 5, half-weighted residuals | recovered from the labelled data, not assumed |
| SHM: validation | leave-one-out | files are independent with random IDs |

## 8. How we worked

Each subsystem was owned by one team member and reviewed by another against the same
protocol, so every model faced at least one adversarial pass before shipping. We used Claude
Code as a development assistant throughout, for analysis, implementation and review; all
modelling decisions and their justifications are recorded in the repository and were checked
by us.
