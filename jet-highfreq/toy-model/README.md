# Toy model: relativistic jet, 5 GHz

| File | Content |
|---|---|
| `jet_model.txt` | the model in `ehtim` text format, **read by the notebook** |
| `jet_model.fits` | the same model as a FITS image |

| Parameter | Value |
|---|---|
| Flux density | 1.0 Jy |
| Structure | bright core, a chain of knots, and a second bright component ~9 mas downstream |
| Grid | 64 × 64 pixels of 281 µas (18 mas field of view); flux centroid ~3 mas from the image centre |
| Frequency | 5 GHz (set by the notebook) |

The notebook looks for `jet_model.txt` next to itself first and then here (`../toy-model/jet_model.txt`), so it runs unchanged from `notebook/`. In Colab, upload `jet_model.txt` to the session files.
