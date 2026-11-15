# Toy model: compact circular Gaussian, 0.5 mas, 5 GHz

| File | Content |
|---|---|
| `gaussian_0.5mas_5GHz.fits` | the model as a FITS image |
| `gaussian_0.5mas_5GHz.txt` | the same model in `ehtim` text format (`eh.image.load_txt`) |

| Parameter | Value |
|---|---|
| Flux density | 1.0 Jy |
| FWHM | 0.5 mas (about half the beam of the EVN + AVN + SKA-Mid) |
| Position | RA 12 h, Dec +4° |
| Frequency | 5 GHz |
| Grid | 64 × 64 pixels of 156 µas (10 mas field of view) |

The notebook builds this model itself (Section 2, parameters `flux_jy`, `src_fwhm_mas`, `src_ra_h`, `src_dec_deg`, `npix_model`, `fov_model`); these files are the model of the reference run, for use in other software or as a check.
