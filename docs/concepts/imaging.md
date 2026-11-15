# Imaging pipeline and diagnostics

## RML imaging in rounds

All reconstructions use `ehtim`'s **regularized maximum likelihood** (RML) imager, `eh.imager.Imager`. It minimises

$$
J(I)=\sum_{d}\alpha_d\,\chi^2_d(I)\;+\;\sum_{r}\beta_r\,R_r(I),
$$

where the data terms χ²<sub>d</sub> compare the image with the data (`vis`, `amp`, `bs` bispectrum, `cphase` closure phases, `logcamp` log closure amplitudes) and the regularizers R<sub>r</sub> impose prior knowledge (`simple` relative entropy, `tv` total variation, `tv2`, `flux` total flux, `cm` centre of mass). Imaging runs in **rounds**: each round starts from the (blurred) result of the previous one and can change the data terms, the regularizers and the dataset.

## `pipeline_3rounds`: closures first, then self-calibration

The single pipeline used for A, B and C in the delivery notebooks:

1. **Round 1** fits only gain-invariant closure quantities (`cphase`, `logcamp`) on the raw data. Antenna-based gain and phase errors do not affect them.
2. The **raw** data are **self-calibrated** to the round-1 image (`self_cal`, one complex gain per station and scan); round 2 fits the bispectrum and the visibility amplitudes (`bs`, `amp`).
3. The raw data are self-calibrated again, to the round-2 image; round 3 refines with total variation.

The pipeline never uses the true model. For reference, the notebooks also run:

* **`pipeline_oracle`**: the same structure, self-calibrating to the **true** model (best case);
* **closures only**: three rounds on `cphase` and `logcamp` (no calibration at all);
* **`closure_rounds_handson`**: the closure-based recipe of the `ehtim` hands-on, on oracle-calibrated data;
* **raw visibilities** (`vis_rounds`): the uncalibrated complex visibilities, which fail by construction once there are gain and phase errors.

The extended jet sources need some adjustments (weaker entropy/TV weights, more iterations, a stronger flux constraint in the closure-only rounds, a phase-only first self-calibration). Each guide lists them with the reasons.

## Restoring beam

The data constrain nothing below the resolution of the array, so each final image is blurred once with the **fitted dirty beam** (`obs.fit_beam`, uniform weighting by default). The metrics compare the restored reconstruction with the true model restored with the same beam.

## Metrics

| Metric | Meaning | Better |
|---|---|---|
| `nrmse` | normalised RMS difference with the restored truth, after alignment | lower |
| `nxcorr` | normalised cross-correlation with the restored truth, after alignment | higher (1 = identical) |
| compact flux / true | flux within 1.5 beams of the peak, relative to the same quantity in the restored truth | 1 |
| peak / core offset | position of the peak relative to the flux centroid, compared with the truth (shift-invariant) | 0 |
| dynamic range | image peak over the off-source rms | higher |
| total flux | total flux of the reconstruction | the true value |

Closure-based imaging does not fix the absolute position of the source, so every metric is shift-invariant or computed after aligning the images.

## The reduced χ² at every iteration {#chi2-per-iteration}

Every notebook records, for **every reconstruction**, the reduced χ² of each active data term **at every iteration** of the optimiser, and plots it. This is done by a small subclass of the imager:

```python
class LoggedImager(eh.imager.Imager):
    # Records the reduced chi^2 of every active data term at each iteration (iteration 0 = initial image).
    def plotcur(self, imvec, **kwargs):
        if getattr(self, 'history', None) is not None:
            chi2 = self.make_chisq_dict(np.exp(imvec))      # the optimizer works on the log-image
            self.history.append({'round': self.round_id, 'iter': self._nit,
                                 **{k: float(v) for k, v in chi2.items()}})
        super().plotcur(imvec, **kwargs)
```

`ehtim` calls `plotcur()` once before the optimisation and after every L-BFGS-B iteration, whether or not `show_updates` is set, so overriding it captures the full history at no extra cost besides one χ² evaluation per iteration. The imaging functions accept a `history=` list and set `imgr.round_id` before each round.

**How to read the χ² figures**

* The x-axis counts iterations cumulatively over the rounds; **dashed vertical lines** mark the start of a new round, **dotted horizontal lines** mark χ² = 1 (a fit to within the thermal noise).
* A **jump** at the start of a round is expected: a new data term starts away from its optimum, the image is re-blurred, or the data were just re-self-calibrated.
* A curve that **settles near 1** means the data are explained to within the noise.
* A curve that **plateaus well above 1** means that no image, together with antenna-based calibration, can explain the data. This is the signature of non-antenna-based errors (the in-band decorrelation of scenario C) and of fitting corrupted raw visibilities.
* A curve **still falling steeply** at the end of a round means the round stopped before convergence: increase `maxit`.
* A curve **below 1** means the noise is being fitted (over-fitting), usually harmless at high SNR.

The final values are also exported as tables (`chi2_final_per_round*.csv`).

## Self-calibration to the final images: how well do the closures work? {#selfcal-test}

Every notebook ends its imaging with an added test. For each scenario (and, in the binary case, each array), the **raw** data are self-calibrated (amplitude and phase, one gain per station and scan or time stamp) to two models:

1. a **closures-only image** (`cphase` + `logcamp` only, no calibration at any stage), which tests what the closure quantities alone recover;
2. the **final image of the pipeline** (the last image generated).

Both are the unrestored images, moved sub-pixel to the true position first: closures do not constrain the absolute position, and a shifted model is a pure antenna-based phase gradient that self-calibration would copy into the data.

The calibrated visibilities are compared, visibility by visibility, with the **noise-free visibilities of the true source** on the same schedule:

$$
\chi^2_\mathrm{true}=\frac{1}{2N}\sum_k\frac{|V^\mathrm{cal}_k-V^\mathrm{true}_k|^2}{\sigma_k^2},
$$

plus the median amplitude error [%] and median phase error [deg] on the baselines with SNR > 5. The same numbers are computed for the raw data and for the **oracle** calibration (self-calibration to the true model; in scenario A, which has no gain errors, the data themselves).

* Self-calibration to the closures-only image ≈ oracle: **the closures alone captured the source** well enough to calibrate the data.
* Self-calibration to the pipeline image better than to the closures-only image: the later rounds (self-calibration, amplitudes, TV) added information that the closures missed.
* Oracle χ² above 1 (scenario C, or a time-variable source): the remaining error is not antenna-based, so no gain calibration can remove it. Compare with the oracle, not with 1.

Each calibrated dataset is finally **imaged once more from the prior with the complex visibilities**, and the χ² of every iteration is plotted, which closes the loop: closure image → self-calibrated visibilities → image.
