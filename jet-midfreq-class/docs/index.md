# Hands-on class: 5 GHz jet with the EVN + AVN + SKA-Mid

**Case folder:** `jet-midfreq-class/` · **Notebook:** `notebook/VLBI_ehtim_handson_ERIS2026_jet_5GHz_class.ipynb` · **Toy model:** `toy-model/jet_model.txt` · **Reference results:** `results/` · **Run time:** ~35 min

!!! important "Array: EVN + AVN + SKA-Mid (20 stations), SKA-Mid included in every simulation"
    Every simulation, calibration and image of the class uses the **EVN + AVN + SKA-Mid**: 11 EVN stations, **4 SKA-Mid elements** (`S5`, the phased-up SKA-Mid core with an SEFD of 3.1 Jy, and the dishes `S004`, `S008`, `S133`) and 5 AVN stations. The **EVN alone (no SKA)** is used only once, as a comparison, in the uv-coverage plot of Section 2.3.

This is the **teaching version** of the [5 GHz jet case](../jet-midfreq/index.md) (ERIS 2026 VLBI training session). It walks through the same physics with more explanation, more intermediate plots and controls that participants are invited to change. Compared with the delivery notebook it:

* explains every concept as it appears (uv-coverage, resolved-out flux, closure quantities, dirty and clean beams, regularizers);
* uses a simpler imaging recipe (`bs` → `amp` + `cphase` → hybrid round on self-calibrated data) and self-calibrates to the true model for illustration;
* compares the regularizers `simple`, `tv` and `tv2`;
* adds a third pipeline that never uses the true model: two rounds on the raw data, then a round that combines the closures with visibilities self-calibrated to the round-2 image, and a test of how much weight those visibilities should get (Section 4.9);
* ends with a proposal-oriented summary and a "bring your own source" extra section.

**How to use it in class:** run the notebook once before the session, so that the slow cells (Sections 2–4) have their outputs. During the session participants change the controls of Section 3 and re-run from there.

---

## 0. Environment setup

Installs/imports `ehtim` 1.2.10 (NumPy < 2) and explains the two Fourier engines: the simulated datasets use the exact DFT (`ttype='direct'`), because the very high SNR of the EVN + AVN + SKA-Mid baselines (the SKA-Mid core `S5` has an SEFD of only 3.1 Jy) would turn the FFT interpolation error into a systematic error; self-calibration and imaging use `ttype='fast'`. Creates the output folder and `save_fig()`.

## 1. Array configuration: EVN (no SKA) vs. EVN + AVN + SKA-Mid

Defines the two arrays as text strings (`evn_str`, `ska_str`, `avn_str`) and writes:

* `data/evn_array.txt`: the **EVN alone (no SKA)**, 11 stations;
* `data/EVN_AVN_SKAMid_array.txt`: the **EVN + AVN + SKA-Mid**, 20 stations.

The cell prints the stations of each network (EVN, **SKA-Mid**, AVN). The SKA-Mid elements are in the Karoo (South Africa); the AVN stations are Hartebeesthoek, Kuntunse (Ghana), Namibia, Botswana and Malindi (Kenya).

!!! question "Exercise"
    Remove `S5` from `ska_str` and re-run the notebook. How do the thermal noise, the dynamic range and the χ² change?

## 2. Sky model: loading the jet, and the ideal observation

* **2.1** Loads `jet_model.txt` and plots it (`01_jet_model.png`).
* **2.2** Observing parameters (5 GHz, 256 MHz, 2-min scans every 10 min, 6-h track) and the ideal observation `obs_jet_ideal`. A note explains how many visibilities to expect (at most 190 baselines × 36 scans) and why `obs.add_all()` is not called (memory).
* **2.3** uv-coverage of the **EVN alone (no SKA)** and of the **EVN + AVN + SKA-Mid**, overlaid (`02_uv_coverage_EVN_noSKA_vs_EVN_AVN_SKAMid.png`). The African stations and SKA-Mid add the north–south baselines where the EVN alone has poor coverage. The markdown explains why uniform coverage matters as much as the longest baseline.

## 3. Realistic errors and visibility corruption

