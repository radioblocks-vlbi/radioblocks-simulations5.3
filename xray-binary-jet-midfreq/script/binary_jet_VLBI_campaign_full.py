#!/usr/bin/env python3
"""
binary_jet_VLBI_campaign_full.py
================================

RADIOBLOCKS scenarios A and B at 5 GHz: the time-variable, precessing, double-sided jet of an X-ray binary
(toy model inspired by the microquasar SS 433) observed with the EVN alone (no SKA) and with the EVN + AVN + SKA-Mid.
FULL-CAMPAIGN version: every day of the campaign is simulated AND imaged, for each error scenario and for each
source-variability rate.

Companion files: the quick-look notebook `binary_jet_VLBI_ehtim_campaign.ipynb` simulates the whole campaign in the
data domain but images a single frame, and `toy_model_xray_binary_jet.py` writes only the toy model (no observation,
no imaging). All three share the same sky model; the notebook and this script also share the arrays, observing
set-up, error scenarios and imaging recipe.

Arrays (SKA-Mid is part of the second one in every run)
-------------------------------------------------------
  * EVN (no SKA):         10 EVN stations (EF, IR, JB, MC, NT, ON, SR, TR, WB, YS).
  * EVN + AVN + SKA-Mid:  the same 10 EVN stations + 4 SKA-Mid elements (S5 = phased-up SKA-Mid core, SEFD 3.1 Jy;
                          S004, S008, S133 = individual SKA-Mid dishes) + 5 AVN stations (HH, KU, NA, BW, ML).
  In the CSV files and folder names the two arrays keep the short tags "EVN" and "EVN+AVN" / "EVN_AVN" (so that
  runs started with earlier versions of the script can be resumed); "EVN+AVN" ALWAYS includes SKA-Mid.
  Figure titles and legends use the explicit names "EVN (no SKA)" and "EVN + AVN + SKA-Mid".

What the script does
--------------------
For each source-variability factor (time compression of the source evolution within one track: 1x "realistic",
5x "exaggerated", 20x "extreme") and each RADIOBLOCKS error scenario (A: thermal noise only; B: thermal noise +
gain errors + generic phase errors), and for every observing day of the campaign:

  1. renders a movie of the evolving source over the 6-h track and observes it with the EVN (no SKA) and the EVN+AVN+SKA-Mid
     (`Movie.observe_same`, so the source changes DURING the track);
  2. saves the observations as UVFITS;
  3. images both datasets with a 3-round RML pipeline (closure phases + amplitudes, then complex visibilities after
     a phase self-calibration to the reconstruction itself). Each day starts from the reconstruction of the
     previous day (blurred and rescaled to the true flux); the first day starts from a broad Gaussian prior;
     The data used for imaging carry a 2% systematic error budget (added in quadrature to the thermal sigma), the
     Gaussian prior is randomly perturbed by 10% to break the point symmetry of the jet, round 1 is repeated if it
     stalls, and the rounds run 150 / 150 / 200 iterations; see SYS_NOISE, PRIOR_PERTURB and IMAGING_ROUNDS.
  4. computes the image-fidelity metrics against the ground truth (RMSE, NRMSE, NXCORR, NXCORR against the truth
     at the same resolution, SSIM, dynamic range, recovered flux, reduced chi^2 of closure phases and amplitudes)
     and appends them to a CSV file (so that an interrupted run loses nothing and can be resumed);
  5. saves per-day frames (truth | EVN (no SKA) | EVN+AVN+SKA-Mid) and FITS images, and at the end of each run builds the animated
     GIFs and a sample of PDF maps (dirty image/beam, clean beam, restored image) for the middle day.
After all runs, it builds the campaign-wide summary plots (PDF + PNG) and a summary table from the CSV files.

Why there is no Scenario C
--------------------------
Scenario C (structured atmospheric corruptions: an ionospheric dTEC screen and a tropospheric delay screen, with
in-band and in-scan decorrelation) is not included in the dynamic case: every visibility already comes from a
different frame of the evolving source, the ionospheric and tropospheric screens would have to be continuous over the 43 days and averaged over channels and sub-integrations for ~15,000 visibilities per day
and array, and the run time (already ~2 days per scenario on a virtual machine) would multiply. It would also mix
two effects (source variability and structured phase errors) that this study is designed to separate. The static
5 GHz notebooks of the project show the effect of Scenario C at this frequency.

Usage
-----
  python binary_jet_VLBI_campaign_full.py                         # everything: A and B, 3 factors, 43 days
  python binary_jet_VLBI_campaign_full.py --scenarios A           # only Scenario A ...
  python binary_jet_VLBI_campaign_full.py --scenarios B           # ... and Scenario B in a second process
  python binary_jet_VLBI_campaign_full.py --factors realistic     # only the realistic variability rate
  python binary_jet_VLBI_campaign_full.py --summary-only          # only rebuild the global plots and tables
  python binary_jet_VLBI_campaign_full.py --days 2 --factors realistic --ttype fast   # quick test (~20 min)

Several processes can write to the same output folder (default `binary_jet_campaign_results/`) as long as they run
different factor/scenario combinations; run `--summary-only` at the end to merge everything. A run that is
interrupted is resumed from the last completed day when the script is started again with the same options
(use --overwrite to start from scratch).

Run time: the previous version of this script (Scenario A only, 50 / 50 / 80 iterations) took about two days on the
virtual machine used for the project (NFFT transforms) for the three variability factors. The longer imaging rounds
of this version roughly double the imaging time, so expect ~3-4 days per scenario; run A and B as two parallel
processes on a multi-core machine, and/or select the factors you need. `--maxit 50 50 80` restores the old speed.
Self-calibrating the ~15,000 EVN+AVN+SKA-Mid visibilities dominates.

Requirements: ehtim 1.2.10 (with NumPy < 2), matplotlib, pandas, imageio (GIFs), scikit-image (optional, SSIM),
pynfft (optional: --ttype nfft; otherwise the FFT-based 'fast' transform is used).
"""

import argparse
import contextlib
import datetime
import gc
import glob
import io
import json
import os
import sys
import time
import warnings

import matplotlib
matplotlib.use('Agg')                    # the script only writes files: no display needed
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse
import numpy as np
import pandas as pd

import ehtim as eh
from ehtim.calibrating.self_cal import self_cal

try:
    import imageio.v2 as imageio
    HAS_IMAGEIO = True
except ImportError:
    HAS_IMAGEIO = False
