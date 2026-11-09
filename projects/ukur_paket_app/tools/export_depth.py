"""Exports the photo mode's depth model (UkurPaket 0.4.2): Depth Anything V2 Small, metric indoor (Apache-2.0),
fixed to an upright 280 x 378 picture, MatMul weights in int8 (36 MB instead of 99 MB, same accuracy here).

    pip install torch transformers onnx onnxruntime
    python tools/export_depth.py app/src/main/assets/depth

Input 'pixel_values' [1, 3, 378, 280]: the upright 3:4 picture resized to that size, RGB / 255, then ImageNet mean/std;
output 'depth' [1, 378, 280], metres along the optical axis.

Why this one (tools/photo/bench_depth_nyu.py: camera height above the floor, the photo mode's one AI number, on 93
upright portrait crops of NYUv2 test photos, Kinect depth as truth, after a per-model calibration):

    model                         median error  p90    PC ms   size
    YOLO26n-depth (0.4.0-0.4.1)   11,7 %        27 %   67      20 MB
    YOLO26l-depth                  7,5 %        17 %   215     106 MB
    DAv2-S metric indoor, int8     7,7 %        21 %   141     36 MB    <- this
    DAv2-S metric indoor, fp32     8,1 %        20 %   160     99 MB

Uncalibrated, it reads the camera 1,21x too high on those photos: the app's default scale is 1 / 1,21 until the phone
is calibrated.
"""
import sys
from pathlib import Path

import torch
from onnxruntime.quantization import QuantType, quantize_dynamic
from transformers import AutoModelForDepthEstimation

H, W = 378, 280


class Wrap(torch.nn.Module):
    def __init__(self, m):
        super().__init__(); self.m = m

    def forward(self, x):
        return self.m(pixel_values=x).predicted_depth


def main(out_dir):
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    m = AutoModelForDepthEstimation.from_pretrained("depth-anything/Depth-Anything-V2-Metric-Indoor-Small-hf").eval()
    fp32 = out / "dav2s-metric-indoor-378x280-fp32.onnx"
    torch.onnx.export(Wrap(m), torch.randn(1, 3, H, W), str(fp32), input_names=["pixel_values"], output_names=["depth"], opset_version=17)
    dst = out / "dav2s-metric-indoor-378x280-int8.onnx"
    quantize_dynamic(str(fp32), str(dst), weight_type=QuantType.QUInt8, op_types_to_quantize=["MatMul", "Gemm"])
    fp32.unlink()
    print(dst, dst.stat().st_size // 1024, "KB")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "app/src/main/assets/depth")
