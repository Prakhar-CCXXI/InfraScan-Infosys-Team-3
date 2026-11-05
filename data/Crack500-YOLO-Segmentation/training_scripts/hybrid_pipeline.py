"""
Hybrid crack pipeline = YOLO11n-Seg (where are cracks: boxes + coarse masks) + U-Net/ResNet34 (fine pixel masks).

Fusion rule (NOT a plain OR of masks). With U-Net probability P and a YOLO-derived region R:
    hybrid = (P >= t_in) inside R   OR   (P >= t_out) outside R        (t_out = None -> nothing outside R)
R = union of YOLO boxes expanded by `margin` px (gate="box") or YOLO masks dilated by `margin` px (gate="mask").
YOLO therefore only *gates* U-Net; it never adds pixels that U-Net did not support.
If t_out is None the U-Net runs only on the (merged) ROI crops, which is faster; otherwise on the full image.
If YOLO finds nothing: empty mask when t_out is None, else only very confident U-Net pixels (P >= t_out) survive.
"""
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import cv2
import numpy as np

MEAN = np.array([0.485, 0.456, 0.406], np.float32)   # same normalisation as train_seg.py
STD = np.array([0.229, 0.224, 0.225], np.float32)


@dataclass
class HybridConfig:
    yolo_conf: float = 0.25
    gate: str = "box"            # "box" | "mask"
    margin: int = 16
    t_in: float = 0.4
    t_out: float | None = None
    yolo_imgsz: int = 640
    min_roi: int = 96            # minimum ROI crop side (px) for U-Net context

    def save(self, path):
        Path(path).write_text(json.dumps(asdict(self), indent=2))

    @staticmethod
    def load(path, key=None):
        d = json.loads(Path(path).read_text())
        return HybridConfig(**(d[key]["config"] if key else d))


# ----------------------------- pure numpy helpers (no torch needed) -----------------------------
def expand_box(b, margin, W, H, min_size=0):
    x0, y0, x1, y1 = [float(v) for v in b]
    x0, y0, x1, y1 = x0 - margin, y0 - margin, x1 + margin, y1 + margin
    if min_size:
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        hw, hh = max(x1 - x0, min_size) / 2, max(y1 - y0, min_size) / 2
        x0, y0, x1, y1 = cx - hw, cy - hh, cx + hw, cy + hh
    return (int(max(0, np.floor(x0))), int(max(0, np.floor(y0))), int(min(W, np.ceil(x1))), int(min(H, np.ceil(y1))))


def merge_boxes(boxes):
    """Merge overlapping/touching integer boxes until stable (so no pixel is processed twice)."""
    boxes = [list(b) for b in boxes]
    changed = True
    while changed:
        changed, out = False, []
        while boxes:
            a = boxes.pop()
            for b in boxes:
                if a[0] <= b[2] and b[0] <= a[2] and a[1] <= b[3] and b[1] <= a[3]:
                    b[:] = [min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])]
                    changed = True
                    break
            else:
                out.append(a)
        boxes = out
    return [tuple(b) for b in boxes]


def region_from_boxes(boxes, shape, margin):
    H, W = shape
    reg = np.zeros(shape, bool)
    for b in boxes:
        x0, y0, x1, y1 = expand_box(b, margin, W, H)
        reg[y0:y1, x0:x1] = True
    return reg


def region_from_masks(masks, shape, margin):
    if len(masks) == 0:
        return np.zeros(shape, bool)
    u = (np.max(masks, 0) > 0).astype(np.uint8)
    if margin > 0:
        u = cv2.dilate(u, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * margin + 1, 2 * margin + 1)))
    return u > 0


def make_region(cfg, boxes, masks, shape):
    return region_from_boxes(boxes, shape, cfg.margin) if cfg.gate == "box" else region_from_masks(masks, shape, cfg.margin)


def fuse(prob, region, t_in, t_out=None):
    m = (prob >= t_in) & region
    if t_out is not None:
        m |= (prob >= t_out) & ~region
    return m.astype(np.uint8)


