#!/usr/bin/env python3
"""
Manager for the loading and saving the save files for the Dark Souls: Remastered. 

CLI:
- `list`   : list available scenarios
- `paths`  : print resolved save paths (debug)
- `load X` : load scenario `X` into the active save directory (optionally backing up current)
- `dump X` : dump current active save into a new scenario folder `X`
- `backup` : backup the current active save into `darkAgent/dsr_save_files/backups/`

Example Usages:
- List available scenarios:
    python save_manager.py list
- Print resolved save paths:
    python save_manager.py paths
- Load a scenario into the active save directory:
    python save_manager.py load <scenario>
- Dump the current active save into a new scenario folder:
    python save_manager.py dump <scenario>
- Backup the current active save into `darkAgent/dsr_save_files/backups/`:
    python save_manager.py backup
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
import time
from dataclasses import dataclass
from pathlib import Path


SL2_NAME = "DRAKS0005.sl2"  # Default save file nmae 
ID_DIR_RE = re.compile(r"^[0-9]+$")  # Regular expression to match the numeric ID directory


def _now_stamp() -> str:
    """Helper function to get the current timestamp in the format of YYYYMMDD-HHMMSS"""
    return time.strftime("%Y%m%d-%H%M%S")


def _repo_default_scenarios_dir() -> Path:
    """Helper function to get the default scenarios directory"""
    return Path(__file__).resolve().parent / "dsr_save_files"


@dataclass(frozen=True)
class SavePaths:
    """Class to store the save paths"""
    wineprefix: Path
    save_root: Path
    user_id: str
    save_dir: Path


def resolve_save_paths(wineprefix: str | None = None, save_root: str | None = None, user_id: str | None = None) -> SavePaths:
    """
    Helper function to resolve the save paths from the environment variables or the command line arguments.
    
    Args:
        wineprefix: The Wine prefix directory
        save_root: The save root directory
        user_id: The user ID directory
    """
    wineprefix_p = Path(wineprefix or os.environ.get("WINEPREFIX", "/opt/prefix")).expanduser()
    env_save_root = os.environ.get("DSR_SAVE_ROOT")
    env_save_dir = os.environ.get("DSR_SAVE_DIR")
    env_user_id = os.environ.get("DSR_USER_ID")

    if save_root:
        save_root_p = Path(save_root).expanduser()
    elif env_save_root:
        save_root_p = Path(env_save_root).expanduser()
    elif env_save_dir:
        save_root_p = Path(env_save_dir).expanduser().parent
    else:
        # Default save root directory is the Wine prefix directory if none of the variables are set: / drive_c/users/root/Documents/NBGI/DARK SOULS REMASTERED
        save_root_p = wineprefix_p / "drive_c/users/root/Documents/NBGI/DARK SOULS REMASTERED"

    if user_id is None:  # If user_id is not set, use the environment variable
        user_id = env_user_id

    if user_id is None:  # If user_id is not set in the environment variables, check if the save root directory exists
        if not save_root_p.exists():
            raise RuntimeError(f"Save root does not exist: {save_root_p}\nIf you are inside the container, run it once (entrypoint will create it),\nor set DSR_SAVE_ROOT / DSR_SAVE_DIR / DSR_USER_ID.")
        ids = sorted([p.name for p in save_root_p.iterdir() if p.is_dir() and ID_DIR_RE.match(p.name)])
        if not ids:
            raise RuntimeError(f"No numeric DSR ID folder found under: {save_root_p}\nTip: start the game once so it generates the ID folder.")
        user_id = ids[0]

    save_dir_p = save_root_p / user_id
    if not save_dir_p.is_dir():
        raise RuntimeError(f"Resolved save directory does not exist: {save_dir_p}")

    return SavePaths(wineprefix=wineprefix_p, save_root=save_root_p, user_id=user_id, save_dir=save_dir_p)


def list_scenarios(scenarios_dir: Path) -> list[str]:
    """Helper function to list the scenarios in the scenarios directory"""
    if not scenarios_dir.exists():
        # If the scenarios directory does not exist, return an empty list
        return []
    out: list[str] = []  # List to store the scenarios
    for p in sorted(scenarios_dir.iterdir()):
        if not p.is_dir():
            continue
        if (p / SL2_NAME).is_file():  # If the scenario directory contains the save file, add the scenario name to the list
            out.append(p.name)
    return out


def _assert_scenario_exists(scenarios_dir: Path, scenario: str) -> Path:
    """Helper function to check if the requested scenario exists"""
    scenario_dir = scenarios_dir / scenario
    if not scenario_dir.is_dir():
        available = list_scenarios(scenarios_dir)
        raise RuntimeError(f"Unknown scenario '{scenario}'.\nScenarios dir: {scenarios_dir}\nAvailable: {', '.join(available) if available else '(none found)'}")
    sl2 = scenario_dir / SL2_NAME
    if not sl2.is_file():
        raise RuntimeError(f"Scenario folder is missing {SL2_NAME}: {scenario_dir}")
    return sl2


def backup_current_save(paths: SavePaths, backup_root: Path) -> Path | None:
    """Helper function to backup the current save into the backup directory"""
    src = paths.save_dir / SL2_NAME
    if not src.is_file():
        return None
    dst_dir = backup_root / "backups" / f"{_now_stamp()}_{paths.user_id}"
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / SL2_NAME
    shutil.copy2(src, dst)
    return dst


def load_scenario(paths: SavePaths, scenarios_dir: Path, scenario: str, backup: bool, wipe_sl2: bool) -> None:
    """Helper function to load a scenario into the active save directory"""
    src = _assert_scenario_exists(scenarios_dir, scenario)
    dst = paths.save_dir / SL2_NAME

    if backup:
        backed_up = backup_current_save(paths, scenarios_dir)
        if backed_up:
            print(f"[save] backed up current save to: {backed_up}")

    if wipe_sl2 and dst.exists():
        dst.unlink()

    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    print(f"[save] loaded scenario '{scenario}' -> {dst}")


def dump_current(paths: SavePaths, scenarios_dir: Path, name: str, overwrite: bool) -> None:
    """Helper function to dump the current active save into a new scenario folder"""
    src = paths.save_dir / SL2_NAME
    if not src.is_file():
        raise RuntimeError(f"No current save file found at: {src}")

    dst_dir = scenarios_dir / name
    dst = dst_dir / SL2_NAME

    if dst.exists() and not overwrite:
        raise RuntimeError(f"Destination already exists: {dst} (use --overwrite)")

    dst_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    print(f"[save] dumped current save -> scenario '{name}': {dst}")


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="save_manager.py", description="Manage Dark Souls Remastered save swapping inside the container.")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("paths", help="Print resolved save paths (root/id/save_dir)")
    sub.add_parser("list", help="List available scenarios")
    load = sub.add_parser("load", help="Load a scenario into the active save directory")
    
    load.add_argument("scenario", help="Scenario name (folder under scenarios-dir)")
    load.add_argument("--no-backup", action="store_true", help="Do not backup current save before replacing")
    load.add_argument("--no-wipe", action="store_true", help="Do not delete existing DRAKS0005.sl2 before copy")

    dump = sub.add_parser("dump", help="Dump the current active save into a new scenario folder")
    dump.add_argument("name", help="Scenario name to create/update under scenarios-dir")
    dump.add_argument("--overwrite", action="store_true", help="Allow overwriting an existing scenario save")

    backup = sub.add_parser("backup", help="Backup the current active save into scenarios-dir/backups/")

    args = p.parse_args(argv)

    scenarios_dir = _repo_default_scenarios_dir()

    if args.cmd == "list":  # List the scenarios in the scenarios directory
        items = list_scenarios(scenarios_dir)
        for name in items:
            print(name)
        return 0

    paths = resolve_save_paths()  # Resolve the save paths

    if args.cmd == "paths":  # Print the save paths
        print(f"wineprefix: {paths.wineprefix}")
        print(f"save_root:  {paths.save_root}")
        print(f"user_id:    {paths.user_id}")
        print(f"save_dir:   {paths.save_dir}")
        print(f"active_sl2: {paths.save_dir / SL2_NAME}")
        return 0

    if args.cmd == "load":  # Load a scenario into the active save directory
        load_scenario(paths=paths, scenarios_dir=scenarios_dir, scenario=args.scenario, backup=not args.no_backup, wipe_sl2=not args.no_wipe)
        return 0

    if args.cmd == "dump":  # Dump the current active save into a new scenario folder
        dump_current(paths=paths, scenarios_dir=scenarios_dir, name=args.name, overwrite=args.overwrite)
        return 0

    if args.cmd == "backup":  # Backup the current active save into the backup directory
        dst = backup_current_save(paths, scenarios_dir)
        if not dst:
            print(f"[save] nothing to backup (missing {SL2_NAME} in {paths.save_dir})")
            return 0
        print(f"[save] backed up current save to: {dst}")
        return 0

    raise AssertionError("unreachable")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
