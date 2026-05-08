# CLAUDE.md

## 项目概述
PixelBeans — 将照片转化为专业拼豆（Perler/Hama）图纸的工具。
最终形态是提供给 App 开发者调用的算法能力（后端 HTTP API / 端侧算法包）。
当前以 Web 验证界面作为算法效果的试验场。

## Python 环境
- **解释器**：Python 3.12.0
- **环境路径**：Conda env `image` → `D:\Anaconda3\envs\image\python`
- **激活方式**：`conda activate image`
- **核心依赖版本**：numpy 2.4.3, Pillow 10.0.1, opencv-python 4.8.1, opencv-contrib-python 4.13.0, fastapi 0.128.0, uvicorn 0.40.0, pydantic 2.12.5, python-multipart 0.0.21, pytest 9.0.3

## 协作语言
- 所有回复使用中文
- 代码注释使用英文（遵循行业惯例）
- 变量/函数/文件命名使用英文

## 技术栈
- **核心算法**：Python 3.12（纯 Python，numpy + Pillow + opencv）
- **API 层**：FastAPI + Pydantic + uvicorn
- **前端**：React 18 + Vite + SVG + Tailwind CSS + Ant Design 5.x
- **PDF 导出**：ReportLab
- **测试**：pytest
- **Lint**：ruff

## 关键开发规则
- 算法核心与 UI/IO 完全解耦，纯 Python 无副作用
- 优先编辑已有文件，不创建新文件除非必要
- 不引入不必要的依赖和抽象
- 不在代码中写多余注释，除非 WHY 非显而易见
- 涉及破坏性操作（删除文件/分支、force push 等）需先确认
- 不提交包含密钥的文件
- `results/` 目录为 CLI 输出产物，不提交

## 项目结构
```
PixelBeans/
├── pixelbeans/          ← 算法核心包（M1 已完成，可 pip install -e .）
├── palettes/            ← 色卡数据（mard.json 已就绪，291 色）
├── server/              ← FastAPI 本地开发层（M2，端口 8003）
├── web/                 ← React + Vite + Ant Design 前端（M2，端口 5173）
├── api/                 ← 线上部署层（server/ 的线上版本，base64 传图）
├── tests/               ← 单元测试
├── docs/                ← plan.md 实施方案 + m2_prd.md
├── images/              ← 样例图（anime.jpg, cartoon.jpg, claude-code.png, cloud1.png）
├── results/             ← CLI 输出产物（不提交）
├── cli.py               ← 命令行入口（python cli.py --input xxx --size 58x58 --out result/）
├── pyproject.toml       ← 项目配置
└── requirements.txt     ← 运行时依赖
```

## 开发命令
```bash
# 算法 CLI
conda activate image
python cli.py --input images/anime.jpg --size 58x58 --out results/anime

# 后端 API（本地开发）
conda activate image
uvicorn server.main:app --host 0.0.0.0 --port 8000

# 前端（本地开发）
cd web && npm run dev -- --host

# 测试
pytest

# Lint
ruff check .
```

## 开发工作流

```
本地 Demo (server/ + web/)
    ↓ 算法验证通过后，同步算法逻辑
API 层 (api/) — 线上部署版本，base64 传图 + Nacos 服务发现
    ↓ 代码推送 + 部署
线上服务 (jszx-pixcelbeans-apiserver)
```

- `server/` 是本地开发层，使用 multipart/form-data 传图，便于快速调试
- `api/` 是线上部署层，使用 JSON `img_url` 传图，对接 Nacos 服务发现和文件网关
- 开发节奏：先在 `server/` + `web/` 完成功能验证 → 将算法改动同步到 `api/` → 部署到线上
- 对比差异时：`api/` vs `jszx-pixcelbeans-apiserver/`（线上实际运行代码）

## 已知问题
- **preview / pattern 图像重复**：线上 `/generate_pattern` 返回的 `preview` 和 `pattern` 两张图视觉上完全一致。根因：`_render_pattern()` 与 `render_preview(mode="square")` 逻辑重复，均为实心色块网格，仅 cell_size 和 1px 间隙不同，正常观看尺寸下无法区分。待确认修复方案后处理。

## 常见问题排查
- 详细规则和已记录的故障解决方案见 [`.claude/rules/`](.claude/rules/) 目录
- 当前收录：[Vite Windows IPv6 绑定问题](.claude/rules/vite-ipv6-windows.md)

## 里程碑
- **M1**（已完成）：算法骨架 + CLI + MARD 色卡 + 单元测试
- **M2**（进行中）：FastAPI 本地 API + React Web 演示 + SVG 图纸渲染
- **M3**（规划中）：手动修图、分板拆图、PDF 打印、中艺/漫奇色卡
