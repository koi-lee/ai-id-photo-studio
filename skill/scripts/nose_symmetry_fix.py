#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
证件照鼻翼对称性修正
====================
用 MediaPipe 面部关键点定位鼻翼，对两侧鼻翼下缘的高度差做局部形变矫正。

原理：
  1. 检测 468 个面部关键点，取左右鼻翼外缘点（索引 129 / 358）
  2. 计算两点垂直高度差 dy
  3. 构造高斯衰减的局部位移场：偏低的一侧上提 dy/2，偏高的一侧下压 dy/2
  4. 用 cv2.remap 应用位移，影响范围由 sigma 控制

设计约束（很重要）：
  - 位移场用高斯衰减，只在鼻翼附近生效，不会波及鼻梁、嘴唇、脸颊
  - 因为是连续形变而不是镜像替换，不会留下"融合痕迹"或"重影"
  - 务必在副本上操作，确认效果后再覆盖正式文件

用法：
  python nose_symmetry_fix.py 输入图.jpg 输出图.jpg
  python nose_symmetry_fix.py 输入图.jpg 输出图.jpg --sigma 30 --max-shift 12
  python nose_symmetry_fix.py ./目录/ --outdir ./修正后/     # 批量

依赖：mediapipe, opencv-python, numpy
"""

import argparse
import os
import sys
import urllib.request


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

import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision
import numpy as np

# MediaPipe FaceMesh 鼻翼关键点索引（468 点模型）
IDX_RIGHT_ALAR = 129   # 画面左侧鼻翼
IDX_LEFT_ALAR = 358    # 画面右侧鼻翼
IDX_NOSE_TIP = 4

IMAGE_EXT = (".png", ".jpg", ".jpeg", ".webp", ".bmp")

# 关键点模型（mediapipe >= 1.0 需要单独下载）
SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(SKILL_DIR, "assets", "face_landmarker.task")
MODEL_URL = ("https://storage.googleapis.com/mediapipe-models/face_landmarker/"
             "face_landmarker/float16/1/face_landmarker.task")


def _ensure_model(model_path):
    """模型缺失时自动从官方地址下载。

    技能包为控制体积（平台上限 3MB）不内置该模型（约 3.6MB），
    首次用到关键点定位时按需拉取；下载失败则给出手动命令。
    """
    if os.path.exists(model_path):
        return True
    parent = os.path.dirname(model_path)
    try:
        os.makedirs(parent, exist_ok=True)
    except OSError:
        pass
    tmp = model_path + ".part"
    try:
        print("ℹ️ 首次使用关键点定位，正在下载模型（约 3.6MB）…")
        urllib.request.urlretrieve(MODEL_URL, tmp)
        os.replace(tmp, model_path)
        print(f"ℹ️ 模型已保存：{model_path}")
        return True
    except Exception as exc:  # 网络不可用 / 无写权限 / 代理拦截
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass
        print(
            f"错误：缺少关键点模型，且自动下载失败（{exc}）\n"
            f"请手动下载后重试：\n  curl -sL -o '{model_path}' {MODEL_URL}",
            file=sys.stderr,
        )
        return False


def detect_landmarks(img_bgr, model_path=None):
    """返回面部关键点坐标数组 (N, 2)，未检测到返回 None。"""
    model_path = model_path or MODEL_PATH
    if not _ensure_model(model_path):
        sys.exit(1)

    h, w = img_bgr.shape[:2]
    # 强制使用 CPU delegate：部分 macOS/ARM 环境下 Metal 后端会崩溃
    # (DrishtiMetalHelper / service_ Service is unavailable)
    try:
        base_options = mp_python.BaseOptions(
            model_asset_path=model_path,
            delegate=mp_python.BaseOptions.Delegate.CPU,
        )
    except Exception:
        base_options = mp_python.BaseOptions(model_asset_path=model_path)
    options = vision.FaceLandmarkerOptions(
        base_options=base_options,
        num_faces=1,
        running_mode=vision.RunningMode.IMAGE,
    )
    with vision.FaceLandmarker.create_from_options(options) as landmarker:
        rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = landmarker.detect(mp_image)

    if not result.face_landmarks:
        return None
    lms = result.face_landmarks[0]
    return np.array([(p.x * w, p.y * h) for p in lms], dtype=np.float64)


def fix_nose_symmetry(img_bgr, sigma=30.0, max_shift=12.0, align="level"):
    """对鼻翼做局部垂直形变，使两侧鼻翼下缘趋于水平。

    sigma: 高斯影响半径（像素），越小越局部
    max_shift: 单侧最大位移（像素），防止修正过度
    align: 'level' 使两侧鼻翼下缘水平；'average' 保留部分原始立体感
    返回 (修正后图像, 位移量dy)
    """
    pts = detect_landmarks(img_bgr)
    if pts is None:
        return img_bgr, 0.0

    h, w = img_bgr.shape[:2]
    p_right = pts[IDX_RIGHT_ALAR]   # 画面左
    p_left = pts[IDX_LEFT_ALAR]     # 画面右

    dy = float(p_right[1] - p_left[1])   # >0 表示画面左鼻翼偏低
    if abs(dy) < 1.5:
        return img_bgr, dy

    # 两侧各承担一半修正量，整体高度保持不变
    if align == "level":
        s_right = dy / 2.0    # 偏低侧上移
        s_left = -dy / 2.0    # 偏高侧下移
    else:
        s_right = dy / 4.0
        s_left = -dy / 4.0

    # 限制单侧位移上限
    s_right = float(np.clip(s_right, -max_shift, max_shift))
    s_left = float(np.clip(s_left, -max_shift, max_shift))

    # 构造采样网格
    grid_x, grid_y = np.meshgrid(
        np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32)
    )

    d_right = np.sqrt((grid_x - p_right[0]) ** 2 + (grid_y - p_right[1]) ** 2)
    d_left = np.sqrt((grid_x - p_left[0]) ** 2 + (grid_y - p_left[1]) ** 2)

    g_right = np.exp(-(d_right ** 2) / (2 * sigma ** 2))
    g_left = np.exp(-(d_left ** 2) / (2 * sigma ** 2))

    # 目标像素 (x,y) 取源图 (x, y + shift)：正值表示内容上移
    shift_total = s_right * g_right + s_left * g_left
    map_y = grid_y + shift_total.astype(np.float32)

    fixed = cv2.remap(
        img_bgr, grid_x, map_y,
        interpolation=cv2.INTER_LANCZOS4,
        borderMode=cv2.BORDER_REPLICATE,
    )
    return fixed, dy


def process_file(src, dst, sigma, max_shift, align):
    img = cv2.imread(src)
    if img is None:
        print(f"[跳过] 无法读取: {src}")
        return
    fixed, dy = fix_nose_symmetry(img, sigma=sigma, max_shift=max_shift, align=align)
    os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
    cv2.imwrite(dst, fixed, [int(cv2.IMWRITE_JPEG_QUALITY), 96])
    print(f"[完成] {os.path.basename(src)} -> {dst}  (检测到高度差 {dy:+.1f}px)")


def main():
    p = argparse.ArgumentParser(description="证件照鼻翼对称性修正（基于面部关键点局部形变）")
    p.add_argument("input", help="输入图片路径或目录")
    p.add_argument("output", nargs="?", default="", help="输出图片路径（单文件模式）")
    p.add_argument("--outdir", default="", help="输出目录（批量模式）")
    p.add_argument("--sigma", type=float, default=30.0, help="高斯影响半径，默认 30")
    p.add_argument("--max-shift", type=float, default=12.0, help="单侧最大位移，默认 12")
    p.add_argument("--align", choices=["level", "average"], default="level",
                   help="level=完全水平；average=保留部分立体感")
    args = p.parse_args()

    if not os.path.exists(args.input):
        sys.exit(f"错误：找不到 {args.input}")

    if os.path.isdir(args.input):
        files = sorted(
            os.path.join(args.input, f)
            for f in os.listdir(args.input)
            if f.lower().endswith(IMAGE_EXT)
        )
        outdir = args.outdir or "./nose_fixed"
        for src in files:
            dst = os.path.join(outdir, os.path.basename(src))
            process_file(src, dst, args.sigma, args.max_shift, args.align)
    else:
        if not args.output:
            sys.exit("错误：单文件模式需要指定输出路径")
        process_file(args.input, args.output, args.sigma, args.max_shift, args.align)


if __name__ == "__main__":
    main()
