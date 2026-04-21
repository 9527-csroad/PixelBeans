# PixelBeans 实施方案 (Plan)

> 项目：将照片转化为专业拼豆图纸的工具
> 最后更新：2026-04-20
> 当前阶段：M1 启动前 · 方案已对齐

---

## 0. 概览

PixelBeans 是一个把任意照片转成专业级拼豆（Perler / Hama 类塑料熔珠）图纸的工具。最终形态是**对外提供给 App 开发者调用的算法能力**——要么作为后端 HTTP API，要么作为可移植的端侧算法包。当前先以 Web 验证界面作为算法效果的试验场。

**非目标**：本项目不提供熔豆工艺教学、不卖材料、不做社交/分享社区。只解决"一张图 → 一份能被精确拼出来的图纸"这个技术问题。

**定位**：对标 Pic2Pat / BeadsPrites 等现有商业工具，在**国产色卡还原度**与**专业图纸输出**两个维度追求超越。

---

## 1. 目标与范围

### 1.1 核心价值主张

对标现有工具的差异化抓手：

| 维度 | 现有商业工具常见做法 | 本项目目标 |
|---|---|---|
| 色彩距离度量 | RGB 欧氏距离或 HSV | CIE LAB + ΔE2000（更贴合人眼感知） |
| 调色板约束 | 通用 K-Means 自由量化 | 强制映射到选定品牌色卡子集 |
| 国产色卡 | 主要支持 Perler/Hama | 主打 MARD / 中艺 / 漫奇 |
| 孤豆处理 | 无 | 连通域分析清理单粒孤色 |
| 输出形态 | 网页预览 + 图片下载 | JSON 结构化数据 + 网格图 + BOM + PDF 分页打印 |
| 工程形态 | 直接出 UI 工具 | 算法核心可复用为 API / 端侧包 |

### 1.2 支持范围

- **拼豆品牌**：首发 MARD（数据已抓取），中艺 / 漫奇 后续跟进
- **豆子尺寸**：算法本身尺寸无关；UI 提供 5mm / 2.6mm 视觉切换
- **图片类型**：RGB / RGBA（带透明通道视为"空格"）；MVP 不做自动抠图
- **输出尺寸**：任意网格尺寸（常用 29×29 / 58×58 / 100×100）

---

## 2. 架构分层

核心原则：**算法核心与 UI/IO 完全解耦**。因为最终要输出给 App 开发者使用，UI 只是验证壳。

```
┌─────────────────────────────────────────────────┐
│  Web UI  (React + Canvas)   ← 验证/演示         │
├─────────────────────────────────────────────────┤
│  HTTP API (FastAPI)         ← 给 App 后端用     │
├─────────────────────────────────────────────────┤
│  Algorithm Core (pixelbeans pkg)  ← 核心资产    │
│   - palette.py   色卡加载 & ΔE2000 最近邻      │
│   - pipeline.py  预处理/像素化/量化/后处理     │
│   - dither.py    误差扩散抖动                   │
│   - export.py    图纸渲染 & BOM 生成            │
│   - types.py     数据模型 & API 合约            │
├─────────────────────────────────────────────────┤
│  Palette Data  (JSON 资产)                      │
│   - mard.json / zhongyi.json / manqi.json       │
│   - scraper.py   抓取/更新脚本                  │
└─────────────────────────────────────────────────┘
```

### 2.1 分层的关键约束

- 算法核心**纯 Python，无任何 HTTP / 文件系统副作用**。所有 I/O 由调用方传入 `numpy.ndarray` 或 `PIL.Image`。
- 色卡数据与算法解耦：算法接受一个 `Palette` 对象作为参数，不感知具体品牌。
- API 层是**薄包装**：只做参数校验、编解码、超时控制，不含算法逻辑。
- UI 层只调 API，不内嵌算法。

### 2.2 端侧移植路径

算法核心通篇纯矩阵运算（无深度学习推理），移植成本可控。路径：

1. Python 作为算法 spec，单元测试作为行为契约
2. 按 spec 重写为目标平台语言（Kotlin / Swift / TypeScript）
3. 用同一批测试图片做回归，确保跨端结果一致
4. 色卡 JSON 格式跨语言通用，零成本复用

---

## 3. 算法管线

