"""Export MobileSAM (Apache 2.0) to two ONNX files for the app: an image encoder and a prompt decoder.

    python tools/export_sam.py <mobile_sam.pt>

encoder.onnx  image [1,3,1024,1024] float (RGB, normalised, longest side resized to 1024, padded)
              -> embeddings [1,256,64,64]
decoder.onnx  embeddings, coords [1,N,2] (pixels in the 1024 frame), labels [1,N] (1 tap, 0 not here,
              2/3 box corners, -1 padding) -> masks [1,3,256,256] logits, scores [1,3]
The encoder is stored in float16 (inputs/outputs stay float32): 13,8 MB, embeddings within 0,3 % of float32.
The decoder's MatMul/Gemm weights are int8 (signed, dynamic quantisation): 4,6 MB instead of 16 MB, masks within
IoU 0,989 of float32 on the conveyor frame (mean 0,997). int8 on the encoder was tried and rejected: it breaks the
masks (they cover the whole image). Check with tools/check_sam_onnx.py.
"""
import sys
from pathlib import Path

import numpy as np
import torch
from torch import nn
from ultralytics import SAM

OUT = Path(__file__).resolve().parents[1] / "app" / "src" / "main" / "assets" / "sam"


class Decoder(nn.Module):
    def __init__(self, sam):
        super().__init__()
        self.pe = sam.prompt_encoder
        self.dec = sam.mask_decoder

    def forward(self, emb, coords, labels):
        pe = self.pe
        c = (coords + 0.5) / 1024.0
        e = pe.pe_layer._pe_encoding(c)
        lab = labels.unsqueeze(-1).expand_as(e)
        e = e * (lab != -1).float() + pe.not_a_point_embed.weight * (lab == -1).float()
        for i in range(pe.num_point_embeddings):
            e = e + pe.point_embeddings[i].weight * (lab == i).float()
        dense = pe.no_mask_embed.weight.reshape(1, -1, 1, 1).expand(1, -1, 64, 64)
        masks, scores = self.dec.predict_masks(emb, pe.get_dense_pe(), e, dense)
        return masks[:, 1:], scores[:, 1:]


def main(weights):
    sam = SAM(weights).model.eval()
    OUT.mkdir(parents=True, exist_ok=True)
    x = torch.randn(1, 3, 1024, 1024)
    tmp = OUT / "encoder_fp32.onnx"
    torch.onnx.export(sam.image_encoder, (x,), tmp, input_names=["image"],
                      output_names=["embeddings"], opset_version=17, dynamo=False)
    dec = Decoder(sam).eval()
    emb = sam.image_encoder(x).detach()
    coords = torch.tensor([[[500.0, 400.0], [0.0, 0.0]]]); labels = torch.tensor([[1.0, -1.0]])
    dec_tmp = OUT / "decoder_fp32.onnx"
    torch.onnx.export(dec, (emb, coords, labels), dec_tmp, input_names=["embeddings", "coords", "labels"],
                      output_names=["masks", "scores"], dynamic_axes={"coords": {1: "n"}, "labels": {1: "n"}},
                      opset_version=17, dynamo=False)
    import onnx
    from onnxconverter_common import float16
    onnx.save(float16.convert_float_to_float16(onnx.load(str(tmp)), keep_io_types=True), str(OUT / "encoder.onnx"))
    tmp.unlink()
    from onnxruntime.quantization import QuantType, quantize_dynamic
    quantize_dynamic(str(dec_tmp), str(OUT / "decoder.onnx"), weight_type=QuantType.QInt8, op_types_to_quantize=["MatMul", "Gemm"])
    dec_tmp.unlink()
    for f in sorted(OUT.glob("*.onnx")):
        print(f.name, f.stat().st_size // 1024, "KB")


if __name__ == "__main__":
    main(sys.argv[1])
