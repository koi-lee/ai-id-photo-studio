#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
规格自检
==========
验证后处理脚本在所有规格 × 各档位下的输出尺寸与 DPI 是否正确。

用于在换机器 / 改脚本后快速确认环境与逻辑没坏。

用法：
  python selfcheck.py                     # 用仓库自带的 examples 图自检
  python selfcheck.py --image 我的图.jpg   # 用指定图自检
  python selfcheck.py --tiers hd,std      # 只检查部分档位
  python selfcheck.py --keep              # 保留临时产物（默认自动清理）

退出码：0 = 全部通过，1 = 有失败项（可直接接进 CI）

依赖：pillow, opencv-python, numpy
"""

import argparse
import shutil
import sys


# --- 跨平台终端编码 ---------------------------------------------------------
# Windows 默认 GBK/CP1252 终端下直接 print 中文或 ℹ️ / → 之类符号会抛
# UnicodeEncodeError 让脚本崩掉。这里做分级处理：
#   · 当前编码装不下中文 → 整条流切 UTF-8
#   · 装得下（如 cp936）  → 只把错误策略降级，中文照常显示、个别符号退化为 ?
def _fix_console_encoding():
    for stream in (sys.stdout, sys.stderr):
        enc = (getattr(stream, "encoding", "") or "").lower()
        if not enc:
            continue
        try:
            "中".encode(enc)
        except (UnicodeEncodeError, LookupError):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except (AttributeError, ValueError, OSError):
                pass
        else:
            try:
                stream.reconfigure(errors="replace")
            except (AttributeError, ValueError, OSError):
                pass


_fix_console_encoding()
import tempfile
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import process_id_photo as proc  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="证件照规格自检：校验各规格输出尺寸与 DPI")
    ap.add_argument("--image", default="",
                    help="测试源图，默认用仓库自带的 examples/male/base-portrait.jpg")
    ap.add_argument("--tiers", default="hd,std,uhd",
                    help="要检查的档位，逗号分隔（默认 hd,std,uhd）")
    ap.add_argument("--keep", action="store_true", help="保留临时产物，便于人工查看")
    args = ap.parse_args()

    here = Path(__file__).resolve().parent
    repo = here.parent.parent
    src = Path(args.image) if args.image else repo / "examples" / "male" / "base-portrait.jpg"
    if not src.exists():
        sys.exit(f"错误：找不到测试源图 {src}\n（请在仓库根目录运行，或用 --image 指定图片）")

    tier_list = [t.strip() for t in args.tiers.split(",") if t.strip()]
    bad_tiers = [t for t in tier_list if t not in proc.TIERS]
    if bad_tiers:
        sys.exit(f"错误：未知档位 {bad_tiers}，可选 {list(proc.TIERS)}")

    print(f"源图：{src}")
    print(f"规格：{len(proc.SPECS)} 种   档位：{', '.join(tier_list)}\n")

    tmp = Path(tempfile.mkdtemp(prefix="idphoto-selfcheck-"))
    results = []
    try:
        # uhd 要求源图足够宽，否则会被脚本的保护机制跳过 —— 这里单独准备一张够大的源图，
        # 让 uhd 的尺寸逻辑也能被真正覆盖
        big = None
        if "uhd" in tier_list:
            need = max(v["hd_width"] for v in proc.SPECS.values()) * 2
            im = Image.open(src).convert("RGB")
            if im.width < need:
                f = min(need / im.width, 4.0)
                im = im.resize((int(im.width * f), int(im.height * f)), Image.LANCZOS)
                big = tmp / "big-source.jpg"
                im.save(big, quality=95)
                print(f"ℹ️  uhd 档用放大源图 {im.size[0]}×{im.size[1]} 检查"
                      f"（原图宽 {Image.open(src).width}px，不足 {need}px）\n")

        for spec in proc.SPECS:
            for tier in tier_list:
                ew, eh = proc.spec_size(spec, tier)
                use = big if (tier == "uhd" and big) else src
                dst = tmp / spec / tier / "check.jpg"
                ow, oh = proc.process(use, dst, spec=spec, tier=tier, watermark=False)
                gdpi = Image.open(dst).info.get("dpi", (0, 0))[0]
                edpi = proc.TIERS[tier]["dpi"]
                results.append((spec, tier, ew, eh, ow, oh, edpi, gdpi,
                                (ow, oh) == (ew, eh) and gdpi == edpi))
    finally:
        if args.keep:
            print(f"临时产物保留在：{tmp}\n")
        else:
            shutil.rmtree(tmp, ignore_errors=True)

    label_w = max(len(s) for s in proc.SPECS) + 2
    print(f"{'规格':<{label_w}}{'档位':<6}{'期望尺寸':<14}{'实际尺寸':<14}{'DPI':<7}结果")
    print("-" * (label_w + 48))
    for spec, tier, ew, eh, ow, oh, edpi, gdpi, ok in results:
        print(f"{spec:<{label_w}}{tier:<6}{f'{ew}x{eh}':<14}{f'{ow}x{oh}':<14}{gdpi:<7}{'OK' if ok else 'FAIL'}")

    failed = [r for r in results if not r[-1]]
    print()
    if failed:
        print(f"失败 {len(failed)}/{len(results)} 项：")
        for spec, tier, ew, eh, ow, oh, edpi, gdpi, _ in failed:
            print(f"  {spec} / {tier}：期望 {ew}x{eh}@{edpi}dpi，实际 {ow}x{oh}@{gdpi}dpi")
        sys.exit(1)

    print(f"全部通过（{len(results)} 项 = {len(proc.SPECS)} 种规格 × {len(tier_list)} 个档位）")


if __name__ == "__main__":
    main()