try:
    from skimage.metrics import structural_similarity as ssim
    HAS_SSIM = True
except ImportError:
    HAS_SSIM = False

warnings.filterwarnings("ignore")

# =============================================================================================================
# 1. CONFIGURATION (identical to the notebook)
# =============================================================================================================
N_DAYS_DEFAULT = 43
FRAMES_PER_DAY = 4.76          # model frames advanced per observing day
MAX_ATTEMPTS   = 150           # safety limit when a day has no usable data

RF_HZ        = 5.0e9
BW_HZ        = 128e6
TINT_S       = 12.0            # scan integration time [s]
TADV_S       = 240.0           # time between scans [s]
ELEVMIN      = 10.0            # minimum elevation [deg]
WINDOW_HOURS = 6.0             # track length [h], centred on the source transit
FPS_SIM      = 4               # movie frames per hour within a track
MJD_START    = 59050.0
RA_SOURCE, DEC_SOURCE = 19.19, 4.98

PHYSICAL_SIZE_REF = 40000.0    # [uas]
OBSERVATION_FOV   = 60000.0    # [uas]
NPIX              = 256

TOY_FOV           = 150.0
SCALE_FACTOR      = PHYSICAL_SIZE_REF / TOY_FOV
FLUX_SCALE        = 1e-4
BLOB_CORE_UAS     = 6.0 * SCALE_FACTOR
BLOB_HALO_UAS     = 14.0 * SCALE_FACTOR
DECAY_UAS         = 100.0 * SCALE_FACTOR
VELOCITY_FACTOR   = 0.4 * SCALE_FACTOR
PRECESSION_PERIOD = 800.0
OPENING_ANGLE     = 0.55
INCLINATION       = 0.0
PHASE_OFFSET      = np.pi / 2.0
SPACING_FRAMES    = 52.0
N_BLOBS           = 20

# Source-variability rate within a track (time-compression factor of the source evolution)
FACTORS = {"realistic": ("01_Realistic", 1.0), "exaggerated": ("02_Exaggerated", 5.0), "extreme": ("03_Extreme", 20.0)}

# RADIOBLOCKS error scenarios (Scenario C is not included in the dynamic case: see the module docstring)
SCENARIOS = {
    "A": dict(label="A: thermal only",       ampcal=True,  phasecal=True,  gain_offset=0.0,  gainp=0.0),
    "B": dict(label="B: thermal+gain+phase", ampcal=False, phasecal=False, gain_offset=0.15, gainp=0.10),
}

# Imaging recipe (identical to the notebook)
IMAGING_ROUNDS = [
    {'data_term': {'cphase': 50, 'amp': 50},
     'reg_term':  {'simple': 10, 'flux': 1e4, 'cm': 50},                  'maxit': 150},
    {'data_term': {'cphase': 80, 'amp': 80},
     'reg_term':  {'tv': 0.05, 'l1': 0.01, 'flux': 1e4, 'cm': 50},       'maxit': 150, 'blur_frac': 0.3},
    {'data_term': {'cphase': 100, 'amp': 100, 'vis': 30},
     'reg_term':  {'tv': 0.05, 'l1': 0.01, 'flux': 1e4, 'cm': 50},       'maxit': 200, 'blur_frac': 0.2, 'selfcal': 'phase'},
]
# Fractional systematic error added in quadrature to the thermal sigma of the data used for IMAGING ONLY (the saved
# UVFITS files are not modified). Needed because the S5-SKA dish baselines reach SNR ~8,600 and the source changes
# during the track: without it the amplitude chi^2 (~2e5) dominates and the optimiser can stall at the start image.
SYS_NOISE = 0.02
PRIOR_PERTURB = 0.10           # random multiplicative perturbation of the Gaussian prior (symmetry breaking)
PRIOR_FWHM_FRAC = 0.4          # FWHM of the Gaussian prior (first day), fraction of the FOV
PREV_INIT_BLUR  = 0.4          # blur of the previous day's reconstruction used as start image, fraction of the resolution
RESTORE_BLUR    = 0.4          # final restoring blur, fraction of the fitted clean beam

EVN_STATIONS = [
    ("EF",  4033947.3,   486990.8,  4900431.0,   25.0),
    ("IR",  3183649.3,  1276903.0,  5359264.7,  480.0),
    ("JB",  3822846.8,  -153802.3,  5086285.9,  300.0),
    ("MC",  4461369.7,   919597.1,  4449559.4,  840.0),
    ("NT",  4934562.8,  1321201.5,  3806484.7, 1100.0),
    ("ON",  3370965.9,   711466.2,  5349664.2,  850.0),
    ("SR",  4865183.5,   791922.3,  4035136.0,   50.0),
    ("TR",  3638558.5,  1221969.7,  5077036.8,  650.0),
    ("WB",  3828767.3,   442446.2,  5064921.6, 1600.0),
    ("YS",  4848761.8,  -261484.2,  4123085.1,  160.0),
]
AVN_STATIONS = [
    ("HH",   5085442.8,     2668263.8,  -2768696.8, 700.0),
    ("S5",   5109303.0031,  2065863.3087, -3230973.0000,   3.1),
    ("S004", 5109040.8523,  2063853.5134, -3238686.0441, 330.0),
    ("S008", 5108654.5126,  2064500.4184, -3239044.2096, 330.0),
    ("S133", 5104477.1687,  2073238.2514, -3242137.6044, 330.0),
    ("KU",   6346222.481,    -35250.5209,   634244.2061, 330.0),
    ("NA",   5632444.680,   1730320.594,  -2433598.729,  330.0),
    ("BW",   5216975.743,   2534223.208,  -2644711.076,  330.0),
    ("ML",   5127067.758,   3792660.5370,   -97962.9258, 330.0),
]
ARRAY_KEYS = {"EVN": "EVN", "EVN+AVN": "EVN_AVN"}          # CSV key -> folder / column tag (kept for resume)
ARRAY_LABEL = {"EVN": "EVN (no SKA)", "EVN+AVN": "EVN + AVN + SKA-Mid"}   # explicit names used in figures and logs

RAD = eh.RADPERUAS
LIMIT_MAS = (OBSERVATION_FOV / 2.0) / 1000.0
EXTENT_MAS = [LIMIT_MAS, -LIMIT_MAS, -LIMIT_MAS, LIMIT_MAS]    # RA increases to the left; use with origin='upper'

