# Rail Corrugation — Presentation Notes

Running reference for the presentation: the concepts, the decisions we made and why, the
headline numbers, and answers to questions judges are likely to ask.

Living document — updated as we go. `PLAN.md` is the detailed engineering record; this is
the version you can speak from.

---

## 1. Key concepts (how to explain it if asked)

**What rail corrugation is.** A regular wavy wear pattern on the top surface of the rail —
the "washboard" texture you feel on an unpaved road, but in steel. Waves are a few
centimetres to a few tens of centimetres apart and only a few tenths of a millimetre to a
few millimetres deep.

**Why it's periodic (the key mechanism).** The wheel-rail-track assembly is springy and has
natural frequencies. A wheel rolling over a small imperfection bounces at one of those
frequencies, lands harder a fixed distance later, and wears the rail slightly more there.
Every subsequent train reinforces the same pattern. Hence:

> **wave spacing = train speed ÷ vibration frequency**

**Why spacing (wavelength) is the right unit, not frequency.** The spacing belongs to the
*rail*; the frequency belongs to your *measurement* of it. Same defect at a different speed
gives a different frequency but the same spacing. So wavelength is what lets you (a) tell a
periodic defect from broadband noise, (b) compare measurements taken across different runs
and speeds, and (c) infer the root cause, since different wavelengths implicate different
resonances and suggest different fixes.

**Why one rail and not both.** On a curve the leading wheelset runs at a slight angle to the
rail — the *attack angle* — which scrubs one rail harder than the other. So corrugation
often develops on a single rail. That is why this is a 3-class problem (`Normal` / `Side I` /
`Side II`): the model must localise *which* rail, not just flag that something is wrong.

**Why it matters commercially.** Squealing and rumble draw noise complaints; the dynamic
wheel-rail forces accelerate fatigue in fasteners, ballast and vehicle running gear, and
raise derailment risk. The fix is grinding or milling — expensive, and it takes the line out
of service. Operators want to know *which sections* are degrading, early.

**Why axle-box sensors.** The axle box is the housing at each end of an axle that holds the
wheel bearing — the closest rigid point to the wheel-rail contact, so it feels the excitation
most directly. Hence our data: 8 cars x 8 axle-box positions = 64 sensors, each recording
vibration and shock. Odd positions are on one rail, even positions on the other, which is how
one recording judges both rails independently.

**Why macro F1 is the metric.** It averages the three per-class F1 scores equally, regardless
of how rare each class is. Plain accuracy would let a model that never detects a fault look
excellent — see Q1 below.

---

## 2. Data at a glance

| | |
|---|---|
| Training files | 272 (234 Normal / 14 Side I / 24 Side II) |
| Test files | 68 (labels held by organisers) |
| Each file | 1 second, 10 kHz, 129 columns |
| Columns | 1 speed-sensor pulse train + 64 positions x (vibration, shock) |
| Side I | axle-box positions 1, 3, 5, 7 |
| Side II | axle-box positions 2, 4, 6, 8 |

---

## 3. Key assumptions and decisions (every one of these is defensible)

**Speed is derived, not given.** Column 1 is a raw binary 0/1 toothed-wheel pulse train, not
a speed value. We count rising edges, divide by 90 teeth, and multiply by wheel
circumference (pi x 0.85 m).

**One tooth = one rising edge** — resolved by evidence, not assumed. Three independent
checks: the pulse duty cycle is 50.0–50.9% with rising edges exactly equalling falling edges
(equal-width teeth and gaps, so one rising edge per tooth); the Info Kit's "a tooth enters
and leaves … the output toggles" implies two transitions but one rising edge per tooth; and
the resulting fleet speeds (mean 37 km/h, max 70 km/h) match metro operation, whereas the
alternative implies an implausible 140 km/h maximum.

**38 stationary training files excluded from the model, handled by an explicit rule.** Their
speed sensor never toggles — the train is stopped — and all 38 are Normal. A stationary train
cannot generate wheel-rail excitation, so `speed == 0 ⇒ Normal` is a physical certainty, not
a guess. Excluding them costs zero minority-class data (none are Side I or Side II) and makes
our cross-validation measure the genuinely hard problem instead of being padded by ~14% free
wins. The rule lives inside the inference path, so every caller gets it.

