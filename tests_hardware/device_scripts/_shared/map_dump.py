"""Included into device scripts at render: one labelled heap block map, delimited exactly as
tests_hardware/heap_map.py's parse_labelled() reads it; mem_info(1) writes the map to the board's console and
allocates nothing, so dumping cannot perturb what it shows. No collect first: the caller decides that."""

import micropython


def dump(label: str) -> None:
    print(f"=== MAP {label} ===")
    micropython.mem_info(1)
    print(f"=== ENDMAP {label} ===")
