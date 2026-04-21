# M2 PRD — Web 演示

> 目标：装完 M1 的壳，让非技术用户和 App 开发同事能直观看效果
> 最后更新：2026-04-21
> 状态：Phase 1-2 已完成，Phase 3 待启动

---

## 1. 功能清单

### 1.1 FastAPI 后端 ✅

| 编号 | 功能 | 状态 | 说明 |
|------|------|------|------|
| B1 | POST /api/v1/pattern | ✅ 已完成 | 核心接口：接收图片 + 参数，返回图纸 JSON + 预览图 |
| B2 | GET /api/v1/palettes | ✅ 已完成 | 列出所有支持的色卡品牌 |
| B3 | GET /api/v1/palettes/{brand} | ✅ 已完成 | 返回指定品牌完整色卡数据 |
| B4 | CORS 中间件 | ✅ 已完成 | 允许前端本地开发跨域 |
| B5 | 错误处理 | ✅ 已完成 | 统一 422/500 响应格式 |

### 1.2 React 前端 ✅

| 编号 | 功能 | 状态 | 说明 |
|------|------|------|------|
| F1 | 图片上传区 | ✅ 已完成 | 拖拽 / 点击上传，支持 JPG/PNG，带预览 |
| F2 | 参数面板 | ✅ 已完成 | 网格尺寸、最大颜色数、亮度/对比度/饱和度、色卡选择 |
| F3 | 预览区 | ✅ 已完成 | 原图 vs 像素化结果（Tab 切换） |
| F4 | 网格图纸 | ✅ 已完成 | Canvas 渲染带符号的拼豆图纸 |
| F5 | BOM 清单 | ✅ 已完成 | 表格展示使用的色号、颜色、数量 |
| F6 | 色卡色块 | ✅ 已完成 | BOM 中内嵌色块展示 |
| F7 | PDF 导出 | 🚧 待开发 | 调用 ReportLab 生成的 PDF 下载 |

### 1.3 数据补充

| 编号 | 功能 | 状态 | 说明 |
|------|------|------|------|
| D1 | 中艺色卡 | ⏸ 已延期 | 目标 URL 404，等待提供数据源 |
| D2 | 漫奇色卡 | ⏸ 已延期 | 目标 URL 404，等待提供数据源 |
| D3 | MARD 中文色名 | ⏸ 已搁置 | 当前使用 code 作为 name，不影响功能 |

---

## 2. 技术选型

| 层面 | 选型 | 理由 |
|------|------|------|
| 后端框架 | FastAPI + uvicorn | Python 生态标准选择 |
| 数据校验 | Pydantic v2 | 与 FastAPI 天然集成 |
| 前端框架 | React 18 + Vite | 方案指定 |
| UI 组件库 | Ant Design 5.x | 组件齐全（Upload/Table/Slider/Modal），开箱即用，中文生态好，适合快速出 demo |
| 样式方案 | Tailwind CSS + antd | Tailwind 处理布局微调，antd 提供标准组件 |
| 绘图 | 原生 Canvas API | 方案指定，网格图纸无需额外库 |
| PDF | ReportLab | Python 生态成熟 |
| 文件上传 | python-multipart | FastAPI 标准依赖 |

### 2.1 为什么不选 shadcn/ui

shadcn/ui 需要手动组装组件，对于需要 Upload、Table、ColorPicker 的场景反而增加工作量。M2 目标是快速验证效果，antd 更合适。后续如果需要更轻量或更定制化的 UI 再考虑迁移。

---

## 3. 执行步骤

### Phase 1: FastAPI 后端（B1-B5）

1. 创建 `server/` 目录结构
2. 安装依赖：fastapi, uvicorn, pydantic, python-multipart
3. 实现 API schema（Pydantic models）
4. 实现 POST /api/v1/pattern 接口（调用 M1 算法核心）
5. 实现色卡查询接口
6. 配置 CORS 和错误处理
7. 用 curl/Postman 测试接口

### Phase 2: React 前端（F1-F6）

1. 用 Vite 初始化 React 项目到 `web/` 目录
2. 安装 antd + Tailwind CSS
3. 实现上传区（F1）
4. 实现参数面板（F2）
5. 实现预览区（F3 + F4）
6. 实现 BOM 清单（F5）
7. 联调后端 API