**One duplicate file dropped.** `Train115` is byte-identical to `Train107` (MD5-verified over
all 340 files). A duplicate carries no new information and would double-weight one sample, and
would leak if the pair straddled a fold. A second duplicate pair was stationary and removed
automatically.

**Two degenerate features dropped.** Max-wavelength saturates at the 1 Hz FFT bin, so it
collapses to a restatement of speed on both sides — their difference is exactly 0 and ratio
exactly 1. Code now asserts no near-constant feature survives.

**Stratified 5-fold cross-validation, not a single holdout.** With only 14 Side I examples, a
single 80/20 split would validate on ~3 of them. Every fold is checked to contain at least 2
of each minority class.

**`class_weight="balanced"`** — measured three separate times; turning it off scores 0.795
vs 0.806.

**A ±0.03 noise floor was declared *before* running ablations**, measured over 30 seeds. Any
variant gaining less than that is treated as unproven. This is why we rejected five plausible
ideas instead of promoting one lucky result.

**Known caveats we state openly.** (a) `speed_mps` is quantised to ~0.0297 m/s steps, so
repeated identical speed values across files are a formula artifact, not duplicate
recordings. (b) The asymmetry features were designed by inspecting labels across the whole
training set — ordinary EDA, not test leakage, but it mildly optimism-biases cross-validation
relative to a fully blind pipeline.

---

## 4. Headline results

**Cross-validated macro F1: 0.806 ± 0.029** (5 repeats x 5-fold). An always-Normal model
scores 0.304.

| | F1 |
|---|---|
| Normal | 0.970 |
| Side II | 0.878 |
| **Side I** | **0.570** ← the bottleneck |

Accuracy is 0.936 versus macro F1 0.806 — that gap is exactly why the metric is macro F1.

Out-of-fold confusion matrix (rows = true):

| | Normal | Side I | Side II |
|---|---|---|---|
| **Normal** | 191 | 2 | 2 |
| **Side I** | 6 | 7 | 1 |
| **Side II** | 4 | 0 | 20 |

Test-set predictions: 59 Normal / 5 Side I / 4 Side II.

---

## 4b. How we validated it (the rubric grades this explicitly)

**The problem.** Scoring a model on data it trained on tells you nothing. But with only 14
Side I files, a single 80/20 split validates on ~3 of them — getting 2 right instead of 1
swings the Side I score by 33 points on pure luck of the draw.

**Cross-validation.** Cut the data into 5 folds; train on 4, validate on the 5th, rotate. Every
file is predicted exactly once by a model that never saw it, so the score covers all 233 files
instead of a lucky 47. **Stratified** = each fold holds a proportional share of each class, so
no fold has zero Side I files. Asserted in code: every fold has >= 2 of each minority class.

**Repeated.** We then repeat the whole 5-fold process 5 times with different fold assignments
and average — that is the `0.806 ± 0.029`. The ± is real run-to-run variation.

**The noise floor — the single most important methodological move.** Before running any
experiment we measured the score across 30 random seeds: mean 0.801, sd 0.030,
range [0.736, 0.845]. That gave a ±0.03 noise floor, declared *in advance*. Anything gaining
less than that is unproven.

It immediately paid off: a reviewer found that disabling class weighting gained +0.024 —
on a single seed. Re-measured over 15 seeds it actually *lost* 0.008, winning on only 6 of 15.
Without the pre-declared floor we would have shipped a worse model with a confident
explanation of why it was better. This is why we rejected five plausible ideas rather than
promoting a lucky one.

**The leakage hunt — four checks.**
1. *Exact duplicates*: MD5-hashed all 340 raw files, found two byte-identical pairs, removed
   them. A pair split across folds means validating on a memorised file.
2. *Near-duplicates*: files from the same track section seconds apart would be near-identical
   without being byte-identical. Nearest-neighbour distances in feature space are smoothly
   unimodal with no tight cluster — no hidden run-groups, so ungrouped splitting is sound.
   (A first pass using cosine similarity looked alarming at median 0.93, but that is an
   artifact of these features being non-negative magnitude statistics sharing a "loudness"
   direction. Standardised Euclidean is the trustworthy metric.)
