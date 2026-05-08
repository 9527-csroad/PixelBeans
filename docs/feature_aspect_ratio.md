# Feature: 保持原图比例模式 (Aspect Ratio Preservation)

> 日期：2026-05-08
> 状态：已完成
> 范围：算法层 (pixelbeans) + CLI + 前端 (web/) + server/ + api/

---

## 1. 背景

当前图像处理始终将图片强制裁为目标 W×H 的宽高比（中心裁剪），导致非目标比例的原图丢失大量内容。

用户需要一个"保持原图比例"模式：根据原图实际宽高比自动计算输出网格，最大化保留原图内容。

---

## 2. 需求描述

### 2.1 两种模式

| 模式 | 用户输入 | 输出网格 | 裁剪行为 |
|---|---|---|---|
| **中心裁剪**（现有，默认） | 宽 W × 高 H | 严格输出 W×H | 按 W:H 比例从原图中心裁剪，再 resize |
| **保持原图比例**（新增） | 最长边 N | 自动计算 W×H | 按原图比例缩放，长边 = N，短边按比例自动算 |

### 2.2 保持原图比例模式的具体行为

以原图 1920×1080（16:9，横向）为例，用户设最长边 = 58：

- 长边（宽）= 58
- 短边（高）= 58 × (1080/1920) ≈ 33
- 输出网格：58×33

以原图 1080×1920（9:16，竖向）为例，用户设最长边 = 58：

- 长边（高）= 58
- 短边（宽）= 58 × (1080/1920) ≈ 33
- 输出网格：33×58

**规则**：长边始终等于用户指定的 N，短边 = round(N × 短/长)，方向由原图决定。

### 2.3 裁剪行为说明

- 中心裁剪模式：按目标比例裁切 → resize → 输出。行为不变。
- 保持原比例模式：**不需要额外裁切**，原图完整保留，只是按 N 做等比缩放。

---

## 3. 实现方案

### 3.1 算法层 (`pixelbeans/types.py`)

`PipelineConfig` 新增两个字段：

```python
preserve_aspect_ratio: bool = False   # 是否保持原图比例
max_dimension: int = 58               # 最长边格子数（仅在 preserve_aspect_ratio=True 时生效）
```

### 3.2 算法层 (`pixelbeans/pipeline.py`)

`preprocess()` 函数开头增加比例计算逻辑：

```python
if config.preserve_aspect_ratio:
    sw, sh = img.size
    if sw >= sh:  # 横向
        tw = config.max_dimension
        th = max(1, round(tw * sh / sw))
    else:         # 竖向
        th = config.max_dimension
        tw = max(1, round(th * sw / sh))
    config = replace(config, target_width=tw, target_height=th)
```

关键决策：
- `preserve_aspect_ratio=True` 时，`target_width/target_height` 被自动覆盖
- `_center_crop_to_aspect` 仍然执行，但此时目标比例 ≈ 原图比例，几乎无裁切
- 改动最小，复用现有裁剪逻辑

### 3.3 CLI 层 (`pixelbeans/cli.py`)

新增命令行参数：

```bash
--preserve-aspect-ratio    保持原图比例（不指定则用中心裁剪模式）
--max-dimension N          最长边格子数（配合 --preserve-aspect-ratio 使用，默认 58）
```

`--size` 在保持比例模式下变为可选。

### 3.4 前端层 (`web/src/App.jsx`)

Radio.Group 切换两种模式，表单动态变化：

- **中心裁剪**：显示 宽 × 高 两个输入框
- **保持原比例**：显示 最长边 输入框 + 实时输出预览（如 "原图 1920×911 → 将输出 58×28"）

API 请求时传递 `preserve_aspect_ratio` + `max_dimension`。

### 3.5 API 层（server/ + api/）

`POST /api/v1/pattern` 新增参数（均有默认值，向后兼容）：

| 参数 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `preserve_aspect_ratio` | bool | false | true = 保持原比例，false = 中心裁剪 |
| `max_dimension` | int | 58 | 最长边格子数 |

- **server/main.py**：Form 参数
- **api/app.py**：JSON 请求体字段（`api/schemas.py` PatternRequest）
- `api/app.py` 响应中的 `width/height` 从"用户输入值"改为"实际输出值"（`result.width/height`），对所有调用方更准确

---

## 4. 边界情况

| 场景 | 处理 |
|---|---|
| 原图本身就是正方形 | 保持比例模式 = 中心裁剪模式（结果相同） |
| 计算出的短边 < 1 | 至少为 1（`max(1, round(...))`） |
| max_dimension <= 0 | 参数校验拒绝 |
| 用户同时指定 --size 和 --preserve-aspect-ratio | --preserve-aspect-ratio 优先，--size 被忽略 |
| 旧客户端不传新参数 | 默认 false（中心裁剪），行为完全不变 |

---

## 5. 测试验证

- CLI 横图验证：cartoon.jpg 290×174 → 58×35 正确
- CLI 横图验证：web1.jpeg 1920×911 → 58×28 正确
- 中心裁剪模式回归：cartoon.jpg --size 58x58 → 58×58 正确
- 37 个单元测试全部通过
- 前端 UI 模式切换正常，输出预览实时计算
