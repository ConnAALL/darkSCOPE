"""
Test script for the memory reader
"""

# Import statements
import argparse

from memory_tools import *
from memory_offsets import *

POLL_HZ = 60.0

# Parse args
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Read DSR memory for a specific instance.")
    p.add_argument("--instance", required=True, help="Instance name from /root/config/dsr_instances.json (e.g. dsr-1).")
    return p.parse_args()

# Main function
def main():
    args = parse_args()
    pid, base, ptrloc = setup_memory_reader(instance=args.instance)
    with open(f"/proc/{pid}/mem", "rb", buffering=0) as mem:  # Open the memory of the process
        dt = 1.0 / POLL_HZ
        while True:
            basex = read_typed(mem, ptrloc, "u64")  # Read the baseX pointer
            struct_base = read_typed_offset(mem, basex, OFF_STRUCT_PTR, "u64")  # Read the struct base
            hp = read_typed_offset(mem, struct_base, OFF_HP, "i32")  # Read the HP value
            hpmax = read_typed_offset(mem, struct_base, OFF_HPMAX, "i32")  # Read the max HP value
            print(f"\rHP {hp} / {hpmax}", end="", flush=True)  # Print the HP value
            time.sleep(dt)  # Sleep for the polling rate

if __name__ == "__main__":
    main()