3. *Per-file features*: every feature comes from one file alone; no statistic is computed
   across the corpus.
4. *Fresh model per fold*: nothing is fitted on data outside a fold's training portion.

**What we deliberately did not do.** We never touched the test set — no test file influenced
feature design, model selection, or any threshold.

---

## 5. Q&A — questions judges are likely to ask

**Q1. Why macro F1 rather than accuracy?**
86% of the data is Normal. A model that predicts Normal for every file scores ~84% accuracy
while detecting zero faults — and macro F1 of 0.304. Our model gets 0.936 accuracy but only
0.806 macro F1, and that gap is precisely the information accuracy hides. We tracked macro F1
throughout and never tuned on accuracy.

**Q2. Your Side I F1 is only 0.57 — why so low?**
Two compounding reasons. There are only 14 Side I examples in the entire training set. And
several are genuinely indistinguishable from Normal in the feature space: we identified the
specific missed files, and one of them sits at the 59th percentile of high-speed Normal files
on our strongest feature — it is mid-distribution, not marginal. We tested five separate
approaches to lift it and documented all five failing. We would rather report an honest 0.57
than claim a fix we could not measure.

**Q3. Isn't discarding 38 training files wasteful?**
They are recordings of a stationary train, all labelled Normal, and a stopped train physically
cannot produce a corrugation signature. We answer them with an explicit deterministic rule
instead. It costs zero Side I or Side II examples, and it makes our reported score measure the
hard problem rather than 14% free wins. The rule is applied to the 9 stationary test files too.

**Q4. How do you know your split isn't leaking?**
Four specific checks. We MD5-hashed all 340 raw files and found two byte-identical duplicate
pairs, which we removed. We checked for *near*-duplicates in feature space — nearest-neighbour
distances are smoothly unimodal with no tight cluster, so there are no hidden same-run groups
that would need grouped splitting. Features are computed strictly per file, with no statistic
computed across files. And every model is fit fresh inside each fold.

**Q5. How do you know 0.806 isn't a lucky random seed?**
We measured across 30 seeds before doing any model selection: mean 0.801, median 0.803,
sd 0.030, range [0.736, 0.845]. Our reported seed sits on the median. We then used that
sd as a pre-declared noise floor for judging every subsequent change.

**Q6. What score do you actually expect on the held-out test set?**
Roughly 0.73–0.85. With 14 Side I examples that spread is irreducible, and we would rather
give you the range than a single point estimate implying precision we do not have.

**Q7. Why gradient boosting? Did you try anything else?**
We tested RandomForest (0.738), LogisticRegression (0.714), SVC (0.675) and ExtraTrees (0.606)
under the identical protocol. HistGradientBoosting at 0.806 was clearly best. We also tested
averaging seven differently-seeded models, which gave exactly zero gain — the variance comes
from which files land in which fold, not from model-fit randomness.

**Q8. Corrugation is a wavelength phenomenon — did you use wavelength features?**
We tried, and they made the model worse. We added relative power in five wavelength bands
spanning 2–64 cm, chosen a priori from the Info Kit's stated physical range rather than tuned
on labels. In isolation the feature looked strong (Side I AUC 0.813 versus 0.69 for our
existing best). In the full model it cost 0.038 macro F1. Strong univariate separability did
not survive contact with the multivariate model, because it arrived as 120 correlated columns
against 233 rows. We reverted it and documented the result.

**Q9. 239 features for 233 training rows — isn't that overfitting?**
It was our concern too, so we tested it. Pruning to a compact feature set was *catastrophic*:
Side I F1 collapsed from 0.570 to 0.189. Adding features also hurt (Q8). The current set sits
near a local optimum for this dataset, and gradient boosting handles the width fine. The
binding constraint is the number of Side I examples, not the number of features.

**Q10. Did you touch the test set?**
Only to generate predictions at the end. No test file influenced feature design, model
selection, or any threshold. Every number we report is cross-validated on training data.