plt.rcParams.update({
    'font.family': 'serif', 'font.serif': ['Times New Roman', 'Liberation Serif', 'DejaVu Serif'],
    'mathtext.fontset': 'cm', 'axes.labelsize': 13, 'axes.titlesize': 14, 'xtick.labelsize': 11,
    'ytick.labelsize': 11, 'legend.fontsize': 10, 'xtick.direction': 'in', 'ytick.direction': 'in',
    'xtick.top': True, 'ytick.right': True, 'axes.grid': True, 'grid.alpha': 0.3, 'grid.linestyle': '--',
})
FACTOR_COLORS = {"01_Realistic": '#1B9E77', "02_Exaggerated": '#D95F02', "03_Extreme": '#7570B3'}


# =============================================================================================================
# 2. UTILITIES
# =============================================================================================================
LOG_FILE = None


def log(msg):
    line = f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    print(line, flush=True)
    if LOG_FILE:
        with open(LOG_FILE, 'a') as f:
            f.write(line + "\n")


@contextlib.contextmanager
def quiet():
    """Silence ehtim's progress messages."""
    with contextlib.redirect_stdout(io.StringIO()) as buf:
        yield buf


def resolve_ttype(choice):
    if choice != 'auto':
        return choice
    try:
        import pynfft  # noqa: F401
        return 'nfft'
    except Exception:
        return 'fast'


def write_array_file(path, stations):
    with open(path, "w") as f:
        f.write("# Site X Y Z SEFD\n")
        for s in stations:
            f.write(f"{s[0]} {s[1]} {s[2]} {s[3]} {s[4]}\n")


# =============================================================================================================
# 3. SKY MODEL (vectorised, numerically identical to Image.add_gauss; see the notebook, Section 2.1)
# =============================================================================================================
def gaussian_array(im, flux, fwhm_rad, x0_rad, y0_rad):
    sigma = fwhm_rad / (2.0 * np.sqrt(2.0 * np.log(2.0)))
    xl = np.arange(0, -im.xdim, -1) * im.psize + (im.psize * im.xdim) / 2.0 - im.psize / 2.0
    yl = np.arange(0, -im.ydim, -1) * im.psize + (im.psize * im.ydim) / 2.0 - im.psize / 2.0
    X, Y = np.meshgrid(xl - x0_rad, yl - y0_rad)
    g = np.exp(-(X**2 + Y**2) / (2.0 * sigma**2))
    return g * (flux / g.sum())


def get_toy_model_frame(frame_idx, base_image):
    """Ground-truth jet at model-frame `frame_idx` (float): a core plus up to N_BLOBS ejecta pairs on a helix."""
    arr = base_image.imvec.reshape(base_image.ydim, base_image.xdim).copy()
    arr += gaussian_array(base_image, 3000.0 * FLUX_SCALE, 5 * SCALE_FACTOR * RAD, 0.0, 0.0)
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
                arr += gaussian_array(base_image, flux,       BLOB_CORE_UAS * RAD, sgn * x1 * RAD, sgn * y1 * RAD)
    out = base_image.copy()
    out.imvec = arr.flatten()
    return out


# =============================================================================================================
# 4. OBSERVING ENGINE (movie -> time-variable visibilities)
# =============================================================================================================
def get_optimal_observation_window(mjd, ra_hr=RA_SOURCE, duration=WINDOW_HOURS, lon_hr=10.0 / 15.0):
    """UTC start/stop [h] of a `duration`-hour track centred on the source transit at the reference longitude."""
    T = (mjd - 51544.5) / 36525.0
    gmst_0h = (6.697374558 + 2400.051336 * T + 0.000025862 * T**2) % 24.0
    transit_utc = ((ra_hr - gmst_0h - lon_hr) % 24.0) * 0.99726958
    start_hr, end_hr = transit_utc - duration / 2.0, transit_utc + duration / 2.0
    if end_hr >= 23.9:
        shift = end_hr - 23.9; start_hr -= shift; end_hr -= shift
    elif start_hr <= 0.1:
        shift = 0.1 - start_hr; start_hr += shift; end_hr += shift
    return start_hr, end_hr


def build_movie(base_frame_idx, base_img, start_hr, end_hr, factor, fps_sim=FPS_SIM, pad=0.1):
    """Movie of the evolving source over the track (centred on base_frame_idx); returns (movie, truth at mid-track)."""
    t0, t1 = start_hr - pad, end_hr + pad
    duration = t1 - t0
    n_frames = int(duration * fps_sim) + 1
    times = list(np.linspace(t0, t1, n_frames))
    arrays, truth = [], None
    for i in range(n_frames):
        frac = i / (n_frames - 1) - 0.5
        frame = base_frame_idx + frac * (duration / 24.0) * FRAMES_PER_DAY * factor
        im = get_toy_model_frame(frame, base_img).center()
        im.mjd = MJD_START
        arrays.append(im.imarr())
        if i == n_frames // 2:
            truth = im.copy()
    movie = eh.movie.Movie(arrays, times=times, psize=base_img.psize, ra=base_img.ra,
                           dec=base_img.dec, rf=base_img.rf, mjd=MJD_START)
    return movie, truth


def observe_day(movie, truth, array, start_hr, end_hr, err, ttype):
    """Observe the movie on the schedule of the central frame, with the errors of the scenario."""
    with quiet():
        tmpl = truth.observe(array, tint=TINT_S, tadv=TADV_S, tstart=start_hr, tstop=end_hr, bw=BW_HZ,
                             ttype=ttype, elevmin=ELEVMIN, ampcal=err['ampcal'], phasecal=err['phasecal'],
                             gain_offset=err['gain_offset'], gainp=err['gainp'], verbose=False)
    if len(tmpl.data) == 0:
        return None
    times_u, counts = np.unique(tmpl.data['time'], return_counts=True)
    valid = times_u[counts >= 3]                       # at least 3 baselines (closure phases need triangles)
    if len(valid) == 0:
        return None
    tmpl.data = tmpl.data[np.isin(tmpl.data['time'], valid)]
    try:
        with quiet():
            return movie.observe_same(tmpl, ttype=ttype, ampcal=err['ampcal'], phasecal=err['phasecal'],
                                      gain_offset=err['gain_offset'], gainp=err['gainp'], verbose=False)
    except Exception as e:
        log(f"   [!] movie.observe_same failed: {e}")
        return None


