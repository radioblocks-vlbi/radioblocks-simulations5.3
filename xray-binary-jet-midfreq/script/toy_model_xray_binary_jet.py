#!/usr/bin/env python3
"""
toy_model_xray_binary_jet.py
============================

Toy model ONLY (no observation, no imaging): the time-variable, precessing, double-sided jet of an X-ray binary
(a toy model inspired by the microquasar SS 433), exactly as used by the notebook
`binary_jet_VLBI_ehtim_campaign.ipynb` (Section 2) and by `binary_jet_VLBI_campaign_full.py`.

The sky model is a compact core plus up to N_BLOBS pairs of ejecta (jet and counter-jet) launched along a precessing
helix; the blobs move outwards, fade with distance and disappear at the edge of the model. The functions and
parameters below are copied from the campaign script, so the frames are identical to the "truth" used there.

What it writes (in --out, default `xray_binary_toy_model/`)
----------------------------------------------------------
  fits/day_XX.fits             true sky on every day of the campaign (centre of the 6-h track), as FITS images
  png/day_XX.png               the same frames as PNG images (common colour scale)
  toy_model_campaign.gif       animation of the whole campaign (needs imageio)
  montage.png                  8 days of the campaign side by side
  light_curve.csv / .png       total flux density per day
  track_day_XX/                (with --track-day) the frames of the source DURING one 6-h track, for a given
                               variability factor (1x, 5x, 20x as in the campaign), as FITS, PNG and GIF
  parameters.json              every parameter used

Usage
-----
  python toy_model_xray_binary_jet.py                               # 43 days, default parameters
  python toy_model_xray_binary_jet.py --days 10 --out test_model    # first 10 days only
  python toy_model_xray_binary_jet.py --track-day 22 --factor 20    # also the evolution within the track of day 22
  python toy_model_xray_binary_jet.py --npix 512 --fov 80000        # finer grid / larger field of view [uas]

Requirements: ehtim 1.2.10 (with NumPy < 2), matplotlib; imageio for the GIFs (optional).
Run time: well under a minute for the 43 days at the default resolution.
"""

import argparse
import json
import os
import warnings

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

import ehtim as eh

try:
    import imageio.v2 as imageio
    HAS_IMAGEIO = True
except ImportError:
    HAS_IMAGEIO = False

warnings.filterwarnings("ignore")

# =============================================================================================================
# PARAMETERS (identical to the notebook and to binary_jet_VLBI_campaign_full.py)
# =============================================================================================================
N_DAYS_DEFAULT = 43
FRAMES_PER_DAY = 4.76          # model frames advanced per observing day
RF_HZ = 5.0e9                  # observing frequency stored in the FITS headers
RA_SOURCE, DEC_SOURCE = 19.19, 4.98
MJD_START = 59050.0
WINDOW_HOURS = 6.0             # track length [h] (only for --track-day)
FPS_SIM = 4                    # frames per hour within a track (only for --track-day)

PHYSICAL_SIZE_REF = 40000.0    # [uas] physical size of the model
OBSERVATION_FOV = 60000.0      # [uas] field of view of the images
NPIX = 256

TOY_FOV = 150.0
SCALE_FACTOR = PHYSICAL_SIZE_REF / TOY_FOV
FLUX_SCALE = 1e-4
BLOB_CORE_UAS = 6.0 * SCALE_FACTOR       # FWHM of the bright core of each blob [uas]
BLOB_HALO_UAS = 14.0 * SCALE_FACTOR      # FWHM of the fainter halo of each blob [uas]
DECAY_UAS = 100.0 * SCALE_FACTOR         # e-folding distance of the blob flux [uas]
VELOCITY_FACTOR = 0.4 * SCALE_FACTOR     # distance travelled by a blob per model frame [uas]
PRECESSION_PERIOD = 800.0                # model frames per precession cycle
OPENING_ANGLE = 0.55                     # opening of the precession cone
INCLINATION = 0.0                        # rotation of the jet axis on the sky [rad]
PHASE_OFFSET = np.pi / 2.0
SPACING_FRAMES = 52.0                    # model frames between ejections
N_BLOBS = 20                             # ejecta pairs
FIRST_FRAME = 50                         # model frame of day 1

RAD = eh.RADPERUAS


# =============================================================================================================
# SKY MODEL
# =============================================================================================================
def gaussian_array(im, flux, fwhm_rad, x0_rad, y0_rad):
    """Circular Gaussian of total `flux` [Jy] on the grid of `im` (numerically identical to Image.add_gauss)."""
    sigma = fwhm_rad / (2.0 * np.sqrt(2.0 * np.log(2.0)))
    xl = np.arange(0, -im.xdim, -1) * im.psize + (im.psize * im.xdim) / 2.0 - im.psize / 2.0
    yl = np.arange(0, -im.ydim, -1) * im.psize + (im.psize * im.ydim) / 2.0 - im.psize / 2.0
    X, Y = np.meshgrid(xl - x0_rad, yl - y0_rad)
    g = np.exp(-(X**2 + Y**2) / (2.0 * sigma**2))
    return g * (flux / g.sum())