**Q11. Isn't the `speed == 0 ⇒ Normal` rule a hack?**
It is a physical constraint, not a heuristic fitted to data. Corrugation is detected through
wheel-rail excitation; with no wheel rotation there is no excitation and no signature to
detect. It holds for all 38 such training files without exception. We consider an explicit,
inspectable rule more defensible than hoping the model rediscovers it.

**Q12. What would you do with more time?**
Not more model tuning — we have evidence that is exhausted. The single highest-value thing
would be more Side I examples; the class is sample-starved, not method-starved. Failing that,
we would investigate whether raw waveform methods (envelope demodulation, or a learned
representation) can separate the specific files our summary statistics cannot, though the
sample size makes any such gain hard to prove.

**Q13. What is your model actually keying on? Can you explain a prediction?**
Yes — see section 4c. The strongest signal is the loudest single axle-box reading on each
rail, which is physically sensible: a corrugated rail hammers the wheels rolling over it, and
taking the maximum across the 8 cars stops a localised fault being averaged away. Our
inference function also returns the class probabilities, the derived speed, and a
plain-English explanation for every prediction, so an operator sees *why*, not just *what*.

**Q14. Why not deep learning — a CNN on the raw waveforms?**
Fourteen examples of the rarest class. A neural network on raw 10 kHz signals would have
millions of parameters and no way to constrain them; it would memorise those 14 files. Our
approach puts the domain knowledge in the features — which sensors are on which rail, how
speed relates to wavelength — so the model only has to learn a decision boundary over 239
meaningful numbers instead of discovering physics from scratch. With thousands of labelled
fault examples the trade-off would flip.

**Q15. Would this generalise to a different train, line, or wheel size?**
Honestly, unverified — everything we have comes from one fleet. Two things should transfer:
the features are mostly ratios and normalised quantities rather than absolute amplitudes, and
speed is derived rather than assumed. Two things would not: the wheel diameter (0.85 m) and
tooth count (90) are hard-coded constants that would need changing, and any different sensor
mounting or sampling rate would shift the feature distributions. We would want to re-validate
on the new fleet rather than assume it carries over.

**Q16. What if both rails are corrugated at once?**
Our model structurally cannot report that — the training labels only ever have one rail
faulty, so there is no such class to predict. In practice it would most likely return
whichever side is worse. If the operator needed that case, the right redesign is two
independent binary detectors rather than one 3-way classifier. We tested that architecture
for other reasons and it scored worse (0.762 vs 0.806), so we did not adopt it — but it is
the correct starting point if the requirement changed.

**Q17. How fast is it? Could it run onboard, in real time?**
About 0.25 seconds to process a 1-second recording end-to-end, single-threaded, on a laptop —
so roughly 4x faster than real time with no optimisation. The trained model is 723 KB. There
is no barrier to running it continuously onboard.

**Q18. What happens if a sensor fails?**
Currently we would take whatever it outputs at face value, and it would corrupt that side's
statistics — especially the `max` features, which are our most important ones and are by
definition sensitive to a single bad channel. That is a real deployment gap. The fix is a
channel sanity check (flat-line or out-of-range detection) that drops bad channels before
aggregation, which is straightforward but we have not built it.

**Q19. Why only 1 second of data? Isn't that very short?**
It is what the dataset provides. At 10 kHz, one second is 10,000 samples per channel and the
train covers roughly 10 metres at typical speed — enough to span many corrugation wavelengths
of a few centimetres, so the periodic signature is present. Longer windows would help mainly
by averaging out noise and by letting you localise *where* on the track the fault is.

**Q20. How would an operator actually use this?**
Run it continuously on in-service trains, tag each prediction with track position from the
train's positioning system, and accumulate a map of which sections are degrading. That turns
grinding from scheduled-by-calendar into targeted-by-condition. The cost asymmetry matters
here: a false positive sends an inspector to a healthy section and wastes a shift, whereas a
false negative leaves a degrading rail generating noise complaints and accelerating fatigue.
Missing faults is the more expensive error, which argues for tuning toward recall — and is
worth noting alongside our Side I recall of 0.50, which is where that cost lands hardest.

