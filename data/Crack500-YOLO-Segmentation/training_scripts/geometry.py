"""
Pixel-based crack geometry from a binary mask. NO physical units unless a scale (mm per pixel) is supplied.
Length: skeleton path length (orthogonal steps = 1, diagonal steps = sqrt2). Width: (2 x distance-to-boundary - 1) sampled on the skeleton (mean and max).
Orientation: principal axis of skeleton pixels, degrees in [0, 180) from the image x-axis (counter-clockwise as displayed).
"""
import numpy as np


def crack_geometry(mask, mm_per_px=None):
    from scipy.ndimage import convolve, distance_transform_edt, label
    from skimage.morphology import skeletonize

    m = np.asarray(mask) > 0
    H, W = m.shape
    area = int(m.sum())
    out = dict(unit="px", area_px=area, crack_density_percent=100.0 * area / float(H * W), length_px=0.0,
               mean_width_px=0.0, max_width_px=0.0, orientation_deg=None, n_components=0, n_branch_points=0, n_endpoints=0)
    if area == 0:
        return _scaled(out, mm_per_px)
    sk = skeletonize(m)
    s = sk.astype(np.uint8)
    orth = int((s[:, 1:] & s[:, :-1]).sum() + (s[1:, :] & s[:-1, :]).sum())
    diag = int((s[1:, 1:] & s[:-1, :-1]).sum() + (s[1:, :-1] & s[:-1, 1:]).sum())
    length = orth + np.sqrt(2.0) * diag if (orth + diag) else float(s.sum())
    dist = distance_transform_edt(m)
    nb = convolve(s, np.ones((3, 3), np.uint8), mode="constant") - s
    ys, xs = np.nonzero(sk)
    ang = None
    if len(xs) >= 2:
        pts = np.stack([xs, -ys], 1).astype(np.float64)
        pts -= pts.mean(0)
        vx, vy = np.linalg.eigh(np.cov(pts.T))[1][:, -1]
        ang = float(np.degrees(np.arctan2(vy, vx)) % 180.0)
    w = np.maximum(2.0 * dist[sk] - 1.0, 1.0)   # local width on the skeleton (exact for a straight strip of integer width)
    out.update(length_px=float(length), mean_width_px=float(w.mean()),
               max_width_px=float(w.max()), orientation_deg=ang,
               n_components=int(label(m, structure=np.ones((3, 3)))[1]),
               n_branch_points=int(((nb >= 3) & (s == 1)).sum()), n_endpoints=int(((nb == 1) & (s == 1)).sum()))
    return _scaled(out, mm_per_px)


def _scaled(d, mm_per_px):
    if mm_per_px:   # only when a trusted calibration is provided
        d.update(unit="mm", length_mm=d["length_px"] * mm_per_px, mean_width_mm=d["mean_width_px"] * mm_per_px,
                 max_width_mm=d["max_width_px"] * mm_per_px, area_mm2=d["area_px"] * mm_per_px ** 2)
    return d
