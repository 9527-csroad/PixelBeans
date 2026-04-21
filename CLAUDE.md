# CLAUDE.md

## 项目概述
PixelBeans — 将照片转化为专业拼豆（Perler/Hama）图纸的工具。
最终形态是提供给 App 开发者调用的算法能力（后端 HTTP API / 端侧算法包）。
当前以 Web 验证界面作为算法效果的试验场。

## 协作语言
- 所有回复使用中文
- 代码注释使用英文（遵循行业惯例）
- 变量/函数/文件命名使用英文

## 技术栈
- **核心算法**：Python 3.10+（纯 Python，numpy + Pillow + opencv）
- **API 层**：FastAPI + Pydantic + uvicorn
- **前端**：React 18 + Vite + Canvas + Tailwind CSS
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

## 项目结构
```
PixelBeans/
├── pixelbeans/          ← 算法核心包（M1 已完成）
├── palettes/            ← 色卡数据（mard.json 已就绪）
├── server/              ← FastAPI 层（M2）
├── web/                 ← React 前端（M2）
├── tests/               ← 单元测试
├── docs/                ← plan.md 实施方案
├── images/              ← 样例图
└── results/             ← 输出产物
```

## 里程碑
- **M1**（已完成）：算法骨架 + CLI
- **M2**（进行中）：FastAPI + React Web 演示
- **M3**（规划中）：手动修图、分板拆图、PDF 打印等
