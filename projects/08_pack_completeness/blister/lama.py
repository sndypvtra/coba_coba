"""LaMa inpainting on a crop (TorchScript big-lama from simple-lama-inpainting)."""
import cv2
import numpy as np
import torch

_M = None


def model(path):
    global _M
    if _M is None:
        _M = torch.jit.load(path, map_location="cpu").eval()
    return _M


def inpaint(path, img_bgr, mask):
    """img_bgr uint8 HxWx3, mask uint8 HxW (255 = fill). Returns uint8 BGR."""
    h, w = mask.shape
    ph, pw = (8 - h % 8) % 8, (8 - w % 8) % 8
    rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    rgb = np.pad(rgb, ((0, ph), (0, pw), (0, 0)), mode="reflect")
    mk = np.pad(mask, ((0, ph), (0, pw)), mode="reflect")
    t = torch.from_numpy(rgb).float().permute(2, 0, 1)[None] / 255.0
    m = torch.from_numpy((mk > 127).astype(np.float32))[None, None]
    with torch.no_grad():
        out = model(path)(t, m)[0]
    out = (out.permute(1, 2, 0) * 255).clamp(0, 255).numpy().astype(np.uint8)[:h, :w]
    return cv2.cvtColor(out, cv2.COLOR_RGB2BGR)
