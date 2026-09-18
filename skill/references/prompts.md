# 生图 Prompt 模板库

所有 prompt 均以英文书写（生图模型对英文指令响应更稳定），把 `{{}}` 占位符替换成实际内容。

> 中文 prompt 在部分模型（尤其是国内厂商的图生图 API）上表现更好 —— 见 `platform-designkit.md` 第三节的 prompt 三要素中文写法。本文件的英文模板适用于英文优先的生图模型。

## 一、通用骨架

```
Chinese 1-inch ID photo, clean pure {{BACKGROUND}} background.
Same person, same face shape, same facial features, same neutral expression and frontal pose.
The face is balanced and symmetric, with a straight and centered nose, even nostrils, symmetrical nose wings.
{{HAIR_LINE}}
Wearing {{CLOTHING}}.
{{EXTRA}}
Professional ID photo style, soft even lighting, no shadows on background,
photorealistic, high detail, sharp focus.
```

| 占位符 | 取值 |
|---|---|
| `{{BACKGROUND}}` | `pure white` / `light blue` / `red` |
| `{{HAIR_LINE}}` | 见第二节：发型不变 / 换发型 |
| `{{CLOTHING}}` | 见第三节 |
| `{{EXTRA}}` | 可选，如 `Forehead visible, eyebrows clear.` |

> **鼻子对称必须默认写进 prompt**：实践发现，不加这句，模型很容易生成鼻翼/鼻孔左右不对称（如一侧鼻翼偏高/偏低）。除非用户明确说"保留真实的不对称"，否则始终包含 `straight and centered nose, even nostrils, symmetrical nose wings`。

## 一之二、面部特征锚定（face_desc）—— 防"被美化"

模型默认倾向把脸往"标准好看"的方向修（磨皮、瘦脸、放大眼睛、提亮肤色）。**只写 `same face` 不够** —— 要把从原图实际观察到的特征**逐项结构化写出来**，模型才没有自由发挥的空间。

生成前先看原图，归纳以下维度（**只写你真正观察到的**）：

| 维度 | 写法示例 |
|---|---|
| 脸型 | `oval face` / `round face` / `square jawline` / `long face` |
| 眉形 | `thick straight black eyebrows` / `thin arched eyebrows` |
| 眼型 | `single-lid almond eyes` / `double-lid eyes with visible crease` |
| 眼尾 | `slightly upturned eye corners` |
| 鼻梁 | `straight nose bridge, medium width` |
| 鼻翼鼻孔 | `even nostrils, symmetrical nose wings` |
| 唇形 | `medium-full lips with natural shape` |
| 下颌线 | `defined but soft jawline` |
| 耳朵 | `ears fully visible, natural shape` |
| 发际线 | `natural straight hairline` |
| 肤色 | `natural skin tone` |
| 年龄感 | `age appearance unchanged` |

**用法** —— 拼进 prompt 的身份锚定段：

```
Preserve these facial features exactly as in the reference photo:
{{FACE_DESC}}.
Do NOT beautify, do NOT slim the face, do NOT enlarge the eyes, do NOT brighten the skin.
```

> ⚠️ **不要套模板**。模板化的"标准脸"描述会把模型往网红脸带，反而偏离原图。不确定的维度**宁可不写** —— 写错的锚定比不写更糟。

## 二、HAIR_LINE 两种写法

### 模式 A：发型完全不变（只换衣服和背景）

```
Keep the EXACT same hairstyle, same hair length, same hair volume and same hair parting as the input photo.
```

> 这句话是"发型不变"模式的命门。漏掉它，模型有相当大概率会顺手把发型改掉。
> 若发现发型仍有变化，追加：`Do not restyle, recolor or reshape the hair in any way.`

### 模式 B：更换发型

从下面挑一条替换 `{{HAIR_LINE}}`。

