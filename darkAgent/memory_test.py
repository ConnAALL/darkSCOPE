"""
Test script for the memory reader
"""

# Import statements
from memory_tools import *
from memory_offsets import *

POLL_HZ = 60.0

# Main function
def main():
    pid, base, ptrloc = setup_memory_reader()
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
