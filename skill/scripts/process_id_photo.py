#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
证件照后处理器（多规格）
============================
去水印 → 按规格比例裁剪 → 高清缩放 → 自适应锐化 → 输出 JPEG

支持中文政务常用规格，用 --spec 切换：
  1inch / small-1inch / large-1inch / small-2inch / 2inch / large-2inch / marriage

为什么默认输出高清档而不是 300dpi 档？
  以一寸为例：295×413 是 25×35mm 在 300dpi 下的理论像素，只有 12 万像素，
  在屏幕上放大查看会明显发糊。1181×1653 保持完全相同的比例，像素量是它的
  16 倍，屏幕清晰、冲印也够用。
  仅在提交系统强制要求时才输出标准版（--tiers 会同时给你两档）。

用法：
  python process_id_photo.py 输入图.png
  python process_id_photo.py 输入图.png --spec 2inch -n 二寸白底_黑色衬衫_经典正式
  python process_id_photo.py 输入图.png --spec marriage --tiers hd,std
  python process_id_photo.py ./原图目录/ --outdir ./out --tiers hd,std,uhd
  python process_id_photo.py 输入图.png --width 2000      # 自定义宽度
  python process_id_photo.py 输入图.png --no-watermark    # 原图无水印（第三方 API 产出）

依赖：pillow, opencv-python, numpy
  安装到隔离虚拟环境（不要全局 pip install）：
    python3 -m venv ~/.venvs/idphoto
    ~/.venvs/idphoto/bin/pip install pillow opencv-python numpy
    ~/.venvs/idphoto/bin/python process_id_photo.py <输入图>
