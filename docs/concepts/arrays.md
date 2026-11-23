# Arrays: SKA is always included

!!! important "Naming used everywhere in the notebooks, figures, tables and guides"
    | Name | Stations | SKA element | Used in |
    |---|---|---|---|
    | **LBA + SKA-Low** | 6 LBA antennas + SKA-Low (7) | **SKA-Low** (tied array) | every simulation of the 250 MHz notebook |
    | **EVN + AVN + SKA-Mid** | 11 EVN + **4 SKA-Mid** + 5 AVN (20) | **SKA-Mid** (`S5`, `S004`, `S008`, `S133`) | every simulation of the 5 GHz Gaussian, jet and class notebooks |
    | **EVN + AVN + SKA-Mid** (X-ray binary case) | 10 EVN + **4 SKA-Mid** + 5 AVN (19) | **SKA-Mid** (`S5`, `S004`, `S008`, `S133`) | the X-ray binary notebook and scripts |
    | **EVN alone (no SKA)** | 11 EVN (10 in the X-ray binary case) | none | only the uv-coverage comparison at 5 GHz, and the comparison array of the X-ray binary case |

    In the campaign script's CSV files and folder names the two X-ray binary arrays keep the short tags `EVN` and `EVN+AVN` / `EVN_AVN`, so that runs started with earlier versions can be resumed. **`EVN+AVN` always includes SKA-Mid.**

## LBA + SKA-Low (250 MHz) {#lba-skalow}

Six Australian Long Baseline Array antennas and SKA-Low at the Murchison Radio-astronomy Observatory:

| Code | Station | SEFD used at 250 MHz |
|---|---|---|
| `PKS` | Parkes 64 m | 2000 Jy |
| `ATCA` | Australia Telescope Compact Array (tied) | 2000 Jy |
| `HOB` | Hobart 26 m | 2000 Jy |
| `CED` | Ceduna 30 m | 2000 Jy |
| `WARK` | Warkworth 30 m (New Zealand) | 2000 Jy |
| `KAT` | Katherine 12 m | 2000 Jy |
| **`SKAL`** | **SKA-Low**, 512 stations of 256 dipoles phased as one VLBI station | **4.4 Jy** (computed) |

* The LBA has **no receivers at 250 MHz** (its lowest band is ~700 MHz at Parkes and 1.3–1.4 GHz elsewhere), so this is a **hypothetical low-frequency configuration**: positions and apertures are real, sensitivities are assumptions.
* The LBA SEFDs are **fixed at ~2000 Jy**, deliberately more conservative than an extrapolation of the 1.3 GHz values with the sky temperature (the notebook prints that extrapolation for reference).
* The SKA-Low SEFD follows from SEFD = 2 k<sub>B</sub> T<sub>sys</sub> / A<sub>eff</sub>, with A<sub>eff</sub> ≈ 256 λ²/3 per station (123 m² at 250 MHz), T<sub>sys</sub> ≈ 100 K (sky + receiver), and `ska_n_tied` = 512 stations phased together: ~2260 Jy per station and **4.4 Jy** for the tied array. Change `ska_n_tied` to model a sub-array.

Every baseline to SKA-Low is therefore far more sensitive than the LBA–LBA baselines, which are the noisiest of the array.

## EVN + AVN + SKA-Mid (5 GHz)

| Network | Code | Station | SEFD [Jy] |
|---|---|---|---|
| EVN | `EF` | Effelsberg 100 m | 25 |
| EVN | `IR` | Irbene 32 m | 480 |
| EVN | `JB` | Jodrell Bank | 300 |
| EVN | `MC` | Medicina 32 m | 840 |
| EVN | `NT` | Noto 32 m | 1100 |
| EVN | `ON` | Onsala | 850 |
| EVN | `SR` | Sardinia 64 m | 50 |
| EVN | `T6` | Tianma 65 m | 26 |
| EVN | `TR` | Toruń 32 m | 650 |
| EVN | `WB` | Westerbork (single dish) | 1600 |
| EVN | `YS` | Yebes 40 m | 160 |
| **SKA-Mid** | **`S5`** | **SKA-Mid phased up as a single VLBI station** | **3.1** (assumed) |
| **SKA-Mid** | **`S004`** | SKA-Mid dish | 330 (assumed) |
| **SKA-Mid** | **`S008`** | SKA-Mid dish | 330 (assumed) |
| **SKA-Mid** | **`S133`** | SKA-Mid dish | 330 (assumed) |
| AVN | `HH` | Hartebeesthoek 26 m (South Africa) | 650 (700 in the X-ray binary case) |
| AVN | `KU` | Kuntunse (Ghana) | 330 (assumed) |
| AVN | `NA` | Namibia | 330 (assumed) |
| AVN | `BW` | Botswana | 330 (assumed) |
| AVN | `ML` | Malindi (Kenya) | 330 (assumed) |

* EVN values are typical published C-band SEFDs (EVN status table; Li et al. 2024, Table A1).
* **SKA-Mid and the AVN dishes are not yet VLBI-capable**: their SEFDs are assumptions for a future network. The thermal-noise level, and therefore every number in the notebooks, depends on them.
* The phased SKA-Mid core `S5` dominates the sensitivity of every baseline it is part of (baselines `S5`–`EF` or `S5`–`T6` have SNRs of thousands), while baselines between two small dishes are the noisiest.
* The north–south baselines between Europe and southern Africa fill the region of the uv-plane where the **EVN alone (no SKA)** has poor coverage. The 5 GHz notebooks show the two coverages side by side.

In the X-ray binary case the EVN has 10 stations (no Tianma) and the African part is the same (4 SKA-Mid + 5 AVN), 19 stations in total. The notebook and the script compare the **EVN (no SKA)** with the **EVN + AVN + SKA-Mid**; the differences between them are the combined effect of the AVN **and** SKA-Mid.

## Array file format

All arrays are written to plain-text files that `eh.array.load_txt()` reads:

```text
# Site X Y Z SEFD
EF 4033947.3 486990.8 4900431.0 25.0
S5 5109303.0031 2065863.3087 -3230973.0000 3.1
...
```

X, Y, Z are geocentric ITRF coordinates in metres; SEFD is in Jy. Each notebook copies its array files to `tables/` in the export folder (`array_LBA6_SKALow.txt`, `array_EVN_AVN_SKAMid.txt`, `array_EVN_alone_noSKA.txt`, `array_EVN_noSKA.txt`).
