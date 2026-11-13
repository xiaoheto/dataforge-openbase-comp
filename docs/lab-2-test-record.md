# Lab 2 测试记录

> 失败、跳过和未运行必须如实记录，不得留空或写成通过。基线尚未提供 `file_sql` 的
> 任何实现，本记录只覆盖各成员自己提交的模块级验证。

## 版本与环境

| 项目 | 记录 |
| --- | --- |
| 主机 | localVM，192.168.24.128 / lilinzhen |
| 操作系统 | Ubuntu 24.04.4 x86_64 |
| CPU / 内存 | 2 核 / 3.5 GiB |
| seekdb 基线 | `2026-competition`，`5bce9e06d` |
| 本分支基线 | `lab2/csv`（B 的 `b060f2eec`） |
| Part C 提交 | `lab2/jsonl-parquet`，`2c9502421` |
| 构建命令 | `./build.sh release --make -j2`（首次加 `--init`） |
| 编译器 | clang++-17（`deps/3rd/usr/local/oceanbase/devtools`） |
| 单元测试 | `ctest --test-dir build_file_sql_tests` |

## 成员 C：JSONL 与 Parquet

### 分支与提交

| 分支 | 提交 | 内容 | 状态 |
| --- | --- | --- | --- |
| `lab2/jsonl-parquet` | `2c9502421` | ③ JSONL 读取、④ Parquet 读取 | 已推送 |
| `lab2/jsonl-parquet` | `309ec9b94` | ④ Parquet 补齐 DATA_PAGE_V1 与字典编码 | 已推送 |

设计说明：`projects/seekdb/docs/file-sql-member-c.md`。

### 依赖结论

基线没有任何 Parquet 依赖（`parquet` / `snappy` / `thrift` 在 `src/` 与 `deps/` 中
零命中，Rust 工作区也没有相关 crate）。因此 Parquet 读取自包含实现 Thrift compact
protocol、Snappy 解压、RLE/bit-packing hybrid 与 PLAIN 编码，未引入需要联网下载的
组件。

### 模块级验证结果

| 检查 | 命令 | 结果 | 备注 |
| --- | --- | --- | --- |
| 主构建 | `./build.sh release --make -j2` | 通过 | 0 error，产出 `build_release/src/observer/seekdb`，`BUILD_BRANCH: lab2/jsonl-parquet` |
| 单元测试 | `ctest --test-dir build_file_sql_tests --output-on-failure` | 通过 | 4/4：`file_sql_types`、`file_sql_csv`（B 的）、`file_sql_parquet`、`file_sql_jsonl_parquet` |
| JSONL 读官方样例 | `ctest -R file_sql_jsonl_parquet` | 通过 | 字段并集 6 列、`score` DOUBLE、`day` DATE、缺失字段为 NULL，与官方 `file_sql_basic.result` 一致 |
| Parquet 读官方样例 | 同上 | 通过 | `row_count=7 min=0 max=6 sum=21`，与官方 `file_sql_basic.result` 一致 |
| Parquet 页版本与编码 | `ctest -R file_sql_parquet` | 通过 | 20 个样本覆盖 DATA_PAGE_V1/V2、PLAIN/RLE/RLE_DICTIONARY、SNAPPY/UNCOMPRESSED、必填与可空列、多 Row Group、五种物理类型、多列与列裁剪 |
| 重扫 | 单元测试覆盖 | 通过 | `rescan` 后再次 `next_batch` 返回同样的行数 |
| 非法输入 | 单元测试覆盖 | 通过 | `sample_size != -1` 被拒绝 |

### 未运行的检查

| 检查 | 原因 |
| --- | --- |
| `file_sql_basic.test` 端到端 | 基线没有实现，A 的表函数注册与 `enable_file_sql` 尚未发布；已部署集群验证到该用例报 `Unknown system variable 'enable_file_sql'`，说明数据部署与用例加载正常 |
| `file_sql_jsonl_parquet.test` 端到端 | 同上；该用例已提交，待公共框架就绪后运行 |
| ⑦ 双文件 JOIN | 需要 A 的原生扫描接口；本提交提供三个格式统一的扫描器接口与 JOIN 用例 |
| 隐藏测试覆盖的场景 | 官方 unit test 未随分支发布，已按其名称推断补充等价 mysqltest 与 20 个 Parquet 样本 |

### 已知限制

- Parquet 支持 DATA_PAGE_V1/V2 与 PLAIN/RLE/RLE_DICTIONARY；DELTA_BINARY_PACKED
  与 BYTE_STREAM_SPLIT 未实现。
- Parquet 只支持 SNAPPY 与 UNCOMPRESSED；ZSTD 与 GZIP 未实现。
- Parquet 的 INT96 时间戳类型不支持。
- Parquet 的嵌套列只读第一层的 definition levels，每一行对应一个叶子值。
- JSONL 只支持扁平对象，嵌套对象与数组被拒绝。
- 两个扫描器都不打开路径、不执行查询：路径授权、`enable_file_sql`、
  `secure_file_priv`、符号链接校验由 A 的公共框架负责；过滤、聚合、排序与 JOIN
  由 seekdb 原生算子完成。

## 成员 A、B

尚未提交。基线分支 `lab2/file-discovery` 与 `lab2/csv` 已存在于远程，
`lab2/csv` 由 B 提供 CSV 读取与类型推断。

## 评分项对照

| 评分项 | 分 | 负责人 | 状态 |
| --- | ---: | --- | --- |
| ① SQL 接口与文件发现 | 7 | A | 未运行 |
| ② CSV 读取 | 10 | B | 未运行 |
| ③ JSONL 读取 | 7 | C | 模块级通过，端到端未运行 |
| ④ Parquet 读取 | 6 | C | 模块级通过，端到端未运行 |
| ⑤ 确定性类型推断 | 6 | B | 未运行 |
| ⑥ 单文件 SQL | 6 | A | 未运行 |
| ⑦ 双文件 JOIN | 4 | C | 阻塞于 A 的框架 |
| ⑧ 安全、稳定性与工程质量 | 4 | A | 未运行 |
| **合计** | **50** | | |

> 官方文字同时出现 50 分与"沿用 30 分"，口径待确认；此处按评分表相加的 50 分记录。
