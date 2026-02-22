from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Iterable
from Xlib import X, XK, display as xdisplay
from Xlib.ext import xtest


@dataclass(frozen=True)
class FoundWindow:
    """Class for storing the found window information."""
    window_id: int
    name: str | None


def _decode_prop_value(v) -> str | None:
    """Decode the property value."""
    if v is None:
        return None
    if isinstance(v, str):
        return v
    if isinstance(v, (bytes, bytearray)):
        s = bytes(v).decode("utf-8", errors="ignore").strip("\x00").strip()
        return s or None
    # Xlib may hand back arrays; just stringify.
    s = str(v).strip()
    return s or None


class X11Input:
    """
    Minimal X11 input injector (keys + mouse) via the XTEST extension.

    Designed to work inside the DSR container, targeting an instance's Xorg display (e.g. ':90').
    """

    def __init__(self, display_str: str):
        self.display_str = display_str
        self.disp = xdisplay.Display(display_str)

        if not self.disp.has_extension("XTEST"):
            raise RuntimeError(f"XTEST extension not available on display {display_str}")

        self.root = self.disp.screen().root

    def close(self) -> None:
        try:
            self.disp.close()
        except Exception:
            pass

    def __enter__(self) -> "X11Input":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def _window_name(self, w) -> str | None:
        # WM_NAME (often enough)
        try:
            name = w.get_wm_name()
            out = _decode_prop_value(name)
            if out:
                return out
        except Exception:
            pass

        # _NET_WM_NAME (UTF-8)
        try:
            atom = self.disp.intern_atom("_NET_WM_NAME")
            prop = w.get_full_property(atom, X.AnyPropertyType)
            if prop is not None:
                out = _decode_prop_value(prop.value)
                if out:
                    return out
        except Exception:
            pass

        return None

    def find_window_by_name(self, name: str) -> FoundWindow | None:
        """
        Return the first window whose title matches exactly `name`.
        """
        target = name.strip()
        if not target:
            return None

        # DFS over the window tree.
        stack = [self.root]
        seen = set()
        while stack:
            w = stack.pop()
            try:
                wid = int(w.id)
            except Exception:
                continue
            if wid in seen:
                continue
            seen.add(wid)

            wname = self._window_name(w)
            if wname == target:
                return FoundWindow(window_id=wid, name=wname)

            try:
                qt = w.query_tree()
                # Children order isn't important; push all.
                stack.extend(qt.children)
            except Exception:
                continue

        return None

    def _get_window(self, window_id: int):
        return self.disp.create_resource_object("window", window_id)

    def focus_window_by_name(self, name: str, *, allow_fallback: bool = True) -> FoundWindow | None:
        """
        Try to focus a window titled `name`. If not found and allow_fallback=True,
        focus the root window to at least make XTEST events land somewhere.
        """
        found = self.find_window_by_name(name)
        if found is None:
            if not allow_fallback:
                return None
            self.root.set_input_focus(X.RevertToParent, X.CurrentTime)
            self.disp.sync()
            return None

        w = self._get_window(found.window_id)
        try:
            w.raise_window()
        except Exception:
            pass
        try:
            w.set_input_focus(X.RevertToParent, X.CurrentTime)
        except Exception:
            # Some setups refuse focus changes; still proceed.
            pass
        self.disp.sync()
        return found

    def _keysym_for_key(self, key: str) -> int:
        k = key.strip()
        if not k:
            raise ValueError("Empty key name")

        # Common aliases
        aliases = {
            "esc": "Escape",
            "escape": "Escape",
            "enter": "Return",
            "return": "Return",
            "space": "space",
            "backspace": "BackSpace",
            "tab": "Tab",
            "left": "Left",
            "right": "Right",
            "up": "Up",
            "down": "Down",
        }
        k = aliases.get(k, k)

        keysym = XK.string_to_keysym(k)
        if keysym == 0 and len(k) == 1:
            keysym = XK.string_to_keysym(k.lower())
        if keysym == 0:
            raise ValueError(f"Unknown key name '{key}' (after alias -> '{k}')")
        return keysym

    def _keycode_for_key(self, key: str) -> int:
        keysym = self._keysym_for_key(key)
        keycode = self.disp.keysym_to_keycode(keysym)
        if not keycode:
            raise RuntimeError(f"Could not resolve keycode for key '{key}' on display {self.display_str}")
        return keycode

    def _fake_key(self, event_type: int, key: str) -> None:
        keycode = self._keycode_for_key(key)
        xtest.fake_input(self.disp, event_type, keycode)

    def hold_key(self, key: str) -> None:
        self._fake_key(X.KeyPress, key)
        self.disp.sync()

    def release_key(self, key: str) -> None:
        self._fake_key(X.KeyRelease, key)
        self.disp.sync()

    def tap_combo(self, keys: Iterable[str], *, hold_s: float = 0.05) -> None:
        keys_list = [k for k in keys if str(k).strip()]
        if not keys_list:
            return

        # Press in-order; release reverse-order.
        for k in keys_list:
            self.hold_key(k)
        if hold_s > 0:
            time.sleep(hold_s)
        for k in reversed(keys_list):
            self.release_key(k)

    def _fake_button(self, event_type: int, button: int) -> None:
        xtest.fake_input(self.disp, event_type, button)

    def hold_left(self) -> None:
        """Send left mouse button down only (no release)."""
        self._fake_button(X.ButtonPress, 1)
        self.disp.sync()

    def release_left(self) -> None:
        """Send left mouse button up only."""
        self._fake_button(X.ButtonRelease, 1)
        self.disp.sync()

    def hold_right(self) -> None:
        """Send right mouse button down only (no release)."""
        self._fake_button(X.ButtonPress, 3)
        self.disp.sync()

    def release_right(self) -> None:
        """Send right mouse button up only."""
        self._fake_button(X.ButtonRelease, 3)
        self.disp.sync()