**Q21. Did you consider treating this as anomaly detection instead of classification?**
It is a reasonable framing given 86% of the data is Normal, and one-class methods trained
only on healthy data would sidestep the tiny fault sample. But it would only tell us *that*
something is wrong, not *which rail* — and localising the side is the actual requirement.
A hybrid (anomaly detection to flag, classification to localise) would be worth exploring
with more time.

---

## 4c. Explainability — what the model actually keys on

Measured by **permutation importance** (scramble one feature's values, see how far macro F1
falls), computed out-of-fold so it reflects generalisation rather than memorised structure.
Script: `explain_model.py`.

**Top features:**

| drop in macro F1 | feature |
|---|---|
| +0.182 | `Side_I_vib_rms_max` — loudest vibration on Side I |
| +0.108 | `Side_II_vib_rms_max` — loudest vibration on Side II |
| +0.061 | `Side_II_vib_rms_std` — how uneven Side II is across sensors |
| +0.040 | `asym_ratio_shock_ptp_mean` — Side I vs II shock peak ratio |

**Plain-English reading:** the model's single strongest signal is *the loudest individual
axle-box reading on each rail* — which is physically sensible. A corrugated rail hammers the
wheels that roll over it, and using the **max** across the 8 cars rather than the mean means a
fault on one part of the train isn't averaged away. Time-domain energy features dominate;
frequency-domain features contribute close to nothing.

### An honest correction we found by measuring this

We had assumed the Side I-vs-Side II **asymmetry** features were the heart of the model. The
importances said otherwise — they carry only 16% of total importance while making up 49% of
the features. So we tested it directly:

| variant | n_feat | macro F1 | F1 Side I |
|---|---|---|---|
| all features (shipped) | 239 | **0.806** | 0.570 |
| without asymmetry features | 121 | 0.784 | 0.543 |
| without single-side features | 119 | 0.597 | 0.189 |

**Removing the asymmetry features costs 0.022 — inside our own ±0.03 noise floor.** So their
contribution is directionally positive but *not proven* by the standard we set ourselves.
The single-side features are the genuinely load-bearing ones; removing those is catastrophic.

Two caveats that matter for how you present this. Permutation importance systematically
*under*-credits correlated features: the asymmetry features are computed *from* the
single-side features, so scrambling one leaves the other able to compensate. And the class
separation is still real and still worth showing — Normal ≈ 0, Side I +0.031, Side II −0.109.
It illustrates the physics beautifully; it just doesn't mean those features dominate the model.

**How to say it:** "Our strongest single signal is peak vibration energy per rail. We also
built explicit Side I vs Side II asymmetry features because that's the physical signature of
single-rail corrugation — they measure as mildly positive, but we hold them to the same
noise-floor standard we used to reject other ideas, and by that standard their benefit isn't
proven. We kept them because they're physically motivated and directionally positive, and we
say so rather than overclaiming."

That consistency — applying the same evidence bar to your own favourite idea as to everyone
else's — is a stronger position than claiming the feature is essential.

---

## 5b. How the model works (if asked to explain it)

**Three stages. The classifier is the least interesting one.**

*Stage 1 — raw signal to meaningful numbers.* Each file is 10,000 timesteps x 129 columns; a
single timestep is meaningless. For each of the 128 sensor channels we compute ten summary
statistics — six in the time domain (RMS energy, spread, peak-to-peak, skew, kurtosis,
zero-crossing rate) and four in the frequency domain (dominant frequency, its energy
concentration, spectral centroid, implied wavelength).

*Stage 2 — exploit the physical structure. This is where the domain knowledge lives.* We do
not treat the 64 positions as 64 unrelated columns. Positions 1/3/5/7 are one rail and
2/4/6/8 the other, so we pool each side's 32 channels by mean, max and standard deviation
(`max` matters — a fault on one car would be diluted by averaging across all eight). Then the
key step: we explicitly compute **Side I minus Side II** and **Side I divided by Side II** for
every statistic, because corrugation on one rail *is* an asymmetry between the sides. We hand
the model that comparison rather than hoping it infers it from 14 examples.

> **Don't overclaim this bit.** When we measured it (section 4c), the asymmetry features
> turned out to contribute +0.022 — inside our noise floor — while plain per-side vibration
> energy did the heavy lifting. Present the asymmetry features as a physically-motivated
> addition we measured honestly, not as the engine of the model.