```
输入图(RGB/RGBA) → [1]预处理 → [2]像素化 → [3]色彩量化 → [4]后处理 → [5]图纸渲染
                                                                        ↓
                                              JSON 图纸数据 + 预览 PNG + BOM + PDF
```

### 3.1 预处理

| 步骤 | 实现 | 参数 |
|---|---|---|
| 读图 & 色彩空间统一 | PIL → numpy，强制 sRGB | — |
| 等比缩放 & 居中裁剪 | 保持用户指定的目标宽高比 | `target_size: (w, h)` |
| 亮度 / 对比度 / 饱和度 | PIL.ImageEnhance | 各自独立参数，默认不变 |
| 锐化（可选） | Unsharp Mask | 默认 off |
| Alpha 阈值 | 低于阈值的像素标记为"空格" | 默认 128 |

### 3.2 像素化

- 将图像降采样到目标网格（如 58×58）
- 采样策略：`cv2.INTER_AREA`（区域均值，降采样的最佳选择；比双线性更抗锯齿且保留主色）
- 输出：形状为 `(H, W, 3)` 的 uint8 数组，每个像素对应一颗豆

### 3.3 色彩量化（核心）

这是本项目与普通工具拉开差距的关键环节。

**第一步：色彩空间转换**

- RGB → CIE LAB（使用 D65 白点）
- 理由：RGB 欧氏距离和人眼感知偏离极大（尤其在蓝绿与肤色区），LAB 是色彩工程的金标准
- 实现：`colour-science.sRGB_to_Lab` 或手写 3×3 变换矩阵（端侧移植友好）

**第二步：可选 K-Means 降色**

- 作用：如果用户设定"最多 30 色"，先用 K-Means 在 LAB 空间聚成 30 簇
- 工具：`sklearn.cluster.MiniBatchKMeans`（比标准 KMeans 快 10x 以上）
- 约束：聚类数 K 不超过色卡总色数

**第三步：调色板约束最近邻**

- 对每个像素（或上一步的 K 个簇心）在色卡 LAB 值集合上找最近邻
- 距离度量：**ΔE2000**（CIEDE2000），不用简单 LAB 欧氏距离
  - 为什么：ΔE2000 对色相、明度、饱和度在不同区域的感知权重做了校正
  - 代价：比欧氏距离慢，但 291 色 × 100×100 像素级别计算量可接受
- 索引加速：先用 LAB 欧氏 KD-Tree 拿 top-5 候选，再用 ΔE2000 精排（90% 加速且结果等价）

**第四步：抖动（可选，默认 off）**

- 支持 Floyd-Steinberg 误差扩散
- 拼豆场景通常关抖动更整洁（每豆是离散单位，抖动会引入视觉噪声）
- 保留为可选项供用户测试

**数据瑕疵处理**：

- MARD Q4 与 R11 共用 `#FFEBFA`：建索引时按字母序优先 Q4，R11 标记为 `aliases=['Q4']`，对量化结果无影响，对 BOM 清单会统一归到 Q4 下

### 3.4 后处理

| 步骤 | 作用 | 实现 |
|---|---|---|
| 孤豆清理 | 单粒或极小（1-2 豆）孤色合并到邻近色 | `cv2.connectedComponents` + 邻域众数投票 |
| 色数上限裁剪 | 若实际使用色数超过用户上限，将出现次数最少的色合并到最近邻 | 按 count 排序 + 迭代合并 |
| 对称镜像（可选） | 部分用户需要镜像豆板 | numpy 翻转 |

### 3.5 图纸渲染与导出

| 输出物 | 内容 | 格式 |
|---|---|---|
| `pattern.json` | 每个格子的 `{x, y, code, hex, symbol}` + 使用到的色卡子集 | JSON（即 API 响应主体） |
| `preview.png` | 像素画预览（可切换圆豆仿真模式） | PNG |
| `grid.png` | 网格图纸：颜色 + 符号双编码，每 10 格十字参考线 | PNG |
| `bom.txt` / `bom.csv` | 色号清单：色号、颜色名、hex、需求数量、小计 | 纯文本 / CSV |
| `pattern.pdf` | A4 分页打印：大图自动拆分多页，带页码和拼接标记 | PDF（ReportLab） |