* **3.1** The error types and the **controls to experiment with**:

    | Control | Default | Reasonable range |
    |---|---|---|
    | `gain_offset_val` | 0.15 | 0.0–0.3 |
    | `gainp_val` | 0.10 | 0.0–0.2 |
    | `elevation_min` | 10° | 5–20° |

    Simulates scenario B (`obs_jet_err`) and scenario A (`obs_jet_thA`).
* **3.2** Self-calibration of B **to the true model** (`cal_jet`), to illustrate that self-calibration corrects station gains without removing source structure.
* **3.3** Visibility amplitude vs. uv-distance: ideal vs. A, ideal vs. B, ideal vs. self-calibrated B (`03_amplitude_vs_uvdistance_A_B_selfcal.png`).
* **3.4** Resolved-out flux: what short and long baselines see.
* **3.5** **Scenario C**: the structured atmospheric corruptions, an ionospheric dTEC and a tropospheric delay random-walk screen (`obs_jet_errC`), its self-calibration (`cal_jet_errC`), and a numerical check that closure phases are unchanged by an antenna-based screen (`04_scenarioC_screen_and_phases.png`). This is the simple, antenna-based version of scenario C; the delivery notebook adds the in-band and in-scan decorrelation.

## 4. RML imaging: closures vs. raw visibilities

