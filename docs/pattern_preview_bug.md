# Pattern Preview Bug: 线上 preview 和 pattern 图像重复

## 问题描述

线上 `/generate_pattern` 接口返回的 `preview_png` 和 `pattern_png` 两张图视觉上完全一致。
本地 Demo 中三张图（拼豆图纸、效果预览、符号图纸）看起来各不相同。

## 根因

**不是后端代码差异**——本地 `api/` 和线上 `jszx-pixcelbeans-apiserver/` 的渲染代码字节级一致。

真正原因是 **前端架构差异**：

- 本地 `web/` 前端的"拼豆图纸"Tab **不使用后端返回的 pattern 图**，而是用 `PatternCanvas.jsx` 从 `result.pattern` 数据渲染 SVG（带色号文字、行列编号、十字线），所以看起来三张图都不同
- 线上（App 端）直接展示后端生成的三张 PIL 图像，其中 `render_preview(mode="square")` 和 `_render_pattern()` 都是纯色块网格，仅 cell_size 不同，肉眼无法区分

```
render_preview(mode="square") → 纯色块，RGBA 透明底，cell_size=8
_render_pattern()              → 纯色块，RGB 白底，cell_size=16
render_grid()                  → 色块 + 符号 + 分隔线，cell_size=24  ← 这张图有独特内容
```

## 修复方案（已实施）

在 `pixelbeans/export.py` 中新增 `render_chart()` 函数，替代原来散落在 `api/app.py` 中的 `_render_pattern()`：

- **preview** (`render_preview`, cell_size=8): 扁平色块预览，快速对比原图效果
- **chart** (`render_chart`, cell_size=20): 色号图纸，带色号文字 + 行列编号 + 十字线，主拼豆参考
- **grid** (`render_grid`, cell_size=24): 符号图纸，带符号 + 分隔线，替代拼豆参考

### 修改范围

| 文件 | 改动 |
|------|------|
| `pixelbeans/export.py` | 新增 `render_chart()` + `write_chart()`，更新 `write_all()` |
| `api/app.py` | 移除 `_render_pattern()`，改用 `render_chart()` |
| `server/main.py` | 返回 `chart_png` |
| `server/schemas.py` | 添加 `chart_png` 字段 |

### 线上同步

线上 `jszx-pixcelbeans-apiserver/` 需要：
1. 同步 `pixelbeans/export.py`（获取 `render_chart`）
2. 同步 `pixcelbeans.py` 中 `_render_pattern` 调用改为 `render_chart`
3. 部署
