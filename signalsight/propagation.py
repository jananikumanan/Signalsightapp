"""Log-distance path-loss model (100 m reference) with per-resource-element power.

Path loss
    d <= d0 (100 m) :  PL(d) = FSPL(d)                          free space close to the tower
    d  > d0         :  PL(d) = FSPL(d0) + 10 * n * log10(d / d0)
    FSPL(d) = 20 log10(f_MHz) + 20 log10(d_km) + 32.44   [dB]

Received power (RSRP-like)
    LTE RSRP is measured per resource element (one subcarrier), not on the whole carrier, so the total EIRP is
    first divided over the carrier's subcarriers:
        N_sc = 12 subcarriers x 5 resource blocks per MHz x BW_MHz = 60 x BW_MHz
        P_rx(d) = EIRP_dBm - 10 log10(N_sc) - PL(d)
    This keeps the -85 / -100 / -110 dBm thresholds (RSRP values) consistent with the transmit power.

This is a *mathematical prediction*: no terrain, buildings, antenna patterns or shadowing.
"""
from __future__ import annotations

import numpy as np

MIN_DIST_M = 10.0    # near-field clamp so the model never diverges at the tower
REF_DIST_M = 100.0   # reference distance d0 of the log-distance model


def fspl_db(dist_m, freq_mhz: float):
    """Free-space path loss for a distance in metres."""
    return 20.0 * np.log10(freq_mhz) + 20.0 * np.log10(np.asarray(dist_m, dtype=np.float64) / 1000.0) + 32.44


def re_offset_db(bw_mhz: float) -> float:
    """Loss from spreading total power over all subcarriers: 10*log10(60 * BW_MHz)."""
    return float(10.0 * np.log10(60.0 * bw_mhz))


def path_loss_db(dist_km, freq_mhz: float, n: float):
    d_m = np.maximum(np.asarray(dist_km, dtype=np.float64) * 1000.0, MIN_DIST_M)
    near = fspl_db(d_m, freq_mhz)
    far = fspl_db(REF_DIST_M, freq_mhz) + 10.0 * n * np.log10(d_m / REF_DIST_M)
    return np.where(d_m <= REF_DIST_M, near, far)


def rx_power_dbm(eirp_dbm: float, freq_mhz: float, n: float, dist_km, bw_mhz: float = 20.0):
    return eirp_dbm - re_offset_db(bw_mhz) - path_loss_db(dist_km, freq_mhz, n)


def radius_km(eirp_dbm: float, freq_mhz: float, n: float, threshold_dbm: float, bw_mhz: float = 20.0) -> float:
    """Distance at which the predicted signal falls to `threshold_dbm`."""
    allowed_pl = eirp_dbm - re_offset_db(bw_mhz) - threshold_dbm
    pl_ref = float(fspl_db(REF_DIST_M, freq_mhz))
    if allowed_pl <= pl_ref:   # inside the free-space segment
        d_m = 1000.0 * 10.0 ** ((allowed_pl - 20.0 * np.log10(freq_mhz) - 32.44) / 20.0)
    else:
        d_m = REF_DIST_M * 10.0 ** ((allowed_pl - pl_ref) / (10.0 * n))
    return 0.0 if d_m <= MIN_DIST_M else float(d_m / 1000.0)


def tower_radius_km(t, threshold_dbm: float) -> float:
    return radius_km(t.eirp_dbm, t.freq_mhz, t.path_loss_exp, threshold_dbm, t.bw_mhz)
