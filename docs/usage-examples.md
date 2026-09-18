# 可运行示例

本页每条命令都能直接执行，用仓库自带的 `examples/` 图即可复现，不需要任何 API 额度 —— 后处理与液化通道完全在本地运行。

## 准备

```bash
python3 -m venv ~/.venvs/idphoto
~/.venvs/idphoto/bin/pip install pillow opencv-python numpy

export PY=~/.venvs/idphoto/bin/python
export SKILL=./skill          # 换成你实际拷贝 skill/ 的位置
```

---

## 示例 1 · 最简：一寸高清照

```bash
$PY $SKILL/scripts/process_id_photo.py examples/male/base-portrait.jpg \
  --outdir /tmp/demo -n 一寸白底_示例
```

**预期输出**

```
[完成] base-portrait.jpg -> /tmp/demo/一寸白底_示例.jpg (1181x1653, 1200dpi)
```

`1181×1653` 是 25×35mm 在 1200dpi 下的像素，保持与标准一寸完全相同的比例，但像素量是 295×413 的 16 倍 —— 屏幕上不糊，打印正好。

---

## 示例 2 · 一键三档（推荐用法）

```bash
$PY $SKILL/scripts/process_id_photo.py examples/female/white-bg-black-suit.jpg \
  --spec 1inch --outdir /tmp/demo3 --tiers hd,std,uhd -n 一寸白底_示例
```

**预期输出结构**（各档自动分目录，不会互相覆盖）

```
/tmp/demo3/
├── 一寸白底_示例.jpg               1181×1653  @1200dpi   ← 主交付
└── 295x413标准版/
    └── 一寸白底_示例.jpg            295×413   @300dpi    ← 政务系统强制要求时用
```

**你会看到超清档被跳过**：

```
[跳过] white-bg-black-suit.jpg 超清档：源图裁剪后仅 1181px 宽 < 需要的 2362px，放大只会得到假细节
```

这是**刻意设计的行为**，不是 bug —— 插值放大会让文件变大却更软。要拿到真超清档，源图（生图模型的输出）宽度必须 ≥2362px。

---

## 示例 3 · 切换规格

```bash
# 二寸
$PY $SKILL/scripts/process_id_photo.py examples/male/white-bg-black-suit.jpg \
  --spec 2inch --outdir /tmp/demo --no-watermark -n 二寸白底_示例
# -> 二寸白底_示例.jpg (1652x2316, 1200dpi)

# 结婚证合影（横版 53×35mm）
$PY $SKILL/scripts/process_id_photo.py examples/female/white-bg-black-suit.jpg \
  --spec marriage --outdir /tmp/demo --no-watermark -n 结婚证合影_示例
# -> 结婚证合影_示例.jpg (2504x1652, 1200dpi)
```

> `--no-watermark` 用于跳过 inpaint 去水印 —— 第三方图生图 API 的产出通常不带水印。宿主内置生图工具的输出带水印，要去掉这个参数。

查看全部规格与说明：

```bash
$PY $SKILL/scripts/process_id_photo.py --help
```

---

## 示例 4 · 全规格自测（验证尺寸正确性）

一条命令跑完 8 种规格，用来确认脚本在你机器上工作正常：

```bash
cd /tmp && rm -rf reg && for spec in small-1inch driving-license 1inch large-1inch \
  small-2inch 2inch large-2inch marriage; do
  $PY ~/path/to/skill/scripts/process_id_photo.py ~/path/to/examples/male/base-portrait.jpg \
    --spec $spec --outdir /tmp/reg/$spec --tiers hd,std --no-watermark
done

$PY -c "
from PIL import Image
from pathlib import Path
for d in sorted(Path('/tmp/reg').iterdir()):
    for f in sorted(d.rglob('*.jpg')):
        im = Image.open(f)
        print(f'{d.name:16} {im.size[0]:>5}x{im.size[1]:<5} {im.info.get(\"dpi\")[0]}dpi  {f.parent.name}')
"
```

**预期尺寸表**

| 规格 | 高清档 @1200dpi | 标准档 @300dpi |
|---|---|---|
| small-1inch / driving-license | 1040×1512 | 260×378 |
| 1inch | 1181×1653 | 295×413 |
| large-1inch | 1560×2268 | 390×567 |
| small-2inch | 1652×2124 | 413×531 |
| 2inch | 1652×2316 | 413×579 |
| large-2inch | 1652×2520 | 413×630 |
| marriage（横版） | 2504×1652 | 626×413 |

---

## 示例 5 · 客观测量清晰度（不要看文件体积）

```python
import cv2, numpy as np

def sharpness(path, norm_width=1181):
    """统一缩放到同一宽度再测 Laplacian 方差，越高越锐。"""
    img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    h, w = img.shape
    if w != norm_width:
        img = cv2.resize(img, (norm_width, int(h * norm_width / w)),
                         interpolation=cv2.INTER_LANCZOS4)
    return round(cv2.Laplacian(img, cv2.CV_64F).var(), 1)

for p in ["examples/male/base-portrait.jpg", "examples/male/white-bg-black-suit.jpg"]:
    print(p, sharpness(p))
```

**为什么必须统一宽度**：不同分辨率的图直接比 Laplacian 毫无意义 —— 分辨率越高，像素级梯度天然越小。

判读标准见 [`quality.md`](../skill/references/quality.md)：
- 成片锐度约为源图的 **1.0–1.1 倍** 属正常
- 超过源图 **1.3 倍** → 过度锐化，会出现光晕

---

## 示例 6 · 局部液化微调（不磨皮改五官）

```bash
# ① 先量：输出左右高度差 Δ
$PY $SKILL/scripts/nose_liquify.py --image examples/male/white-bg-black-suit.jpg --measure

# ② 出多档对比条，让用户指一个数字（不要逐档来回问）
$PY $SKILL/scripts/nose_liquify.py --image examples/male/white-bg-black-suit.jpg \
  --ladder 2,4,6,8 --strip /tmp/对比条.png

# ③ 定稿并复测
$PY $SKILL/scripts/nose_liquify.py --image examples/male/white-bg-black-suit.jpg \
  --auto --out /tmp/修正.png
```

> **为什么不用修图软件**：生成式修图（以及多数一键美颜）会对任何"局部微调"请求做**整脸重绘** —— 磨皮、瘦脸、提亮，而目标部位几乎不变。液化用 `cv2.remap` 做几何形变，皮肤纹理 100% 保留，图片也不出本机。
>
> 方法与边界见 [`liquify-geometry-retouch.md`](../skill/references/liquify-geometry-retouch.md)。

---

## 说明：这些示例不包含"生图"环节

上面全部是**本地后处理**，不需要任何 API 额度。真正需要额度的部分（把原片变成白底证件照）属于图生图通道，见：

- [`platform-designkit.md`](../skill/references/platform-designkit.md) — 第三方图生图 API（以美图设计室为例）
- [`platform-host.md`](../skill/references/platform-host.md) — 宿主内置生图能力

仓库里的 `examples/` 图片就是"生图"环节的产出示例（AI 生成模特），可作为对照。
