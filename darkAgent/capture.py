"""
Capture or record a specific DSR instance's display into `/root/captures/<timestamp>/`.

Usage:
    Capture a single screenshot:
        python3 /root/darkAgent/capture.py --instance dsr-1 -capture
    Record a GIF for 5 seconds:
        python3 /root/darkAgent/capture.py --instance dsr-1 -record --seconds 5
"""

from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, cast

CAPTURES_ROOT = Path("/root/captures")
CONFIG_PATH = Path("/root/config/dsr_instances.json")
FPS = 24.0
DEFAULT_DISPLAY = os.environ.get("DISPLAY", ":99")


def _timestamp() -> str:
    # include microseconds to avoid collisions when starting captures simultaneously
    return datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")


def _load_instances(config_path: Path) -> Dict[str, Any]:
    if not config_path.is_file():
        raise SystemExit(f"ERROR: missing config file: {config_path}")
    try:
        cfg = json.loads(config_path.read_text(encoding="utf-8"))
    except Exception as e:
        raise SystemExit(f"ERROR: failed to parse {config_path}: {e}")
    instances = cfg.get("instances")
    if not isinstance(instances, dict):
        raise SystemExit(f"ERROR: config {config_path} must contain an 'instances' object")
    return instances


def _display_for_instance(instance_name: str) -> str:
    instances = _load_instances(CONFIG_PATH)
    inst = instances.get(instance_name)
    if not isinstance(inst, dict):
        available = ", ".join(sorted(instances.keys()))
        raise SystemExit(f"ERROR: unknown instance '{instance_name}'. Available: {available}")

    display_num = inst.get("display_num")
    if isinstance(display_num, int):
        return f":{display_num}"

    # fallback if someone manually writes 'display' like ':99'
    display = inst.get("display")
    if isinstance(display, str) and display.strip():
        return display.strip()

    raise SystemExit(f"ERROR: instance '{instance_name}' missing integer 'display_num' in {CONFIG_PATH}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Capture or record X11 frames.")
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("-capture", action="store_true", help="Capture a single screenshot.")
    mode.add_argument("-record", action="store_true", help="Record at ~24 FPS for --seconds, then write recording.gif.")
    p.add_argument("--seconds", type=float, default=None, help="Required for -record: stop automatically after N seconds (e.g. --seconds 5).")

    src = p.add_mutually_exclusive_group()
    src.add_argument("--instance", help="Instance name from /root/config/dsr_instances.json (e.g. dsr-1).")
    src.add_argument("--display", default=None, help="X11 DISPLAY to capture from (e.g. :90).")
    args = p.parse_args()
    if args.record and args.seconds is None:
        p.error("--seconds is required when using -record")
    if args.record and args.seconds is not None and args.seconds <= 0:
        p.error("--seconds must be > 0")
    return args


def _ensure_run_dir() -> Path:
    """Ensure the run directory exists"""
    run_dir = CAPTURES_ROOT / _timestamp()  # Create the run directory with the timestamp
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def _save_png(run_dir: Path, name: str, screenshot) -> Path:
    """Save the screenshot to the given path"""
    from PIL import Image

    path = run_dir / name
    img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
    img.save(path)
    return path


def _write_gif(frames_dir: Path, out_path: Path, fps: float) -> None:
    """
    Merge frame PNGs into a single animated GIF.

    This is intentionally simple; GIFs can get large for long recordings.
    """
    from PIL import Image

    frame_paths = sorted(frames_dir.glob("frame_*.png"))
    if not frame_paths:
        raise RuntimeError(f"No frames found in {frames_dir}")

    duration_ms = max(1, int(round(1000.0 / fps)))

    frames = []
    for p in frame_paths:
        with Image.open(p) as im:
            frames.append(im.convert("P", palette=Image.ADAPTIVE, colors=256))

    first, rest = frames[0], frames[1:]
    first.save(out_path, save_all=True, append_images=rest, duration=duration_ms, loop=0, optimize=False, disposal=2)


def capture_once() -> Path:
    run_dir = _ensure_run_dir()  # Ensure the run directory exists
    display = os.environ.get("DISPLAY", "")
    print("DISPLAY:", display)
    print("Output dir:", run_dir)

    from mss import mss

    with mss() as sct:  # Capture the screen
        monitor = sct.monitors[0]  # full virtual screen
        screenshot = sct.grab(monitor)  # Capture the screenshot
        path = _save_png(run_dir, "capture.png", screenshot)
        print("Saved:", path)
        return path


def record_png_sequence(seconds: float) -> Path:
    """Record a sequence of screenshots and save them as a GIF"""
    run_dir = _ensure_run_dir()
    frames_dir = run_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=False)

    display = os.environ.get("DISPLAY", "")
    print("DISPLAY:", display)
    print("Output dir:", run_dir)
    print(f"Recording at ~{FPS:.0f} FPS for {seconds:g}s... (Ctrl+C stops early)")

    frame_interval = 1.0 / FPS
    start = time.perf_counter()
    frame_idx = 0

    from mss import mss

    with mss() as sct:  # Capture the screen
        monitor = sct.monitors[0]  # full virtual screen
        try:
            while True:
                if (time.perf_counter() - start) >= seconds:
                    break
                screenshot = sct.grab(monitor)
                _save_png(frames_dir, f"frame_{frame_idx:06d}.png", screenshot)
                frame_idx += 1

                next_t = start + frame_idx * frame_interval
                now = time.perf_counter()
                sleep_s = next_t - now
                if sleep_s > 0:
                    time.sleep(sleep_s)
        except KeyboardInterrupt:
            pass

    print(f"Stopped. Saved {frame_idx} frames to: {frames_dir}")
    gif_path = run_dir / "recording.gif"
    _write_gif(frames_dir, gif_path, FPS)
    print("Wrote:", gif_path)
    return run_dir


def main() -> None:
    args = parse_args()
    CAPTURES_ROOT.mkdir(parents=True, exist_ok=True)  # Create the captures root directory if it doesn't exist

    if args.instance:
        os.environ["DISPLAY"] = _display_for_instance(args.instance)  # Set the display environment variable to the display number for the given instance
    else:
        os.environ["DISPLAY"] = args.display or DEFAULT_DISPLAY  # Set the display environment variable to the display number for the given display

    if args.capture:
        capture_once()  # Capture a single screenshot
        return
    if args.record:
        record_png_sequence(cast(float, args.seconds))  # Record a sequence of screenshots
        return

if __name__ == "__main__":
    main()
