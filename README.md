# RADIOBLOCKS VLBI simulations with `ehtim`

Jupyter notebooks (and one campaign script) that simulate, corrupt, calibrate and image VLBI observations with [`eht-imaging`](https://github.com/achael/eht-imaging) 1.2.10, under the RADIOBLOCKS error scenarios A (thermal noise), B (+ gains and random phases) and C (+ structured atmospheric corruptions: an ionospheric (dispersive) and a tropospheric (non-dispersive) phase screen).

**Contact:** questions, comments and collaboration requests are welcome at [radioblocks.vlbi@gmail.com](mailto:radioblocks.vlbi@gmail.com).

**Every array includes an SKA telescope:** **LBA + SKA-Low** at 250 MHz and **EVN + AVN + SKA-Mid** at 5 GHz. The only array without SKA, the **EVN alone (no SKA)**, is used as a comparison and always labelled that way.

📖 **User guide:** https://radioblocks-vlbi.github.io/radioblocks-vlbi-ehtim/

## Cases

| Case | Array | Frequency | Source | Scenarios |
|---|---|---|---|---|
| [`point-source-lowfreq/`](point-source-lowfreq/) | LBA + SKA-Low | 250 MHz | circular Gaussian, 80 mas | A, B, C |
| [`point-source-midfreq/`](point-source-midfreq/) | EVN + AVN + SKA-Mid | 5 GHz | circular Gaussian, 0.5 mas | A, B, C |
| [`jet-midfreq/`](jet-midfreq/) | EVN + AVN + SKA-Mid | 5 GHz | relativistic jet | A, B, C |
| [`jet-midfreq-class/`](jet-midfreq-class/) | EVN + AVN + SKA-Mid | 5 GHz | relativistic jet, hands-on class version | A, B, C |
| [`xray-binary-jet-midfreq/`](xray-binary-jet-midfreq/) | EVN (no SKA) vs. EVN + AVN + SKA-Mid | 5 GHz | X-ray binary: time-variable precessing jet (SS 433-like microquasar) | A, B |

Every case folder has the same layout:

```text
<case>/
├── README.md
├── notebook/        executed notebook (X-ray binary: also script/ with the campaign and toy-model scripts)
├── toy-model/       source model files and parameters
├── results/         reference run
│   ├── figures/       PNG
│   ├── images/        FITS (input model and every reconstruction)
│   ├── tables/        CSV metrics, chi^2 per round, array files, README
│   └── visibilities/  UVFITS (and txt) of every scenario and calibration
├── docs/            user guide of the case (index.md + figures)
└── mkdocs.yml       the case's part of the documentation site
```

Shared documentation (home page, installation, arrays, scenarios, imaging pipeline, references) is in the root `docs/` folder.

## Quick start

```bash
pip install -r requirements.txt          # ehtim 1.2.10 needs numpy<2
cd jet-midfreq/notebook                 # or any other case
jupyter lab
```

A new run writes its outputs next to the notebook; the reference results in `<case>/results/` are not overwritten.

## Documentation website (GitHub Pages)

The site is built with [MkDocs Material](https://squidfunk.github.io/mkdocs-material/). The root `mkdocs.yml` merges the root `docs/` with the `docs/` of every case through the [monorepo plugin](https://github.com/backstage/mkdocs-monorepo-plugin), and `.github/workflows/docs.yml` publishes it.

1. The site address uses the GitHub account `radioblocks-vlbi`; if the repository moves to another account, change it in `mkdocs.yml` and in this README.
2. Push to `main`.
3. In the repository, open **Settings → Pages** and set **Source: GitHub Actions**. Every push to `main` then rebuilds and publishes the site.

Local preview:

```bash
pip install -r requirements-docs.txt
mkdocs serve        # http://127.0.0.1:8000
```

To add a case: create `<new-case>/` with the same layout, a `mkdocs.yml` (`site_name: <new-case>`, `docs_dir: docs`, `nav: [Guide: index.md]`) and one line under *Cases* in the root `mkdocs.yml`:
`- <new-case>: '!include ./<new-case>/mkdocs.yml'`.

## Reproducibility

Scenario A is reproduced exactly. Scenarios B and C use `ehtim` gain/phase seeds derived from Python's string hashing, so their numbers change slightly between sessions; start Jupyter with `PYTHONHASHSEED=0` to fix them.

## License

This project is distributed under the [GNU General Public License v3.0](LICENSE).