# =============================================================================================================
# 5. IMAGING AND METRICS (identical recipe and metrics to the notebook)
# =============================================================================================================
def perturbed_prior(prior, seed):
    """Gaussian prior times a small random perturbation (fixed seed, flux preserved). The jet is point-symmetric and so
    is a centred Gaussian: symmetric data acting on a symmetric image give symmetric gradients, so the optimiser
    leaves the start image only slowly (an amplitude-chi^2 plateau of ~50 iterations, sometimes a complete stall).
    The perturbation breaks the symmetry (plateau of 4-7 iterations in tests)."""
    out = prior.copy()
    rng = np.random.default_rng(seed)
    out.imvec = prior.imvec * np.exp(PRIOR_PERTURB * rng.standard_normal(prior.imvec.size))
    out.imvec *= prior.total_flux() / out.imvec.sum()
    return out


def amp_chi2(imgr, im):
    """Reduced amplitude chi^2 of image `im` for the data of `imgr` (only the pixels inside the imager's clipfloor
    mask are free parameters). Returns NaN if it cannot be computed (the stall guard is then skipped)."""
    try:
        m = getattr(imgr, '_embed_mask', None)
        v = im.imvec if (m is None or np.all(m)) else im.imvec[np.asarray(m, bool)]
        return float(imgr.make_chisq_dict(v).get('amp', np.nan))
    except Exception:
        return np.nan


def run_imaging_pipeline(obs, total_flux, ttype, init_image=None):
    """3-round RML imaging with phase self-calibration before round 3. Returns (image, final_obs, round_status, obs_used).
    Round 1 starts from `init_image` (previous day, blurred and rescaled) or from the perturbed Gaussian prior.
    Stall guard: if round 1 does not lower the amplitude chi^2 by at least 10%, it is repeated from a new perturbation
    of the prior (up to 3 attempts)."""
    if SYS_NOISE > 0:
        with quiet():
            obs = obs.add_fractional_noise(SYS_NOISE)
    res = obs.res()
    empty = eh.image.make_square(obs, NPIX, OBSERVATION_FOV * RAD)
    sz = PRIOR_FWHM_FRAC * OBSERVATION_FOV * RAD
    prior = empty.add_gauss(total_flux, (sz, sz, 0, 0, 0))
    if init_image is not None and init_image.total_flux() > 0:
        start = init_image.blur_circ(res * PREV_INIT_BLUR)
        start.imvec *= total_flux / start.total_flux()
    else:
        start = None
    out, cur, status = prior, obs, []
    for k, rnd in enumerate(IMAGING_ROUNDS, 1):
        if rnd.get('selfcal'):
            with quiet():
                cur = self_cal(obs, out, method=rnd['selfcal'], ttype=ttype)
        n_attempts = 3 if k == 1 else 1
        for attempt in range(n_attempts):
            if k == 1:
                init = start if (attempt == 0 and start is not None) else perturbed_prior(prior, seed=attempt)
            else:
                bf = rnd.get('blur_frac', 0.0)
                init = out.blur_circ(res * bf) if bf > 0 else out
            with quiet() as buf:
                imgr = eh.imager.Imager(cur, init, init, total_flux, data_term=rnd['data_term'],
                                        reg_term=rnd['reg_term'], maxit=rnd['maxit'], ttype=ttype, show_updates=False)
                new = imgr.make_image(clipfloor=1e-9)
                c0, c1 = amp_chi2(imgr, init), amp_chi2(imgr, new)
            plt.close('all')
            stalled = k == 1 and 'amp' in rnd['data_term'] and c1 > 0.9 * c0
            if not stalled or attempt == n_attempts - 1:
                break
            log(f"      round 1: amplitude chi^2 did not decrease ({c0:.0f} -> {c1:.0f}); retrying from a new prior")
        out = new
        status.append("ABNORMAL" if "ABNORMAL" in buf.getvalue() else
                      "stalled" if stalled else "retried" if attempt > 0 else "ok")
    return out, cur, status, obs


def calc_rmse(d_true, d_rec):
    return float(np.sqrt(np.mean((d_true - d_rec) ** 2)))


def calc_nrmse(d_rec, d_true):
    a, b = d_rec / d_rec.sum(), d_true / d_true.sum()
    return float(np.sqrt(np.mean((a - b) ** 2)) / np.sqrt(np.mean(b ** 2)))


def calc_nxcorr(d_true, d_rec):
    norm = np.sqrt(np.sum(d_true ** 2) * np.sum(d_rec ** 2))
    return float(np.sum(d_true * d_rec) / norm) if norm > 0 else 0.0


def calc_ssim(d_true, d_rec):
    return float(ssim(d_true, d_rec, data_range=d_true.max())) if HAS_SSIM else np.nan


def calc_dynamic_range(d_rec, d_ref):
    """Peak / rms of the reconstruction where the reference (truth restored with the same beam) is < 1% of its peak."""
    off = d_ref < 0.01 * d_ref.max()
    rms = np.std(d_rec[off])
    return float(d_rec.max() / rms) if rms > 0 else np.inf


def calc_chi2_amp(obs, im_rec, ttype):
    try:
        with quiet():
            sim = im_rec.observe_same_nonoise(obs, ttype=ttype)
        a_o, a_s = obs.unpack(['amp', 'sigma']), sim.unpack(['amp'])
        m = a_o['sigma'] > 0
        return float(np.sum(((a_o['amp'][m] - a_s['amp'][m]) / a_o['sigma'][m]) ** 2) / np.sum(m))
    except Exception:
        return np.nan


def calc_chi2_cphase(obs, im_rec, ttype):
    try:
        with quiet():
            o = obs.copy(); o.add_cphase(count='min')
            sim = im_rec.observe_same_nonoise(obs, ttype=ttype); sim.add_cphase(count='min')
        co, cs = o.cphase, sim.cphase
        if len(co) != len(cs):
            return np.nan
        diff = np.angle(np.exp(1j * np.radians(co['cphase'])) * np.exp(-1j * np.radians(cs['cphase'])))
        m = co['sigmacp'] > 0
        return float(np.sum((diff[m] / np.radians(co['sigmacp'][m])) ** 2) / np.sum(m))
    except Exception:
        return np.nan


