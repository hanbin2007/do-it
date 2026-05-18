#!/usr/bin/env python3
"""Build a complete, ready-to-use modpack zip from a Modrinth .mrpack file.

Output structure (drop contents into a Minecraft instance folder):
  pack-root/
    mods/                          (all mod jars)
    config/                        (from overrides/config)
    configureddefaults/            (from overrides/configureddefaults, applied by ConfiguredDefaults mod)
    options.txt etc.               (any other override files)
    MODPACK_INFO.txt               (human readable summary)
"""
import hashlib
import json
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

MRPACK = Path("/home/user/do-it/modpacks/Hammer-1.19.0+1.20.1.forge.mrpack")
WORK = Path("/tmp/hammer_build")
OUT_DIR_NAME = "Hammer-1.19.0-1.20.1-forge"
OUT_ZIP = Path(f"/home/user/do-it/modpacks/{OUT_DIR_NAME}-complete.zip")


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
    req = urllib.request.Request(url, headers={"User-Agent": "hammer-pack-builder/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r, dest.open("wb") as f:
        shutil.copyfileobj(r, f)
    got = sha1_of(dest)
    if got != expected_sha1:
        raise RuntimeError(f"SHA1 mismatch for {dest.name}: got {got}, expected {expected_sha1}")


def main():
    if WORK.exists():
        shutil.rmtree(WORK)
    WORK.mkdir(parents=True)

    extracted = WORK / "extracted"
    extracted.mkdir()
    with zipfile.ZipFile(MRPACK) as z:
        z.extractall(extracted)

    index = json.loads((extracted / "modrinth.index.json").read_text())
    print(f"Pack: {index['name']} {index['versionId']}")
    print(f"Deps: {index['dependencies']}")
    print(f"Mods: {len(index['files'])}")

    pack_root = WORK / OUT_DIR_NAME
    pack_root.mkdir()

    overrides = extracted / "overrides"
    if overrides.exists():
        for item in overrides.iterdir():
            target = pack_root / item.name
            if item.is_dir():
                shutil.copytree(item, target)
            else:
                shutil.copy2(item, target)
        print(f"Copied overrides: {[p.name for p in overrides.iterdir()]}")

    print("Downloading mods...")
    for f in index["files"]:
        path = f["path"]
        url = f["downloads"][0]
        sha1 = f["hashes"]["sha1"]
        size = f["fileSize"]
        dest = pack_root / path
        download(url, dest, sha1, size)

    info = pack_root / "MODPACK_INFO.txt"
    lines = [
        f"Pack name : {index['name']}",
        f"Version   : {index['versionId']}",
        f"Game      : Minecraft {index['dependencies'].get('minecraft', '?')}",
        f"Loader    : Forge {index['dependencies'].get('forge', '?')}",
        f"Source    : https://modrinth.com/modpack/hammer",
        "",
        "Installation:",
        "  1) Install Minecraft 1.20.1 with Forge "
        + index['dependencies'].get('forge', '?')
        + " (e.g. via your launcher: PCL2, HMCL, vanilla launcher, etc.).",
        "  2) Copy the contents of this folder (mods/, config/, configureddefaults/, etc.) "
        "into your Minecraft instance's game directory (.minecraft or instance folder).",
        "  3) Launch the game with the Forge profile.",
        "",
        "Mods included:",
    ]
    for f in sorted(index["files"], key=lambda x: x["path"].lower()):
        lines.append(f"  - {Path(f['path']).name}")
    info.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Zipping -> {OUT_ZIP}")
    OUT_ZIP.parent.mkdir(parents=True, exist_ok=True)
    if OUT_ZIP.exists():
        OUT_ZIP.unlink()
    with zipfile.ZipFile(OUT_ZIP, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for p in sorted(pack_root.rglob("*")):
            if p.is_file():
                zf.write(p, p.relative_to(pack_root.parent))

    total = OUT_ZIP.stat().st_size
    print(f"Done. Size: {total:,} bytes ({total / 1024 / 1024:.2f} MiB)")


if __name__ == "__main__":
    main()
