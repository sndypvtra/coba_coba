"""MobileSAM at a 512 input for phones without a fast CPU (Urovo DT50/DT20): the same weights, a quarter of the work.

    python tools/export_sam512.py <mobile_sam.pt> <out_dir>

The image encoder (TinyViT) is rebuilt with img_size=512 and given MobileSAM's weights unchanged (its window attention
biases depend on the window size, not on the picture size), so it returns a 32 x 32 embedding instead of 64 x 64.
The prompt decoder gets the dense positional encoding of that 32 x 32 grid and takes coordinates in the 512 frame;
its masks come out 128 x 128. Both stay float32: on ARM cores without native float16 (Cortex-A53/A55 class) a
float16 model runs emulated, which is what made the 1024 encoder take 13,7 s on the DT50.

encoder512.onnx  image [1,3,512,512] -> embeddings [1,256,32,32]
decoder512.onnx  embeddings, coords [1,N,2] (pixels in the 512 frame), labels [1,N] -> masks [1,3,128,128], scores [1,3]
Check against the 1024 model with tools/check_sam512.py.
"""
import sys
from pathlib import Path

import torch
from torch import nn
from ultralytics import SAM
from ultralytics.models.sam.modules.tiny_encoder import TinyViT

SIZE = 512
GRID = SIZE // 16


def _ln2d(self, x):
    """LayerNorm2d in plain ops (newer ultralytics uses x.shape[1:2], which the ONNX tracer cannot export)."""
    u = x.mean(1, keepdim=True)
    s = (x - u).pow(2).mean(1, keepdim=True)
    x = (x - u) / torch.sqrt(s + self.eps)
    return self.weight[:, None, None] * x + self.bias[:, None, None]


from ultralytics.nn.modules import transformer as _tr  # noqa: E402
_tr.LayerNorm2d.forward = _ln2d


class Decoder(nn.Module):
    def __init__(self, sam):
        super().__init__()
        self.pe = sam.prompt_encoder
        self.dec = sam.mask_decoder

    def forward(self, emb, coords, labels):
        pe = self.pe
        c = (coords + 0.5) / float(SIZE)
        e = pe.pe_layer._pe_encoding(c)
        lab = labels.unsqueeze(-1).expand_as(e)
        e = e * (lab != -1).float() + pe.not_a_point_embed.weight * (lab == -1).float()
        for i in range(pe.num_point_embeddings):
            e = e + pe.point_embeddings[i].weight * (lab == i).float()
        dense = pe.no_mask_embed.weight.reshape(1, -1, 1, 1).expand(1, -1, GRID, GRID)
        dense_pe = pe.pe_layer((GRID, GRID)).unsqueeze(0)
        masks, scores = self.dec.predict_masks(emb, dense_pe, e, dense)
        return masks[:, 1:], scores[:, 1:]


def encoder(sam):
    enc = TinyViT(img_size=SIZE, in_chans=3, num_classes=1000, embed_dims=[64, 128, 160, 320], depths=[2, 2, 6, 2],
                  num_heads=[2, 4, 5, 10], window_sizes=[7, 7, 14, 7], mlp_ratio=4.0, drop_rate=0.0, drop_path_rate=0.0,
                  use_checkpoint=False, mbconv_expand_ratio=4.0, local_conv_size=3, layer_lr_decay=0.8)
    r = enc.load_state_dict(sam.image_encoder.state_dict(), strict=True)
    return enc.eval()


def main(weights, out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    sam = SAM(weights).model.eval()
    enc = encoder(sam)
    x = torch.randn(1, 3, SIZE, SIZE)
    torch.onnx.export(enc, (x,), out / "encoder512.onnx", input_names=["image"], output_names=["embeddings"], opset_version=17, dynamo=False)
    dec = Decoder(sam).eval()
    emb = enc(x).detach()
    coords = torch.tensor([[[250.0, 200.0], [0.0, 0.0]]]); labels = torch.tensor([[1.0, -1.0]])
    tmp = out / "decoder512_fp32.onnx"
    torch.onnx.export(dec, (emb, coords, labels), tmp, input_names=["embeddings", "coords", "labels"], output_names=["masks", "scores"],
                      dynamic_axes={"coords": {1: "n"}, "labels": {1: "n"}}, opset_version=17, dynamo=False)
    from onnxruntime.quantization import QuantType, quantize_dynamic
    quantize_dynamic(str(tmp), str(out / "decoder512.onnx"), weight_type=QuantType.QInt8, op_types_to_quantize=["MatMul", "Gemm"])
    tmp.unlink()
    for f in sorted(out.glob("*512*.onnx")):
        print(f.name, f.stat().st_size // 1024, "KB")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
