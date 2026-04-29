# PixelBeans API 接口文档

> **版本**: 1.0.0
> **协议**: HTTP POST / JSON
> **部署**: `api/` 文件夹独立运行

---

## 快速开始

### 启动服务

```bash
cd api
pip install -r requirements.txt
python -m uvicorn app:app --host 0.0.0.0 --port 8000
```

### 调用方式

```
POST /api/v1/pattern
Content-Type: application/json
```

---

## 生成拼豆图纸

### POST `/api/v1/pattern`

将上传图片转换为拼豆图纸，返回色号网格、BOM 清单和三张预览图。

### 请求体

| 字段 | 类型 | 必填 | 默认值 | 范围 | 说明 |
|------|------|------|--------|------|------|
| `image` | string | ✅ | — | — | Base64 编码的图片（JPG/PNG），不含 `data:` 前缀 |
| `width` | int | ✅ | — | 10-500 | 目标网格宽度（列数） |
| `height` | int | ✅ | — | 10-500 | 目标网格高度（行数） |
| `palette` | string | ✅ | — | — | 色卡品牌，如 `"mard"` |
| `max_colors` | int | — | `null` | 1-100 | 最大颜色数（不限制填 null） |
| `brightness` | float | — | `1.0` | 0.1-3.0 | 亮度调节 |
| `contrast` | float | — | `1.0` | 0.1-3.0 | 对比度调节 |
| `saturation` | float | — | `1.0` | 0.1-3.0 | 饱和度调节 |
| `sharpen` | bool | — | `false` | — | 是否应用锐化 |
| `remove_isolated` | bool | — | `true` | — | 是否清理孤豆 |
| `min_region_size` | int | — | `2` | 1-10 | 最小连通区域大小 |

### 请求示例（Python）

```python
import base64, requests

with open("input.jpg", "rb") as f:
    b64 = base64.b64encode(f.read()).decode()

resp = requests.post("http://localhost:8000/api/v1/pattern", json={
    "image": b64,
    "width": 58,
    "height": 58,
    "palette": "mard",
})
result = resp.json()
```

### 成功响应（HTTP 200）

| 字段 | 类型 | 说明 |
|------|------|------|
| `width` | int | 网格宽度 |
| `height` | int | 网格高度 |
| `pattern` | array | 二维网格 `pattern[y][x]`，每项 `{ "code": string, "hex": string }` |
| `colors` | array | 使用的颜色清单 |
| `stats` | object | 统计信息 |
| `preview_image` | string | Base64 PNG，像素风预览（8px cells） |
| `grid_image` | string | Base64 PNG，符号网格+十字线（24px cells） |
| `pattern_image` | string | Base64 PNG，纯色网格无符号（16px cells） |

#### `pattern[y][x]` — 单个格子

| 字段 | 类型 | 说明 |
|------|------|------|
| `code` | string | 色号，如 `"E1"`, `"T1"` |
| `hex` | string | 颜色值，如 `"#FDD3CC"` |

#### `colors[]` — 颜色清单

| 字段 | 类型 | 说明 |
|------|------|------|
| `code` | string | 色号，如 `"E1"` |
| `name` | string | 色名 |
| `hex` | string | 颜色值 |
| `symbol` | string | 符号（图纸中代表该色的标记） |
| `count` | int | 该颜色的使用数量 |

#### `stats` — 统计信息

| 字段 | 类型 | 说明 |
|------|------|------|
| `total_beads` | int | 总豆数 |
| `unique_colors` | int | 使用的不同颜色数 |
| `empty_cells` | int | 空格数（透明/无豆） |

### 成功响应示例

```json
{
  "width": 40,
  "height": 40,
  "stats": { "total_beads": 1600, "unique_colors": 31, "empty_cells": 0 },
  "colors": [
    { "code": "E1", "name": "E1", "hex": "#FDD3CC", "symbol": "E", "count": 351 },
    { "code": "T1", "name": "T1", "hex": "#FFFFFF", "symbol": "e", "count": 298 }
  ],
  "pattern": [
    [
      { "code": "T1", "hex": "#FFFFFF" },
      { "code": "E1", "hex": "#FDD3CC" }
    ]
  ],
  "preview_image": "iVBORw0KGgo...",
  "grid_image": "iVBORw0KGgo...",
  "pattern_image": "iVBORw0KGgo..."
}
```

### 错误响应

| 状态码 | `detail` | 说明 |
|--------|----------|------|
| 404 | `"Palette 'xxx' not found"` | 色卡不存在 |
| 400 | `"Invalid image: ..."` | 图片解码失败 |
| 500 | `"Pattern generation failed: ..."` | 生成过程异常 |

错误示例（HTTP 400）：

```json
{
  "detail": "Invalid image: cannot identify image file",
  "error_code": null
}
```
