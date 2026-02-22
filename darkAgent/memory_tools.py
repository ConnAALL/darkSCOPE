"""
Tools for reading a specific memmory offset in the game by using process ID and obtaining values
"""

# Import statements
import os
import re
import struct
from typing import Callable, Dict

from memory_offsets import *

from instance_config import resolve_instance

PROC_SUBSTR = "DarkSoulsRemastered.exe"  # Substring for finding the game process


def _read_proc_environ(pid: int) -> bytes:
    try:
        with open(f"/proc/{pid}/environ", "rb") as f:
            return f.read()
    except Exception:
        return b""


def _env_has_wineprefix(pid: int, wineprefix: str) -> bool:
    if not wineprefix:
        return False
    env = _read_proc_environ(pid)
    if not env:
        return False
    return f"WINEPREFIX={wineprefix}".encode("utf-8") in env


def find_game_pid(substr: str, maps_needle: str, wineprefix: str | None = None) -> int:
    """
    Finds the process ID of the game process by searching for the substring in the command line and checking if the module is in the maps
    Args:
        substr: Substring for finding the game process. e.g. "DarkSoulsRemastered.exe"
        maps_needle: Substring for finding the module in the maps e.g. "DarkSoulsRemastered.exe"
        wineprefix: If provided, only match processes whose environment has WINEPREFIX=<wineprefix>
    Returns:
        The process ID of the game process. If not found, raises a RuntimeError
    """
    for d in os.listdir("/proc"):  # Iterate over all processes
        if not d.isdigit():  # If the process is not a number, skip it
            continue
        pid = int(d)  # Convert the process ID to an integer
        try:
            # Open the command line of the process and read the output
            cmd = open(f"/proc/{pid}/cmdline", "rb").read().decode(errors="ignore")
            if substr not in cmd:
                continue
            if wineprefix is not None and not _env_has_wineprefix(pid, wineprefix):
                continue
            # Only accept this PID if its maps contains the module
            with open(f"/proc/{pid}/maps", "r", encoding="utf-8", errors="ignore") as f:
                if any(maps_needle.lower() in line.lower() for line in f):  # If the module is in the maps, return the process ID
                    return pid
        except Exception:
            pass
    raise RuntimeError(f"Could not find process containing '{substr}' with module in maps")



def module_base(pid: int, needle: str) -> int:
    """
    Finds the base address of the module by searching for the needle in the maps
    Args:
        pid: The process ID of the game process. e.g. 1234
        needle: The substring to search for in the maps. e.g. "DarkSoulsRemastered.exe"
    Returns:
        The base address of the module. If not found, raises a RuntimeError
    """
    with open(f"/proc/{pid}/maps", "r", encoding="utf-8") as f:
        for line in f:
            if needle not in line:
                continue
            m = re.match(r"^([0-9a-fA-F]+)-", line)  # Match the base address of the module
            if m:
                return int(m.group(1), 16)  # Convert the base address to an integer
    raise RuntimeError("Could not find module base in maps")


def read_exact(mem, addr: int, n: int) -> bytes:
    """
    Reads exactly n bytes from the memory at the given address
    Args:
        mem: The memory object
        addr: The address to read from
        n: The number of bytes to read
    Returns:
        The bytes read from the memory
    """
    mem.seek(addr)
    b = mem.read(n)
    if len(b) != n:
        raise RuntimeError(f"Short read at 0x{addr:X}")
    return b


def u64(mem, addr: int) -> int:
    """
    Reads a 64-bit unsigned integer from the memory at the given address
    Args:
        mem: The memory object
        addr: The address to read from
    Returns:
        The 64-bit unsigned integer read from the memory
    """
    return struct.unpack("<Q", read_exact(mem, addr, 8))[0]


def i32(mem, addr: int) -> int:
    """
    Reads a 32-bit signed integer from the memory at the given address
    Args:
        mem: The memory object
        addr: The address to read from
    Returns:
        The 32-bit signed integer read from the memory
    """
    return struct.unpack("<i", read_exact(mem, addr, 4))[0]


def type_readers() -> Dict[str, Callable]:
    """
    Maps type strings like "u64" to concrete reader functions (mem, addr) -> value.
    """
    return {"u64": u64, "i32": i32}


def read_typed(mem, addr: int, type_str: str):
    """
    Generic typed read from an absolute address.

    Example:
        hp = read_typed(mem, struct_base + OFF_HP, "i32")
    """
    readers = type_readers()
    reader = readers.get(type_str)
    if reader is None:
        raise ValueError(f"Unknown type_str '{type_str}'. Supported: {sorted(readers.keys())}")
    return reader(mem, addr)


def read_typed_offset(mem, base_addr: int, offset: int, type_str: str):
    """
    Reads a typed value from the memory at the given address with the given offset
    Args:
        mem: The memory object
        base_addr: The base address of the module
        offset: The offset to the value
        type_str: The type of the value to read
    Returns:
        The value read from the memory
    """
    return read_typed(mem, base_addr + offset, type_str)


def setup_memory_reader(instance: str | None = None) -> tuple[int, int, int]:
    """
    Sets up the memory reader by finding the process ID, base address, and pointer location of the baseX pointer
    Args:
        instance: If provided, target that instance by selecting the game PID whose environment matches the instance WINEPREFIX.
    Returns:
        The process ID, base address, and pointer location of the baseX pointer
    """
    wineprefix = None
    if instance is not None:
        inst = resolve_instance(instance)
        if not inst.wineprefix:
            raise RuntimeError(f"Instance '{instance}' is missing 'wineprefix' in /root/config/dsr_instances.json")
        wineprefix = inst.wineprefix
    pid = find_game_pid(PROC_SUBSTR, PROC_SUBSTR, wineprefix=wineprefix)  # Find the process ID of the game process
    base = module_base(pid, PROC_SUBSTR)  # Find the base address of the module
    ptrloc = base + BASEX_PTRLOC_RVA  # Find the pointer location of the baseX pointer
    return pid, base, ptrloc