def image_and_score(obs, truth, ttype, prev):
    """Image one dataset and compute every metric. Returns (row dict, aligned unrestored image, restored image, beam)."""
    t0 = time.time()
    zbl = truth.total_flux()
    try:
        raw, obs_cal, status, obs_sys = run_imaging_pipeline(obs, zbl, ttype, init_image=prev)
        failed = False
    except Exception as e:                       # keep the campaign going; the day is flagged in the CSV
        log(f"      [!] imaging failed ({e}); the Gaussian prior is used as reconstruction for this day")
        empty = eh.image.make_square(obs, NPIX, OBSERVATION_FOV * RAD)
        sz = PRIOR_FWHM_FRAC * OBSERVATION_FOV * RAD
        raw, obs_cal, status, failed = empty.add_gauss(zbl, (sz, sz, 0, 0, 0)), obs, ["FAILED"] * 3, True
        obs_sys = obs
    with quiet():
        beam = obs.fit_beam()
        aligned = truth.align_images([raw])[0][0]
    restored = aligned.blur_gauss(beam, RESTORE_BLUR)
    d_true, d_rec = truth.imarr(), restored.imarr()
    d_tb = truth.blur_gauss(beam, RESTORE_BLUR).imarr()
    row = {
        "n_vis": len(obs.data),
        "rmse_mJy_px": calc_rmse(d_true, d_rec) * 1e3, "nrmse": calc_nrmse(d_rec, d_true),
        "nxcorr": calc_nxcorr(d_true, d_rec), "nxcorr_blurred_truth": calc_nxcorr(d_tb, d_rec),
        "ssim": calc_ssim(d_true, d_rec), "dynamic_range": calc_dynamic_range(d_rec, d_tb),
        "flux_ratio": raw.total_flux() / zbl,
        "chi2_cphase": calc_chi2_cphase(obs_sys, raw, ttype), "chi2_amp": calc_chi2_amp(obs_cal, raw, ttype),
        "beam_maj_mas": beam[0] / RAD / 1e3, "beam_min_mas": beam[1] / RAD / 1e3, "beam_pa_deg": np.degrees(beam[2]),
        "rounds_status": "/".join(status), "imaging_failed": failed, "seconds": time.time() - t0,
    }
    return row, aligned, restored, beam


# =============================================================================================================
# 6. PLOTTING HELPERS (orientation: ehtim's imarr() has row 0 = north and column 0 = east -> origin='upper')
# =============================================================================================================
def draw_beam_ellipse(ax, beam, color='white'):
    bmaj, bmin, pa = beam[0] / RAD / 1e3, beam[1] / RAD / 1e3, beam[2]
    # position angle measured from north through east; RA increases to the left -> rotation of -PA in data coords
    ax.add_patch(Ellipse((0.8 * LIMIT_MAS, -0.8 * LIMIT_MAS), width=bmin, height=bmaj, angle=-np.degrees(pa),
                         facecolor='none', edgecolor=color, linewidth=1.5))


def show_map(ax, arr_mJy, title, beam=None, vmin=0, vmax=None, cmap='afmhot'):
    im = ax.imshow(arr_mJy, origin='upper', cmap=cmap, extent=EXTENT_MAS, vmin=vmin, vmax=vmax)
    ax.set_xlim(LIMIT_MAS, -LIMIT_MAS); ax.set_ylim(-LIMIT_MAS, LIMIT_MAS); ax.grid(False)
    ax.set_title(title); ax.set_xlabel("Relative RA [mas]")
    if beam is not None:
        draw_beam_ellipse(ax, beam)
    return im


def save_map(arr, filename, title, beam=None, cmap='afmhot', vmin=None, vmax=None, unit="mJy/pixel", scale=1e3):
    fig, ax = plt.subplots(figsize=(6, 5))
    a = arr * scale
    im = show_map(ax, a, title, beam, vmin=np.min(a) if vmin is None else vmin, vmax=vmax, cmap=cmap)
    ax.set_ylabel("Relative Dec [mas]")
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04).set_label(unit)
    fig.savefig(filename, bbox_inches='tight')
    plt.close(fig)