*Stage 3 — classify, with a physical rule in front.* If the derived speed is zero, return
Normal without consulting the model. Otherwise the 239 features go to a gradient-boosted tree
ensemble which returns three class probabilities; we take the highest.

**What gradient boosting is, in one paragraph.** A decision tree is a flowchart of yes/no
questions ("is Side I's vibration energy more than 0.03 above Side II's?"). One tree is crude.
Gradient boosting builds many small trees in sequence, each trained on what the previous ones
got *wrong*, and sums their outputs — a committee where each member specialises in the
mistakes of everyone before them. It suits this problem because it needs no feature scaling,
discovers interactions automatically (e.g. that an asymmetry value means something different
at high speed), and is fast enough to run our full 25-fit validation in about a minute.

**Feature engineering did ~85% of the work.** Swapping in four entirely different model
families moved the score by a few points; changing the *features* moved it by 0.2.

---

## 5c. Known gaps and limitations (volunteer these before a judge finds them)

Ranked by how much they'd actually matter in deployment. Naming a limitation yourself reads
as competence; being caught by it doesn't.

### Gap 1 — Side I recall is 0.50. This is the headline weakness.
We miss half of Side I faults. Two compounding causes: only 14 training examples, and several
are genuinely indistinguishable from Normal in feature space (one sits at the 59th percentile
of high-speed Normal files on our strongest feature — mid-distribution, not marginal). We
tested five approaches to lift it and documented all five failing.
**Operational cost:** this is the *expensive* direction of error — a missed fault leaves a
degrading rail in service. Say so before they point it out.
**What would fix it:** more Side I examples. The class is sample-starved, not method-starved.

### Gap 2 — A stuck speed sensor on a moving train would be silently called Normal.
Our rule says `speed == 0 ⇒ Normal`. A *failed* speed sensor looks identical to a stopped
train, so a moving train with a dead sensor would be waved through as healthy — a false
negative caused by instrumentation, not by the rail.

**We quantified it and it is cleanly detectable.** Vibration energy separates the two states
almost perfectly:

| state | vibration energy |
|---|---|
| genuinely stationary (n=38) | 0.0698 – 0.0718 (spread of 0.002) |
| moving (n=234) | 0.0701 – 0.8330 |

The only 3 moving files inside the stationary band are crawling at 0.03–0.5 m/s — under
2 km/h, effectively stopped. A guard of *"speed is zero but vibration exceeds 0.0718"* would
raise **zero** false alarms on the 38 stationary training files while catching **231 of 234**
moving ones.

**We checked the live test set: all 9 stationary test files sit at 0.0699–0.0715, genuinely
quiet.** So no prediction in our submission is affected — but the gap is real for deployment,
and we can state exactly how we'd close it.

### Gap 3 — A failed vibration channel would corrupt our most important features.
Our single strongest feature is `Side_I_vib_rms_max` — the *loudest* reading across a side.
By construction, one flat-lined or railed-out channel dominates a max. We currently take
whatever a sensor reports at face value. The fix is a per-channel sanity check (flat-line,
out-of-range, stuck-value detection) before aggregation. Straightforward; not built.

### Gap 4 — The model structurally cannot report both rails faulty.
Training labels only ever have one rail faulty, so no such class exists to predict. In
practice it would return whichever side is worse. If that case mattered operationally, the
right redesign is two independent binary detectors — an architecture we tested for other
reasons, which scored worse (0.762 vs 0.806), so we didn't adopt it.

### Gap 5 — No severity grading, and no abstention.
We output a class, not "how bad is it" — but maintenance planning needs prioritisation, not
just detection. Relatedly, the model always commits to an answer; it has no "I'm not sure,
send a human" option, which is exactly what you'd want for a borderline Side I case given our
recall. Both are natural next features: `predict_rail_detailed` already returns class
probabilities, so an abstention threshold is a small step.

