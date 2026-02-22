#!/usr/bin/env python3
"""
Input test harness: pick an action by number and inject it into a DSR instance.

The actions are hardcoded to match the legacy `temp/dark-souls-agent` action list:
  ["w","a","s","d","attack","backstep","heal","strong-attack","front-roll","left-roll","back-roll","right-roll"]
"""
from __future__ import annotations

import argparse
import curses
import sys
import time
from dataclasses import dataclass
from typing import Sequence

from instance_config import resolve_instance
from x11_input import X11Input

def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="DSR input test (numbered action menu).")
    p.add_argument("--instance", required=True, help="Instance name from /root/config/dsr_instances.json (e.g. dsr-1).")
    p.add_argument("--action-ms", type=int, default=250, help="Hold duration for each action (ms). Default: 250 (legacy key_delay=0.25s).")
    return p.parse_args(argv)

@dataclass(frozen=True)
class MenuAction:
    name: str
    keys: Sequence[str]
    mouse: str | None = None


def _legacy_menu_actions() -> list[MenuAction]:
    """
    Actions copied from the legacy temp project action_strings:
      ["w","a","s","d","attack","backstep","heal","strong-attack","front-roll","left-roll","back-roll","right-roll"]
    """
    return [
        MenuAction("w", ("w",)),
        MenuAction("a", ("a",)),
        MenuAction("s", ("s",)),
        MenuAction("d", ("d",)),
        MenuAction("attack", (), mouse="left_click"),
        MenuAction("backstep", ("space",)),
        MenuAction("heal", ("r",)),
        MenuAction("strong-attack", ("Shift_L",), mouse="left_click"),
        MenuAction("front-roll", ("w", "space")),
        MenuAction("left-roll", ("a", "space")),
        MenuAction("back-roll", ("s", "space")),
        MenuAction("right-roll", ("d", "space")),
    ]


def _print_menu(actions: Sequence[MenuAction]) -> None:
    print()
    print("Choose an action (press a number key; no Enter):")
    for i, a in enumerate(actions, start=1):
        parts = []
        if a.keys:
            parts.append(" + ".join(a.keys))
        if a.mouse:
            parts.append(a.mouse)
        label = " + ".join(parts) if parts else "(noop)"
        print(f"  {i:>2}. {a.name:<13}  ({label})")
    print()
    print("Press 1-9 for actions 1..9.")
    print("For 10-12: press '1' then '0/1/2' quickly.")
    print("q = quit")
    print()

def _execute_action(x11: X11Input, a: MenuAction, hold_s: float) -> None:
    """
    Legacy semantics: hold all relevant inputs DOWN, sleep hold_s, then release.
    """
    if a.mouse == "right_click":
        # Modifiers (e.g. Shift) held while mouse button is held.
        for k in a.keys:
            x11.hold_key(k)
        try:
            x11.hold_right()
            time.sleep(hold_s)
            x11.release_right()
        finally:
            for k in reversed(list(a.keys)):
                x11.release_key(k)
        return
    if a.mouse == "left_click":
        for k in a.keys:
            x11.hold_key(k)
        try:
            x11.hold_left()
            time.sleep(hold_s)
            x11.release_left()
        finally:
            for k in reversed(list(a.keys)):
                x11.release_key(k)
        return

    # Keyboard-only (single or combo)
    x11.tap_combo(a.keys, hold_s=hold_s)


