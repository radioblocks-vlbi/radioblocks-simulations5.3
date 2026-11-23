# RADIOBLOCKS VLBI simulations with `ehtim`

This site is the user guide of a set of Jupyter notebooks (and one long-running script) that **simulate, corrupt, calibrate and image VLBI observations** with [`eht-imaging`](https://github.com/achael/eht-imaging) (`ehtim` 1.2.10). The test cases share three error scenarios (A, B and C, the RADIOBLOCKS definitions), one imaging recipe and one report format, so their results can be compared directly.

**Contact:** questions, comments and collaboration requests are welcome at [radioblocks.vlbi@gmail.com](mailto:radioblocks.vlbi@gmail.com).

!!! important "Every array includes an SKA telescope"
    SKA is part of every array that is simulated and imaged in this project:

    * at **250 MHz** the array is the **LBA + SKA-Low**: six Long Baseline Array antennas **plus SKA-Low**;
    * at **5 GHz** the array is the **EVN + AVN + SKA-Mid**: the European VLBI Network, the African VLBI Network **and four SKA-Mid elements** (the phased-up SKA-Mid core `S5` and the dishes `S004`, `S008`, `S133`).

    The only array without SKA is the **EVN alone (no SKA)**, and it is always labelled that way. It appears in two places: the uv-coverage comparison of the 5 GHz notebooks, and the X-ray binary campaign, where it is the comparison array for the EVN + AVN + SKA-Mid. See [Arrays](concepts/arrays.md).

## The cases

The repository has **one folder per case**. Each folder holds the same five things:

```text
<case>/
├── notebook/      the executed notebook (and, for the X-ray binary, script/ with the campaign and toy-model scripts)
├── toy-model/     the source model and its parameters
├── results/       reference run: figures/ (PNG), images/ (FITS), tables/ (CSV), visibilities/ (UVFITS)
├── docs/          the user guide of the case (this site, under Cases)
└── mkdocs.yml     the case's part of this site
```

| Case | Array | Frequency | Source | Scenarios |
|---|---|---|---|---|
| [point-source-lowfreq](point-source-lowfreq/index.md) | **LBA + SKA-Low** | 250 MHz | circular Gaussian, 80 mas | A, B, C |
| [point-source-midfreq](point-source-midfreq/index.md) | **EVN + AVN + SKA-Mid** | 5 GHz | circular Gaussian, 0.5 mas | A, B, C |
| [jet-midfreq](jet-midfreq/index.md) | **EVN + AVN + SKA-Mid** | 5 GHz | relativistic jet | A, B, C |
| [jet-midfreq-class](jet-midfreq-class/index.md) | **EVN + AVN + SKA-Mid** | 5 GHz | relativistic jet (hands-on class) | A, B, C |
| [xray-binary-jet-midfreq](xray-binary-jet-midfreq/index.md) | **EVN (no SKA)** vs. **EVN + AVN + SKA-Mid** | 5 GHz | X-ray binary: time-variable precessing jet (SS 433-like microquasar) | A, B |

All cases except the class are **delivery** notebooks in report format. The class notebook covers the jet case as a guided hands-on session, with explanations and exercises.

## What every notebook contains

1. **Array and sensitivities**: station positions, SEFDs and observing set-up, with the SKA element named explicitly.
2. **Source model** and an error-free **reference observation**, with its uv-coverage.
3. **Scenarios A, B and C**: thermal noise; thermal noise + gains + random phases; thermal noise + gains + structured atmospheric corruptions (an ionospheric and a tropospheric phase screen).
4. **Self-calibration and closure checks.**
5. **Imaging** with a multi-round RML pipeline (closure quantities first, then iterative self-calibration), plus reference strategies.
6. **Results analysis**: image metrics, diagnostics, **the reduced χ² of every data term at every iteration for every reconstruction**, a comparison of imaging strategies and a discussion of the numbers.
7. **Self-calibration to the final images**: the raw data are self-calibrated to the closures-only image and to the final pipeline image, the calibrated visibilities are compared with the true ones, and imaged again ([how well do the closures work?](concepts/imaging.md#selfcal-test)).
8. **Export** of all UVFITS files, FITS images, figures and tables to one folder and one zip file.

## How to read the guides

Each guide follows **the same section order as its notebook**. For each section it explains what the code does, which parameters you can change and what they control, which outputs to expect, and how to read the figures. It ends with the results of the reference run (the run whose outputs are stored with the delivery) and with common problems.

Start with [Getting started](getting-started.md) to install the software and run a notebook. The [Concepts](concepts/scenarios.md) pages describe what the notebooks share: the arrays, the error scenarios and the imaging pipeline.