### Gap 6 — Generalisation beyond this fleet is unverified.
Wheel diameter (0.85 m) and tooth count (90) are hard-coded constants; a different train needs
them changed. Different sensor mounting or sampling rate would shift feature distributions.
In our favour: most features are ratios or normalised quantities rather than absolute
amplitudes, and speed is derived rather than assumed. We'd re-validate on a new fleet rather
than assume it transfers.

### Gap 7 — Missing context the dataset never gave us.
No track position, curvature, rail age, grinding history, or weather. Curvature especially
would likely be strongly predictive, since attack angle on curves is a primary cause. Track
position is also what turns this from a per-recording classifier into the thing an operator
actually wants: a map of which sections are degrading.

### Gap 8 — Two methodological caveats we disclose rather than hide.
(a) The asymmetry features were designed by inspecting labels across the whole training set —
ordinary EDA, not test leakage, but it mildly optimism-biases cross-validation versus a fully
blind pipeline. (b) The probability-boost sweep chose its value from the same curve it was
evaluated on; we reported it as within noise and didn't adopt it, so nothing rests on it.

---

## 5d. Explaining the basics out loud (rehearse these)

**"What is rail corrugation and why care?"**
> A regular ripple pattern that wears into the top surface of a rail — the washboard texture
> you get on an unpaved road, but in steel, waves a few centimetres to tens of centimetres
> apart and under a few millimetres deep. Operators care because it makes trains screech and
> rumble, generating noise complaints and a rough ride, and because the hammering fatigues
> both track and vehicle — and the only fix, grinding the rail smooth, is expensive and takes
> the line out of service.

**"Why are the ripples evenly spaced?"**
> Because the wheel wears the rail rhythmically, not continuously. The wheel-rail-track
> assembly is springy and has natural bounce frequencies. A wheel rolling over a tiny
> imperfection bounces, lands harder a fixed distance later, and wears that spot more —
> creating a new dip. Every train after repeats it in the same places. The spacing is fixed
> because it is just speed ÷ bounce frequency, both roughly constant for a stretch of track.

**"Why not just look at the vibration frequency?"**
> Frequency depends on the rail *and* on how fast you are going — the same damaged rail gives
> a different frequency at 10 m/s than at 18 m/s. What is fixed is the *spacing*, which
> belongs to the rail rather than to your trip over it. So we derive speed from the
> toothed-wheel pulse sensor first, which lets us convert frequency into wavelength.

**"Why does one recording judge two rails?"**
> There are sensors on both sides: 8 cars x 8 axle-box positions = 64 sensors, with odd
> positions on one rail and even on the other. A single one-second recording carries 32
> channels of evidence about each rail at once, which is what makes localising the faulty
> side possible rather than just flagging that something is wrong.

---

## 5e. The frequency-vs-energy tension (likely question from anyone who knows rail)

**Q. Corrugation is a wavelength phenomenon — so why doesn't your model use frequency
features?**

Measured feature importance by family:

| family | total importance |
|---|---|
| **time-domain (energy/amplitude)** | **0.553** |
| frequency-domain | **0.003** |

Frequency features contribute **under 1%**. Two families even score slightly negative.
`speed_mps` as a standalone feature scores 0.0000. The top three features are all RMS —
*how loud* the vibration is, not what frequency it sits at.

**The honest framing:** we detect the **symptom** (a corrugated rail hammers harder and more
unevenly on one side) rather than the **mechanism** (the characteristic wavelength).

> "We built both. The importance analysis shows the model is driven almost entirely by
> time-domain energy, with frequency features contributing under 1%. We also tested explicit
> wavelength-band features, chosen a priori from the Info Kit's stated physical range, and
> they *cost* us 0.038 macro F1. So we detect the consequence rather than the mechanism. With
> more fault examples the wavelength route would likely become viable, since it is the more
> physically-grounded signal — but on 14 Side I examples, amplitude is what generalises."

Strong because it shows you knew the theory, built the theory-driven version, measured it, and
let the measurement win.

---

## 6. One-line summary if you only get a sentence

We built a physically-grounded 3-class detector that scores **0.806 macro F1** in
cross-validation against **0.304** for a trivial baseline, with every design decision
measured rather than assumed — including five improvements we tested and rejected because
they did not clear a noise floor we declared in advance.