def _run_menu_loop_keypress(*, instance: str, display: str, desktop_name: str, action_ms: int) -> None:
    actions = _legacy_menu_actions()
    hold_s = max(0.0, float(action_ms) / 1000.0)

    def _run(stdscr) -> None:
        curses.curs_set(0)
        curses.noecho()
        curses.cbreak()
        stdscr.keypad(True)
        stdscr.timeout(50)  # poll every 50ms

        with X11Input(display) as x11:
            x11.focus_window_by_name(desktop_name, allow_fallback=True)

            def render(status: str) -> None:
                stdscr.erase()
                lines: list[str] = []
                lines.append(f"DSR input test | instance={instance} display={display} desktop={desktop_name}")
                lines.append("Press 1-9 for actions 1..9. For 10-12: press 1 then 0/1/2 quickly. q to quit.")
                lines.append(f"Hold duration: {hold_s:.2f}s (legacy key_delay=0.25s)")
                lines.append("")
                for i, a in enumerate(actions, start=1):
                    parts = []
                    if a.keys:
                        parts.append(" + ".join(a.keys))
                    if a.mouse:
                        parts.append(a.mouse)
                    label = " + ".join(parts) if parts else "(noop)"
                    lines.append(f"{i:>2}. {a.name:<13} ({label})")
                lines.append("")
                lines.append(status)
                for row, line in enumerate(lines[: max(0, curses.LINES - 1)]):
                    stdscr.addstr(row, 0, line[: max(0, curses.COLS - 1)])
                stdscr.refresh()

            pending_1 = False
            pending_deadline = 0.0
            status = "Ready."

            while True:
                # If we saw a leading '1' and timed out waiting for the second digit, execute action 1.
                if pending_1 and time.time() >= pending_deadline:
                    pending_1 = False
                    a = actions[0]
                    status = f"Run: 1 ({a.name})"
                    render(status)
                    _execute_action(x11, a, hold_s)
                    # Ignore any buffered keypresses while executing.
                    stdscr.timeout(0)
                    while stdscr.getch() != -1:
                        pass
                    stdscr.timeout(50)
                    status = "Ready."
                    render(status)
                    continue

                render(status)
                ch = stdscr.getch()
                if ch == -1:
                    continue

                # Quit
                if ch in (ord("q"), ord("Q")):
                    return

                # Digits
                if ord("0") <= ch <= ord("9"):
                    d = chr(ch)

                    if pending_1:
                        pending_1 = False
                        # interpret 10/11/12 only; otherwise run 1 and then treat this digit as a new input
                        if d in ("0", "1", "2"):
                            idx = 10 + int(d)  # 10,11,12
                            a = actions[idx - 1]
                            status = f"Run: {idx} ({a.name})"
                            render(status)
                            _execute_action(x11, a, hold_s)
                            stdscr.timeout(0)
                            while stdscr.getch() != -1:
                                pass
                            stdscr.timeout(50)
                            status = "Ready."
                            continue
                        # else: fall through to treat as '1' action after timeout logic? run now:
                        a1 = actions[0]
                        status = f"Run: 1 ({a1.name})"
                        render(status)
                        _execute_action(x11, a1, hold_s)
                        stdscr.timeout(0)
                        while stdscr.getch() != -1:
                            pass
                        stdscr.timeout(50)
                        status = "Ready."
                        # now process current digit as new immediate action (if 2-9 or 1 again)
                        if d == "1":
                            pending_1 = True
                            pending_deadline = time.time() + 0.35
                            status = "Got '1'... waiting for 0/1/2 for 10-12 (or timeout -> 1)."
                            continue
                        if d == "0":
                            # no action 0
                            status = "No action 0."
                            continue
                        idx2 = int(d)
                        if 1 <= idx2 <= len(actions):
                            a2 = actions[idx2 - 1]
                            status = f"Run: {idx2} ({a2.name})"
                            render(status)
                            _execute_action(x11, a2, hold_s)
                            stdscr.timeout(0)
                            while stdscr.getch() != -1:
                                pass
                            stdscr.timeout(50)
                            status = "Ready."
                        else:
                            status = f"Out of range: {idx2}"
                        continue

                    # No pending prefix
                    if d == "1" and len(actions) >= 10:
                        pending_1 = True
                        pending_deadline = time.time() + 0.35
                        status = "Got '1'... waiting for 0/1/2 for 10-12 (or timeout -> 1)."
                        continue

                    idx = int(d)
                    if idx == 0:
                        status = "No action 0."
                        continue
                    if not (1 <= idx <= len(actions)):
                        status = f"Out of range: {idx}"
                        continue

                    a = actions[idx - 1]
                    status = f"Run: {idx} ({a.name})"
                    render(status)
                    _execute_action(x11, a, hold_s)
                    # Ignore buffered keypresses while executing.
                    stdscr.timeout(0)
                    while stdscr.getch() != -1:
                        pass
                    stdscr.timeout(50)
                    status = "Ready."
                    continue

                # Ignore everything else
                status = f"Ignored key: {ch}"

    curses.wrapper(_run)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    inst = resolve_instance(args.instance)
    try:
        _run_menu_loop_keypress(
            instance=inst.name,
            display=inst.display,
            desktop_name=inst.desktop_name,
            action_ms=int(args.action_ms),
        )
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
