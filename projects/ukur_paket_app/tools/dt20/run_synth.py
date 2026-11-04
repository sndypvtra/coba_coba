"""Synthetic test of the DT20 engine: generate sweeps of known objects, solve each, compare with the truth.

    python tools/dt20/run_synth.py <work_dir> [case ...]      # cases: box-0 cylinder-0 sack-0 box-1 ... box_dt50-0 rotate-0

Prints a table and writes <work_dir>/summary.json. Scale error is measured against the simulated camera path itself
(similarity fit of the solved camera centres to the true ones), so it is independent of the object.
"""
import json
import shutil
import sys
import traceback
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import solve as S                    # noqa: E402
import synth_sweep as Y              # noqa: E402


def true_scale_error(work):
    cc = np.load(work / "camera_centres.npy")
    p, _ = Y.trajectory(cc[:, 0] / Y.FPS)
    c = cc[:, 1:]
    mx, my = c.mean(0), p.mean(0); xc, yc = c - mx, p - my
    u, d, vt = np.linalg.svd(yc.T @ xc / len(c)); sg = np.eye(3); sg[2, 2] = np.sign(np.linalg.det(u @ vt))
    s = np.trace(np.diag(d) @ sg) / xc.var(0).sum()
    return 100 * (1 / s - 1)


def main(root, cases):
    root = Path(root); root.mkdir(parents=True, exist_ok=True)
    rows = []
    for case in cases:
        kind, seed = case.rsplit("-", 1)
        rec = root / case; work = root / f"{case}_work"
        for p in (rec, work):
            if p.exists(): shutil.rmtree(p)
        dt50 = kind.endswith("_dt50"); base = kind.replace("_dt50", "")
        Y.main(rec, "box" if base == "rotate" else base, base == "rotate", int(seed), dt50)
        try:
            r = S.solve(rec, work)
            row = {"case": case, "truth_cm": r["tape_cm"], "size_cm": r["size_cm"], "error_cm": r["error_cm"],
                   "scale_error_pct": round(true_scale_error(work), 2), "scale_sd_pct": r["scale_sd_pct"],
                   "time_offset_ms": r["time_offset_ms"], "floor_vs_gravity_deg": r["floor_vs_gravity_deg"],
                   "object_points": r["object_points"], "seconds_pc": r["seconds_pc"]}
        except BaseException as e:   # noqa: BLE001 - a failed case is a result too
            row = {"case": case, "failed": f"{type(e).__name__}: {e}"[:200]}
            if not isinstance(e, SystemExit): traceback.print_exc()
        rows.append(row)
        print(json.dumps(row))
    (root / "summary.json").write_text(json.dumps(rows, indent=2))
    print("\n| case | truth L x W x H (cm) | engine (cm) | error (cm) | scale error | time offset |")
    print("|---|---|---|---|---|---|")
    for r in rows:
        if "failed" in r: print(f"| {r['case']} | | failed: {r['failed']} | | | |"); continue
        f = lambda v: " x ".join(f"{x:.1f}" for x in v)
        print(f"| {r['case']} | {f(r['truth_cm'])} | {f(r['size_cm'])} | {' / '.join(f'{x:+.1f}' for x in r['error_cm'])} | "
              f"{r['scale_error_pct']:+.2f} % | {r['time_offset_ms']} ms |")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:] or ["box-0", "cylinder-0", "sack-0", "box-1", "cylinder-1", "sack-1", "box_dt50-0", "sack_dt50-1", "rotate-0"])
