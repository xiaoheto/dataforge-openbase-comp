# DataForge OpenBase Competition

DataForge 团队参加第六届 OceanBase 数据库大赛的协调仓库。本仓库保存比赛文档、执行计划和两个官方项目的精确代码基线；功能代码在对应 submodule 中开发。

## 仓库结构

```text
.
├── docs/                  赛题、Lab、环境与协作说明
└── projects/
    ├── seekdb/            xiaoheto/seekdb submodule
    └── powercontext/      xiaoheto/powercontext submodule
```

两个 submodule 都固定在官方 `2026-competition` 分支：

| 项目 | 当前基线 | 官方上游 |
| --- | --- | --- |
| seekdb | `5bce9e06d` | `oceanbase/seekdb` |
| PowerContext | `dab24006` | `oceanbase/powercontext` |

## 首次获取

```bash
git clone --recurse-submodules https://github.com/xiaoheto/dataforge-openbase-comp.git
cd dataforge-openbase-comp

# 已经 clone 主仓库但没有初始化子模块时执行
git submodule update --init --recursive
```

新 clone 的 submodule 默认可能处于 detached HEAD。开始开发前在各项目中建立本地比赛分支：

```bash
git -C projects/seekdb switch --track origin/2026-competition
git -C projects/powercontext switch --track origin/2026-competition
```

## 当前工作

第一阶段用两周完成 seekdb Lab 0–1，三人并行实现 AI 函数增强的六个评分项。PowerContext 暂不开发，只保留可复现的比赛基线。

- [文档索引](docs/README.md)
- [两周执行计划](docs/lab-0-1-execution-plan.md)
- [仓库与 submodule 协作规范](docs/repository-workflow.md)

不要在父仓库中直接复制 seekdb 或 PowerContext 源码。功能提交先进入对应 fork，再由父仓库更新 submodule 指针。
