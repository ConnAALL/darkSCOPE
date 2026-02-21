#!/usr/bin/env python3
"""
Simple script for generating the config files for running multiple instances inside the container. 

Usage: 
    python3 /root/scripts/generate_config.py --num-instances <num_instances>
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

# Hyperparameters for the paths and templates
DEFAULT_OUT = Path("/root/config/dsr_instances.json")
RUN_GAME = Path("/root/scripts/run_game.sh")
TEMPLATE_PREFIX = Path("/opt/prefix")
ID_DIR_PREFIX_RE = tuple(str(d) for d in range(10))


def _instance_name(i: int) -> str:
    """Create an instance name for the ith instance"""
    return f"dsr-{i + 1}"  # dsr-1, dsr-2, ...


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate /root/config/dsr_instances.json for <num_instances> instances.")
    p.add_argument("--num-instances", type=int, required=True, help="Number of instances to generate.")
    p.add_argument("--base-display", type=int, default=90, help="First X display number (default: 90).")
    p.add_argument("--base-vnc-port", type=int, default=5901, help="First VNC port (default: 5901).")
    p.add_argument("--wineprefix-base", default="/opt/prefix_", help="Prefix path base (default: /opt/prefix_).")
    p.add_argument("--desktop-res", default="800x600", help="Per-instance desktop resolution (default: 800x600).")
    p.add_argument("--desktop-name-prefix", default="DSR_", help="Per-instance desktop name prefix (default: DSR_).")
    p.add_argument("--init-timeout-sec", type=int, default=60, help="Timeout for save folder initialization per instance.")
    p.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Output path (default: /root/config/dsr_instances.json).")
    return p.parse_args()


def _save_root_for_prefix(wineprefix: str) -> Path:
    """Resolve the save root directory for a given Wine prefix"""
    return Path(wineprefix) / "drive_c/users/root/Documents/NBGI/DARK SOULS REMASTERED"


def _find_numeric_id_dir(save_root: Path) -> Optional[str]:
    """Find the numeric ID directory for a given save root"""
    if not save_root.is_dir():
        return None
    ids = []
    for p in save_root.iterdir():
        if p.is_dir() and p.name and p.name[0] in ID_DIR_PREFIX_RE and p.name.isdigit():
            ids.append(p.name)
    if not ids:
        return None
    ids.sort()
    return ids[0]  # Return the first numeric ID directory


def _ensure_prefix(prefix: Path) -> None:
    """Ensure the Wine prefix directory exists"""
    if prefix.exists():
        if not prefix.is_dir():
            raise SystemExit(f"ERROR: WINEPREFIX exists but is not a directory: {prefix}")
        return
    if not TEMPLATE_PREFIX.is_dir():
        raise SystemExit(f"ERROR: Template prefix not found: {TEMPLATE_PREFIX}")
    prefix.parent.mkdir(parents=True, exist_ok=True)
    print(f"[generate_config] Cloning template prefix {TEMPLATE_PREFIX} -> {prefix}")
    shutil.copytree(TEMPLATE_PREFIX, prefix, symlinks=True)


def _init_save_folder_for_instance(name: str, wineprefix: str, display_num: int, xdg_runtime_dir: str, timeout_sec: int) -> Tuple[str, Path, Path]:
    """
    Ensure the numeric DSR save ID folder exists for a given WINEPREFIX by running the game headless briefly.
    Returns:
        user_id: The numeric DSR save ID directory
        save_root: The save root directory
        save_dir: The save directory
    """
    save_root = _save_root_for_prefix(wineprefix)
    user_id = _find_numeric_id_dir(save_root)
    if user_id:
        return user_id, save_root, save_root / user_id

    if not RUN_GAME.is_file():
        raise SystemExit(f"ERROR: Missing run_game.sh at {RUN_GAME}")

    print(f"[generate_config] ({name}) Initializing save folder via headless game run...")
    save_root.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["WINEPREFIX"] = wineprefix
    env["DISPLAY_NUM"] = str(display_num)
    env["XDG_RUNTIME_DIR"] = xdg_runtime_dir

    # Run the game in the hadless mode to initialize the save folder
    proc = subprocess.Popen([str(RUN_GAME), "headless"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        deadline = time.time() + timeout_sec
        while time.time() < deadline:
            user_id = _find_numeric_id_dir(save_root)  # Check if the numeric ID directory exists
            if user_id:
                break
            if proc.poll() is not None:
                raise SystemExit(f"ERROR: ({name}) headless game process exited before save ID folder appeared")  # If the game process exited before the save ID folder appeared, raise an error
            time.sleep(0.5)
        if not user_id:
            raise SystemExit(f"ERROR: ({name}) timed out after {timeout_sec}s waiting for save ID folder under {save_root}")  # If the game process timed out after the timeout seconds, raise an error
    finally:
        try:
            proc.terminate()
        except Exception:
            pass
        try:
            proc.wait(timeout=5)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
            try:
                proc.wait(timeout=5)
            except Exception:
                pass

    return user_id, save_root, save_root / user_id


def main() -> int:
    args = parse_args()
    if args.num_instances <= 0:
        raise SystemExit("--num-instances must be >= 1")

    instances: Dict[str, Dict[str, Any]] = {}
    for i in range(args.num_instances):
        name = _instance_name(i)
        display_num = args.base_display + i
        vnc_port = args.base_vnc_port + i
        wineprefix = f"{args.wineprefix_base}{name}"
        xdg_runtime_dir = f"/tmp/xdg_{display_num}"
        inst: Dict[str, Any] = {
            "display_num": display_num,
            "vnc_port": vnc_port,
            "wineprefix": wineprefix,
            "desktop_res": args.desktop_res,
            "desktop_name": f"{args.desktop_name_prefix}{i + 1}",
            "xdg_runtime_dir": xdg_runtime_dir,
        }
        _ensure_prefix(Path(wineprefix))
        user_id, save_root, save_dir = _init_save_folder_for_instance(name=name, wineprefix=wineprefix, display_num=display_num, xdg_runtime_dir=xdg_runtime_dir, timeout_sec=args.init_timeout_sec)
        inst["dsr_user_id"] = user_id
        inst["dsr_save_root"] = str(save_root)
        inst["dsr_save_dir"] = str(save_dir)

        instances[name] = inst

    cfg = {"instances": instances}

    out_path: Path = args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = out_path.with_suffix(out_path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(cfg, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    tmp_path.replace(out_path)

    print(f"[generate_config] wrote {out_path}")
    for name, inst in instances.items():
        print(f"{name}: DISPLAY=:{inst['display_num']} VNC_PORT={inst['vnc_port']} WINEPREFIX={inst['wineprefix']}")  # Print the instance name, display number, VNC port, and Wine prefix

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
