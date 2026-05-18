#!/usr/bin/env python3
"""Build the Superb Warfare (SBW) modpack: main mod + all 1.20.1 Forge addons + required libs.

No optimization mods. Drop the resulting folder's contents into a Minecraft
1.20.1 + Forge instance.
"""
import hashlib
import json
import shutil
import urllib.request
import zipfile
from pathlib import Path

WORK = Path("/tmp/sbw_build")
OUT_DIR_NAME = "SuperbWarfare-1.20.1-forge"
OUT_ZIP = Path(f"/home/user/do-it/modpacks/{OUT_DIR_NAME}-complete.zip")

# Required library mods.
LIBS = [
    (
        "kotlinforforge-4.12.0-all.jar",
        "https://cdn.modrinth.com/data/ordsPcFz/versions/Zsh14XeQ/kotlinforforge-4.12.0-all.jar",
        "962fdb760409d6d71cbf079235f1ca94e3863a22",
        7442998,
    ),
    (
        "curios-forge-5.14.1+1.20.1.jar",
        "https://cdn.modrinth.com/data/vvuO3ImH/versions/IPQlZkz1/curios-forge-5.14.1%2B1.20.1.jar",
        "452175b95ad3db6ff58bb8968f6bf7a9d1e0f480",
        398066,
    ),
    (
        "geckolib-forge-1.20.1-4.8.3.jar",
        "https://cdn.modrinth.com/data/8BmcQJ2H/versions/HVdLnQMI/geckolib-forge-1.20.1-4.8.3.jar",
        "fead1d1645e16cfa02f39113481ead355230f8fd",
        1039047,
    ),
]

# Main mod.
MAIN = (
    "Superb_Warfare-0.8.9-final.jar",
    "https://cdn.modrinth.com/data/4Jenpfk2/versions/oc8KhZpb/Superb_Warfare-0.8.9-final.jar",
    None,  # sha1 filled in below
    31691008,
)

# All 1.20.1 Forge addons (filled in below). Loaded from /tmp/sbw_pack.json built by the lookup step.
# Entries: (filename, url, sha1, size).
ADDONS_JSON = Path("/tmp/sbw_pack.json")


def sha1_of(p: Path) -> str:
    h = hashlib.sha1()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, dest: Path, expected_sha1: str, expected_size: int) -> None:
    if dest.exists() and dest.stat().st_size == expected_size and sha1_of(dest) == expected_sha1:
        print(f"  [cache] {dest.name}")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"  [get  ] {dest.name} ({expected_size:,} bytes)")
    req = urllib.request.Request(url, headers={"User-Agent": "sbw-pack-builder/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r, dest.open("wb") as f:
        shutil.copyfileobj(r, f)
    got = sha1_of(dest)
    if got != expected_sha1:
        raise RuntimeError(f"SHA1 mismatch for {dest.name}: got {got}, expected {expected_sha1}")


def main():
    if WORK.exists():
        shutil.rmtree(WORK)
    pack_root = WORK / OUT_DIR_NAME
    mods_dir = pack_root / "mods"
    mods_dir.mkdir(parents=True)

    print("Downloading libraries...")
    for fn, url, sha1, size in LIBS:
        download(url, mods_dir / fn, sha1, size)

    print("Downloading Superb Warfare main mod and addons...")
    entries = json.loads(ADDONS_JSON.read_text())
    for e in entries:
        download(e["url"], mods_dir / e["filename"], e["sha1"], e["size"])

    info = pack_root / "MODPACK_INFO.txt"
    lines = [
        "Pack name : Superb Warfare + addons",
        "Game      : Minecraft 1.20.1",
        "Loader    : Forge (47.x recommended)",
        "Source    : https://modrinth.com/mod/superb-warfare",
        "",
        "This pack contains ONLY Superb Warfare, its 1.20.1 Forge addons, and the",
        "required library mods. No optimization/performance mods are included.",
        "",
        "Installation:",
        "  1) Install Minecraft 1.20.1 + Forge 47.x (any recent build).",
        "  2) Copy this folder's mods/ into your game directory.",
        "  3) Launch the game with the Forge profile.",
        "",
        "Libraries:",
    ]
    for fn, _, _, _ in LIBS:
        lines.append(f"  - {fn}")
    lines.append("")
    lines.append("Superb Warfare + addons:")
    for e in entries:
        tag = "  (main)" if e["slug"] == "superb-warfare" else ""
        lines.append(f"  - {e['filename']}{tag}")
    info.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Zipping -> {OUT_ZIP}")
    OUT_ZIP.parent.mkdir(parents=True, exist_ok=True)
    if OUT_ZIP.exists():
        OUT_ZIP.unlink()
    # Jars are already deflated; use ZIP_STORED for them to skip wasted CPU + slight size win.
    with zipfile.ZipFile(OUT_ZIP, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for p in sorted(pack_root.rglob("*")):
            if p.is_file():
                comp = zipfile.ZIP_STORED if p.suffix == ".jar" else zipfile.ZIP_DEFLATED
                zf.write(p, p.relative_to(pack_root.parent), compress_type=comp)

    total = OUT_ZIP.stat().st_size
    print(f"Done. Size: {total:,} bytes ({total / 1024 / 1024:.2f} MiB)")


if __name__ == "__main__":
    main()