* **4.0** What a closure quantity is, and why antenna-based errors cancel in it.
* **4.1** Helper functions: `align_to_model()`, `nrmse()`, `run_rml_imager()` and **`LoggedImager`** / **`plot_chi2_histories()`**, which record and plot the χ² of every data term at every iteration (see [Imaging](../concepts/imaging.md#chi2-per-iteration)).
* **4.2** The imaging pipeline, run 6 times (ideal, A, B and C with closures + hybrid self-cal; B and C with raw visibilities), **each run recording its χ² history** in `hist_class`:

    | Round | Data terms | Regularizers | Iterations |
    |---|---|---|---|
    | 1 | `bs` | `simple`, `flux`, `cm` | 150 |
    | 2 | `amp`, `cphase` | `tv`, `flux`, `cm` | 200 |
    | 3 (self-calibrated data) | `amp`, `cphase`, `logcamp` | `tv`, `flux`, `cm` | 200 |

    Raw-visibility runs: 2 rounds on `vis` (60 + 180 iterations).
* **4.3** Visual comparison and NRMSE of ideal, A, B and C (`05_reconstructions_ideal_A_B_C.png`).
* **4.4** Dirty beam, fitted clean beam and the B image with the beam drawn (`06_dirty_beam_clean_beam.png`).
* **4.5** Regularizers `simple`, `tv` and `tv2` on scenario B (`07_regularizers_simple_tv_tv2.png`), each run also recording its χ² history (`hist_reg`).
* **4.6** Final reduced χ² of each image against its data (`cphase`, `logcamp`, `amp`).
* **4.7** **Convergence of the data fit, iteration by iteration**: all nine reconstructions (six of 4.2 and three of 4.5) in one figure, `07b_chi2_convergence_all_reconstructions.png`, with a printout of the number of iterations and final χ² of each.

* **4.8** **Self-calibration to the final images: how well do the closures work?** Makes a **closures-only image** of A, B and C (`cphase` + `logcamp`, three rounds, no calibration), self-calibrates the **raw** data to it and to the **final image of the 4.2 pipeline**, and compares the calibrated visibilities with the noise-free visibilities of the true jet (reduced χ² against the truth, median amplitude and phase errors), next to the raw data and the oracle calibration. Each calibrated dataset is then imaged with the raw-visibility recipe. Figures: `07c_selfcal_to_final_images_visibility_errors.png`, `07d_images_closures_only_and_selfcalibrated_visibilities.png` and **`07e_chi2_convergence_closures_only_and_selfcalibrated_visibilities.png`** (χ² at every iteration of the closures-only and self-calibrated-visibility reconstructions). The calibrated visibilities are saved as UVFITS. See [Self-calibration test](../concepts/imaging.md#selfcal-test).

* **4.9** **A third pipeline: closures + self-calibrated visibilities.** The two pipelines of 4.2 (closures, raw visibilities) and the closures-only images of 4.8 are kept; 4.9 adds a pipeline built as with real data, which never uses the true jet and gives the self-calibrated visibilities a significant weight:

    | Round | Data | Data terms (weights) | Regularizers | Iterations |
    |---|---|---|---|---|
    | 1 | raw data | `bs` (100) | `simple` 10, `flux` 1, `cm` 50 | 60 |
    | 2 | raw data | `amp` (50) + `cphase` (100) | `tv` 1, `flux` 1, `cm` 50 | 80 |
    | — | self-calibration of the raw data (amplitude and phase, per station and scan) to the **round-2 image** | | | |
    | 3 | self-calibrated data | `vis` (50) + `cphase` (100) + `logcamp` (50) | `tv` 10, `flux` 1, `cm` 50 | 100 |

    It runs for Ideal, A, B and C with the **χ² recorded at every iteration**, and is compared with the closures pipeline (4.2), the closures-only images (4.8) and the raw-visibility pipeline (4.2). Its images also enter the metrics, bar charts and Pareto front of Section 5. Figures: `07f_pipelines_closures_rawvis_selfcalvis.png` and **`07g_chi2_convergence_selfcalvis_pipeline.png`**; table `pipeline_closures_selfcal_vis.csv`.

    **4.9.1** repeats only round 3, from the same round-2 image and the same self-calibrated data, with four sets of data terms: closures only (`cphase` + `logcamp`), the 4.9 pipeline (`vis` 50), visibility-heavy (`vis` 500) and visibilities only. Figures `07h_round3_visibility_weight_test.png` and `07i_chi2_convergence_visibility_weight_test.png`; table `round3_visibility_weight_test.csv`.

!!! question "Exercise"
    In the 4.7 figure, compare `vis` for the raw-visibility runs of B and C with the closure terms of the closure runs. Why can the first never reach χ² = 1? In 4.8, why does the oracle χ² of scenario C stay above that of B? In 4.9.1, why does the closure χ² grow when the visibilities get more weight, even though the `vis` χ² improves?

## 5. Analysis of results: global scientific quality

NRMSE, NXCORR, total flux, core flux and core offset, dynamic range and the χ² for every reconstruction of the three pipelines (closures, raw visibilities, closures + self-calibrated visibilities) and of the regularizer test, with three figures: metrics per scenario (`08_metrics_per_scenario.png`), a Pareto front of fidelity against data error (`09_pareto_fidelity_vs_error.png`), and closure-phase vs. visibility-phase errors (`10_closure_phase_vs_visibility_phase_errors.png`). It ends with a **discussion of the results** of the run.

## 6. From this notebook to a real observation proposal

What a Time Allocation Committee expects from a feasibility study (uv-coverage, sensitivity, imaging simulations, error budget) and how each section maps onto it, e.g. for a joint EVN + AVN + SKA-Mid session.

## 7. Export

`results_jet_5GHz_class/` and its zip: visibilities of every scenario (raw, oracle-calibrated, self-calibrated to the final images and to the round-2 images), FITS images, every figure, metric tables, `array_EVN_AVN_SKAMid.txt`, `array_EVN_alone_noSKA.txt` and a summary of the numbers to quote in a proposal.

## Extra: bring your own source

Converts a FITS image to an `ehtim` text model (`fits_to_ehtim_txt()`) and repeats the ideal → corrupted → self-cal → imaging chain on it with the **EVN + AVN + SKA-Mid**, reusing the functions above. Nothing earlier depends on it.

## Summary and references

What was done in each section, and the references (ehtim papers, EVN status table, Li et al. 2024 for the EVN, AVN and SKA-Mid positions and SEFDs).

---

## Results of the reference run

Reference run: one CPU core, **~35 min**. Array: **EVN + AVN + SKA-Mid** (20 stations). The class notebook draws the thermal noise and the station errors without fixed seeds, so every run gives different numbers: typically a few hundredths in NRMSE, up to ~0.07 between two runs ([why](../getting-started.md#reproducibility)).

**Data.** 6376 visibilities with the EVN + AVN + SKA-Mid, against 1860 with the **EVN alone (no SKA)** (×3.4); median SNR 182 in A. The shortest 10% of baselines see 90% of the jet flux, the longest 10% only 4% (resolved out). Fitted beam 1.96 × 0.87 mas, PA 91°.

<figure markdown>
![uv coverage](figures/02_uv_coverage_EVN_noSKA_vs_EVN_AVN_SKAMid.png)
<figcaption>uv-coverage of the EVN alone (no SKA), of the EVN + AVN + SKA-Mid, and both overlaid.</figcaption>
</figure>

| Reconstruction | NRMSE | NXCORR | flux [Jy] | dynamic range |
|---|---|---|---|---|
| Ideal (closures pipeline) | 0.36 | 0.93 | 1.01 | 628 |
| Scenario A (closures pipeline) | 0.43 | 0.91 | 1.01 | 538 |
| Scenario B (closures pipeline) | 0.34 | 0.94 | 1.00 | 639 |
| Scenario B (raw visibilities) | 1.59 | −0.02 | 0.03 | 19 |
| Scenario C (closures pipeline) | 0.37 | 0.93 | 1.00 | 541 |
| Scenario C (raw visibilities) | 0.94 | 0.52 | 0.10 | 18 |
| Ideal (closures + self-cal vis, 4.9) | 0.32 | 0.95 | 1.03 | 209 |
| Scenario A (closures + self-cal vis, 4.9) | 0.34 | 0.94 | 1.03 | 190 |
| Scenario B (closures + self-cal vis, 4.9) | 0.49 | 0.87 | 0.97 | 268 |
| Scenario C (closures + self-cal vis, 4.9) | 0.43 | 0.90 | 0.83 | 179 |
| Regularizer `simple` / `tv` / `tv2` (B) | 0.44 / 0.43 / 0.43 | 0.90 / 0.91 / 0.91 | 0.95 | 584 / 601 / 608 |

<figure markdown>
![reconstructions](figures/05_reconstructions_ideal_A_B_C.png)
<figcaption>Ideal, A, B and C: closures pipeline and raw-visibility reconstructions (Section 4.2).</figcaption>
</figure>

<figure markdown>
![chi2 every reconstruction](figures/07b_chi2_convergence_all_reconstructions.png)
<figcaption>Section 4.7: reduced χ² per iteration for all nine reconstructions. The closure-based runs are still improving at the end of round 3; the raw-visibility runs flatten at ~10⁶.</figcaption>
</figure>

**Section 4.8: how well do the closures work?**

| | Phase error | Amplitude error | χ² vs. true visibilities |
|---|---|---|---|
| raw data (B, C) | ~90° | 11–12% | ~3.0–3.5 × 10⁶ |
| self-cal to the closures-only image | **1.0–1.9°** | 14–15% | ~2.1–2.6 × 10⁴ |
| self-cal to the final 4.2 pipeline image | 1.4–3.3° | 6–9% | 4 × 10³ – 1 × 10⁴ |
| oracle (true jet) | 0.2° | 0.5% | ~9 |

<figure markdown>
![self-cal errors](figures/07c_selfcal_to_final_images_visibility_errors.png)
<figcaption>Raw data self-calibrated to the closures-only image and to the final pipeline image, compared with the true visibilities.</figcaption>
</figure>

<figure markdown>
![closures-only and self-calibrated images](figures/07d_images_closures_only_and_selfcalibrated_visibilities.png)
<figcaption>Rows: closures-only image; image of the visibilities self-calibrated to it; image of the visibilities self-calibrated to the final pipeline image. Columns: scenarios A, B, C.</figcaption>
</figure>

<figure markdown>
![chi2 closures-only and self-calibrated](figures/07e_chi2_convergence_closures_only_and_selfcalibrated_visibilities.png)
<figcaption>χ² per iteration of the closures-only imaging and of the imaging of the self-calibrated visibilities.</figcaption>
</figure>

**Section 4.9: the third pipeline, closures + self-calibrated visibilities.**

| Dataset | closures pipeline (4.2) | closures only (4.8) | raw visibilities (4.2) | closures + self-cal vis (4.9) | closure-phase χ², 4.2 → 4.9 |
|---|---|---|---|---|---|
| Ideal | 0.36 | — | — | 0.32 | 39 → 282 |
| A | 0.43 | 0.40 | — | 0.34 | 50 → 302 |
| B | 0.34 | 0.43 | 1.59 | **0.49** | 42 → 235 |
| C | 0.37 | 0.45 | 0.94 | **0.43** | 32 → 368 |

(NRMSE against the reference image, lower is better. The closure-phase χ² is computed on the raw data.)

<figure markdown>
![three pipelines](figures/07f_pipelines_closures_rawvis_selfcalvis.png)
<figcaption>Per dataset: the closures pipeline (4.2), the closures-only image (4.8), the raw-visibility pipeline (4.2) and the closures + self-calibrated visibilities pipeline (4.9).</figcaption>
</figure>

<figure markdown>
![chi2 third pipeline](figures/07g_chi2_convergence_selfcalvis_pipeline.png)
<figcaption>χ² per iteration of the 4.9 pipeline: rounds 1–2 on the raw data, round 3 on the data self-calibrated to the round-2 image.</figcaption>
</figure>

With gain errors (B and C) the 4.9 pipeline is clearly worse than the closures pipeline: higher NRMSE, core flux at 87% and 79% of the reference, only 0.83 Jy in C, and a third of the dynamic range. In every dataset its images fit the closure phases 6–11 times worse. The data were self-calibrated to the round-2 image (NRMSE 0.38–0.48), so they agree with that image, errors included, and the `vis` term rewards staying close to it. For Ideal and A, which have no gain errors to solve, its NRMSE is lower in this run, but its closure χ² is still 6–7 times higher.

**Section 4.9.1: how much weight for the self-calibrated visibilities?** Only round 3 is repeated, from the same round-2 image and the same self-calibrated data:

| Round-3 variant | closure-phase χ² (A / B / C) | `vis` χ² (A / B / C) | NRMSE (A / B / C) | flux [Jy] |
|---|---|---|---|---|
| closures only | **148 / 71 / 154** | 2.8 × 10⁵ / 2.8 × 10⁵ / 5.8 × 10⁵ | 0.37 / 0.52 / **0.34** | 1.37–1.48 |
| 4.9 pipeline (`vis` 50) | 302 / 235 / 368 | 1776 / 1316 / 2354 | 0.34 / 0.49 / 0.43 | 0.85–1.05 |
| visibility-heavy (`vis` 500) | 526 / 476 / 805 | 1288 / 930 / 1653 | 0.34 / 0.51 / 0.44 | 0.85–1.05 |
| visibilities only | 722 / 583 / 1026 | 1251 / 927 / 1614 | 0.34 / 0.52 / 0.44 | 0.84–1.04 |

<figure markdown>
![visibility weight test](figures/07h_round3_visibility_weight_test.png)
<figcaption>Round-2 image (the self-calibration model) and the four round-3 variants, for scenarios A, B and C.</figcaption>
</figure>

<figure markdown>
![chi2 visibility weight test](figures/07i_chi2_convergence_visibility_weight_test.png)
<figcaption>χ² per iteration of round 3 for each variant, scenarios B and C.</figcaption>
</figure>

The more weight the self-calibrated visibilities get, the worse the image fits the closures: the closure-phase χ² grows by a factor 5–8 from "closures only" to "visibilities only", while raising the `vis` weight from 50 to 500 or more improves the `vis` χ² by less than a factor 1.5. In C the closures-only round gives the best image (NRMSE 0.34 against 0.43–0.44). In A and B the NRMSE differences are small (≤ 0.04), and the closures-only round has its own weakness: with no amplitudes and a weak flux constraint (`flux` 1), its total flux drifts to 1.4–1.5 Jy.

**Take-home messages for the class.**

* Closure quantities make B and C as good as A; raw visibilities fail completely.
* The closures alone determine the **phases** very well (1–2° after self-calibration to the closures-only image); the **amplitudes** need calibrated-amplitude rounds.
* Self-calibrated visibilities are only as good as the model they were calibrated to (Sections 4.8 and 4.9): giving them much weight pulls the image towards that model and away from the closures. Keep their weight low until the model is good, and iterate self-calibration and imaging (phase first, amplitudes later).
* The χ² histories show when a run stopped too early, and the closure χ² on the raw data shows whether an image is consistent with the gain-invariant data: compare images only once their χ² has flattened.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `jet_model.txt` not found (point-source fallback used) | Run the notebook from `notebook/` (it reads `../toy-model/jet_model.txt`) or copy the model next to it (Colab: upload it). |
| A figure appears at the end of every imaging round | Make sure `run_rml_imager` is the notebook's version (it wraps `make_image_I` with `plt.ioff()`). |
| The class runs out of time | Run the notebook before the session; participants only re-run Sections 3–5 after changing the controls. |
| Numbers differ from those in the guide | Expected: the class notebook draws the thermal noise and the station errors without fixed seeds. |
