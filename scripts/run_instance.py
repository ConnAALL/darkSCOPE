#!/usr/bin/env python3
"""
Launch one or more Dark Souls Remastered instances inside the container. 

Reads instance definitions from `/root/config/dsr_instances.json` and starts a
set of instances with isolated resources:
- Xorg display number (DISPLAY_NUM)
- VNC port (VNC_PORT)
- Wine prefix (WINEPREFIX) to avoid wineserver/game collisions
- XDG runtime dir (XDG_RUNTIME_DIR) to avoid shared runtime state

Usage:
  Starting a single instance:
    python3 /root/scripts/run_instance.py dsr-1
  Starting multiple instances:
    python3 /root/scripts/run_instance.py --instances dsr-1,dsr-2,dsr-3
  Starting all instances:
    python3 /root/scripts/run_instance.py --all
  Starting multiple instances in headless mode:
    python3 /root/scripts/run_instance.py --mode headless --instances dsr-1,dsr-2
  Starting a single instance in GUI mode:
    python3 /root/scripts/run_instance.py --mode gui dsr-1
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


CONFIG_PATH = Path("/root/config/dsr_instances.json")
TEMPLATE_PREFIX = Path("/opt/prefix")
RUN_GAME = Path("/root/scripts/run_game.sh")


def _die(msg: str) -> "None":
    """Raise a SystemExit with an error message"""
    raise SystemExit(f"ERROR: {msg}")


def _load_config(path: Path) -> Dict[str, Any]:
    """Load the config file from the given path"""
    if not path.is_file():
        _die(f"Missing config file: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        _die(f"Failed to parse JSON config {path}: {e}")


def _require(d: Dict[str, Any], key: str, typ: type):
    """Require a key to be present in the config and of the given type"""
    if key not in d:
        _die(f"Config missing required key '{key}'")
    v = d[key]
    if not isinstance(v, typ):
        _die(f"Config key '{key}' must be {typ.__name__}, got {type(v).__name__}")
    return v


def _ensure_prefix(prefix: Path) -> None:
    """Ensure the Wine prefix directory exists"""
    if prefix.exists():
        if not prefix.is_dir():
            _die(f"WINEPREFIX exists but is not a directory: {prefix}")
        return

    if not TEMPLATE_PREFIX.is_dir():
        _die(f"Template prefix not found: {TEMPLATE_PREFIX}")

    prefix.parent.mkdir(parents=True, exist_ok=True)
    print(f"[run_instance] Cloning template prefix {TEMPLATE_PREFIX} -> {prefix}")
    shutil.copytree(TEMPLATE_PREFIX, prefix, symlinks=True)


def _parse_args(argv: List[str]) -> argparse.Namespace:
    """Parse the command line arguments"""
    p = argparse.ArgumentParser(description="Start headless-vnc DSR instances defined in /root/config/dsr_instances.json.")
    p.add_argument("--mode", choices=("gui", "headless", "headless-vnc"), default="headless-vnc", help="How to run each instance (default: headless-vnc).")
    sel = p.add_mutually_exclusive_group()
    sel.add_argument("--all", action="store_true", help="Start all instances from the config.")
    sel.add_argument("--instances", help="Comma-separated instance names (e.g. a,b,c).")
    p.add_argument("instance", nargs="?", help="Single instance name (positional).")
    return p.parse_args(argv)


def _split_instances(s: str) -> List[str]:
    """Split the instances string into a list of instance names"""
    items = []
    for part in s.split(","):
        part = part.strip()
        if part:
            items.append(part)
    return items


def _resolve_selected_instances(args: argparse.Namespace, all_names: Iterable[str]) -> List[str]:
    """Resolve the selected instances from the command line arguments"""
    if args.all:
        return sorted(all_names)
    if args.instances:
        return _split_instances(args.instances)
    if args.instance:
        return [args.instance]
    _die("Select instances via positional <name>, --instances a,b,c, or --all")


def _prepare_env(name: str, inst: Dict[str, Any]) -> Tuple[Dict[str, str], int, int, Path]:
    """Prepare the environment for the given instance"""
    display_num = _require(inst, "display_num", int)
    vnc_port = _require(inst, "vnc_port", int)
    wineprefix = Path(_require(inst, "wineprefix", str))

    desktop_res = inst.get("desktop_res", "800x600")
    desktop_name = inst.get("desktop_name", f"DSR_{name}")
    xdg_runtime_dir = Path(inst.get("xdg_runtime_dir", f"/tmp/xdg_{display_num}"))

    _ensure_prefix(wineprefix)
    xdg_runtime_dir.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["DISPLAY_NUM"] = str(display_num)
    env["VNC_PORT"] = str(vnc_port)
    env["WINEPREFIX"] = str(wineprefix)
    env["XDG_RUNTIME_DIR"] = str(xdg_runtime_dir)
    env["DESKTOP_RES"] = str(desktop_res)
    env["DESKTOP_NAME"] = str(desktop_name)

    # If generate_config initialized the save folder, pass it through for downstream scripts.
    dsr_user_id = inst.get("dsr_user_id")
    dsr_save_root = inst.get("dsr_save_root")
    dsr_save_dir = inst.get("dsr_save_dir")
    if isinstance(dsr_user_id, str) and isinstance(dsr_save_root, str) and isinstance(dsr_save_dir, str):
        env["DSR_USER_ID"] = dsr_user_id
        env["DSR_SAVE_ROOT"] = dsr_save_root
        env["DSR_SAVE_DIR"] = dsr_save_dir
    return env, display_num, vnc_port, wineprefix


def main(argv: List[str]) -> int:
    """Main function to run the script"""
    args = _parse_args(argv)

    cfg = _load_config(CONFIG_PATH)
    instances = cfg.get("instances")
    if not isinstance(instances, dict):
        _die("Config must contain an 'instances' object")

    if not RUN_GAME.is_file():
        _die(f"Missing run_game.sh at {RUN_GAME}")

    selected = _resolve_selected_instances(args, instances.keys())
    if not selected:
        _die("No instances selected")

    # Validate early so we fail before starting any processes.
    missing = [n for n in selected if n not in instances]
    if missing:
        available = ", ".join(sorted(instances.keys()))
        _die(f"Unknown instance(s): {', '.join(missing)}. Available: {available}")

    procs: List[Tuple[str, subprocess.Popen[bytes]]] = []

    try:
        for name in selected:
            inst = instances[name]
            if not isinstance(inst, dict):
                _die(f"Instance '{name}' must be an object")
            env, display_num, vnc_port, wineprefix = _prepare_env(name, inst)
            print(f"[run_instance] starting instance={name} mode={args.mode} DISPLAY_NUM={display_num} VNC_PORT={vnc_port} WINEPREFIX={wineprefix}")  # Print the instance name, mode, display number, VNC port, and Wine prefix
            p = subprocess.Popen([str(RUN_GAME), args.mode], env=env)  # Run the game in the given mode (headless, headless-vnc, gui)
            procs.append((name, p))

        # Wait for all children. Ctrl+C will terminate them.
        exit_code = 0  # Exit code of the last process to exit
        for name, p in procs:
            rc = p.wait()
            if rc != 0 and exit_code == 0:
                exit_code = rc
            print(f"[run_instance] instance={name} exited rc={rc}")
        return exit_code
    except KeyboardInterrupt:
        print("[run_instance] Ctrl+C received. Stopping instances...")
        for _, p in procs:
            try:
                p.terminate()
            except Exception:
                pass
        for _, p in procs:
            try:
                p.wait(timeout=10)
            except Exception:
                try:
                    p.kill()
                except Exception:
                    pass
        return 130


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

