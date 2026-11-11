# Lab 2 两周执行计划

## 目标与交付

实现 Lab 2「文件即数据库」，让 `read_csv`、`read_json`/`read_ndjson`、`read_parquet`、`glob`
直接读取本地文件，由 seekdb SQL 引擎完成过滤、聚合、排序和 JOIN，不预先建表也不导入数据。

最终交付包括：

- seekdb `lab2/integration` 分支上的实现与测试；
- 八个评分项的 PR 和交叉评审记录；
- `docs/lab-2-test-record.md`，记录环境、提交、命令、结果和已知限制。

## 契约

基线已发布 `tools/deploy/mysql_test/test_suite/file_sql/` 下的测试数据、mysqltest 与期望输出，
但没有任何实现。以下契约由 `file_sql_basic.test` 与 `file_sql_basic.result` 反推得到，是三个人的
共同依据。

### 开关与语法

| 项 | 契约 |
| --- | --- |
| 开关 | `@@session.enable_file_sql` 默认 `0`；关闭时调用表函数报 `1235` |
| 开启 | `set session enable_file_sql = ON`；结束时恢复 `OFF` |
| 表函数 | `read_csv(path)`、`read_json(path, format = 'newline_delimited')`、`read_parquet(path)`、`glob(pattern)` |
| 格式参数 | `read_csv(path, 'xml')` 报 `1064` |
| `sample_size` | 只支持 `-1`，`sample_size = 10` 报 `1235` |
| `DESCRIBE` | `describe select * from read_csv(...)` 返回 `column_name`、`column_type`、`null`、`key`、`default`、`extra` 六列 |
| `glob` | 只返回一列 `file`，值为文件完整路径 |

### 数据语义

| 项 | 契约 |
| --- | --- |
| 列名去重 | 重复表头 `id` 自动改名为 `id__2` |
| CSV 类型推断 | `id` BIGINT、`name` VARCHAR、`score` DOUBLE、`active` BOOLEAN、`day` DATE、`created` DATETIME、`note` VARCHAR、`id__2` BIGINT |
| 可空性 | `day`、`created` 可空，其余非空；空字段即 `NULL` |
| `DATETIME` 格式 | `2026-08-01 10:11:12` 与 `2026-08-03T12:13:14` 两种分隔符都要能解析 |
| 引号 | 字段内换行 `"hello,\nworld"`、转义引号 `"say ""hi"""` |
| 布尔 | `true` / `false` |
| 数值输出 | `DOUBLE` 不带尾随 `.0`，`87` 而非 `87.0`；`round(avg(score), 2) = 91.92` |
| JSONL | 取字段并集，缺失字段补 `NULL`；`score` 整数与浮点混合时统一为 DOUBLE |
| Parquet | 列 `c1`，7 行，`min = 0`、`max = 6`、`sum = 21` |
| `COPY` | `copy (select ...) to path (format csv, header, nullstr 'NULL')`，导出后可被 `read_csv` 读回 |

### 测试数据

| 文件 | 内容 |
| --- | --- |
| `data/basic.csv` | 3 行 8 列，含字段内换行、转义引号、ISO `T` 分隔时间戳、空字段 |
| `data/basic.jsonl` | 3 行扁平对象，字段各不相同且互相有缺失 |
| `data/invalid.txt` | 扩展名不受支持，用于错误路径 |
| `data/simple.parquet.b64` | base64 编码的 `PAR1` 文件，由 `copy_file_sql_data.inc` 在远端解码 |

## 团队分工

| 成员 | 主责 | 分值目标 |
| --- | --- | ---: |
| A | ① SQL 接口与文件发现、⑥ 单文件 SQL、⑧ 安全、稳定性与工程质量 | 17 |
| B | ② CSV 读取、⑤ 确定性类型推断 | 16 |
| C | ③ JSONL 读取、④ Parquet 读取、⑦ 双文件 JOIN | 17 |

分工依据：

- A 负责表函数注册、扫描与执行计划接入、聚合下推，以及开关、路径校验和资源限制。
  这三项工作都会被另外两人复用，需要统一出口，否则路径检查散落三处，安全项将直接判 0。
- B 负责 CSV 解析器与类型推断落地。`DESCRIBE` 的期望类型就是 CSV 的推断结果，两者必须同一套
  推断引擎，因此归同一人。
- C 负责两个互不依赖的格式实现，以及建立在 A 框架与 B 的 CSV 之上的跨格式 JOIN。

⑦ 双文件 JOIN 放在 C，是因为它依赖 CSV 与 JSONL/Parquet 都已就绪，安排在第二周；
若第一周 B 的 CSV 提前完成，可提前启动。

## 接口与实现边界

- 语法遵循 DuckDB 风格：`read_csv`、`read_json`、`read_ndjson`、`read_parquet`、`glob`、
  `DESCRIBE SELECT * FROM read_*()`、`COPY (query) TO path`。
- 文件扫描必须流式执行，不得把整个文件物化到内存；全文件物化导致 OOM 的用例判定失败。
- CSV 与 JSONL 使用全量 Schema 推断，`sample_size` 仅支持 `-1`。
- `glob()` 仅用于发现文件，返回一列 `file`。
- 功能默认关闭，开启 `enable_file_sql` 后仍须通过 `secure_file_priv` 校验。
- 不得使用 DuckDB、SQLite、Polars SQL 等外部查询引擎代执行；整题记 0 分。
- 路径越界或绕过 `secure_file_priv` 视为严重缺陷，安全项记 0 分。
- 不得破坏现有普通 SQL 与既有功能；异常数据、路径越界和文件变化不得导致崩溃、错误结果或资源泄漏。

