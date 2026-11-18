"""
Grad-CAM / Grad-CAM++ for the InfraScan classifier (ConvNeXt-Tiny etc.) and the U-Net segmentation model.

The CAM arithmetic (compute_cam, upsample_cam, overlay_heatmap) is pure numpy and unit-tested. The hook code (GradCAM,
explain_classifier, explain_segmentation) needs torch and has NOT been run in the authoring environment: smoke-test it on 3 images first.

  classifier   : target = the crack logit;                    layer = model.features[-1] (torchvision ConvNeXt-Tiny)
  segmentation : target = sum of logits inside the mask;      layer = model.encoder.layer4 (smp U-Net / ResNet34); coarse (stride 32)
A CAM shows where the model looked; it is not a proof of why, and it is coarse for thin cracks.
"""
from __future__ import annotations

import cv2
import numpy as np

IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], np.float32)
IMAGENET_STD = np.array([0.229, 0.224, 0.225], np.float32)


# ------------------------------------------------ pure numpy ------------------------------------------------
def compute_cam(acts: np.ndarray, grads: np.ndarray, plus: bool = False) -> np.ndarray:
    """acts, grads: (C, h, w) -> CAM (h, w) in [0, 1]. All-zero when nothing contributes (never NaN)."""
    acts, grads = acts.astype(np.float64), grads.astype(np.float64)
    if plus:   # Grad-CAM++ (Chattopadhay et al. 2018), exponential-score closed form
        g2, g3 = grads ** 2, grads ** 3
        denom = 2 * g2 + acts.sum((1, 2), keepdims=True) * g3
        alpha = g2 / np.where(denom != 0, denom, 1e-7)
        w = (alpha * np.maximum(grads, 0)).sum((1, 2))
    else:
        w = grads.mean((1, 2))
    cam = np.maximum((w[:, None, None] * acts).sum(0), 0)
    m = cam.max()
    return (cam / m).astype(np.float32) if m > 0 else np.zeros_like(cam, np.float32)


def upsample_cam(cam: np.ndarray, size_wh) -> np.ndarray:
    c = cv2.resize(cam, tuple(size_wh), interpolation=cv2.INTER_LINEAR)
    c = np.clip(c, 0, None); m = c.max()
    return (c / m).astype(np.float32) if m > 0 else c.astype(np.float32)


def overlay_heatmap(bgr: np.ndarray, cam01: np.ndarray, alpha: float = 0.4) -> np.ndarray:
    heat = cv2.applyColorMap((np.clip(cam01, 0, 1) * 255).astype(np.uint8), cv2.COLORMAP_JET)
    return cv2.addWeighted(bgr, 1 - alpha, heat, alpha, 0)


# ------------------------------------------------ torch hooks ------------------------------------------------
class GradCAM:
    def __init__(self, model, layer, plus: bool = False):
        self.model, self.plus, self.acts, self.grads = model, plus, None, None
        layer.register_forward_hook(self._fwd)

    def _fwd(self, module, inp, out):
        self.acts = out.detach()
        out.register_hook(lambda g: setattr(self, "grads", g.detach()))

    def __call__(self, x, score_fn):
        """x: (1,3,H,W) tensor; score_fn(model_output) -> scalar tensor. Returns the CAM at the layer resolution."""
        import torch
        self.model.zero_grad(set_to_none=True)
        with torch.enable_grad():
            out = self.model(x)
            score = score_fn(out)
            score.backward()
        return compute_cam(self.acts[0].float().cpu().numpy(), self.grads[0].float().cpu().numpy(), self.plus), out.detach()


def explain_classifier(model, rgb_uint8, device, size: int = 256, layer=None, plus: bool = False):
    """Returns (crack probability, CAM upsampled to the original image size, overlay BGR). Preprocessing = Resize(size) + ImageNet normalisation."""
    import torch
    model.eval().to(device)
    h, w = rgb_uint8.shape[:2]
    x = cv2.resize(rgb_uint8, (size, size), interpolation=cv2.INTER_LINEAR)
    x = torch.from_numpy(((x.astype(np.float32) / 255 - IMAGENET_MEAN) / IMAGENET_STD).transpose(2, 0, 1).copy())[None].to(device)
    cam, out = GradCAM(model, layer if layer is not None else model.features[-1], plus)(x, lambda o: o.reshape(-1)[0])
    prob = float(torch.sigmoid(out.reshape(-1)[0]).cpu())
    cam_full = upsample_cam(cam, (w, h))
    return prob, cam_full, overlay_heatmap(cv2.cvtColor(rgb_uint8, cv2.COLOR_RGB2BGR), cam_full)


def explain_segmentation(model, rgb_uint8, device, thr: float = 0.4, mask=None, layer=None, plus: bool = False):
    """CAM for 'why this crack mask': score = sum of logits over the mask (the predicted mask at `thr` unless one is given). Image sides must allow padding to /32."""
    import torch
    import torch.nn.functional as F
    model.eval().to(device)
    h, w = rgb_uint8.shape[:2]
    x = torch.from_numpy(((rgb_uint8.astype(np.float32) / 255 - IMAGENET_MEAN) / IMAGENET_STD).transpose(2, 0, 1).copy())[None].to(device)
    ph, pw = (32 - h % 32) % 32, (32 - w % 32) % 32
    xp = F.pad(x, (0, pw, 0, ph), mode="reflect" if (ph < h and pw < w) else "replicate")
    if mask is None:
        with torch.no_grad():
            mask = (torch.sigmoid(model(xp))[0, 0, :h, :w] >= thr).cpu().numpy()
    m = torch.zeros(xp.shape[-2:], device=device); m[:h, :w] = torch.from_numpy(np.asarray(mask > 0, np.float32)).to(device)
    if float(m.sum()) == 0:
        return np.zeros((h, w), np.float32), cv2.cvtColor(rgb_uint8, cv2.COLOR_RGB2BGR)
    cam, _ = GradCAM(model, layer if layer is not None else model.encoder.layer4, plus)(xp, lambda o: (o[0, 0] * m).sum())
    cam_full = upsample_cam(cam, (xp.shape[-1], xp.shape[-2]))[:h, :w]
    return cam_full, overlay_heatmap(cv2.cvtColor(rgb_uint8, cv2.COLOR_RGB2BGR), cam_full)
