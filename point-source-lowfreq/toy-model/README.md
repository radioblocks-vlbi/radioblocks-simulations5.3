# Toy model: circular Gaussian, 80 mas, 250 MHz

| File | Content |
|---|---|
| `gaussian_80mas_250MHz.fits` | the model as a FITS image |
| `gaussian_80mas_250MHz.txt` | the same model in `ehtim` text format (`eh.image.load_txt`) |

| Parameter | Value |
|---|---|
| Flux density | 1.0 Jy |
| FWHM | 80 mas (about 1.5 times the nominal 50 mas resolution of the LBA + SKA-Low) |
| Position | RA 5 h, Dec −35° |
| Frequency | 250 MHz |
| Grid | 64 × 64 pixels of 10 mas (640 mas field of view) |

The notebook builds this model itself (Section 2, parameters `flux_jy`, `src_fwhm_mas`, `src_ra_h`, `src_dec_deg`); these files are the model of the reference run, for use in other software or as a check.
