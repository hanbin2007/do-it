#!/usr/bin/env python3
"""Split the built SBW pack into two zips, each well under GitHub's 100 MB limit.

Part A (core): main mod + libs + small addons.
Part B (content): the big vehicle/content addons.
"""
import zipfile
from pathlib import Path

PACK_ROOT = Path("/tmp/sbw_build/SuperbWarfare-1.20.1-forge")
MODS = PACK_ROOT / "mods"
OUT_DIR = Path("/home/user/do-it/modpacks")

# Filenames of big content addons that go into Part B.
PART_B_MODS = {
    "vvp-beta-1.20.1-0.2.0.jar",                       # Vintage Vehicle Pack
    "fcp-1.0.1.jar",                                   # Frontline Combat Pack
    "ashvehicle-1.20.1-4.5-8.8.jar",                   # AshVehicle
    "sbw_more_drone_detector-2.0.2-forge-1.20.1.jar",  # More Drone Detector
    "sbw-drone-range-config-1.0.83 Forge 1.20.1.jar",  # Tactical Drone
}


def write_zip(out_path: Path, jar_names: set, info_text: str):
    print(f"-> {out_path.name}")
    if out_path.exists():
        out_path.unlink()
    with zipfile.ZipFile(out_path, "w") as zf:
        zf.writestr("SuperbWarfare-1.20.1-forge/INSTALL.txt", info_text)
        for jar in sorted(jar_names):
            src = MODS / jar
            if not src.exists():
                raise RuntimeError(f"missing: {src}")
            # jars are already deflated; ZIP_STORED avoids wasted CPU and gives us a tiny size win.
            zf.write(src, f"SuperbWarfare-1.20.1-forge/mods/{jar}", compress_type=zipfile.ZIP_STORED)
    sz = out_path.stat().st_size
    print(f"   {sz:,} bytes ({sz / 1024 / 1024:.2f} MiB)  files: {len(jar_names)}")


def main():
    all_jars = {p.name for p in MODS.iterdir()}
    part_b = all_jars & PART_B_MODS
    part_a = all_jars - PART_B_MODS

    missing = PART_B_MODS - all_jars
    if missing:
        raise RuntimeError(f"part B mods missing: {missing}")

    info_a = (
        "Superb Warfare pack - Part A (core)\n"
        "===================================\n\n"
        "This zip contains the main Superb Warfare mod, required libraries, and small addons.\n"
        "For the large content addons (Vintage Vehicle Pack, Frontline Combat Pack, AshVehicle,\n"
        "More Drone Detector, Tactical Drone) also extract Part B into the same mods/ folder.\n\n"
        "Minecraft 1.20.1 + Forge 47.x. Drop mods/ into your game directory.\n"
    )
    info_b = (
        "Superb Warfare pack - Part B (content addons)\n"
        "=============================================\n\n"
        "This zip contains large content addons for the Superb Warfare mod:\n"
        "  - Vintage Vehicle Pack\n"
        "  - Frontline Combat Pack\n"
        "  - AshVehicle\n"
        "  - More Drone Detector\n"
        "  - Tactical Drone (sbw-drone-range-config)\n\n"
        "Requires Part A (which contains the main mod and libraries).\n"
        "Extract this into the same Minecraft instance folder as Part A.\n"
    )

    write_zip(OUT_DIR / "SuperbWarfare-1.20.1-forge-partA-core.zip", part_a, info_a)
    write_zip(OUT_DIR / "SuperbWarfare-1.20.1-forge-partB-content.zip", part_b, info_b)


if __name__ == "__main__":
    main()
