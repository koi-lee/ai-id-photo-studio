#!/usr/bin/env python3
"""Reject unreviewed or changed image assets in the public repository."""

import hashlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IMAGE_SUFFIXES = {
    ".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp", ".tif", ".tiff",
    ".bmp", ".gif", ".avif", ".jfif", ".jp2", ".jxl", ".raw", ".dng",
    ".cr2", ".cr3", ".nef", ".nrw", ".arw", ".orf", ".rw2", ".raf",
    ".srw", ".pef", ".x3f", ".3fr", ".fff", ".dcr", ".kdc", ".erf",
    ".mef", ".mos", ".mrw", ".rwl", ".iiq", ".bay",
}

# Existing public example image baseline from base commit 7e51ca9.
# Hash equality is not proof of image provenance; changed assets require review.
APPROVED_SHA256 = {
    "examples/couple/black-suit-ivory-dress.png": "2fc0d2619a7dcd43d7bc0e04eb54139e8b496f46cb9ab0bfebe8123b04b555f8",
    "examples/couple/blue-white-shirts.png": "3c69a6e89248309f69493a91e53dfae7174175ac876e9a374087cff04136e564",
    "examples/couple/couple-white-shirts-red-preview.png": "af00f6c67184bd893142d8521a45fd74d611583ca565961b40b0bc868e1b9dd1",
    "examples/couple/grey-suit-ivory-dress.png": "bbe3274425a60817b3b24472dc6344b053dcb52f66d77973e2b3dbad92d0ee58",
    "examples/couple/ivory-chinese-outfits.png": "6df32d25d6dc12c2c67234cf64da9b92d4c01920bb0830caf12324d06816ca47",
    "examples/female/base-portrait.jpg": "32001b5a26ab1789f56f09e4763b68c9cbeb0c6450e85b2fae125eb9a52327ef",
    "examples/female/blue-bg-navy-suit.jpg": "f8dd68a68bf1509e185c8048742b420633a1cf5931d51791e8fb9e13231dedc1",
    "examples/female/red-bg-black-suit.jpg": "91ebd102e111cc6273b377df8ec614538247dab88d68f0cdcd0eacfb4b79bc31",
    "examples/female/white-bg-black-suit.jpg": "5b3942aaa15153c2474129c49bcac395b90c4104979ebb468e743b7f61aca0f5",
    "examples/female/white-bg-cream-shirt.jpg": "8f294dbfa17e75373b7196bc44df6e8df30b483d66a52bfa8b4c55734041b3f0",
    "examples/male/base-portrait.jpg": "d62743c6daf23d2967eeb9b9f02382ba97fc780b3374a44bb98b80fa296b9f4c",
    "examples/male/blue-bg-navy-suit.jpg": "abde5e490957960a94889fdaa2d48c1291965c1ed2d04df9d1d9ba6e91343fa0",
    "examples/male/red-bg-black-suit.jpg": "00726bb579357ab03a09ca6fc2edcfead01f8c98601a8c2bd0e62f2dbfde3e27",
    "examples/male/white-bg-black-suit.jpg": "be4eb46f929cf5caf11407e33ef96373964642e487f52cba944227815c2a4bb6",
    "examples/male/white-bg-light-blue-shirt.jpg": "9c95117e108390eb4d991553c318125b7baebc98f1c7c9d488542da3ef9b6669",
}


def main() -> int:
    result = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        check=True,
        stdout=subprocess.PIPE,
    )
    tracked = {
        name.decode("utf-8")
        for name in result.stdout.split(b"\0")
        if name and Path(name.decode("utf-8")).suffix.lower() in IMAGE_SUFFIXES
    }
    failures = []
    for path in sorted(tracked - APPROVED_SHA256.keys()):
        failures.append(f"未审核的图片文件：{path}")
    for path in sorted(tracked & APPROVED_SHA256.keys()):
        asset = ROOT / path
        if asset.is_symlink() or not asset.is_file():
            failures.append(f"图片不是普通文件：{path}")
            continue
        digest = hashlib.sha256(asset.read_bytes()).hexdigest()
        if digest != APPROVED_SHA256[path]:
            failures.append(f"图片哈希变化，需核验来源后更新白名单：{path}")

    if failures:
        print("公开仓库图片检查失败：", file=sys.stderr)
        print("\n".join(f"- {item}" for item in failures), file=sys.stderr)
        return 1
    print(f"公开仓库图片检查通过：{len(tracked)} 张图片均与当前白名单基线一致。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
