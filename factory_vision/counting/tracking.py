"""Tracker configuration.

Stock tracker thresholds assume supervised confidences. Zero-shot scores run
far lower, so the gates are retuned in trackers/*.yaml and resolved here.
"""

from __future__ import annotations

from pathlib import Path

from factory_vision.paths import OUTPUT_DIR, ROOT

TRACKER_DIR = Path(__file__).resolve().parent / "trackers"


def resolve_tracker_cfg(name: str, overrides: dict | None = None, tag: str = "") -> Path:
    """Rewrite the tracker YAML with an absolute ReID path and clip overrides.

    Ultralytics resolves a relative ``model:`` against the working directory, so
    the checked-in relative path only works when run from the project root.
    ``overrides`` carries the per-clip gate tuning from ClipConfig.
    """
    import yaml

    src = TRACKER_DIR / f"{name}_zeroshot.yaml"
    cfg = yaml.safe_load(src.read_text())
    reid = cfg.get("model")
    if reid and reid != "auto" and not Path(reid).is_absolute():
        cfg["model"] = str((ROOT / reid).resolve())
    if overrides:
        cfg.update(overrides)
    dst = OUTPUT_DIR / f".{name}{('_' + tag) if tag else ''}_resolved.yaml"
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(yaml.safe_dump(cfg, sort_keys=False))
    return dst

