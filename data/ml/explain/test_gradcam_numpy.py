"""Tests for the numpy part of gradcam.py (no torch).  Run: python ml/explain/test_gradcam_numpy.py"""
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from gradcam import compute_cam, overlay_heatmap, upsample_cam


def test_matches_definition():
    rng = np.random.RandomState(0); A, G = rng.rand(5, 8, 8), rng.randn(5, 8, 8) + 0.5       # mixed-sign gradients with a positive mean
    ref = np.maximum((G.mean((1, 2))[:, None, None] * A).sum(0), 0); assert ref.max() > 0; ref = ref / ref.max()
    assert np.allclose(compute_cam(A, G), ref, atol=1e-6) and 0 <= compute_cam(A, G).min() and compute_cam(A, G).max() == 1.0


def test_uniform_gradient_gives_channel_sum():
    A = np.random.RandomState(1).rand(4, 6, 6); cam = compute_cam(A, np.ones_like(A)); ref = A.sum(0) / A.sum(0).max()
    assert np.allclose(cam, ref, atol=1e-6)


def test_negative_gradients_give_zero_not_nan():
    A = np.random.RandomState(2).rand(3, 5, 5); cam = compute_cam(A, -np.ones_like(A)); assert (cam == 0).all() and not np.isnan(cam).any()
    assert not np.isnan(compute_cam(np.zeros((3, 5, 5)), np.zeros((3, 5, 5)), plus=True)).any()


def test_peak_location_both_variants():
    A = np.zeros((2, 10, 10)); A[0, 7, 3] = 1.0; A[1, 2, 8] = 0.2; G = np.zeros_like(A); G[0] = 1.0; G[1] = 0.1
    for plus in (False, True):
        cam = compute_cam(A, G, plus=plus); assert np.unravel_index(cam.argmax(), cam.shape) == (7, 3), plus


def test_upsample_and_overlay():
    cam = compute_cam(np.random.RandomState(3).rand(3, 4, 4), np.ones((3, 4, 4))); up = upsample_cam(cam, (64, 48))
    assert up.shape == (48, 64) and abs(up.max() - 1) < 1e-6
    ov = overlay_heatmap(np.zeros((48, 64, 3), np.uint8), up); assert ov.shape == (48, 64, 3) and ov.dtype == np.uint8


if __name__ == "__main__":
    for n in [n for n in dir() if n.startswith("test_")]: globals()[n](); print("PASS", n)