# =============================================================================================================
# 7. ONE RUN = one variability factor x one scenario, all days
# =============================================================================================================
def run_combination(out_dir, fac_name, factor, sc_key, n_days, ttype, arrays, overwrite=False, save_txt=False):
    err = SCENARIOS[sc_key]
    run_dir = f"{out_dir}/{fac_name}/Scenario_{sc_key}"
    dirs = {k: f"{run_dir}/{k}" for k in ("frames", "frames_model", "frames_EVN", "frames_EVN_AVN", "pdf_midpoint")}
    for a in ARRAY_KEYS.values():
        dirs[f"uv_{a}"] = f"{run_dir}/uvfits/{a}"
        dirs[f"fits_{a}"] = f"{run_dir}/fits/{a}"
    for d in dirs.values():
        os.makedirs(d, exist_ok=True)
    csv_path, done_flag = f"{run_dir}/metrics_per_day.csv", f"{run_dir}/DONE"

    if overwrite:
        for p in (csv_path, done_flag):
            if os.path.exists(p):
                os.remove(p)
    if os.path.exists(done_flag) and os.path.exists(csv_path):
        n_done = pd.read_csv(csv_path)['day'].nunique()
        if n_done >= n_days:
            log(f"== {fac_name} / Scenario {sc_key}: already complete ({n_done} days; use --overwrite to redo)")
            return
        os.remove(done_flag)                      # more days requested than done: continue the campaign

    # ---- resume from the last completed day, if any
    prev = {a: None for a in ARRAY_KEYS}
    day, offset = 0, 0
    if os.path.exists(csv_path):
        old = pd.read_csv(csv_path)
        counts = old.groupby('day')['array'].nunique()
        complete = sorted(counts[counts == len(ARRAY_KEYS)].index)
        old = old[old['day'].isin(complete)]
        old.to_csv(csv_path, index=False)
        if complete:
            day = int(complete[-1]); offset = int(old['offset'].max()) + 1
            for a_name, a_tag in ARRAY_KEYS.items():
                p = f"{dirs['fits_' + a_tag]}/recon_unrestored_day{day:02d}.fits"
                if os.path.exists(p):
                    with quiet():
                        prev[a_name] = eh.image.load_fits(p)
            log(f"== {fac_name} / Scenario {sc_key}: resuming after day {day}")

    log(f"== {fac_name} (factor {factor:g}x) / {err['label']}: days {day + 1}..{n_days}")
    base = eh.image.make_empty(NPIX, OBSERVATION_FOV * RAD, ra=RA_SOURCE, dec=DEC_SOURCE, rf=RF_HZ)
    start_hr, end_hr = get_optimal_observation_window(MJD_START)
    vmax_path = f"{run_dir}/colour_scale_vmax_mJy.txt"        # common colour scale of all frames of this run
    vmax_mJy = float(open(vmax_path).read()) if (day > 0 and os.path.exists(vmax_path)) else None
    t_run = time.time()

    while day < n_days:
        if offset >= MAX_ATTEMPTS:
            log("   [!] attempt limit reached"); break
        movie, truth = build_movie(50 + offset * FRAMES_PER_DAY, base, start_hr, end_hr, factor)
        obs = {a: observe_day(movie, truth, arr, start_hr, end_hr, err, ttype) for a, arr in arrays.items()}
        del movie
        if any(o is None for o in obs.values()):
            log(f"   attempt {offset}: no usable data, skipping"); offset += 1; continue
        day += 1
        t_day = time.time()
        if vmax_mJy is None:
            vmax_mJy = truth.imvec.max() * 1e3 * 0.6
            open(vmax_path, 'w').write(f"{vmax_mJy:.6f}")

        rows, restored, beams = [], {}, {}
        for a_name, a_tag in ARRAY_KEYS.items():
            o = obs[a_name]
            o.mjd = MJD_START + offset
            with quiet():
                o.save_uvfits(f"{dirs['uv_' + a_tag]}/obs_day_{day:02d}.uvfits")
                if save_txt:
                    o.save_txt(f"{dirs['uv_' + a_tag]}/obs_day_{day:02d}.txt")
            row, aligned, rest, beam = image_and_score(o, truth, ttype, prev[a_name])
            prev[a_name] = aligned
            restored[a_name], beams[a_name] = rest, beam
            with quiet():
                aligned.save_fits(f"{dirs['fits_' + a_tag]}/recon_unrestored_day{day:02d}.fits")
                rest.save_fits(f"{dirs['fits_' + a_tag]}/recon_restored_day{day:02d}.fits")
            rows.append({"factor": fac_name, "time_factor": factor, "scenario": sc_key, "array": a_name,
                         "day": day, "offset": offset, "truth_flux_Jy": truth.total_flux(), **row})
        with quiet():
            truth.save_fits(f"{run_dir}/fits/truth_day{day:02d}.fits")
        df = pd.DataFrame(rows)
        df.to_csv(csv_path, mode='a', header=not os.path.exists(csv_path), index=False)

        # ---- frames (truth | EVN | EVN+AVN) and single panels
        d_mod = truth.imarr() * 1e3
        fig, axes = plt.subplots(1, 3, figsize=(18, 6))
        im = show_map(axes[0], d_mod, "Ground truth", vmax=vmax_mJy)
        axes[0].set_ylabel("Relative Dec [mas]")
        for ax, a_name in zip(axes[1:], ARRAY_KEYS):
            r = df[df['array'] == a_name].iloc[0]
            show_map(ax, restored[a_name].imarr() * 1e3,
                     f"{ARRAY_LABEL[a_name]} (RMSE {r['rmse_mJy_px']:.2f} mJy/px, NXCORR {r['nxcorr']:.2f})", beams[a_name], vmax=vmax_mJy)
        fig.colorbar(im, ax=axes, fraction=0.015, pad=0.01).set_label("mJy / pixel")
        fig.suptitle(f"{fac_name} ({factor:g}x) | Scenario {sc_key} | day {day:02d}", fontsize=16, fontweight='bold')
        fig.savefig(f"{dirs['frames']}/f_{day:03d}.png", bbox_inches='tight', facecolor='white', dpi=90)
        plt.close(fig)
        for sub, arr_mJy, title, beam in [("frames_model", d_mod, "Ground truth", None),
                                          ("frames_EVN", restored["EVN"].imarr() * 1e3, "EVN (no SKA)", beams["EVN"]),
                                          ("frames_EVN_AVN", restored["EVN+AVN"].imarr() * 1e3, "EVN + AVN + SKA-Mid", beams["EVN+AVN"])]:
            fig, ax = plt.subplots(figsize=(6, 5))
            im = show_map(ax, arr_mJy, f"{title} | day {day:02d}", beam, vmax=vmax_mJy)
            ax.set_ylabel("Relative Dec [mas]")
            fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04).set_label("mJy / pixel")
            fig.savefig(f"{dirs[sub]}/f_{day:03d}.png", bbox_inches='tight', facecolor='white', dpi=90)
            plt.close(fig)

        # ---- sample of PDF maps for the middle day
        if day == n_days // 2 + 1:
            fov_rad = OBSERVATION_FOV * RAD
            save_map(truth.imarr(), f"{dirs['pdf_midpoint']}/ground_truth.pdf", "Ground truth")
            for a_name, a_tag in ARRAY_KEYS.items():
                o = obs[a_name]
                with quiet():
                    dimg, dbeam = o.dirtyimage(NPIX, fov_rad), o.dirtybeam(NPIX, fov_rad)
                cb = base.add_gauss(1.0, (beams[a_name][0], beams[a_name][1], beams[a_name][2], 0, 0))
                # ehtim divides the dirty image and beam by the SUM of the beam over the image (~0 without zero
                # spacings, negative for the EVN here): use the beam's central value instead (-> Jy per dirty beam)
                b0 = dbeam.imarr()[NPIX // 2, NPIX // 2]
                save_map(dimg.imarr() / b0, f"{dirs['pdf_midpoint']}/dirty_image_{a_tag}.pdf", f"Dirty image ({ARRAY_LABEL[a_name]})",
                         cmap='inferno', unit="mJy/beam")
                save_map(dbeam.imarr() / b0, f"{dirs['pdf_midpoint']}/dirty_beam_{a_tag}.pdf",
                         f"Dirty beam ({ARRAY_LABEL[a_name]})", cmap='RdBu_r', vmin=-0.5, vmax=0.5, unit="normalised", scale=1.0)
                save_map(cb.imarr() / cb.imarr().max(), f"{dirs['pdf_midpoint']}/clean_beam_{a_tag}.pdf",
                         f"Clean beam ({ARRAY_LABEL[a_name]})", cmap='inferno', unit="normalised", scale=1.0)
                save_map(restored[a_name].imarr(), f"{dirs['pdf_midpoint']}/restored_image_{a_tag}.pdf",
                         f"Restored image ({ARRAY_LABEL[a_name]})", beam=beams[a_name], vmin=0, vmax=vmax_mJy)

        r_e, r_c = df.iloc[0], df.iloc[1]
        elapsed = (time.time() - t_run) / 3600
        log(f"   day {day:02d}/{n_days} | S = {truth.total_flux():.2f} Jy | NXCORR EVN (no SKA) {r_e['nxcorr']:.3f}, "
            f"EVN+AVN+SKA-Mid {r_c['nxcorr']:.3f} | {time.time() - t_day:.0f} s | elapsed {elapsed:.2f} h")
        del obs
        gc.collect()
        offset += 1

    # ---- GIFs
    if HAS_IMAGEIO:
        for sub, name in [("frames", "Animation"), ("frames_model", "Animation_Model"),
                          ("frames_EVN", "Animation_EVN"), ("frames_EVN_AVN", "Animation_EVN_AVN")]:
            files = sorted(glob.glob(f"{dirs[sub]}/f_*.png"))
            if files:
                imgs = [imageio.imread(f) for f in files]
                shape = imgs[0].shape                       # bbox_inches='tight' can change the size by a pixel
                imgs = [im[:shape[0], :shape[1]] for im in imgs if im.shape[0] >= shape[0] and im.shape[1] >= shape[1]]
                imageio.mimsave(f"{run_dir}/{name}_{fac_name}_Scenario_{sc_key}.gif", imgs, fps=10)
    else:
        log("   [!] imageio not installed: GIFs not created")
    if day >= n_days:
        open(done_flag, 'w').write(datetime.datetime.now().isoformat())
    log(f"== {fac_name} / Scenario {sc_key} finished in {(time.time() - t_run) / 3600:.2f} h")


# =============================================================================================================
# 8. CAMPAIGN-WIDE SUMMARY (built from the CSV files, so separate processes can be merged)
# =============================================================================================================
def build_summary(out_dir):
    files = sorted(glob.glob(f"{out_dir}/*/Scenario_*/metrics_per_day.csv"))
    if not files:
        log("No metrics files found: nothing to summarise."); return
    df = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
    sum_dir = f"{out_dir}/global_summary"
    os.makedirs(sum_dir, exist_ok=True)
    df.to_csv(f"{sum_dir}/all_metrics_per_day.csv", index=False)
    scen = sorted(df['scenario'].unique())
    facs = sorted(df['factor'].unique())

    def styled(ax, sub, col):
        for fac in facs:
            for a_name, ls in (("EVN", '-'), ("EVN+AVN", '--')):
                d = sub[(sub['factor'] == fac) & (sub['array'] == a_name)].sort_values('day')
                if len(d):
                    ax.plot(d['day'], d[col], ls, lw=1.8, marker='o', ms=3, color=FACTOR_COLORS.get(fac, 'k'),
                            label=f"{ARRAY_LABEL[a_name]} ({fac.split('_', 1)[-1]})")

    plots = [("01_global_chi2_cphase", "chi2_cphase", r"Final closure-phase $\chi^2$", True),
             ("02_global_chi2_amp", "chi2_amp", r"Final amplitude $\chi^2$", True),
             ("04_global_rmse", "rmse_mJy_px", "RMSE [mJy/pixel]", False),
             ("05_global_nxcorr", "nxcorr", "NXCORR (vs truth)", False),
             ("05b_global_nxcorr_blurred_truth", "nxcorr_blurred_truth", "NXCORR (vs truth at the same resolution)", False),
             ("06_global_dynamic_range", "dynamic_range", "Dynamic range", True),
             ("08_global_flux_ratio", "flux_ratio", "Recovered / true flux", False)]
    for fname, col, ylabel, logy in plots:
        fig, axes = plt.subplots(1, len(scen), figsize=(8 * len(scen), 5.5), sharey=True, squeeze=False)
        for ax, s in zip(axes[0], scen):
            styled(ax, df[df['scenario'] == s], col)
            ax.set_title(f"Scenario {s}: {SCENARIOS.get(s, {}).get('label', s)}"); ax.set_xlabel("Observing day")
            if logy:
                ax.set_yscale('log')
        axes[0, 0].set_ylabel(ylabel)
        axes[0, -1].legend(bbox_to_anchor=(1.02, 1), loc='upper left')
        plt.tight_layout()
        for ext in ('pdf', 'png'):
            fig.savefig(f"{sum_dir}/{fname}.{ext}", bbox_inches='tight', dpi=130)
        plt.close(fig)

    # Pareto: fidelity vs dynamic range
    fig, axes = plt.subplots(1, len(scen), figsize=(7.5 * len(scen), 5.5), sharey=True, squeeze=False)
    for ax, s in zip(axes[0], scen):
        for fac in facs:
            for a_name, mk in (("EVN", 'o'), ("EVN+AVN", 's')):
                d = df[(df['scenario'] == s) & (df['factor'] == fac) & (df['array'] == a_name)]
                ax.scatter(d['dynamic_range'], d['nxcorr'], color=FACTOR_COLORS.get(fac, 'k'), marker=mk, alpha=0.7,
                           edgecolor='k' if mk == 's' else 'none', label=f"{ARRAY_LABEL[a_name]} ({fac.split('_', 1)[-1]})")
        ax.set_xscale('log'); ax.set_xlabel("Dynamic range"); ax.set_title(f"Scenario {s}")
    axes[0, 0].set_ylabel("NXCORR (vs truth)")
    axes[0, -1].legend(bbox_to_anchor=(1.02, 1), loc='upper left')
    plt.tight_layout()
    for ext in ('pdf', 'png'):
        fig.savefig(f"{sum_dir}/03_pareto_scatter.{ext}", bbox_inches='tight', dpi=130)
    plt.close(fig)

    # Triple plot (one row per scenario)
    fig, axes = plt.subplots(len(scen), 3, figsize=(18, 4.8 * len(scen)), squeeze=False, sharex=True)
    for r, s in enumerate(scen):
        sub = df[df['scenario'] == s]
        for c, (col, title, logy) in enumerate([("rmse_mJy_px", "RMSE [mJy/pixel]", False),
                                                ("nxcorr", "NXCORR", False), ("dynamic_range", "Dynamic range", True)]):
            styled(axes[r, c], sub, col)
            axes[r, c].set_title(f"Scenario {s}: {title}")
            if logy:
                axes[r, c].set_yscale('log')
    for ax in axes[-1]:
        ax.set_xlabel("Observing day")
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc='upper center', bbox_to_anchor=(0.5, 1.04), ncol=6, frameon=True)
    plt.tight_layout()
    for ext in ('pdf', 'png'):
        fig.savefig(f"{sum_dir}/07_global_triple_metrics.{ext}", bbox_inches='tight', dpi=130)
    plt.close(fig)

    # Summary table: mean +- std over the days
    cols = ["rmse_mJy_px", "nrmse", "nxcorr", "nxcorr_blurred_truth", "ssim", "dynamic_range", "flux_ratio",
            "chi2_cphase", "chi2_amp", "seconds"]
    g = df.groupby(['factor', 'scenario', 'array'])
    tab = g[cols].agg(['mean', 'std'])
    tab.columns = [f"{a}_{b}" for a, b in tab.columns]
    tab['n_days'] = g['day'].nunique()
    tab['failed_days'] = g['imaging_failed'].sum()
    tab.round(4).to_csv(f"{sum_dir}/summary_table.csv")
    with open(f"{sum_dir}/summary_table.md", 'w') as f:
        f.write("| factor | scenario | array | days | RMSE [mJy/px] | NXCORR | NXCORR (same res.) | dynamic range | flux ratio |\n")
        f.write("|---|---|---|---|---|---|---|---|---|\n")
        for (fac, s, a), r in tab.iterrows():
            f.write(f"| {fac} | {s} | {a} | {int(r['n_days'])} | {r['rmse_mJy_px_mean']:.3f} ± {r['rmse_mJy_px_std']:.3f} | "
                    f"{r['nxcorr_mean']:.3f} ± {r['nxcorr_std']:.3f} | {r['nxcorr_blurred_truth_mean']:.3f} ± "
                    f"{r['nxcorr_blurred_truth_std']:.3f} | {r['dynamic_range_mean']:.0f} ± {r['dynamic_range_std']:.0f} | "
                    f"{r['flux_ratio_mean']:.3f} ± {r['flux_ratio_std']:.3f} |\n")
    log(f"Summary written in '{sum_dir}/' ({len(df)} rows from {len(files)} runs)")


