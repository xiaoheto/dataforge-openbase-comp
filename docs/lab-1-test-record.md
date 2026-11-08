# Lab 1 测试记录

> 在第 13 天干净环境复现时填写。失败、跳过和未运行必须如实记录，不得留空或写成通过。
>
> 每位成员单独一节，互不覆盖。Part A 的记录到「Part A 测试记录」为止，Part C 的记录在文末。

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

Part A 只覆盖自身两个评分项，其余四项如实记为未运行。`ai_function_enhancement` 套件在跨行 `AI_EMBED` 用例停止，该用例属 Part B。Ollama Provider 与 `AI_RERANK` 两项的结果见文末「Part C 测试记录」。

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
| C | Ollama Provider、`AI_RERANK` | 分支 `lab1/ollama`（`6147e3bd8`）、`lab1/ai-rerank`（`6478e02b4`），基线 `b6cc9ac51`；附加修复 `lab1/ai-endpoint-max-concurrency`（`714e3c88a`） |

## Part C 测试记录（成员 C：Ollama Provider、`AI_RERANK`）

### 版本与环境

| 项目 | 记录 |
| --- | --- |
| seekdb 提交 | `lab1/ollama` = `6147e3bd8`，`lab1/ai-rerank` = `6478e02b4`，`lab1/ai-endpoint-max-concurrency` = `714e3c88a`，基线 `b6cc9ac51`（`lab1/integration`） |
| 父仓库提交 | 待填写（Mock AI Service 的 embedding 默认维度改为 768、换行符工具修正） |
| 操作系统 | Ubuntu 24.04.4 LTS x86_64，VMware 虚拟机 `localVM`（宿主 Windows） |
| CPU / 内存 | Intel Core Ultra 7 155H，2 核 / 3.5 GiB（交换分区 3.5 GiB），编译并行度 `-j2` |
| 构建命令 | 首次 `./build.sh release --init --make -j2`，之后 `./build.sh release --make -j2` |
| OBD / seekdb 版本 | OBD 4.1.0 / seekdb 1.4.0.0，`REVISION: 1-2ac0b16390e59f41b58fe5974abcd4e10657f6b7`（三个功能分支的本地合并），`BUILD_TIME: Nov 8 2026 22:05` |
| mysql 端口 | 10000，`obd.sh prepare -b ./build_release -p /tmp/obtest` + `obd.sh deploy -c ./tools/deploy/single.yaml`（`memory_budget: "2G"`、`cpu_count: "2"`，虚拟机内存只有 3.5 GiB）。内表 `__all_ai_model_endpoint` 加列后必须重建集群 |
| Mock AI Service | `python3 tools/mock-ai-service/mock_ai_service.py 8000`，embedding 默认维度 768 |
| 测试命令 | `./tools/deploy/obd.sh mysqltest -n single --disable-reboot --test-dir ./mysql_test/test_suite/ai_function/t --result-dir ./mysql_test/test_suite/ai_function/r --test-set <用例名>`（`obd.sh` 会切到 `tools/deploy`，路径不能重复写 `./tools/deploy/` 前缀） |

### 评分项结果

| 评分项 | 测试命令或用例 | 结果 | 证据或备注 |
| --- | --- | --- | --- |
| Ollama Provider | `ai_function_enhancement`、`ai_function_ollama` | 通过 | 官方套件 `Total 1, Passed 1, Failed 0`；自建用例 `ai_function_ollama`（新增 `t/ai_function_ollama.test` 与 `r/mysql/ai_function_ollama.result`）同样 `Passed 1, Failed 0`。覆盖：provider 原样入库（`ollama` 入库为 `ollama`，`ALTER` 写 `"Ollama"` 后为 `Ollama`，比较仍不区分大小写）、ollama 允许空 access_key（openai 传空 access_key 报 11114 `The param 'access_key' is empty or null`，未知 provider 报 11116 `The value of param 'provider' is invalid`）、补全走 `/api/generate` 读 `$.response`、向量化走 `/api/embed` 读 `$.embeddings` 且维度为 768 |
| `AI_RERANK` 结果正确性 | `ai_function_enhancement`、`ai_function_rerank` | 通过 | 官方套件 `Total 1, Passed 1, Failed 0`；自建用例 `ai_function_rerank`（新增 `t/ai_function_rerank.test` 与 `r/mysql/ai_function_rerank.result`）同样 `Passed 1, Failed 0`。覆盖：字符串数组返回条数为 4 且按分数降序（`apple` 首条、`banana` 次条、`vegetable` 末条）、`doc_key` 路径首条 `id = a`、条数 2、第 4 个参数为 NULL 时按纯字符串文档处理、数组为空 / 元素非字符串 / 元素非对象 / 缺 doc key / doc key 为空 / 模型不存在均报 1210 |

### 附加修复：端点的 `max_concurrency` 参数

官方 `ai_model_endpoint_ddl` 用例期望端点支持 `max_concurrency`，但上游所有分支（含 `2026-competition`）都没有这个字段，用例在基线就失败。修复放在独立分支 `lab1/ai-endpoint-max-concurrency`（`714e3c88a`），不在评分项分支里。