def get_toy_model_frame(frame_idx, base_image):
    """True sky at model frame `frame_idx` (float): a core plus up to N_BLOBS ejecta pairs on a precessing helix."""
    arr = base_image.imvec.reshape(base_image.ydim, base_image.xdim).copy()
    arr += gaussian_array(base_image, 3000.0 * FLUX_SCALE, 5 * SCALE_FACTOR * RAD, 0.0, 0.0)      # core
    max_radius = PHYSICAL_SIZE_REF / 1.6
    fade_start = max_radius * 0.95
    for i in range(N_BLOBS):
        birth = i * SPACING_FRAMES
        if birth > 205:
            continue
        age = frame_idx - birth
        if age < 0:
            continue
        r = age * VELOCITY_FACTOR
        if r > max_radius:
            continue
        phase = -2 * np.pi * (birth / PRECESSION_PERIOD) + PHASE_OFFSET
        x_loc, y_loc = r, r * OPENING_ANGLE * np.sin(phase) * 0.8
        x1 = x_loc * np.cos(INCLINATION) - y_loc * np.sin(INCLINATION)
        y1 = x_loc * np.sin(INCLINATION) + y_loc * np.cos(INCLINATION)
        opacity = 1.0 if r <= fade_start else (max_radius - r) / (max_radius - fade_start)
        flux = 7500.0 * FLUX_SCALE * np.exp(-r / DECAY_UAS) * opacity
        if flux > 0.05 * FLUX_SCALE:
            for sgn in (+1, -1):                                  # jet and counter-jet
                arr += gaussian_array(base_image, flux * 0.2, BLOB_HALO_UAS * RAD, sgn * x1 * RAD, sgn * y1 * RAD)
                arr += gaussian_array(base_image, flux, BLOB_CORE_UAS * RAD, sgn * x1 * RAD, sgn * y1 * RAD)
    out = base_image.copy()
    out.imvec = arr.flatten()
    return out


def day_to_frame_idx(day):
    """Model frame at the centre of the track of observing day `day` (1-based), as in the campaign."""
    return FIRST_FRAME + (day - 1) * FRAMES_PER_DAY


# =============================================================================================================
# OUTPUT HELPERS
# =============================================================================================================
def save_png(im, path, title, vmax_mJy, limit_mas):
    fig, ax = plt.subplots(figsize=(5.6, 5), facecolor='white')
    m = ax.imshow(im.imarr() * 1e3, origin='upper', cmap='afmhot', vmin=0, vmax=vmax_mJy,
                  extent=[limit_mas, -limit_mas, -limit_mas, limit_mas])
    ax.set_xlabel("Relative RA [mas]"); ax.set_ylabel("Relative Dec [mas]"); ax.set_title(title, fontsize=10)
    fig.colorbar(m, ax=ax, fraction=0.046, pad=0.03).set_label("mJy / pixel")
    fig.tight_layout(); fig.savefig(path, dpi=110); plt.close(fig)


def write_gif(png_paths, path, fps):
    if HAS_IMAGEIO and png_paths:
        imageio.mimsave(path, [imageio.imread(p) for p in png_paths], duration=1.0 / fps, loop=0)
        return True
    return False