def overlay(bgr, mask, color, alpha=0.55):
    out = bgr.copy()
    sel = mask > 0
    out[sel] = ((1 - alpha) * out[sel] + alpha * np.array(color, np.float32)).astype(np.uint8)
    return out


def render_panel(bgr, res, gt=None, unet_mask=None, width=480):
    """original | YOLO boxes+mask | U-Net mask | hybrid mask | ground truth (optional)."""
    H, W = bgr.shape[:2]
    y = overlay(bgr, res["yolo_mask"], (0, 0, 255))
    for b in res["boxes"]:
        x0, y0, x1, y1 = [int(v) for v in b["xyxy"]]
        cv2.rectangle(y, (x0, y0), (x1, y1), (0, 255, 255), 2)
        cv2.putText(y, f"{b['conf']:.2f}", (x0, max(12, y0 - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
    tiles = [("original", bgr), ("YOLO boxes + mask", y)]
    if unet_mask is not None:
        tiles.append(("U-Net mask", overlay(bgr, unet_mask, (255, 128, 0))))
    tiles.append((f"hybrid ({res['mode']})", overlay(bgr, res["hybrid_mask"], (0, 255, 0))))
    if gt is not None:
        tiles.append(("ground truth", overlay(bgr, gt, (255, 0, 255))))
    s = width / float(W)
    outs = []
    for name, t in tiles:
        t = cv2.resize(t, (width, int(H * s)), interpolation=cv2.INTER_AREA)
        cv2.rectangle(t, (0, 0), (width, 18), (0, 0, 0), -1)
        cv2.putText(t, name, (4, 13), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
        outs.append(t)
    return np.hstack(outs)


# ----------------------------- model-backed pipeline -----------------------------
class HybridCrackPipeline:
    def __init__(self, yolo_ckpt, unet_ckpt, device=None, encoder="resnet34", cfg: HybridConfig | None = None):
        import segmentation_models_pytorch as smp
        import torch
        from ultralytics import YOLO

        self.torch = torch
        self.device = torch.device(device or ("cuda" if torch.cuda.is_available() else "cpu"))
        self._ydev = 0 if self.device.type == "cuda" else "cpu"
        self.yolo = YOLO(str(yolo_ckpt))
        self.unet = smp.Unet(encoder_name=encoder, encoder_weights=None, in_channels=3, classes=1)
        self.unet.load_state_dict(torch.load(str(unet_ckpt), map_location=self.device))
        self.unet.to(self.device).eval()
        self.cfg = cfg or HybridConfig()

    def sync(self):
        if self.device.type == "cuda":
            self.torch.cuda.synchronize()

    # --- YOLO ---
    def yolo_detect(self, bgr, conf=None):
        """-> boxes (n,4 xyxy, original px), confs (n,), masks (n,H,W uint8, original size)."""
        H, W = bgr.shape[:2]
        conf = self.cfg.yolo_conf if conf is None else conf
        r = self.yolo.predict(bgr, imgsz=self.cfg.yolo_imgsz, conf=conf, retina_masks=True,
                              device=self._ydev, verbose=False)[0]
        if r.masks is None or r.boxes is None or len(r.boxes) == 0:
            return np.zeros((0, 4), np.float32), np.zeros(0, np.float32), np.zeros((0, H, W), np.uint8)
        boxes = r.boxes.xyxy.cpu().numpy().astype(np.float32)
        confs = r.boxes.conf.cpu().numpy().astype(np.float32)
        masks = (r.masks.data.cpu().numpy() > 0.5).astype(np.uint8)
        if masks.shape[1:] != (H, W):   # safety: bring masks to original size
            masks = np.stack([cv2.resize(mm, (W, H), interpolation=cv2.INTER_NEAREST) for mm in masks])
        return boxes, confs, masks

    # --- U-Net (identical pre-processing / padding / tiling logic as train_seg.py, fp32) ---
    def _pad_run(self, x):
        F = self.torch.nn.functional
        H, W = x.shape[-2:]
        ph, pw = (32 - H % 32) % 32, (32 - W % 32) % 32
        if ph or pw:
            x = F.pad(x, (0, pw, 0, ph), mode="reflect" if (ph < H and pw < W) else "replicate")
        return self.torch.sigmoid(self.unet(x).float())[..., :H, :W]

    def _unet_run(self, rgb):
        t = self.torch
        x = t.from_numpy(((rgb.astype(np.float32) / 255.0 - MEAN) / STD).transpose(2, 0, 1).copy()).unsqueeze(0).to(self.device)
        H, W = x.shape[-2:]
        with t.no_grad():
            if max(H, W) <= 1024:
                p = self._pad_run(x)
            else:
                tile, stride = 768, 512
                th, tw = min(tile, H), min(tile, W)
                ys = sorted(set(list(range(0, H - th + 1, stride)) + [H - th]))
                xs = sorted(set(list(range(0, W - tw + 1, stride)) + [W - tw]))
                acc, cnt = t.zeros(1, 1, H, W, device=self.device), t.zeros(1, 1, H, W, device=self.device)
                for y0 in ys:
                    for x0 in xs:
                        acc[..., y0:y0 + th, x0:x0 + tw] += self._pad_run(x[..., y0:y0 + th, x0:x0 + tw])
                        cnt[..., y0:y0 + th, x0:x0 + tw] += 1
                p = acc / cnt
        return p[0, 0].cpu().numpy()

    def unet_prob(self, rgb):
        return self._unet_run(rgb)

    def unet_prob_rois(self, rgb, rois):
        """U-Net on ROI crops only; probabilities are pasted back at the ORIGINAL image coordinates (zeros elsewhere)."""
        canvas = np.zeros(rgb.shape[:2], np.float32)
        for x0, y0, x1, y1 in rois:
            canvas[y0:y1, x0:x1] = self._unet_run(np.ascontiguousarray(rgb[y0:y1, x0:x1]))
        return canvas

    # --- full hybrid ---
    def predict(self, bgr, cfg: HybridConfig | None = None, measure=True):
        from geometry import crack_geometry   # local import keeps module usable without skimage for helpers

        cfg = cfg or self.cfg
        H, W = bgr.shape[:2]
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        T = {}
        self.sync(); t0 = time.perf_counter()
        boxes, confs, masks = self.yolo_detect(bgr, cfg.yolo_conf)
        self.sync(); T["yolo_ms"] = 1000 * (time.perf_counter() - t0)
        yolo_mask = (np.max(masks, 0) if len(masks) else np.zeros((H, W), np.uint8)).astype(np.uint8)

        t1 = time.perf_counter(); prob = None
        if len(boxes) == 0:
            if cfg.t_out is None:
                mode, hybrid = "no_detection_empty", np.zeros((H, W), np.uint8)
            else:
                mode = "no_detection_strict_unet"
                prob = self.unet_prob(rgb); hybrid = (prob >= cfg.t_out).astype(np.uint8)
        else:
            region = make_region(cfg, boxes, masks, (H, W))
            if cfg.t_out is None:
                rois = merge_boxes([expand_box(b, cfg.margin, W, H, cfg.min_roi) for b in boxes])
                prob, mode = self.unet_prob_rois(rgb, rois), "roi_crops"
            else:
                prob, mode = self.unet_prob(rgb), "full_image_dual_threshold"
            hybrid = fuse(prob, region, cfg.t_in, cfg.t_out)
        self.sync(); T["unet_fuse_ms"] = 1000 * (time.perf_counter() - t1); T["total_ms"] = T["yolo_ms"] + T["unet_fuse_ms"]

        res = dict(mode=mode, image_size=dict(width=W, height=H), yolo_detected=bool(len(boxes)),
                   boxes=[dict(xyxy=[float(v) for v in b], conf=float(c)) for b, c in zip(boxes, confs)],
                   yolo_mask=yolo_mask, hybrid_mask=hybrid, hybrid_prob=prob, timing_ms=T, config=asdict(cfg))
        if measure:
            res["measurements"] = crack_geometry(hybrid)
        return res