符号编码规则：按色卡出现顺序分配 `A-Z a-z 0-9` 等字符，保证同一图纸内每色唯一。

---

## 4. 色卡数据

### 4.1 首发：MARD 291 色（已完成）

- **数据源**：https://www.pixel-beads.com/zh/mard-bead-color-chart
- **产物**：`palettes/mard.json`
- **结构**：
  ```json
  {
    "brand": "MARD",
    "source": "...",
    "total": 291,
    "categories": {"核心标准色": 291, "珍珠质感色": 0, "高亮荧光色": 0},
    "colors": [
      {"code": "A1", "name": "A1", "hex": "#FAF4C8", "category": "核心标准色"},
      ...
    ]
  }
  ```
- **前缀分布**：A(26) B(32) C(29) D(26) E(24) F(25) G(21) H(23) M(15) P(23) Q(5) R(28) T(1) Y(5) ZG(8)

### 4.2 已知瑕疵与处理策略

| 问题 | 影响 | 处理策略 |
|---|---|---|
| Q4 与 R11 共用 `#FFEBFA` | 唯一 hex 仅 290，KD-Tree 会冲突 | 字母序优先 Q4，R11 在索引中标记为 alias；BOM 统一归 Q4 |
| 色名字段 = 色号（无真实中文名如"樱花粉"） | UI 展示只能显示 `A1`，体验受损 | M2 前补充：从淘宝卖家图 / 官方资料人工整理一份 `code → name` 映射 |
| ZG 系列语义未知 | 不影响量化，但影响 UI 分组展示 | 待查：是否属于某特殊材质或近期新增系列 |

### 4.3 后续色卡（待办）

- **中艺**：同站点 `/zh/zhongyi-bead-color-chart` 路径可探测
- **漫奇**：同站点 `/zh/manqi-bead-color-chart` 路径可探测
- 若同站无数据，从淘宝官方店铺 / 拼豆社群人工整理

### 4.4 色卡 LAB 值预计算

所有色卡加载后在 `Palette.__init__` 中一次性 sRGB → LAB 转换并缓存，避免每次量化时重复计算。KD-Tree 也在初始化时建立。

---

## 5. API 合约

给 App 后端调用的 HTTP 接口形态。此合约一旦锁定，算法核心的函数签名与 JSON schema 同步锁定。

### 5.1 生成图纸

**Endpoint**：`POST /api/v1/pattern`

**请求体**（`multipart/form-data` 或 JSON + base64）：

```json
{
  "image": "<base64 或 multipart file>",
  "target_size": { "width": 58, "height": 58 },
  "palette": { "brand": "MARD", "subset": null },
  "max_colors": 30,
  "dither": false,
  "preprocessing": {
    "brightness": 1.0,
    "contrast": 1.0,
    "saturation": 1.0,
    "sharpen": false
  },
  "postprocessing": {
    "remove_isolated_beads": true,
    "min_region_size": 2
  }
}
```

**响应**：

```json
{
  "ok": true,
  "size": { "width": 58, "height": 58 },
  "pattern": [
    [
      {"code": "A1", "hex": "#FAF4C8", "symbol": "A"},
      {"code": "B3", "hex": "#......", "symbol": "B"},
      ...
    ],
    ...
  ],
  "palette_used": [
    {"code": "A1", "name": "A1", "hex": "#FAF4C8", "symbol": "A", "count": 142}
  ],
  "stats": {
    "total_beads": 3364,
    "unique_colors": 27,
    "empty_cells": 0
  },
  "preview_png_base64": "...",
  "meta": {
    "version": "0.1.0",
    "algorithm_hash": "sha256:...",
    "generated_at": "2026-04-20T12:00:00Z"
  }
}
```

### 5.2 色卡查询

- `GET /api/v1/palettes` — 列出所有支持的品牌
- `GET /api/v1/palettes/{brand}` — 返回该品牌完整色卡数据

### 5.3 版本策略

- URL 版本号 `/v1/`，breaking change 时升到 `/v2/`
- `meta.algorithm_hash` 用于端侧/后端的算法一致性校验

---

## 6. 仓库结构

