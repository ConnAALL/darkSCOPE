"""
Test script for the memory reader
"""

# Import statements
import argparse

from memory_tools import *
from memory_offsets import *
import time

POLL_HZ = 60.0

# Parse args
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Read DSR memory for a specific instance.")
    p.add_argument("--instance", required=True, help="Instance name from /root/config/dsr_instances.json (e.g. dsr-1).")
    return p.parse_args()

# Main function
def main():
    args = parse_args()
    pid, base, basex_ptrloc, baseb_ptrloc, boss_static_base = setup_memory_reader(instance=args.instance)
    with open(f"/proc/{pid}/mem", "rb", buffering=0) as mem:  # Open the memory of the process
        dt = 1.0 / POLL_HZ
        while True:
            # --- Read Health (BaseX) ---
            basex = read_typed(mem, basex_ptrloc, "u64")  # Read the baseX pointer
            struct_base = read_typed_offset(mem, basex, OFF_STRUCT_PTR, "u64")  # Read the struct base
            hp = read_typed_offset(mem, struct_base, OFF_HP, "i32")  # Read the HP value
            hpmax = read_typed_offset(mem, struct_base, OFF_HPMAX, "i32")  # Read the max HP value
            
            # --- Read Deaths (BaseB) ---
            game_data_struct_base = read_typed(mem, baseb_ptrloc, "u64") # Read the struct base of the BaseB pointer
            death_num = read_typed_offset(mem, game_data_struct_base, OFF_DEATH_NUM, "i32") # Read the death number
            
            # --- Read Boss HP ---
            boss_root_ptr = read_typed(mem, boss_static_base, "u64") 
            boss_hp = read_pointer_chain(mem, boss_root_ptr, ASYLUM_DEMON_OFFSETS, "i32") 
            
            # --- Output ---
            print(f"\rHP {hp} / {hpmax} | Deaths {death_num} | Boss HP {boss_hp}    ", end="", flush=True)
            time.sleep(dt)  # Sleep for the polling rate

if __name__ == "__main__":
    main()
