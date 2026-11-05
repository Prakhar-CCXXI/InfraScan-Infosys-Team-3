"""Unit tests for the pure-Python parts (no torch / ultralytics needed).  Run: python -m pytest -q ml/hybrid"""
import sys
from pathlib import Path
import cv2, numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from geometry import crack_geometry
from hybrid_pipeline import expand_box, fuse, merge_boxes, region_from_boxes
from prepare_yolo_dataset import iou, mask_to_polygons, polygons_to_mask, to_yolo_lines


def test_geometry_exact_strips():
    for w in (3, 5, 9):
        m = np.zeros((200, 200), np.uint8); m[100 - w // 2:100 - w // 2 + w, 20:120] = 1
        g = crack_geometry(m)
        assert abs(g["mean_width_px"] - w) < 0.5 and abs(g["max_width_px"] - w) < 0.5 and 90 < g["length_px"] < 101
        assert g["orientation_deg"] < 1 or g["orientation_deg"] > 179
        assert g["unit"] == "px" and "length_mm" not in g


def test_geometry_diagonal_length_and_scale():
    m = np.zeros((200, 200), np.uint8); cv2.line(m, (20, 20), (120, 120), 1, 1)
    g = crack_geometry(m, mm_per_px=0.5)
    assert abs(g["length_px"] - 141.4) < 3 and abs(g["length_mm"] - 0.5 * g["length_px"]) < 1e-6
    assert crack_geometry(np.zeros((8, 8)))["area_px"] == 0


def test_fusion_is_not_a_plain_or():
    prob = np.zeros((60, 60), np.float32); prob[10:12, 10:30] = 0.6; prob[40:42, 10:30] = 0.95
    reg = region_from_boxes([(8, 8, 32, 14)], (60, 60), 0)
    assert fuse(prob, reg, 0.5, None).sum() == 40          # nothing outside the YOLO region
    assert fuse(prob, reg, 0.5, 0.9).sum() == 80           # confident U-Net pixels outside survive
    assert fuse(prob, reg, 0.7, None).sum() == 0           # YOLO never adds pixels U-Net does not support


def test_boxes():
    assert merge_boxes([(0, 0, 10, 10), (8, 8, 20, 20), (100, 100, 120, 120)]) == [(0, 0, 20, 20), (100, 100, 120, 120)] or \
           sorted(merge_boxes([(0, 0, 10, 10), (8, 8, 20, 20), (100, 100, 120, 120)])) == [(0, 0, 20, 20), (100, 100, 120, 120)]
    assert expand_box((5, 5, 30, 30), 16, 100, 100) == (0, 0, 46, 46)


def test_label_conversion_valid_and_faithful():
    m = np.zeros((360, 640), np.uint8); cv2.polylines(m, [np.array([(30, 40), (200, 120), (400, 100), (600, 300)])], False, 1, 3)
    polys, _ = mask_to_polygons(m)
    assert iou(polygons_to_mask(polys, m.shape), m) > 0.9
    for line in to_yolo_lines(polys, 640, 360):
        v = line.split(); c = np.array(v[1:], float)
        assert v[0] == "0" and len(c) >= 6 and len(c) % 2 == 0 and c.min() >= 0 and c.max() <= 1
    line = np.zeros((50, 50), np.uint8); line[25, 5:45] = 1
    assert len(mask_to_polygons(line)[0]) == 1               # 1-px line survives as a valid polygon