```
PixelBeans/
├── docs/
│   └── plan.md                   ← 本文件
├── palettes/                     ← 色卡数据资产
│   ├── scraper.py                ← 抓取 & 更新脚本
│   ├── mard.json                 ← 已就绪
│   ├── zhongyi.json              ← 待办
│   └── manqi.json                ← 待办
├── pixelbeans/                   ← 算法核心包（可 pip install -e .）
│   ├── __init__.py
│   ├── types.py                  ← dataclass: Palette, PatternCell, PipelineConfig...
│   ├── palette.py                ← 色卡加载 + LAB 缓存 + KD-Tree + ΔE2000
│   ├── pipeline.py               ← 主管线 run(image, config) → PatternResult
│   ├── dither.py                 ← Floyd-Steinberg
│   ├── postprocess.py            ← 孤豆清理 + 色数裁剪
│   ├── export.py                 ← PNG / PDF / BOM 渲染
│   └── color_science.py          ← sRGB↔LAB, ΔE2000 实现
├── server/                       ← FastAPI 层（M2 加入）
│   ├── main.py
│   ├── schemas.py                ← Pydantic 模型（与 5. API 合约对应）
│   └── routers/
├── web/                          ← React 前端（M2 加入）
├── cli.py                        ← 命令行入口，M1 主验证手段
├── tests/
│   ├── fixtures/                 ← 样例图 + 黄金结果
│   ├── test_palette.py
│   ├── test_pipeline.py
│   └── test_regression.py        ← 同图同参数结果稳定性
├── images/                       ← 样例图（已存在）
├── code/                         ← 占位，当前为空
├── pyproject.toml
├── requirements.txt
└── README.md
```

---

## 7. 迭代路径

### M1 · 算法骨架 + CLI

**目标**：一条龙跑通"图片 → 图纸 JSON + 预览 PNG"，MARD 色卡，命令行调用。

**包含**：
- `palettes/scraper.py` + 正式版 `palettes/mard.json`（已完成）
- `pixelbeans/` 完整算法核心（6 个模块）
- `cli.py` 命令行入口
- `tests/` 单元测试 + 3 张样例图回归
- `pyproject.toml` / `requirements.txt`

**不包含**：FastAPI、React UI、PDF 导出、抖动、中艺/漫奇色卡、真实中文色名

### M2 · Web 演示

**目标**：装完 M1 的壳，让非技术用户和 App 开发同事能直观看效果。

**包含**：
- FastAPI 包装（API 合约见第 5 节）
- React + Canvas 前端
  - 拖拽上传
  - 实时预览对比（原图 vs 像素化 vs 图纸）
  - BOM 清单展示
  - PDF 打印导出
- 新增中艺 / 漫奇色卡
- 补充 MARD 真实中文色名

### M3 · 对标商业工具

**目标**：从"能用"推进到"专业好用"。

**包含**：
- 手动修图（画笔 / 吸管 / 填充 / 替换色号）
- 分板拆图（大图自动拆成 29×29 标准板）
- 符号双编码打印视图（色弱 / 黑白打印友好）
- 色卡用户标定工具（拍照校正屏幕偏差）
- 抖动算法对比工具
- 性能优化：WebAssembly 关键路径

---

## 8. M1 执行清单

按实现顺序：

- [ ] **8.1** 初始化 `pyproject.toml`、`requirements.txt`、目录骨架
- [ ] **8.2** `pixelbeans/types.py`：定义 `Palette` / `PaletteColor` / `PipelineConfig` / `PatternCell` / `PatternResult` dataclass
- [ ] **8.3** `pixelbeans/color_science.py`：sRGB↔LAB、ΔE2000、纯 NumPy 实现（不依赖 colour-science 运行时，移植更容易）
- [ ] **8.4** `pixelbeans/palette.py`：从 JSON 加载 + LAB 预计算 + KD-Tree + alias 处理（Q4/R11）
- [ ] **8.5** `pixelbeans/pipeline.py`：预处理 + 像素化 + 量化（含可选 K-Means 降色）主函数
- [ ] **8.6** `pixelbeans/postprocess.py`：孤豆清理 + 色数裁剪
- [ ] **8.7** `pixelbeans/export.py`：PNG 预览 + 网格图 + BOM 文本导出（PDF 留 M2）
- [ ] **8.8** `cli.py`：`python cli.py --input xxx.jpg --size 58x58 --palette mard --out result/`
- [ ] **8.9** `palettes/scraper.py`：把本次手工抓取脚本固化（含 Q4/R11 瑕疵注释）
- [ ] **8.10** `tests/`：色卡加载、ΔE2000 黄金值、端到端小图回归
- [ ] **8.11** 在 `images/` 中准备 3 张代表性样例图（人像、卡通、风景），肉眼验收

