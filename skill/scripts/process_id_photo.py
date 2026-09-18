#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中国1寸证件照处理器（通用版）
==============================
去水印 → 按 25:35 比例裁剪 → 高清缩放 → 轻度锐化 → 输出 JPEG

为什么默认输出 1181×1653 而不是 295×413？
  295×413 是 1 寸照片在 300dpi 下的理论像素值，但它只有 12 万像素，
  在手机/电脑屏幕上放大查看会明显发糊。1181×1653 保持完全相同的
  25:35 比例，像素量是它的 16 倍，屏幕清晰、冲印也够用。
  仅在提交系统强制要求时才用 --std 输出 295×413。

用法：
  python process_id_photo.py 输入图.png
  python process_id_photo.py 输入图.png --outdir ./workbuddy1寸照 -n 一寸白底_黑色衬衫_经典正式
  python process_id_photo.py ./原图目录/ --outdir ./workbuddy1寸照
  python process_id_photo.py 输入图.png --std          # 标准小图 295×413
  python process_id_photo.py 输入图.png --width 2000   # 自定义宽度
  python process_id_photo.py 输入图.png --no-watermark # 原图无水印

依赖：pillow, opencv-python, numpy
  安装到隔离虚拟环境（不要全局 pip install）：
    python3 -m venv ~/.venvs/idphoto
    ~/.venvs/idphoto/bin/pip install pillow opencv-python
    ~/.venvs/idphoto/bin/python process_id_photo.py <输入图>
"""

import argparse
import os
import sys

from PIL import Image, ImageFilter
import cv2
import numpy as np

# 1 寸比例：25mm x 35mm
TARGET_RATIO = 295 / 413  # ≈ 0.7143

HD_WIDTH = 1181    # 高清默认宽度，高度自动 ≈1653
STD_WIDTH = 295    # 标准小图宽度，高度 413

DEFAULT_OUTDIR = "./id_photos"

# AI 生成图右下角水印的占比（相对图宽/高）—— 按需微调
WM_RATIO_W = 0.176
WM_RATIO_H = 0.091

IMAGE_EXT = (".png", ".jpg", ".jpeg", ".webp", ".bmp")


def remove_watermark(img_np):
    """用 OpenCV inpaint 抹掉右下角的水印。"""
    h, w = img_np.shape[:2]
    mask = np.zeros((h, w), dtype=np.uint8)
    mask[h - int(h * WM_RATIO_H):h, w - int(w * WM_RATIO_W):w] = 255
    return cv2.inpaint(img_np, mask, 3, cv2.INPAINT_TELEA)


def crop_to_id_ratio(img):
    """按 1 寸比例居中裁剪，略微下移以保住头顶。"""
    w, h = img.size
    new_h = int(w / TARGET_RATIO)
    if new_h <= h:
        top = min((h - new_h) // 2 + 20, h - new_h)
        return img.crop((0, top, w, top + new_h))
    new_w = int(h * TARGET_RATIO)
    left = (w - new_w) // 2
    return img.crop((left, 0, left + new_w, h))


def build_name(src, name, outdir):
    if name:
        stem = name
    else:
        stem = "一寸白底_" + os.path.splitext(os.path.basename(src))[0]
    if not stem.lower().endswith(".jpg"):
        stem += ".jpg"
    return os.path.join(outdir, stem)


def process(src, dst, watermark=True, width=HD_WIDTH, sharpen=True):
    img = Image.open(src).convert("RGB")
    arr = np.array(img)
    if watermark:
        arr = remove_watermark(arr)
    img = Image.fromarray(arr)

    # 先在原始分辨率下按 1 寸比例裁剪，避免二次损失
    img = crop_to_id_ratio(img)

    # 一步 LANCZOS 缩放到目标尺寸
    out_w = width
    out_h = round(width / TARGET_RATIO)
    img = img.resize((out_w, out_h), Image.LANCZOS)

    # 轻度锐化，补偿重采样带来的柔化
    if sharpen:
        img = img.filter(ImageFilter.UnsharpMask(radius=1.2, percent=55, threshold=3))

    os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
    # dpi=1200 时 1181px 正好对应 25mm，冲印尺寸标准
    img.save(dst, "JPEG", quality=96, dpi=(1200, 1200), subsampling=0)
    return out_w, out_h


def main():
    p = argparse.ArgumentParser(
        description="中国1寸证件照处理器：去水印 → 裁剪 → 高清缩放 → 锐化",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("input", help="输入图片路径，或包含图片的目录（批量）")
    p.add_argument("-n", "--name", default="", help="输出文件名（不含目录）")
    p.add_argument("--outdir", default=DEFAULT_OUTDIR, help=f"输出目录，默认 {DEFAULT_OUTDIR}")
    p.add_argument("--width", type=int, default=HD_WIDTH,
                   help=f"输出宽度像素，默认 {HD_WIDTH}（高度按 1 寸比例自动计算）")
    p.add_argument("--std", action="store_true",
                   help=f"输出标准小图 {STD_WIDTH}×413（仅系统强制要求时使用）")
    p.add_argument("--no-watermark", action="store_true", help="跳过去水印步骤")
    p.add_argument("--no-sharpen", action="store_true", help="跳过锐化步骤")
    args = p.parse_args()

    if not os.path.exists(args.input):
        sys.exit(f"错误：找不到输入路径 {args.input}")

    width = STD_WIDTH if args.std else args.width

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

    for src in files:
        dst = build_name(src, args.name, args.outdir)
        w, h = process(src, dst,
                       watermark=not args.no_watermark,
                       width=width,
                       sharpen=not args.no_sharpen)
        print(f"[完成] {os.path.basename(src)} -> {dst} ({w}x{h})")

    print(f"\n共处理 {len(files)} 张，输出目录：{args.outdir}")


if __name__ == "__main__":
    main()