# =============================================================================================================
# 9. MAIN
# =============================================================================================================
def main():
    global LOG_FILE, SYS_NOISE
    p = argparse.ArgumentParser(description=__doc__.split("Usage")[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--scenarios', nargs='+', default=list(SCENARIOS), choices=list(SCENARIOS))
    p.add_argument('--factors', nargs='+', default=list(FACTORS), choices=list(FACTORS))
    p.add_argument('--days', type=int, default=N_DAYS_DEFAULT, help="number of observing days (default 43)")
    p.add_argument('--ttype', default='auto', choices=['auto', 'nfft', 'fast', 'direct'],
                   help="Fourier transform: 'auto' = nfft if pynfft is installed, otherwise fast")
    p.add_argument('--out', default='binary_jet_campaign_results', help="output folder (shared by parallel runs)")
    p.add_argument('--overwrite', action='store_true', help="redo the selected runs from day 1")
    p.add_argument('--save-txt', action='store_true', help="also save the observations as ehtim .txt files")
    p.add_argument('--summary-only', action='store_true', help="only rebuild the global summary from the CSV files")
    p.add_argument('--maxit', type=int, nargs=3, default=[r['maxit'] for r in IMAGING_ROUNDS], metavar=('R1', 'R2', 'R3'),
                   help="iterations of the three imaging rounds (default 150 150 200; 50 50 80 is ~2x faster but "
                        "stops far from convergence)")
    p.add_argument('--sys-noise', type=float, default=SYS_NOISE,
                   help="fractional systematic error added to sigma for imaging (default 0.02; 0 disables it)")
    a = p.parse_args()

    os.makedirs(a.out, exist_ok=True)
    LOG_FILE = f"{a.out}/run_log.txt"
    if a.summary_only:
        build_summary(a.out); return

    SYS_NOISE = a.sys_noise
    for rnd, m in zip(IMAGING_ROUNDS, a.maxit):
        rnd['maxit'] = m
    ttype = resolve_ttype(a.ttype)
    log("=" * 100)
    log(f"Binary-jet VLBI campaign | scenarios {a.scenarios} | factors {a.factors} | {a.days} days | ttype '{ttype}' "
        f"| output '{a.out}/' | maxit {a.maxit} | sys. noise {SYS_NOISE:g}")
    if not HAS_SSIM:
        log("[!] scikit-image not installed: SSIM will be NaN")
    os.makedirs(f"{a.out}/arrays", exist_ok=True)
    write_array_file(f"{a.out}/arrays/evn_array.txt", EVN_STATIONS)
    write_array_file(f"{a.out}/arrays/evn_avn_array.txt", EVN_STATIONS + AVN_STATIONS)
    arrays = {"EVN": eh.array.load_txt(f"{a.out}/arrays/evn_array.txt"),
              "EVN+AVN": eh.array.load_txt(f"{a.out}/arrays/evn_avn_array.txt")}
    with open(f"{a.out}/config_{datetime.datetime.now():%Y%m%d_%H%M%S}.json", 'w') as f:
        json.dump({"args": vars(a), "ttype": ttype, "scenarios": SCENARIOS, "factors": FACTORS,
                   "imaging_rounds": IMAGING_ROUNDS, "RF_HZ": RF_HZ, "BW_HZ": BW_HZ, "TINT_S": TINT_S, "TADV_S": TADV_S,
                   "ELEVMIN": ELEVMIN, "WINDOW_HOURS": WINDOW_HOURS, "MJD_START": MJD_START, "NPIX": NPIX,
                   "OBSERVATION_FOV_uas": OBSERVATION_FOV, "PRIOR_FWHM_FRAC": PRIOR_FWHM_FRAC,
                   "PREV_INIT_BLUR": PREV_INIT_BLUR, "RESTORE_BLUR": RESTORE_BLUR, "SYS_NOISE": SYS_NOISE,
                   "PRIOR_PERTURB": PRIOR_PERTURB}, f, indent=2, default=str)

    t0 = time.time()
    for fac_key in a.factors:
        fac_name, factor = FACTORS[fac_key]
        for sc_key in a.scenarios:
            run_combination(a.out, fac_name, factor, sc_key, a.days, ttype, arrays,
                            overwrite=a.overwrite, save_txt=a.save_txt)
    build_summary(a.out)
    log(f"ALL DONE in {(time.time() - t0) / 3600:.2f} h. Results in '{a.out}/'.")


if __name__ == '__main__':
    main()
