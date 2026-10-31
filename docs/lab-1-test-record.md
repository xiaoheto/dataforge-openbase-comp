# Lab 1 测试记录

> 在第 13 天干净环境复现时填写。失败、跳过和未运行必须如实记录，不得留空或写成通过。

## 版本与环境

| 项目 | 记录 |
| --- | --- |
| seekdb 最终提交 | Part A 功能提交 `4b9d8905c`（分支 `lab1/ai-prompt`），基线 `5bce9e06d` |
| 父仓库提交 | 待填写 |
| 操作系统 | Ubuntu 24.04.5 LTS x86_64 |
| CPU / 内存 | 18 核 / 7.4 GiB，编译并行度 `-j2` |
| 构建命令 | `./build.sh release --make -j2` |
| OBD / seekdb 版本 | OBD 4.1.0 / seekdb 1.4.0.0 |
| mysql 端口 | 10000 |
| Mock AI Service 提交与启动命令 | `python3 tools/mock-ai-service/mock_ai_service.py 8000` |

## 评分项结果

| 评分项 | 测试命令或用例 | 结果 | 证据或备注 |
| --- | --- | --- | --- |
| `AI_PROMPT` 类型与模板增强 | `ai_prompt` mysqltest | 通过 | 覆盖 JSON Object/Array、重复占位符、`TEXT`/`LONGTEXT`/BLOB、普通字符串与非法类型回归 |
| `AI_EMBED` 单行语义 | `ai_function_enhancement` | 未运行 | 属 Part B |
| `AI_COMPLETE` 请求与响应 | `ai_function_enhancement` | 通过 | `complete_ok = 1`，`complete_config_ok = 1`；覆盖普通 Prompt、`AI_PROMPT` 结果、JSON config、`NULL` config、`temperature`/`max_tokens` |
| Ollama Provider | `ai_function_enhancement` | 未运行 | 属 Part C |
| `AI_RERANK` 结果正确性 | `ai_function_enhancement` | 未运行 | 属 Part C |
| `AI_EMBED` 跨行批量 | `ai_function_enhancement` | 未运行 | 属 Part B；套件在该用例处停止 |

Part A 只覆盖自身两个评分项，其余四项如实记为未运行。`ai_function_enhancement` 套件在跨行 `AI_EMBED` 用例停止，该用例属 Part B。

结果只使用 `通过`、`失败`、`跳过` 或 `未运行`。

## 回归结果

| 检查 | 命令 | 结果 | 备注 |
| --- | --- | --- | --- |
| 增量构建 | `./build.sh release --make -j2` | 通过 | 提交 `4b9d8905c` 涉及的 `unity_ob_sql_ob_sql_engine_expr_15` 编译单元重新编译通过，产物与改动前二进制对应的 `.o` 逐字节一致（md5 `d13bfcd5`），确认 LF 归一化不改变机器码 |
| AI 函数目标 mysqltest | `./tools/deploy/obd.sh mysqltest -n single --disable-reboot --test-dir ./mysql_test/test_suite/ai_function/t --result-dir ./mysql_test/test_suite/ai_function/r --test-set ai_prompt` | 通过 | `obd.sh` 会切换到 `tools/deploy` 作为工作目录，路径不能重复写 `./tools/deploy/` 前缀 |
| 完整 `ai_function` suite | `./tools/deploy/obd.sh mysqltest -n single --disable-reboot --suite ai_function` | 未运行 | 待 Part B、Part C 完成后补齐 |
| 普通 SQL 冒烟 | 待填写 | 未运行 | 待填写 |
| 连续重复运行 | 待填写 | 未运行 | 待填写 |

## 已知限制

- Mock AI Service 由 `tools/mock-ai-service/` 提供，只验证请求构造、响应解析和错误处理路径，不能替代比赛隐藏测试使用的官方服务。
- `tools/deploy/activate_obd.sh` 的 `OBD_HOME` 修复是本地部署改动，保持为未提交状态，不随功能提交推送。

## 团队贡献

| 成员 | 负责内容 | PR |
| --- | --- | --- |
| A | `AI_PROMPT`、`AI_COMPLETE` | 待填写 |
| B | `AI_EMBED` 单行与跨行批量 | 待填写 |
| C | Ollama Provider、`AI_RERANK` | 待填写 |
