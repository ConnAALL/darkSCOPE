"""Defining the action space for the Dark Souls: Remastered game."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Literal, Tuple

# Key names
KEY_W = "w"
KEY_A = "a"
KEY_S = "s"
KEY_D = "d"
KEY_Q = "q"
KEY_SPACE = "space"
KEY_SHIFT = "Shift_L"
KEY_HEAL = "r"

# Mouse action
MouseAction = Literal["left_click", "right_click"]


@dataclass(frozen=True)
class ActionSpec:
    """
    A single logical action expressed as a simultaneous combo of keys (pressed together, then released), and/or a mouse click.
    """
    keys: Tuple[str, ...] = ()
    mouse: MouseAction | None = None


# Named action space
ACTIONS: Dict[str, ActionSpec] = {
    "move_fwd": ActionSpec(keys=(KEY_W,)),
    "move_left": ActionSpec(keys=(KEY_A,)),
    "move_back": ActionSpec(keys=(KEY_S,)),
    "move_right": ActionSpec(keys=(KEY_D,)),
    "lock_on": ActionSpec(keys=(KEY_Q,)),
    "attack": ActionSpec(mouse="left_click"),
    "strong_attack": ActionSpec(keys=(KEY_SHIFT,), mouse="left_click"),
    "heal": ActionSpec(keys=(KEY_HEAL,)),
    "backstep": ActionSpec(keys=(KEY_SPACE,)),
    "roll_fwd": ActionSpec(keys=(KEY_W, KEY_SPACE)),
    "roll_left": ActionSpec(keys=(KEY_A, KEY_SPACE)),
    "roll_back": ActionSpec(keys=(KEY_S, KEY_SPACE)),
    "roll_right": ActionSpec(keys=(KEY_D, KEY_SPACE)),
    "click_left": ActionSpec(mouse="left_click"),
    "click_right": ActionSpec(mouse="right_click"),
}


def get_action(name: str) -> ActionSpec | None:
    return ACTIONS.get(name)