| 发型 | HAIR_LINE 描述 |
|---|---|
| 微分碎盖 | `Hairstyle changed to a modern Korean micro-parted textured fringe: top hair about 5-7cm with light natural volume, slightly parted airy fringe on forehead, sides tapered short but not shaved, natural black hair, matte texture.` |
| 韩式纹理侧分 | `Hairstyle changed to a Korean textured side part with a 3:7 parting: top hair styled up and to one side with soft volume and visible texture, clean forehead partly visible, sides tapered neatly and short, natural black hair, mature business look.` |
| 美式前刺 | `Hairstyle changed to a textured forward quiff: short sides with clean taper fade, top hair cut short and styled upward and forward with matte texture, youthful energetic clean look, natural black hair. Forehead visible, eyebrows not covered.` |
| 渐变层次短发 | `Hairstyle changed to a 2025 tapered layered short cut: low fade on sides starting from below the ears, top hair 3-5cm with light volume and natural messy texture, clean neckline, modern and fresh, natural black hair.` |
| 微分碎盖（蓬松加强版） | `Hairstyle changed to a voluminous textured crop with strong root lift: top hair 6-7cm with visible layered texture and lifted roots, airy parted fringe, sides kept with a soft taper (NOT shaved), natural black hair.` |
| 轻熟侧背 | `Hairstyle changed to a classic side-swept back hairstyle: hair combed back and to one side with light hold, tapered short sides, clean mature executive look, forehead fully visible, natural black hair with slight healthy shine.` |
| 自然抓刺 | `Hairstyle changed to a natural textured spiky cut: sideburns kept 5-8cm, hair styled with soft upward texture, warm and approachable look, natural black hair.` |
| 括号刘海 | `Hairstyle changed to a Korean comma fringe: fringe parted in the middle and curled inward on both sides like a bracket, top hair puffed with volume, sides neat, natural black hair.` |
| 圆寸 / 短碎发 | `Hairstyle changed to a short even buzz cut with slightly textured top, very short and clean, natural black hair.` |
| 羊毛卷碎盖 | `Hairstyle changed to a lightly permed wool-curly crop: soft S-shaped curls on top giving airy volume, not too tight, sides short, natural black hair.` |

## 三、CLOTHING 常用取值

| 需求 | CLOTHING 写法 |
|---|---|
| 纯色衬衫 | `a solid BLACK button-up dress shirt` |
| 彩色衬衫 | `a solid DARK NAVY BLUE / DARK CHARCOAL GRAY / DARK FOREST GREEN / DARK BROWN / DARK BURGUNDY button-up dress shirt` |
| 西装 + 白衬衫 | `a dark charcoal gray suit jacket over a crisp white dress shirt` |
| 藏青西装 | `a navy blue suit jacket over a white dress shirt` |
| 中山装 / 立领 | `a navy blue mandarin-collar jacket` |

> **白衣服必须换深色**：用户原始照片若穿白色或浅色上衣，`{{CLOTHING}}` 必须替换为深色款式，否则人物会与白底融为一体。

## 四、参数建议（宿主内置生图工具）

| 场景 | size | input_fidelity | 备注 |
|---|---|---|---|
| 只换衣服（发型不变） | `1024x1536` | `0.90` | 保真度调高，最大限度保留原貌 |
| 换发型 | `1024x1536` | `0.85` | 兼顾换发型与保脸 |
| 换发型 + 换衣服 | `1024x1536` | `0.85` | 同上 |
| 发现五官被改变 | `1024x1536` | `0.90` | 提高保真，并加强 `same face` 与 face_desc 措辞 |

**绝对不要并发提交多个生图请求**，宿主内置工具会返回 `error request aborted`。一次一个，串行执行。

> 参数含义、平台差异与安装方式见 `platform-host.md`。

## 五、双模式对比输出的组织方式

用户要"发型不变 vs 换发型"对比时，建议这样组织：

```
输出目录/
├── 发型不变/
│   ├── 一寸白底_黑色衬衫_经典正式.jpg
│   └── 一寸白底_深蓝衬衫_沉稳商务.jpg
└── 换发型/
    ├── 一寸白底_微分碎盖_自然清爽.jpg
    └── 一寸白底_韩式纹理侧分_沉稳商务.jpg
```

命名统一为 `一寸白底_<特征>_<风格>.jpg`，让用户能直接对比选择。
