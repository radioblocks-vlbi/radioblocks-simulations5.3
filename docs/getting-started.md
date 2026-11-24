# Getting started

## Requirements

| Package | Version | Why |
|---|---|---|
| Python | 3.9–3.12 | `ehtim` 1.2.10 is tested on these versions |
| `ehtim` | **1.2.10** | Every function signature used in the notebooks was checked against this version |
| `numpy` | **< 2** | `ehtim` 1.2.10 uses the old NumPy C API |
| `scipy`, `matplotlib`, `pandas`, `astropy` | recent | analysis, figures and tables |
| `imageio` | recent | GIFs of the X-ray binary campaign script |
| `scikit-image` | optional | SSIM metric of the campaign script (the metric is skipped if it is missing) |
| `pynfft` | optional | `--ttype nfft` in the campaign script; the notebooks never need it |

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

!!! note "The `No NFFT installed!` warning"
    `ehtim` prints this warning on import when `pynfft` is missing. You can ignore it: the notebooks use `ttype='fast'` (FFT) for imaging and `ttype='direct'` (exact DFT) for the simulated data.

## Running a notebook

=== "Locally (Jupyter)"

    ```bash
    cd point-source-lowfreq/notebook      # or any other case
    jupyter lab
    ```
    Run the notebook from its case's `notebook/` folder, top to bottom (*Run → Run All Cells*). Each notebook writes a `data/` folder and a results folder next to it, plus a zip file. The reference results of each case are in its `results/` folder and are not overwritten.

=== "Google Colab"

    1. Upload the notebook (*File → Upload notebook*).
    2. For the two jet notebooks, upload `toy-model/jet_model.txt` of the case to the session files (the folder icon on the left). The notebooks stop with an error if the file is missing.
    3. Run the first cell. If it installs `ehtim`, NumPy is downgraded: **restart the session once** (*Runtime → Restart session*) and run everything again from the top.
    4. At the end, the results zip file is downloaded automatically.

=== "Command line (no browser)"

    ```bash
    pip install nbclient
    jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=7200 \
        point-source-lowfreq/notebook/VLBI_ehtim_LBA6_SKALow_250MHz_ABC.ipynb --output LBA_executed.ipynb
    ```

## Run times (one CPU core)

| Notebook | Time of the reference run |
|---|---|
| point-source-lowfreq | ~10 min |
| point-source-midfreq | ~30 min |
| jet-midfreq | ~50 min |
| jet-midfreq-class | ~35 min |
| xray-binary-jet-midfreq, notebook | ~1 h 30 min (~40 min with `RUN_SELFCAL_TEST = False`) |
| xray-binary-jet-midfreq, script | **days** (see the [guide](xray-binary-jet-midfreq/index.md#the-full-campaign-script)) |

Most of the time goes into self-calibration and RML imaging with the 20-station EVN + AVN + SKA-Mid array, including the added self-calibration test of every notebook.

## Reproducibility


```bash
PYTHONHASHSEED=0 jupyter lab
```

The **hands-on class notebook** (`jet-midfreq-class`) does not fix the seed of the thermal noise either, so all its scenarios, including A, change from run to run (NRMSE by a few hundredths, up to ~0.07). Participants who re-run it should compare trends, not exact numbers.

## Outputs

Every notebook ends with an **Export** section that collects everything in one folder (and zips it). The `results/` folder of each case holds the same structure for the reference run:

| Folder | Content |
|---|---|
| `visibilities/` (the X-ray binary notebook calls it `uvfits/` in its own export) | the reference observation and every scenario as `.uvfits` (AIPS, CASA, Difmap) and `.txt` |
| `figures/` | every figure of the notebook as `.png`, including the χ² convergence figures |
| `images/` | the input model and every reconstruction as `.fits` |
| `tables/` | metric tables, final χ² per round, regularizers and weights of every pipeline, SEFDs, scenario-C atmospheric screens (ionospheric + tropospheric), array files and a `README.txt` |