## 日程

| 时间 | 工作 | 完成门槛 |
| --- | --- | --- |
| 第 1 天 | 三人共同敲定表函数签名、文件扫描接口和类型推断接口；A 先落①的表函数注册与 `enable_file_sql` 开关 | 接口头文件合入 `lab2/integration`，其余两人能基于它开工 |
| 第 2–3 天 | B 实现 CSV 解析（引号、转义、字段内换行、重复表头）；C 实现 JSONL 解析与字段并集；A 实现 `secure_file_priv` 校验与路径规范化 | 三人各自分支能对 `file_sql_basic.test` 的前几组用例给出结果 |
| 第 4–5 天 | B 落地类型推断与 `DESCRIBE`；C 实现 Parquet 读取；A 实现扫描结果的表达式下推 | ①②③⑤ 的公开用例通过 |
| 第 6–7 天 | C 实现批量扫描与 Parquet 列裁剪；A 完成聚合、`GROUP BY`、`HAVING`、`ORDER BY`、`LIMIT`；B 补 `COPY ... TO path` | `file_sql_basic.test` 前 6 组用例通过 |
| 第 8–9 天 | C 实现双文件 JOIN 与跨格式 JOIN；A 收尾资源上限、错误诊断与文件变化检测 | `file_sql_basic.test` 全套通过 |
| 第 10 天 | 三人合入 `lab2/integration`，跑通完整 `file_sql` 套件与既有 AI 套件回归 | 无新增回归，无崩溃或错误结果 |
| 第 11–12 天 | 补等价 mysqltest 与边界用例：坏行诊断、类型冲突、嵌套 JSONL 拒绝、路径越界、文件变化、资源上限 | 补充用例全部通过并提交 PR |
| 第 13 天 | 集成机从干净 checkout 复现构建、部署和测试 | 形成完整测试记录 |
| 第 14 天 | 缺陷修复和交付冻结 | 最终提交与记录一致 |

## 测试矩阵

- ① 表函数与发现：`glob` 返回单列、别名与命名参数、`DESCRIBE`、格式参数校验、`sample_size` 校验、扩展名不支持。
- ② CSV：表头有无、UTF-8、LF 与 CRLF、引号与转义、字段内换行、`NULL`、坏行诊断、批量扫描、重复表头。
- ③ JSONL：字段并集、缺失字段补 `NULL`、类型冲突、拒绝嵌套对象与数组。
- ④ Parquet：Footer Schema、多 Row Group、可空列、基础类型、列裁剪。
- ⑤ 类型推断：七类目标类型、类型宽化、数值边界、日期合法性、全 `NULL` 列。
- ⑥ 单文件 SQL：表达式、别名、`WHERE`、`ORDER BY`、`LIMIT`、`GROUP BY`、`HAVING` 与五种聚合。
- ⑦ JOIN：`INNER JOIN`、`LEFT JOIN`、跨格式 JOIN，计划走 seekdb 原生执行。
- ⑧ 安全与稳定性：默认关闭、`secure_file_priv`、防路径逃逸、文件变化、资源限制、错误诊断。
- 回归：普通 SQL、既有 AI 函数、完整 `file_sql` 与 `ai_function` 套件。

## 分支与 PR

| 分支 | 负责人 | 内容 |
| --- | --- | --- |
| `lab2/file-discovery` | A | ①⑥⑧ |
| `lab2/csv` | B | ②⑤ |
| `lab2/jsonl-parquet` | C | ③④⑦ |
| `lab2/integration` | — | 只接受经过评审的 PR |

每个 PR 只对应一个评分项，附构建命令、目标测试和实际结果，并由至少一名非作者评审。
依赖分支每天 rebase 到 `lab2/integration`。共同改动（表函数注册、路径校验、类型推断接口）
先由 A 提公共 PR 合入，各人再基于它开发，避免重复实现。

## 资源约定

- 沿用 Lab 1 的约定：8 GiB 内存使用 `-j2`，16 GiB 使用 `-j4`，32 GiB 以上最多 `-j8`。
- Parquet 读取需要额外的列式解析依赖，引入前先评估是否已随基线提供，避免引入需要联网下载的组件。
- 三人使用各自 Linux/WSL；构建环境问题参照 `docs/seekdb-install-and-deploy.md`。
- WSL2 用户注意 NAT 与 DNS 稳定性问题，必要时按 `docs/repository-workflow.md` 的说明处理。

## 风险

| 风险 | 影响 | 应对 |
| --- | --- | --- |
| 总分 50 与 30 的口径未定 | 影响排期优先级 | 待确认前按 50 分排期，优先保证①⑤⑥这 19 分 |
| 官方 C++ unit test 未发布 | 隐藏测试可能覆盖看不到的场景 | 补充等价 mysqltest，并按 unit test 名称推断的场景补边界用例 |
| Parquet 实现工作量大 | ④ 只有 6 分 | 先做 Footer Schema 与单 Row Group 的最小可用版本，保住 ④ 的基础分；列裁剪可后置 |
| `enable_file_sql` 变量作用域 | 隐藏测试可能用全局变量 | 会话级与全局级都要支持，且默认值一致 |
| 三人同时改表函数注册与路径校验 | 合并冲突与安全漏洞 | 公共部分只由 A 提 PR 合入，各人 rebase 后再开发 |
