# DataForge 比赛文档

本目录收录团队协作规范、执行计划、课程 Lab 要求、架构导读和环境搭建说明。seekdb 与 PowerContext 均以官方 `2026-competition` 分支为基线。

## 阅读顺序

1. [仓库与 submodule 协作规范](repository-workflow.md)：统一远程、分支和 PR 流程。
2. [Lab 0–1 两周执行计划](lab-0-1-execution-plan.md)：查看分工、日程和验收门槛。
3. [Lab 1 测试记录](lab-1-test-record.md)：在集成阶段持续填写可复现证据。
4. [课程 Lab 总览](competition-labs.md)：查看 Lab 1、Lab 2 的目标、评分标准和测试入口。
5. [Lab 0：seekdb 架构导读](lab-0-seekdb-architecture.md)：理解 SQL 从解析到执行的主流程和源码目录。
6. [seekdb 从源码构建与部署](seekdb-install-and-deploy.md)：完成依赖安装、编译、单机部署和 mysqltest 配置。
7. [Lab 0 架构讲义（PDF）](lab-0-seekdb-architecture.pdf)：配合架构导读阅读。
8. [Mock AI Service](../tools/mock-ai-service/README.md)：本地起公开测试所需的 8000 端口服务。
9. [PowerContext 官方比赛题目与公开自测](../projects/powercontext/competition/README.md)：后续选择 PowerContext 赛题时阅读。
10. [赛事总览原图](assets/competition-overview.png)：保留官网赛题分类原始截图。

## 基本约定

- 除非文档另有说明，seekdb 命令均在 `projects/seekdb` 中执行。
- 两个项目统一使用 `2026-competition` 作为基线；功能开发在 `lab1/*` 分支上进行，开始实验前记录当前提交。
- 路径、命令、变量、SQL 标识符和源码符号使用行内代码格式。
- 多行 Shell、SQL、配置或输出使用带语言标识的代码块。
- 执行会删除实例数据的命令前，先核对部署名和数据目录。

开始实验前先检查本地仓库：

```bash
git -C projects/seekdb branch --show-current
git -C projects/seekdb rev-parse --short HEAD
git -C projects/powercontext branch --show-current
git -C projects/powercontext rev-parse --short HEAD
```

`projects/powercontext` 应停在 `2026-competition`。`projects/seekdb` 在基线同步时也是 `2026-competition`，开发时应切到对应的 `lab1/*` 功能分支。若输出为 `master`，比赛题目和公开自测可能不存在，应先按[协作规范](repository-workflow.md)同步正确分支。

## 文档维护

更新文档时请保持标题层级连续，表格包含表头，代码块注明语言，并同步修正文档内链接。实验规则与官方赛题冲突时，应保留冲突说明并标注待确认，避免自行推断评分口径。