| 项目 | 内容 |
| --- | --- |
| 取值范围 | 必须是 JSON 数字且在 1 ~ 1024 之间，否则报 `11116 The value of param 'max_concurrency' is invalid`（官方用例用 `--error 11116` 断言）。小数 `3.5`、JSON `null`、负数、超大整数同样报 11116 |
| 存储 | 内表 `__all_ai_model_endpoint` 增加 `max_concurrency` 列，视图 `DBA_OB_AI_MODEL_ENDPOINTS` 增加 `MAX_CONCURRENCY` 列，未设置时为 0（不限制并发） |
| 影响 | 内表结构变化，**已存在的集群必须重建**（`obd.sh destroy` + `prepare` + `deploy`），否则旧表没有该列 |
| 验证 | `--test-set ai_model_endpoint_ddl` 从失败变为 `Total 1, Passed 1, Failed 0` |

审核记录（2026-11-08）：

| 检查 | 方法 | 结果 |
| --- | --- | --- |
| 与官方期望逐字节一致 | 用 `--record` 录一份结果，与官方 `r/mysql/ai_model_endpoint_ddl.result` 做 `diff` | 两份文件完全相同（10682 字节） |
| 边界取值 | 手工 SQL：1 和 1024 接受；0、1025、`3.5`、`null`、负数、10^20、`2147483647` 均报 11116 | 与官方用例的断言一致 |
| 失败的 ALTER 不污染数据 | 连续 5 次非法 ALTER 后再查视图与内表 | 值仍是上一次合法的 512，事务回滚正确 |
| ALTER 不带该参数时保留原值 | 先 `max_concurrency:64`，再只改 `provider` | 仍为 64；带上该参数则被替换为 7 |
| 落盘与持久化 | 查内表 `__all_ai_model_endpoint`；再 `obd.sh restart -n single` 重启集群后复查 | 重启前后都是 512，值持久 |
| 运行时可用 | 带 `max_concurrency:64` 的端点调用 `ai_complete()` | 返回正常，读取端点的路径不受新列影响 |
| 写入路径唯一 | 全仓检索 `OB_ALL_AI_MODEL_ENDPOINT_TNAME` | 只有 `ob_ai_service_proxy.cpp` 与 `ob_ai_service_executor.cpp` 写这张表，新增列的三个位置都已覆盖 |
| 限流本身 | 代码走查 | **参数只做校验、存储与展示，没有真正限制并发请求数**；官方用例只覆盖 DDL 行为，上游也没有参考实现，限流逻辑不在本次改动范围内 |

### 回归结果

| 检查 | 命令 | 结果 | 备注 |
| --- | --- | --- | --- |
| 官方 `ai_function` 套件 | `--test-set ai_function_enhancement` | 通过 | `Total 1, Passed 1, Failed 0`，整套跑到最后一行。该套件包含 Part B 的跨行 `AI_EMBED` 用例，二进制里含 Part B 那一行 NULL 修复（本地未提交），去掉后套件会在第 47 行停止 |
| `AI_PROMPT` 回归 | `--test-set ai_prompt` | 通过 | `Total 1, Passed 1, Failed 0` |
| 模型 DDL 回归 | `--test-set ai_model_ddl` | 通过 | `Total 1, Passed 1, Failed 0` |
| 模型名大小写回归 | `--test-set ai_model_lower_case_name_mysql0`、`--test-set ai_model_lower_case_name_mysql1` | 通过 | 各 `Total 1, Passed 1, Failed 0` |
| 端点 DDL 回归 | `--test-set ai_model_endpoint_ddl` | 通过 | 加了 `max_concurrency` 的分支之后 `Total 1, Passed 1, Failed 0`。修复前失败于第 38 行 `CREATE_AI_MODEL_ENDPOINT`，报 `11115: The param 'max_concurrency' is invalid`：基线 `b6cc9ac51` 的 `ObAiModelEndpointInfo` 没有这个字段、参数白名单也没有它（`git show b6cc9ac51:src/share/ai_service/ob_ai_service_struct.cpp` 中无 `concurrency`），上游所有分支同样如此 |
| 三个分支合并 | `git merge lab1/ai-rerank`（在 `lab1/ollama` 上）、`lab1/ai-endpoint-max-concurrency`（基于 `lab1/ollama`） | 通过 | 自动合并无冲突，合并结果与本地实测工作区逐字节一致（仅 `ob_expr_ai_embed.cpp` 与 `tools/deploy/activate_obd.sh` 两处本地未提交改动不同） |

### 已知限制

- Mock AI Service 只验证请求构造、响应解析和错误处理路径，不能替代比赛隐藏测试使用的官方服务；rerank 的分数按与查询的公共词个数计算，只用于验证排序逻辑。
- 二进制里含 Part B 的 `AI_EMBED` NULL 行修复（本地未提交），因此官方套件能跑完全程；只合入本分支时套件会在第 47 行停止。
- 虚拟机上的构建与部署全部无 root 完成，依赖装在 `~/opt`：`m4`（bison 生成 parser 需要 `M4` 环境变量）、`libaio.so.1t64`（`src/oblib/CMakeLists.txt` 找的是 `libaio.so.1t64`，系统里只有 `libaio.so.1`）、`libtool`（`tools/deploy/copy.sh` 用 `libtool --mode=install cp` 拷二进制）。
- `tools/deploy/activate_obd.sh` 的 `OBD_HOME` 修复（`$DIR` 未定义，应为 `$DEPLOY_PATH`）与 obd 插件补丁（seekdb 1.4 不再提供 `oceanbase.__all_server`）都是本地部署改动，保持未提交状态。

