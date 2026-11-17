"""Cross-check of the app's own ArUco detector (core/.../marker/Aruco.kt) against OpenCV's, on the synthetic photos
ArucoTest writes with -Pukur.markerOut=<dir>: same ids, same printed top-left corner, and how far each detector's
corners are from the true ones (OpenCV with sub-pixel corner refinement).

    ./gradlew :core:testDebugUnitTest --tests '*ArucoTest*' -Pukur.markerOut=/tmp/markers --rerun-tasks
    python tools/marker/check_opencv.py /tmp/markers
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np


def main(d: str) -> None:
    det = cv2.aruco.ArucoDetector(cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50),
                                  cv2.aruco.DetectorParameters())
    p = det.getDetectorParameters()
    p.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
    det.setDetectorParameters(p)
    for png in sorted(Path(d).glob("*.png")):
        truth = json.loads(png.with_suffix(".json").read_text())
        img = cv2.imread(str(png), cv2.IMREAD_GRAYSCALE)
        corners, ids, _ = det.detectMarkers(img)
        t = np.array(truth["corners"])
        if ids is None:
            print(f"{png.stem:8s} OpenCV found nothing (truth id {truth['id']})")
            continue
        for c, i in zip(corners, ids.flatten()):
            # OpenCV's corners are at pixel centres = integer coordinates; the app's (and the truth's) at +0.5
            err = np.linalg.norm(c[0] + 0.5 - t, axis=1).max()
            print(f"{png.stem:8s} OpenCV id {i} (truth {truth['id']}), corners within {err:.2f} px, "
                  f"top-left {'same' if np.linalg.norm(c[0][0] + 0.5 - t[0]) < 3 else 'DIFFERENT'}")


if __name__ == "__main__":
    main(sys.argv[1])
