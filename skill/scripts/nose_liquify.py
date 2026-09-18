#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
nose_liquify.py — 证件照/人像「鼻子几何微调」工具（保纹理液化法）

设计目标
--------
只改变鼻翼/鼻孔的**几何位置**（左右高低），皮肤纹理、毛孔、脸型 100% 保持原图像素，
不做任何磨皮、美白、瘦脸。适用于「左右鼻翼不对称」「一侧鼻孔偏低/偏高」的修正。

原理
----
对原图做 numpy/cv2.remap 位移映射：以两个高斯权重场分别作用于左右鼻翼，
局部把像素块整体上推或下压，权重在边缘平滑衰减，因此不会出现接缝或重影。

典型用法
--------
# 1) 先测量：报告两侧鼻孔底缘高度差（Δ = 左 - 右，越小越齐平）
python nose_liquify.py --image 原图.jpg --measure

# 2) 自动定档：自动搜索使两侧鼻孔底缘齐平的位移量并输出
python nose_liquify.py --image 原图.jpg --auto --out 输出.png

# 3) 手动指定：左侧下压 7px（右不动）
python nose_liquify.py --image 原图.jpg --left-px 7 --out 输出.png

# 4) 出多档对比条给用户挑（原图 + 各档裁剪并排）
python nose_liquify.py --image 原图.jpg --ladder 2,4,6,8 --strip 对比条.png

坐标说明（重要）
----------------
本脚本一律使用**画面坐标**：图像 x 增大方向为「画面右侧」。
用户口中的「我的左边」等于看照片时的画面左侧 —— 沟通时必须先确认，
且以用户标注截图为准；实测数据经常与用户主观判断相反（光影错觉）。

