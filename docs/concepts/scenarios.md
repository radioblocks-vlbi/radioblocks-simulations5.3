# Error scenarios A, B and C

All notebooks use the RADIOBLOCKS scenario definitions (the same as the `ehtim` ionospheric-corruption hands-on). Each one is compared with an error-free **reference observation**, which is not itself a scenario.

| Scenario | Errors | `observe()` settings |
|---|---|---|
| Reference | none | `add_th_noise=False`, `ampcal=True`, `phasecal=True` |
| **A** | thermal noise only | `add_th_noise=True`, `ampcal=True`, `phasecal=True` |
| **B** | thermal noise + gain errors + generic (`ehtim` random) phase errors | `add_th_noise=True`, `ampcal=False` with `gain_offset=0.15`, `gainp=0.10`, `phasecal=False` |
| **C** | thermal noise + gain errors + structured atmospheric phase errors: ionospheric (dTEC) and tropospheric (delay) | same noise and gains as B, `phasecal=True`, plus a physical phase screen |

The gain-error budget (`gain_offset = 0.15`, a constant 15% offset per station; `gainp = 0.10`, a 10% gain fluctuation) is the same in every notebook, so the scenarios are directly comparable across arrays and frequencies.

## Scenario A: thermal noise

Stations are perfectly calibrated. The only corruption is receiver noise, whose level follows from the SEFDs of the two stations of each baseline, the bandwidth and the integration time. Scenario A measures what the **array** can do: its uv-coverage, resolution and sensitivity.

## Scenario B: gains and random phases

`ehtim` multiplies each visibility by complex station gains: amplitude errors of the size set by `gain_offset` and `gainp`, and, with `phasecal=False`, an independent random phase per station and time stamp. These errors are **antenna-based**: they cancel exactly in closure phases and closure amplitudes, and self-calibration can solve for them.

## Scenario C: a physical atmospheric screen (ionosphere + troposphere) {#scenario-c}

Scenario C keeps the noise and gains of B but replaces the random phases (`phasecal=True`) by an **atmospheric** phase screen with a physical frequency and time dependence. It has two terms: a dispersive one from the **ionosphere** and a non-dispersive one from the **troposphere** (which also absorbs residual clock errors). For station *i*:

$$
\phi_i(t,\nu)=\frac{K\,\mathrm{dTEC}_i(t)}{\nu}+2\pi\nu\,\tau_i(t),\qquad K=8.448\times10^{9}\ \mathrm{rad\,Hz\,TECU^{-1}} .
$$

* **dTEC** (dispersive, ionospheric term): a static per-station offset (`dtec0_sigma` = 0.3 TECU) plus a random walk (`dtec_rate` = 0.02 TECU/√min).
* **Delay** τ (non-dispersive, tropospheric term; it also absorbs clock errors): a static offset (`tau0_sigma_ns` = 0.5 ns) plus a random walk (`tau_rate_ns` = 0.01 ns/√min).

Each visibility is multiplied by

$$
\Gamma_{ij}=\big\langle e^{\,i(\phi_i-\phi_j)}\big\rangle_{\nu,\,t},
$$

averaged over `n_chan` = 32 channels across the band and over sub-integrations of the 2-min scan. The thermal noise is added **after** the screen, so the decorrelation lowers the signal but not the noise.

!!! warning "Why scenario C is harder"
    The average of the phase over the band and the scan is **not antenna-based**: |Γ<sub>ij</sub>| < 1 depends on the *difference* between the two stations' phase slopes. Self-calibration (which solves one gain per station and scan) and closure quantities can only remove the antenna-based part. What remains limits the fit: the reduced χ² of the data cannot reach 1.

**The same screen parameters are used at both frequencies**, so the comparison isolates the effect of the frequency:

| | 250 MHz (LBA + SKA-Low) | 5 GHz (EVN + AVN + SKA-Mid) |
|---|---|---|
| Phase of 1 TECU | 33.8 rad | 1.7 rad |
| Dominant in-band decorrelation | **ionosphere** (dTEC) | **troposphere** (delay) |
| What would fix it in practice | dispersive fringe fit / ionospheric calibration | standard fringe fit (delay and rate) |

The 5 GHz notebooks therefore also image scenario C after an **idealised fringe fit** (`obs_Cff`): the scan-average delay and dTEC, and their linear drift within the scan, are removed per baseline before the averaging. It is an extra reference, not a fourth scenario.

## Scenario C in the binary-jet case

The time-variable binary-jet case uses **A and B only**. Every visibility already comes from a different frame of the evolving source, and a physical screen would have to be continuous over the 43 days of the campaign and averaged over channels and sub-integrations for ~15,000 visibilities per day and array, multiplying a run time that is already measured in days. It would also mix two effects (source variability and structured phase errors) that the study is designed to separate. The static 5 GHz notebooks show what scenario C does at this frequency.

## Reproducibility note

The screen and the thermal noise use fixed seeds, but `ehtim` draws the station gains and phases of B and C from seeds derived from Python's string hashing, which changes between sessions. Use `PYTHONHASHSEED=0` to reproduce B and C exactly (see [Getting started](../getting-started.md#reproducibility)).
