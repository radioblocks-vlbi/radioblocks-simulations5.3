# binary-jet-highfreq

**Binary jet, mid frequency: EVN (no SKA) vs. EVN + AVN + SKA-Mid, 5 GHz**

| | |
|---|---|
| Array | **EVN (no SKA) and EVN + AVN + SKA-Mid** |
| Frequency | 5 GHz |
| Source | time-variable precessing double-sided jet (SS 433-like) |
| Error scenarios | A, B |
| Run time (one core) | ~1 h 30 min (notebook); days (script) |

## Contents

| Folder | Content |
|---|---|
| `notebook/` | `binary_jet_VLBI_ehtim_campaign.ipynb`, executed (outputs of the reference run included) |
| `toy-model/` | the source model and its parameters |
| `results/` | outputs of the reference run: `figures/` (PNG), `images/` (FITS), `tables/` (CSV, array files, README), `visibilities/` (UVFITS, txt) |
| `script/` | `binary_jet_VLBI_campaign_full.py`: the full 43-day campaign, every day imaged (runs for days; see the guide) |
| `docs/` | the user guide of this case (`index.md` + figures), published on the project's GitHub Pages site |

## Run it

```bash
pip install -r ../requirements.txt     # ehtim 1.2.10, numpy<2
cd notebook
jupyter lab

# full campaign (days):
python ../script/binary_jet_VLBI_campaign_full.py --scenarios A
```

A new run writes its outputs next to the notebook (`notebook/binary_jet_results/` and a zip file; the script writes `binary_jet_campaign_results/`), so the reference results in `results/` are not overwritten.

## Guide

[`docs/index.md`](docs/index.md), also on the documentation website under *Cases → binary-jet-highfreq*.