def main():
    ap = argparse.ArgumentParser(description="Toy model of the precessing jet of an X-ray binary (SS 433-like).")
    ap.add_argument("--days", type=int, default=N_DAYS_DEFAULT, help="observing days (default 43)")
    ap.add_argument("--out", default="xray_binary_toy_model", help="output folder")
    ap.add_argument("--npix", type=int, default=NPIX, help="pixels per side (default 256)")
    ap.add_argument("--fov", type=float, default=OBSERVATION_FOV, help="field of view [uas] (default 60000)")
    ap.add_argument("--track-day", type=int, default=None, help="also write the frames within the track of this day")
    ap.add_argument("--factor", type=float, default=1.0,
                    help="variability factor within the track for --track-day (1 realistic, 5 exaggerated, 20 extreme)")
    ap.add_argument("--fps", type=float, default=4.0, help="frames per second of the GIFs")
    args = ap.parse_args()

    for sub in ("fits", "png"):
        os.makedirs(os.path.join(args.out, sub), exist_ok=True)
    base = eh.image.make_empty(args.npix, args.fov * RAD, ra=RA_SOURCE, dec=DEC_SOURCE, rf=RF_HZ, mjd=MJD_START)
    limit_mas = args.fov / 2000.0

    # ---- one frame per observing day
    frames = {d: get_toy_model_frame(day_to_frame_idx(d), base).center() for d in range(1, args.days + 1)}
    vmax = 0.6 * max(f.imvec.max() for f in frames.values()) * 1e3        # common colour scale [mJy/pixel]
    pngs, rows = [], []
    for d, im in frames.items():
        im.save_fits(os.path.join(args.out, "fits", f"day_{d:02d}.fits"))
        p = os.path.join(args.out, "png", f"day_{d:02d}.png")
        save_png(im, p, f"X-ray binary jet, day {d} (model frame {day_to_frame_idx(d):.1f}), "
                        f"S = {im.total_flux():.2f} Jy", vmax, limit_mas)
        pngs.append(p); rows.append((d, day_to_frame_idx(d), im.total_flux()))
    gif_ok = write_gif(pngs, os.path.join(args.out, "toy_model_campaign.gif"), args.fps)

    # ---- light curve
    with open(os.path.join(args.out, "light_curve.csv"), "w") as f:
        f.write("day,model_frame,total_flux_Jy\n")
        f.writelines(f"{d},{fr:.2f},{s:.5f}\n" for d, fr, s in rows)
    fig, ax = plt.subplots(figsize=(8, 3.6), facecolor='white')
    ax.plot([r[0] for r in rows], [r[2] for r in rows], 'o-', color='#D95F02')
    ax.set_xlabel("Observing day"); ax.set_ylabel("Total flux density [Jy]")
    ax.set_title("Toy model of the X-ray binary jet: light curve"); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(os.path.join(args.out, "light_curve.png"), dpi=120); plt.close(fig)

    # ---- montage of 8 days
    show = np.unique(np.linspace(1, args.days, min(8, args.days)).round().astype(int))
    fig, axes = plt.subplots(2, 4, figsize=(18, 8.4), facecolor='white')
    for ax in axes.flat[len(show):]:
        ax.axis('off')
    for ax, d in zip(axes.flat, show):
        m = ax.imshow(frames[d].imarr() * 1e3, origin='upper', cmap='afmhot', vmin=0, vmax=vmax,
                      extent=[limit_mas, -limit_mas, -limit_mas, limit_mas])
        ax.set_title(f"Day {d}  S = {frames[d].total_flux():.2f} Jy")
    for ax in axes[1]:
        ax.set_xlabel("Relative RA [mas]")
    for ax in axes[:, 0]:
        ax.set_ylabel("Relative Dec [mas]")
    fig.colorbar(m, ax=axes, fraction=0.015, pad=0.01).set_label("mJy / pixel")
    fig.suptitle("Toy model of the precessing jet of an X-ray binary (SS 433-like)", fontsize=15, fontweight='bold')
    fig.savefig(os.path.join(args.out, "montage.png"), dpi=110); plt.close(fig)

    # ---- optional: the source DURING one track (what Movie.observe_same sees in the campaign)
    if args.track_day is not None:
        tdir = os.path.join(args.out, f"track_day_{args.track_day:02d}_factor_{args.factor:g}")
        os.makedirs(tdir, exist_ok=True)
        n = int(WINDOW_HOURS * FPS_SIM) + 1
        tpngs = []
        for k, t in enumerate(np.linspace(-WINDOW_HOURS / 2, WINDOW_HOURS / 2, n)):
            fr = day_to_frame_idx(args.track_day) + (t / 24.0) * FRAMES_PER_DAY * args.factor
            im = get_toy_model_frame(fr, base).center()
            im.save_fits(os.path.join(tdir, f"t{k:02d}.fits"))
            p = os.path.join(tdir, f"t{k:02d}.png")
            save_png(im, p, f"Day {args.track_day}, t = {t:+.2f} h from transit (factor {args.factor:g}x)", vmax, limit_mas)
            tpngs.append(p)
        write_gif(tpngs, os.path.join(tdir, "track.gif"), args.fps)

    params = {k: v for k, v in globals().items() if k.isupper() and isinstance(v, (int, float))}
    params.update({"days": args.days, "npix": args.npix, "fov_uas": args.fov,
                   "track_day": args.track_day, "factor": args.factor})
    with open(os.path.join(args.out, "parameters.json"), "w") as f:
        json.dump(params, f, indent=2)
    print(f"Toy model written to '{args.out}/': {len(frames)} daily frames (FITS + PNG), light curve, montage"
          + (", GIF" if gif_ok else " (install imageio for the GIF)")
          + (f", track of day {args.track_day}" if args.track_day is not None else "") + ".")
    print(f"Total flux: {min(r[2] for r in rows):.2f}-{max(r[2] for r in rows):.2f} Jy "
          f"(day 22: {frames[22].total_flux():.2f} Jy)" if 22 in frames else "")


if __name__ == "__main__":
    main()