### M1 DoD（Definition of Done）

1. `python cli.py --input images/sample_cartoon.png --size 58x58 --palette mard --max-colors 30 --out result/` 成功运行，产物齐全
2. 产物包含：`pattern.json`、`preview.png`、`grid.png`、`bom.txt`
3. 3 张样例图的预览与原图对比肉眼判定"像"（主观验收）
4. `pytest` 全绿
5. 同一图 + 同一参数两次运行结果完全一致（确定性）

---

## 9. 风险与未决项

| 编号 | 项 | 状态 | 风险等级 | 处理计划 |
|---|---|---|---|---|
| R1 | MARD 真实中文色名缺失 | 已知 | 低 | M2 前从外部资料整理 |
| R2 | 中艺 / 漫奇 色卡数据源未验证 | 未验证 | 中 | M1 进行中探测 pixel-beads.com 子路径 |
| R3 | ΔE2000 Python 实现性能 | 未测 | 中 | 若 100×100 图 >1s，加 numba JIT 或 Cython |
| R4 | 端侧移植的测试一致性 | 未设计 | 中 | M1 测试固化为 JSON 黄金值，跨语言可复用 |
| R5 | Q4 / R11 同 hex 可能影响还原度（两色物理材质不同但数字值相同） | 已知 | 低 | 先按 alias 处理；若用户反馈再细化 |
| R6 | 大图 PDF 打印的分页拼接标记设计 | 未设计 | 低 | M3 再处理 |

---

## 10. 技术栈 & 依赖

### 10.1 核心库（运行时）

| 库 | 用途 | 版本约束 |
|---|---|---|
| numpy | 矩阵运算 | `>=1.24` |
| Pillow | 图像 I/O + 基础处理 | `>=10.0` |
| opencv-python-headless | 降采样 + 连通域分析 | `>=4.8` |

**已移除**（相比初稿）：

- `scikit-learn`：K-Means 改为自实现 ~30 行 NumPy 向量化代码。色卡 ~300 色、图像 ~10K 像素量级下性能充足，且减少端侧移植难度
- `scipy`：KD-Tree 移除，brute-force 最近邻在当前数据规模下毫秒级足够

### 10.2 M2 追加

| 库 | 用途 |
|---|---|
| fastapi + uvicorn | HTTP API |
| pydantic | 请求/响应 schema |
| reportlab | PDF 导出 |
| python-multipart | 文件上传 |

### 10.3 前端（M2）

- React 18 + Vite
- Canvas 原生 API（不用额外 pixel art 库）
- Tailwind CSS

### 10.4 开发期

| 库 | 用途 |
|---|---|
| pytest | 测试 |
| ruff | lint + format |
| mypy | 类型检查（非强制） |

### 10.5 不使用

- **PyTorch / TensorFlow**：本项目无深度学习推理，不引入这种重依赖
- **colour-science**（运行时）：仅开发期用于交叉验证，运行时自己实现 LAB / ΔE2000（端侧移植友好）
- **rembg**：MVP 不做抠图，已对齐

---

## 附录 A · 关键决策记录

| 决策 | 选择 | 日期 | 理由 |
|---|---|---|---|
| 算法核心语言 | Python | 2026-04-20 | 色彩科学与图像处理生态成熟；端侧后期按 spec 重写 |
| 部署形态 | 后端 API（Web UI 先做验证） | 2026-04-20 | 最终给 App 开发者用 |
| 抠图功能 | MVP 不做 | 2026-04-20 | rembg 模型依赖过重，延后到 M3 |
| 首发色卡 | MARD 291 色 | 2026-04-20 | 数据源已验证 |
| 色彩距离 | CIE LAB + ΔE2000 | 2026-04-20 | 行业金标准，对肤色/蓝绿区过渡关键 |
| 默认关抖动 | Floyd-Steinberg 作为可选项 | 2026-04-20 | 拼豆离散单位场景下抖动通常降低观感 |