"""

import argparse
import os
import sys

from PIL import Image, ImageFilter
import cv2
import numpy as np

# ---------------------------------------------------------------- 规格表
# px300 = 该规格在 300dpi 下的标准像素（用于标准版与宽高比）
# hd_width = 高清档宽度（屏幕查看与打印的主交付）
# head_offset = 竖版裁剪时向下偏移的像素，用于保住头顶；横版构图不适用，取 0
SPECS = {
    "small-1inch": {"label": "小一寸",     "px300": (260, 378), "hd_width": 1040, "head_offset": 20},
    "1inch":       {"label": "一寸",       "px300": (295, 413), "hd_width": 1181, "head_offset": 20},
    "large-1inch": {"label": "大一寸",     "px300": (390, 567), "hd_width": 1560, "head_offset": 20},
    "small-2inch": {"label": "小二寸",     "px300": (413, 531), "hd_width": 1652, "head_offset": 20},
    "2inch":       {"label": "二寸",       "px300": (413, 579), "hd_width": 1652, "head_offset": 20},
    "large-2inch": {"label": "大二寸",     "px300": (413, 630), "hd_width": 1652, "head_offset": 20},
    "marriage":    {"label": "结婚证合影", "px300": (626, 413), "hd_width": 2504, "head_offset": 0},
}
# 驾照与"小一寸"尺寸相同（22×32mm），单独列一个别名方便按用途选
SPECS["driving-license"] = dict(SPECS["small-1inch"], label="驾照")
DEFAULT_SPEC = "1inch"

# 档位定义：scale 为相对高清档宽度的倍数
TIERS = {
    "hd":  {"scale": 1,    "dpi": 1200, "quality": 96, "subdir": ""},
    "std": {"scale": None, "dpi": 300,  "quality": 96, "subdir": "{w}x{h}标准版"},  # 用 px300 尺寸
    "uhd": {"scale": 2,    "dpi": 2400, "quality": 98, "subdir": "超清版"},
}
DEFAULT_OUTDIR = "./id_photos"

# AI 生成图右下角水印的占比（相对图宽/高）—— 按需微调
WM_RATIO_W = 0.176
WM_RATIO_H = 0.091

IMAGE_EXT = (".png", ".jpg", ".jpeg", ".webp", ".bmp")


def spec_size(spec, tier):
    """返回 (宽, 高)。"""
    cfg = SPECS[spec]
    pw, ph = cfg["px300"]
    ratio = pw / ph                      # 以 300dpi 标准像素的比值为准
    if tier == "std":
        w = pw
    else:
        w = round(cfg["hd_width"] * TIERS[tier]["scale"])
    return w, round(w / ratio)


def remove_watermark(img_np):
    """用 OpenCV inpaint 抹掉右下角的水印。"""
    h, w = img_np.shape[:2]
    mask = np.zeros((h, w), dtype=np.uint8)
    mask[h - int(h * WM_RATIO_H):h, w - int(w * WM_RATIO_W):w] = 255
    return cv2.inpaint(img_np, mask, 3, cv2.INPAINT_TELEA)


def crop_to_spec(img, spec):
    """按规格比例居中裁剪。

    源图比目标"更高"→ 切上下，并下移 head_offset 保住头顶；
    源图比目标"更宽"→ 切左右。横版规格 head_offset 为 0。
    """
    cfg = SPECS[spec]
    pw, ph = cfg["px300"]
    ratio = pw / ph
    offset = cfg["head_offset"]

    w, h = img.size
    new_h = int(w / ratio)
    if new_h <= h:
        top = min((h - new_h) // 2 + offset, h - new_h)
        return img.crop((0, top, w, top + new_h))
    new_w = int(h * ratio)
    left = (w - new_w) // 2
    return img.crop((left, 0, left + new_w, h))


def sharpen_percent(src_w, out_w):
    """按缩放比自适应锐化强度，避免过锐出光晕。

    源图/目标 ≥1.2（大幅缩小）→ 32%
    1.0–1.2（小幅缩小）        → 45%
    <1.0（放大）               → 40%
    """
    scale = src_w / out_w
    if scale >= 1.2:
        return 32
    if scale >= 1.0:
        return 45
    return 40


def process(src, dst, spec=DEFAULT_SPEC, tier="hd", width=None,
            watermark=True, sharpen=True):
    img = Image.open(src).convert("RGB")
    arr = np.array(img)
    if watermark:
        arr = remove_watermark(arr)
    img = Image.fromarray(arr)

    # 先在原始分辨率下按规格比例裁剪，避免二次损失
    img = crop_to_spec(img, spec)
    src_w = img.size[0]

    out_w, out_h = (width, round(width * spec_size(spec, tier)[1] / spec_size(spec, tier)[0])) \
        if width else spec_size(spec, tier)

    img = img.resize((out_w, out_h), Image.LANCZOS)

    if sharpen:
        pct = sharpen_percent(src_w, out_w)
        img = img.filter(ImageFilter.UnsharpMask(radius=1.2, percent=pct, threshold=3))

    os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
    dpi = TIERS[tier]["dpi"]
    quality = TIERS[tier]["quality"]
    img.save(dst, "JPEG", quality=quality, dpi=(dpi, dpi), subsampling=0)
    return out_w, out_h


def build_name(src, name, outdir, spec=DEFAULT_SPEC):
    if name:
        stem = name
    else:
        label = SPECS[spec]["label"]
        stem = f"{label}白底_" + os.path.splitext(os.path.basename(src))[0]
    if not stem.lower().endswith(".jpg"):
        stem += ".jpg"
    return os.path.join(outdir, stem)


def main():
    p = argparse.ArgumentParser(
        description="证件照后处理器：去水印 → 规格裁剪 → 高清缩放 → 自适应锐化",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="可用规格：\n  " + "\n  ".join(
            f"{k:<14} {v['label']}  {v['px300'][0]}x{v['px300'][1]} @300dpi → 高清 {v['hd_width']}px 宽"
            for k, v in SPECS.items()
        ),
    )
    p.add_argument("input", help="输入图片路径，或包含图片的目录（批量）")
    p.add_argument("--spec", default=DEFAULT_SPEC, choices=list(SPECS),
                   help=f"规格，默认 {DEFAULT_SPEC}（一寸）")
    p.add_argument("-n", "--name", default="", help="输出文件名（不含目录）")
    p.add_argument("--outdir", default=DEFAULT_OUTDIR, help=f"输出目录，默认 {DEFAULT_OUTDIR}")
    p.add_argument("--tiers", default="",
                   help="一键输出多档，逗号分隔：hd,std,uhd。各档自动输出到独立子目录，"
                        "避免同名覆盖（标准版覆盖高清版是踩过的坑）")
    p.add_argument("--width", type=int, default=None, help="自定义输出宽度（高度按规格比例自动计算）")
    p.add_argument("--std", action="store_true", help="等价于 --tiers std（单出标准版）")
    p.add_argument("--no-watermark", action="store_true", help="跳过去水印步骤")
    p.add_argument("--no-sharpen", action="store_true", help="跳过锐化步骤")
    args = p.parse_args()

    if not os.path.exists(args.input):
        sys.exit(f"错误：找不到输入路径 {args.input}")

    # 决定输出哪些档位
    if args.tiers:
        wanted = [t.strip() for t in args.tiers.split(",") if t.strip()]
        bad = [t for t in wanted if t not in TIERS]
        if bad:
            sys.exit(f"错误：未知档位 {bad}，可选 {list(TIERS)}")
    elif args.std:
        wanted = ["std"]
    else:
        wanted = ["hd"]

    if os.path.isdir(args.input):
        files = sorted(
            os.path.join(args.input, f)
            for f in os.listdir(args.input)
            if f.lower().endswith(IMAGE_EXT)
        )
        if not files:
            sys.exit(f"错误：目录中没有图片 {args.input}")
    else:
        files = [args.input]

    cfg = SPECS[args.spec]
    made = []
    for src in files:
        for tier in wanted:
            w, h = spec_size(args.spec, tier)
            subdir = TIERS[tier]["subdir"].format(w=w, h=h)
            outdir = os.path.join(args.outdir, subdir) if subdir else args.outdir

            # 超清档必须真的放得下，否则是插值假细节
            if tier == "uhd":
                probe = Image.open(src)
                cropped_w = crop_to_spec(probe.convert("RGB"), args.spec).size[0]
                if cropped_w < w:
                    print(f"[跳过] {os.path.basename(src)} 超清档：源图裁剪后仅 {cropped_w}px 宽 "
                          f"< 需要的 {w}px，放大只会得到假细节")
                    continue

            dst = build_name(src, args.name, outdir, args.spec)
            ow, oh = process(src, dst, spec=args.spec, tier=tier, width=args.width,
                             watermark=not args.no_watermark,
                             sharpen=not args.no_sharpen)
            print(f"[完成] {os.path.basename(src)} -> {dst} ({ow}x{oh}, {TIERS[tier]['dpi']}dpi)")
            made.append(dst)

    print(f"\n规格：{cfg['label']}（{cfg['px300'][0]}x{cfg['px300'][1]} @300dpi）"
          f"，共输出 {len(made)} 个文件，根目录：{args.outdir}")


if __name__ == "__main__":
    main()
