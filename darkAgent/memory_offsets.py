"""
File for storing the memory offsets in the game
"""

BASEX_PTRLOC_RVA = 0x1C77E50  # BaseX pointer location
BASEB_PTRLOC_RVA = 0x1C8A530  # BaseB pointer location
BOSS_BASE_PTRLOC_RVA = 0x01C823A0  # Static base for the boss

# Obtaining the HP
OFF_STRUCT_PTR = 0x68  # Offset to the struct pointer
OFF_HP = 0x3E8  # Offset to the HP value
OFF_HPMAX = 0x3EC  # Offset to the max HP value

# Death count
OFF_DEATH_NUM = 0x98  # Offset to the Death Count value

# Obtaining the Asylum Demon
ASYLUM_DEMON_OFFSETS = [0x8, 0x28, 0x3E8]  # The pointer chain that was manually extracted for the health of the Asylum Demon