依赖：opencv-python (cv2)、numpy。需在隔离虚拟环境运行，不要全局 pip install。
"""

import argparse
import os
import sys

import cv2
import numpy as np

# 默认鼻翼中心（1181x1653 一寸高清图的实测值，仅作兜底；正常情况自动检测）
DEFAULT_L = (562.0, 776.0)
DEFAULT_R = (645.0, 778.0)
DEFAULT_SIGMA = (58.0, 40.0)


# ----------------------------------------------------------------------------- 测量
def find_nostrils(img, thresh=90, band=(690, 810), xrange=(400, 745)):
    """在鼻部条带内用暗区检测定位两侧鼻孔，返回 (左心, 右心, 左底 y, 右底 y)。"""
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    y0, y1 = band
    x0, x1 = xrange
    roi = g[y0:y1, x0:x1]
    dark = (roi < thresh).astype(np.uint8) * 255
    dark = cv2.morphologyEx(dark, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, lab, stats, cent = cv2.connectedComponentsWithStats(dark, 8)
    blobs = []
    for i in range(1, n):
        area = stats[i, cv2.CC_STAT_AREA]
        if area < 40:
            continue
        blobs.append((area,
                      stats[i, cv2.CC_STAT_TOP] + stats[i, cv2.CC_STAT_HEIGHT] + y0,
                      cent[i][0] + x0, cent[i][1] + y0))
    if len(blobs) < 2:
        return None
    blobs.sort(reverse=True)
    a, b = blobs[0], blobs[1]
    left, right = (a, b) if a[2] < b[2] else (b, a)
    return (left[2], left[3]), (right[2], right[3]), int(left[1]), int(right[1])


def measure_bottom(img, xa, xb, thresh):
    """返回指定 x 区间内暗部（鼻孔/鼻底阴影）的最低 y。"""
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    sub = g[690:840, xa:xb]
    ys = np.where((sub < thresh).any(axis=1))[0]
    return int(ys.max() + 690) if len(ys) else None


def measure(img, quiet=False):
    """输出两侧鼻孔底缘、鼻翼底缘的高度差表。Δ = 左 - 右，恒为 0 表示齐平。"""
    nost = find_nostrils(img)
    lob = measure_bottom(img, 500, 610, 90)     # 左鼻孔暗口底
    rob = measure_bottom(img, 615, 715, 90)     # 右鼻孔暗口底
    lwb = measure_bottom(img, 470, 610, 120)    # 左鼻翼/鼻底阴影线
    rwb = measure_bottom(img, 610, 740, 120)    # 右鼻翼/鼻底阴影线
    if not quiet:
        print(f"  左鼻孔底={lob}  右鼻孔底={rob}  Δ={lob - rob:+d}")
        print(f"  左鼻翼底={lwb}  右鼻翼底={rwb}  Δ={lwb - rwb:+d}")
        if nost:
            print(f"  自动检测鼻翼中心: 左({nost[0][0]:.0f},{nost[0][1]:.0f}) "
                  f"右({nost[1][0]:.0f},{nost[1][1]:.0f})")
    return dict(lob=lob, rob=rob, lwb=lwb, rwb=rwb,
                d_nostril=(lob - rob), d_wing=(lwb - rwb))


# ----------------------------------------------------------------------------- 形变
def gauss_field(shape, center, sigma):
    h, w = shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cx, cy = center
    sx, sy = sigma
    return np.exp(-(((xx - cx) ** 2) / (2 * sx ** 2) + ((yy - cy) ** 2) / (2 * sy ** 2)))


def liquify(img, left_px=0.0, right_px=0.0, center_l=None, center_r=None, sigma=DEFAULT_SIGMA):
    """局部液化。

    left_px / right_px：正数 = 该侧**下压**（画面向下），负数 = 上提，单位像素。
    """
    h, w = img.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    map_y = yy.copy()
    if left_px:
        map_y -= float(left_px) * gauss_field(img.shape, center_l or DEFAULT_L, sigma)
    if right_px:
        map_y -= float(right_px) * gauss_field(img.shape, center_r or DEFAULT_R, sigma)
    return cv2.remap(img, xx, map_y, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)


def autolevel(img, center_l=None, center_r=None, sigma=DEFAULT_SIGMA,
              lo=-12.0, hi=12.0, step=0.25, target="nostril"):
    """搜索使两侧齐平（Δ≈0）的「左压 d px」档位。

    只压左翼时右翼也会被轻微带动（高斯场有重叠），故用实测 Δ 迭代而不是直接换算。
    """
    key = "d_nostril" if target == "nostril" else "d_wing"
    best, best_cost = 0.0, None
    rows = []
    d = lo
    while d <= hi + 1e-6:
        out = liquify(img, left_px=d, center_l=center_l, center_r=center_r, sigma=sigma)
        m = measure(out, quiet=True)
        cost = abs(m[key])
        rows.append((d, m["d_nostril"], m["d_wing"]))
        if best_cost is None or cost < best_cost:
            best, best_cost = d, cost
        d += step
    return best, rows


# ----------------------------------------------------------------------------- 对比条
def make_strip(orig, variants, out_path, crop=(425, 655, 775, 855), scale=1.9, labels=None):
    """原图与各档位并排成对比条，便于用户挑档。variants: [(label, img), ...]"""
    x0, y0, x1, y1 = crop
    panels = []
    for i, (lab, im) in enumerate([("原图", orig)] + list(variants)):
        c = im[y0:y1, x0:x1].copy()
        c = cv2.resize(c, (0, 0), fx=scale, fy=scale, interpolation=cv2.INTER_LANCZOS4)
        cv2.putText(c, lab, (10, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.95, (0, 0, 255), 2)
        panels.append(c)
        panels.append(np.full((6, c.shape[1], 3), 255, np.uint8))
    cv2.imwrite(out_path, np.vstack(panels[:-1]))


# ----------------------------------------------------------------------------- CLI
def main():
    ap = argparse.ArgumentParser(description="鼻子几何微调（保纹理液化法）")
    ap.add_argument("--image", required=True, help="输入图（原图，勿用生成式修图结果）")
    ap.add_argument("--measure", action="store_true", help="只测量并打印高度差")
    ap.add_argument("--auto", action="store_true", help="自动搜索齐平档位并输出")
    ap.add_argument("--left-px", type=float, default=None, help="左鼻翼位移px：正=下压，负=上提")
    ap.add_argument("--right-px", type=float, default=0.0, help="右鼻翼位移px：正=下压，负=上提")
    ap.add_argument("--target", choices=["nostril", "wing"], default="nostril",
                    help="auto 模式对齐基准：鼻孔底缘(默认) 或 鼻翼底缘")
    ap.add_argument("--ladder", default=None, help="多档对比，如 2,4,6,8（均为左压px）")
    ap.add_argument("--strip", default=None, help="输出对比条文件路径")
    ap.add_argument("--sigma", default="58,40", help="高斯场标准差 sx,sy（默认 58,40）")
    ap.add_argument("--out", default=None, help="输出文件路径（png 无损 / jpg 可加 --quality）")
    ap.add_argument("--quality", type=int, default=96, help="jpg 输出质量，默认 96")
    ap.add_argument("--no-autocenter", action="store_true", help="禁用鼻翼中心自动检测")
    args = ap.parse_args()

    img = cv2.imread(args.image)
    if img is None:
        sys.exit(f"读不到图片：{args.image}")

    sigma = tuple(float(v) for v in args.sigma.split(","))
    cl = cr = None
    if not args.no_autocenter:
        nost = find_nostrils(img)
        if nost:
            cl, cr = nost[0], nost[1]

    print(f"输入: {args.image}  尺寸 {img.shape[1]}x{img.shape[0]}")
    print("原始测量:")
    m0 = measure(img)

    if args.measure and not args.auto and args.left_px is None and not args.ladder:
        return

    if args.auto:
        d, rows = autolevel(img, cl, cr, sigma, target=args.target)
        print(f"\n自动定档: 左压 {d:+.2f}px（对齐目标={args.target}）")
        for dd, dn, dw in rows[::max(1, len(rows) // 8)]:
            print(f"   d={dd:+.2f}  Δ鼻孔={dn:+d}  Δ鼻翼={dw:+d}")
        out = liquify(img, left_px=d, center_l=cl, center_r=cr, sigma=sigma)
        print("修正后测量:")
        measure(out)
        if args.out:
            save(out, args.out, args.quality)
        return

    if args.ladder:
        vals = [float(v) for v in args.ladder.split(",")]
        variants = []
        for d in vals:
            out = liquify(img, left_px=d, center_l=cl, center_r=cr, sigma=sigma)
            print(f"\n左压 {d}px 后测量:")
            measure(out)
            variants.append((f"左压{d:g}px", out))
            if args.out and len(vals) == 1:
                save(out, args.out, args.quality)
        if args.strip:
            make_strip(img, variants, args.strip)
            print(f"\n对比条: {args.strip}")
        return

    if args.left_px is not None or args.right_px:
        out = liquify(img, left_px=args.left_px or 0, right_px=args.right_px,
                      center_l=cl, center_r=cr, sigma=sigma)
        print(f"\n左移 {args.left_px or 0}px / 右移 {args.right_px}px 后测量:")
        measure(out)
        if args.out:
            save(out, args.out, args.quality)
        return

    print("\n未指定操作。用 --measure / --auto / --left-px / --ladder。")


def save(img, path, quality):
    ext = os.path.splitext(path)[1].lower()
    if ext in (".jpg", ".jpeg"):
        cv2.imwrite(path, img, [cv2.IMWRITE_JPEG_QUALITY, quality])
    else:
        cv2.imwrite(path, img)
    print(f"已输出: {path}")


if __name__ == "__main__":
    main()
