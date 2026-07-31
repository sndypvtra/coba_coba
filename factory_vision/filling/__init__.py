"""Fill-volume inspection on a bottling line (case 4).

Not a counting problem and not zero-shot. Product inside the bottle is segmented
on saturation, the liquid surface is located by width, and the volume below it is
integrated over the bottle's bore as a stack of discs.

    from factory_vision.filling import run_case
    summary = run_case(capacity_ml=1500.0)

This is a calibrated single-station inspection: every constant in
``calibration.py`` is tied to this camera, bottle and product.
"""

from __future__ import annotations

from factory_vision.filling.calibration import (LIQUID_LO, ROI, THREAD_DATUM_Y,
                                                SURFACE_BAND)
from factory_vision.filling.pipeline import run, run_case

__all__ = ["run_case", "run", "LIQUID_LO", "ROI", "THREAD_DATUM_Y", "SURFACE_BAND"]
