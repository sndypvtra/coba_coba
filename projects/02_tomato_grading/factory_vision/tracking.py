"""Tracker configuration.

Stock tracker thresholds assume supervised confidences. Zero-shot scores run
far lower, so the gates are retuned in trackers/*.yaml and resolved here.
"""

from __future__ import annotations

from pathlib import Path

from factory_vision.paths import ROOT

TRACKER_DIR = Path(__file__).resolve().parent / "trackers"


def resolve_tracker_cfg(name: str, overrides: dict | None = None, tag: str = "",
                        output_dir: Path | None = None) -> Path:
    """Rewrite the tracker YAML with an absolute ReID path and clip overrides.

    Ultralytics resolves a relative ``model:`` against the working directory, so
    the checked-in relative path only works when run from one specific place -
    and every project now runs from its own folder. Resolving it against the
    repository root instead makes that irrelevant. ``overrides`` carries the
    per-clip gate tuning, and the rewritten file lands in the calling project's
    own output so two projects cannot overwrite each other's.
    """
    import yaml

    src = TRACKER_DIR / f"{name}_zeroshot.yaml"
    cfg = yaml.safe_load(src.read_text())
    reid = cfg.get("model")
    if reid and reid != "auto" and not Path(reid).is_absolute():
        cfg["model"] = str((ROOT / reid).resolve())
    if overrides:
        cfg.update(overrides)
    out = output_dir or (ROOT / "output")
    dst = out / f".{name}{('_' + tag) if tag else ''}_resolved.yaml"
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(yaml.safe_dump(cfg, sort_keys=False))
    return dst

