# Lab 1 测试记录

> 在第 13 天干净环境复现时填写。失败、跳过和未运行必须如实记录，不得留空或写成通过。

## 版本与环境

| 项目 | 记录 |
| --- | --- |
| seekdb 最终提交 | Part A 功能提交 `b6cc9ac51`（分支 `lab1/ai-prompt`），基线 `5bce9e06d` |
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
| `AI_PROMPT` 类型与模板增强 | `ai_prompt` mysqltest | 通过 | `Total 1, Passed 1, Failed 0`，1.27s。与官方 `ai_prompt.result` 逐条一致：JSON Object/Array 参数保留结构、重复占位符、`CHAR`/`VARCHAR`/`BINARY`/`VARBINARY`/`TINYBLOB`/`TEXT`/`LONGTEXT` 模板、非法类型与 NULL 字面量回归 |
| `AI_COMPLETE` 请求与响应 | `ai_function_enhancement` | 通过 | 套件执行到 Part B 用例前，`complete_ok = 1`、`complete_config_ok = 1`；覆盖普通 Prompt、`AI_PROMPT` 的 JSON 结果、JSON config、`NULL` config、`temperature`/`max_tokens` |
| `AI_EMBED` 单行语义 | `ai_function_enhancement` | 未运行 | 属 Part B。套件中的单行语句（`embed_dimension = 4`、`requested_dimension = 768`）执行通过，但那是基线自带能力，本分支不含 Part B 改动，不作为 Part B 的验证结果 |
| `AI_EMBED` 跨行批量 | `ai_function_enhancement` | 失败 | 套件在此停止：`At line 47: query 'select id, json_length(ai_embed('enhance_embed', content)) as dimension from ai_enhance_batch order by id' failed: 1210: Incorrect arguments to ai_embed, model id or content is null`。属 Part B：基线的 `AI_EMBED` 无 `eval_batch_func_`，逐行路径把 NULL 行当错误 |
| Ollama Provider | `ai_function_enhancement` | 未运行 | 属 Part C，套件在 Part B 用例处停止，未执行 |
| `AI_RERANK` 结果正确性 | `ai_function_enhancement` | 未运行 | 属 Part C，套件在 Part B 用例处停止，未执行 |

Part A 只覆盖自身两个评分项，其余四项如实记为未运行。`ai_function_enhancement` 套件在跨行 `AI_EMBED` 用例停止，该用例属 Part B。

结果只使用 `通过`、`失败`、`跳过` 或 `未运行`。

## 回归结果

| 检查 | 命令 | 结果 | 备注 |
| --- | --- | --- | --- |
| 增量构建 | `make -C build_release seekdb -j2` | 通过 | `BUILD_TIME: Nov  1 2026 02:38:55`；含改动的编译单元 `unity_ob_sql_ob_sql_engine_expr_15` 的归档对象 md5 `f93b785205b2ea52c58e20e448444eb8`，与改动后源码独立编译的产物逐字节一致，确认二进制含修复 |
| 二进制 REVISION 与提交一致性 | `build_release/src/observer/seekdb -V` | 通过 | `REVISION: 1-b6cc9ac518dc9c6b39fd7e478736072dd6057e55`，与分支 `lab1/ai-prompt` 的 HEAD 一致。`GIT_REVISION` 由 cmake 配置期 `git rev-parse HEAD` 写入 `ob_version.cpp`，修复提交后需重新配置 cmake |
| AI_PROMPT 目标 mysqltest | `./obd.sh mysqltest -n single --disable-reboot --test-dir ./mysql_test/test_suite/ai_function/t --result-dir ./mysql_test/test_suite/ai_function/r --test-set ai_prompt` | 通过 | `Total 1, Passed 1, Failed 0`。`obd.sh` 会切换到 `tools/deploy` 作为工作目录，路径不能重复写 `./tools/deploy/` 前缀 |
| 完整 `ai_function` suite | `./obd.sh mysqltest -n single --disable-reboot --test-dir ./mysql_test/test_suite/ai_function/t --result-dir ./mysql_test/test_suite/ai_function/r --test-set ai_function_enhancement` | 失败 | 套件在 Part B 的跨行 `AI_EMBED` 用例处停止，Part A 的用例此前全部通过 |
| 重复占位符缓冲区回归 | `select ai_complete('enhance_complete', ai_prompt('{0}/{0}', json_array(1,true)));` | 通过 | 返回 `[1, true]/[1, true]`；字符串参数同样通过，`ai_prompt('{0}/{0}', 'hello world')` 返回 `hello world/hello world`。修复前两者均报 `OB_BUF_NOT_ENOUGH`。公共用例只构造 JSON 不做替换，覆盖不到该路径，故手工验证。用 Mock AI Service 的回显模式读取服务端实际收到的 prompt |
| NULL 参数语义回归 | `select ai_prompt('{0}', v) from t_null;`（`v` 为 NULL 值列） | 通过 | 报 `ERROR 5083 (22000): Invalid data type for the operation`，与 NULL 字面量在类型推导阶段的报错一致。修复前静默返回空串。公共用例只有 NULL 字面量（plan 期拦截），覆盖不到运行时路径，故手工验证 |
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