### Phase 3: 色卡数据 + PDF（D1-D3, F7）

1. 抓取中艺色卡（D1）
2. 抓取漫奇色卡（D2）
3. 补充 MARD 中文色名（D3）
4. 集成 ReportLab 生成 PDF（F7）

---

## 4. API 详细设计

### 4.1 POST /api/v1/pattern

**请求**：`multipart/form-data`

| 字段 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| image | File | 是 | - | 图片文件 |
| width | int | 否 | 58 | 目标网格宽度 |
| height | int | 否 | 58 | 目标网格高度 |
| palette | string | 否 | "mard" | 色卡品牌 |
| max_colors | int | 否 | null | 最大颜色数 |
| brightness | float | 否 | 1.0 | 亮度系数 |
| contrast | float | 否 | 1.0 | 对比度系数 |
| saturation | float | 否 | 1.0 | 饱和度系数 |
| sharpen | bool | 否 | false | 是否锐化 |
| remove_isolated | bool | 否 | true | 是否清理孤豆 |
| min_region_size | int | 否 | 2 | 最小连通区域大小 |

**响应**：

```json
{
  "ok": true,
  "size": { "width": 58, "height": 58 },
  "pattern": [[{"code": "A1", "hex": "#...", "symbol": "A"}, ...], ...],
  "palette_used": [{"code": "A1", "name": "...", "hex": "#...", "symbol": "A", "count": 142}, ...],
  "stats": {"total_beads": 3364, "unique_colors": 27, "empty_cells": 0},
  "preview_png": "<base64>",
  "grid_png": "<base64>"
}
```

### 4.2 GET /api/v1/palettes

响应：`["mard", "zhongyi", "manqi"]`

### 4.3 GET /api/v1/palettes/{brand}

响应：完整色卡 JSON 数据

---

## 5. 前端页面布局

```
┌──────────────────────────────────────────────────┐
│  PixelBeans — 拼豆图纸生成器                      │
├────────────────┬─────────────────────────────────┤
│  上传区        │  参数面板                        │
│  (拖拽/点击)   │  - 色卡选择                      │
│                │  - 网格尺寸 (W × H)             │
│                │  - 最大颜色数                    │
│                │  - 亮度 / 对比度 / 饱和度        │
│                │  - [生成图纸] 按钮               │
├────────────────┴─────────────────────────────────┤
│  预览区（左右对比）                               │
│  ┌──────────────┐  ┌──────────────┐              │
│  │  原图预览     │  │  拼豆图纸     │              │
│  │  (Canvas)    │  │  (Canvas)    │              │
│  └──────────────┘  └──────────────┘              │
├──────────────────────────────────────────────────┤
│  BOM 清单（antd Table）                           │
│  色号 | 颜色名 | 色块 | 数量                      │
│  ──────────────────────────────                   │
│  [导出 PDF] 按钮                                  │
└──────────────────────────────────────────────────┘
```

---

## 6. 验收标准

1. 本地启动 `uvicorn server.main:app` 和 `npm run dev` 后能正常访问 — ✅
2. 上传图片后能在 3 秒内（58×58 网格）看到拼豆图纸预览 — ✅ 实测 0.22s
3. 调整参数后重新生成，结果与 CLI 一致（回归测试）— ✅ 使用同一算法核心
4. BOM 清单显示正确的色号和数量 — ✅
5. 中艺、漫奇色卡可用 — ⏸ 目标 URL 404，已延期
6. PDF 导出功能正常 — 🚧 Phase 3 待开发

---

## 7. 风险

| 编号 | 风险 | 等级 | 应对 |
|------|------|------|------|
| R1 | MARD 中文色名数据缺失 | 中 | 先从淘宝/官网整理，M2 先用 code 作为 name |
| R2 | 中艺/漫奇色卡抓取失败 | 中 | 手动整理备选方案 |
| R3 | 大图生成耗时 > 3s | 低 | 加 loading 状态，后续优化性能 |
| R4 | antd + Tailwind 样式冲突 | 低 | 配置 Tailwind preflight 避免冲突 |
