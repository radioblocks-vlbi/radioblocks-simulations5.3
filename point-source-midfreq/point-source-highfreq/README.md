# point-source-midfreq

**Point source, mid frequency: EVN + AVN + SKA-Mid, 5 GHz**

| | |
|---|---|
| Array | **EVN + AVN + SKA-Mid** |
| Frequency | 5 GHz |
| Source | compact circular Gaussian, 0.5 mas FWHM, 1 Jy |
| Error scenarios | A, B, C |
| Run time (one core) | ~30 min |

## Contents

| Folder | Content |
|---|---|
| `notebook/` | `VLBI_ehtim_EVN_AVN_SKAMid_5GHz_Gaussian_ABC.ipynb`, executed (outputs of the reference run included) |
| `toy-model/` | the source model and its parameters |
| `results/` | outputs of the reference run: `figures/` (PNG), `images/` (FITS), `tables/` (CSV, array files, README), `visibilities/` (UVFITS, txt) |
| `docs/` | the user guide of this case (`index.md` + figures), published on the project's GitHub Pages site |

## Run it

```bash
pip install -r ../requirements.txt     # ehtim 1.2.10, numpy<2
cd notebook
jupyter lab
```

A new run writes its outputs next to the notebook (`notebook/results_*/` and a zip file), so the reference results in `results/` are not overwritten.

## Guide

[`docs/index.md`](docs/index.md), also on the documentation website under *Cases → point-source-midfreq*.
