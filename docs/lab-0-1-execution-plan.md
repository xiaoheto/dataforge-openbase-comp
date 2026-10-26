# Lab 0–1 两周执行计划

## 目标与交付

先完成 Lab 0 环境与架构训练，再完成 Lab 1 六个子题，目标 60/60。

最终交付包括：

- seekdb `lab1/integration` 分支上的实现与测试；
- 六个评分项的 PR 和交叉评审记录；
- `docs/lab-1-test-record.md`，记录环境、提交、命令、结果和已知限制。

本阶段只开发 seekdb。PowerContext 保持在比赛基线，后续选题时另行规划。

## 团队分工

| 成员 | 主责 | 分值目标 |
| --- | --- | ---: |
| A | `AI_PROMPT`、`AI_COMPLETE` | 20 |
| B | `AI_EMBED` 单行与跨行批量 | 20 |
| C | Ollama Provider、`AI_RERANK` | 20 |

成员同时负责对应实现、测试和 PR 说明。评审采用循环关系：A 评审 B，B 评审 C，C 评审 A；复杂公共改动再增加一名评审。

## 接口与实现边界

- `AI_PROMPT(template, ...)` 扩展 `TEXT`/`LONGTEXT`、JSON、嵌套和占位符处理，保持 JSON 返回类型。
- `AI_COMPLETE(model, prompt[, config])` 支持普通文本、`AI_PROMPT` 结果、JSON config 和长文本输出。
- `AI_EMBED(model, content[, dimension])` 校验正整数维度和返回向量；批量执行保持 SQL 接口不变。
- `AI_RERANK(model, query, documents[, doc_key])` 支持字符串与对象数组，保持原始文档身份和稳定排序。
- Ollama Provider 名称大小写不敏感，允许空 access key，并遵循官方自测规定的原生 Completion 与 Embedding 协议。
- 异常响应必须产生明确 SQL 错误，不得导致崩溃、结果错位、部分结果或资源泄漏。

## 日程

| 时间 | 工作 | 完成门槛 |
| --- | --- | --- |
| 第 1 天 | 三人初始化 submodule、工具链和首次构建；选内存最大的电脑作为集成机 | 三台环境记录完成，至少两台能构建 |
| 第 2 天 | Lab 0 架构走读、部署、SQL、`EXPLAIN` 和基线 mysqltest | 基线测试通过后才开始功能开发 |
| 第 3–5 天 | A 完成 `AI_PROMPT`；B 完成单行 `AI_EMBED`；C 完成 Ollama | 三个 10 分项分别通过目标测试并提交 PR |
| 第 6 天 | 第一轮集成与公共工具代码冲突处理 | 前 30 分公开测试全部通过 |
| 第 7–9 天 | A 完成 `AI_COMPLETE`；B 完成批量 `AI_EMBED`；C 完成 `AI_RERANK` | 后三个功能分别通过目标测试并提交 PR |
| 第 10 天 | 按基础工具、Provider、表达式和批量执行顺序完成集成 | 六项功能在同一提交上可运行 |
| 第 11–12 天 | 边界用例、隐藏测试模拟和完整 AI suite 回归 | 无新增回归，无崩溃或行映射错误 |
| 第 13 天 | 集成机从干净 checkout 复现构建、部署和测试 | 形成完整测试记录 |
| 第 14 天 | 缓冲、缺陷修复和交付冻结 | 最终提交与记录一致 |

## 测试矩阵

- `AI_PROMPT`：`TEXT`/`LONGTEXT`、JSON Array/Object、嵌套 Prompt、重复或非法占位符、Unicode、转义和 `NULL`。
- `AI_EMBED`：默认或显式 dimension、零/负数/非整数、非法向量元素、维度不符、乱序 index、`NULL`、过滤、`LIMIT` 和多批次。
- `AI_COMPLETE`：普通 Prompt、`AI_PROMPT` JSON、空或完整 config、长文本、空响应、非法 JSON 和网络失败。
- Ollama：Endpoint 增删改查、Provider 大小写、空 access key、非流式 Completion 和 Embedding。
- `AI_RERANK`：字符串数组、对象数组、doc key、跨批次全局 index、相同分数稳定排序，以及缺失、重复或越界 index。
- 回归：普通 SQL、现有 AI 函数、目标 mysqltest 和完整 `ai_function` suite。

比赛分支存在公开 C++ unit test 时直接运行；若某个 unit test 未随分支发布，则补充等价 mysqltest，不创建虚假的测试目标。

## 资源约定

- 8 GiB 内存使用 `-j2`，16 GiB 使用 `-j4`，32 GiB 以上最多使用 `-j8`。
- 三人使用各自 Linux/WSL，不购买长期服务器。
- 只有在第一天结束时没有任何电脑能用 `-j1/-j2` 完成构建，才临时租用 16–32 GiB Linux 实例。
- Mock AI Service 固定使用官方实现和端口 `8000`；不得用真实模型结果替代比赛自测。
