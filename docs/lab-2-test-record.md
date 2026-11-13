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
| Part C 提交 | `lab2/jsonl-parquet`，`d960b0fa9`、`309ec9b94`、`790f728bd` |
| 构建命令 | `./build.sh release --make -j2`（首次加 `--init`） |
| 编译器 | clang++-17（`deps/3rd/usr/local/oceanbase/devtools`） |
| 单元测试 | `ctest --test-dir /tmp/build_fs_test` |

## 成员 C：JSONL 与 Parquet

### 分支与提交

| 分支 | 提交 | 内容 | 状态 |
| --- | --- | --- | --- |
| `lab2/jsonl-parquet` | `d960b0fa9` | ③ JSONL 读取、④ Parquet 读取 | 已推送 |
| `lab2/jsonl-parquet` | `309ec9b94` | ④ Parquet 补齐 DATA_PAGE_V1 与字典编码 | 已推送 |
| `lab2/jsonl-parquet` | `790f728bd` | 修复损坏的 Parquet 样本，并加入样本完整性检查 | 已推送 |
| `lab2/jsonl-parquet` | `10e288402` | 设计文档补上样本完整性检查的说明 | 已推送 |
| `lab2/jsonl-parquet` | `411f2bc56` | 拒绝不存在的 projection 列，修复初始化失败后的段错误，补齐契约用例 | 已推送 |

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
| 单元测试 | `ctest --test-dir /tmp/build_fs_test --output-on-failure` | 通过 | 4/4：`file_sql_types`、`file_sql_csv`（B 的）、`file_sql_parquet`、`file_sql_jsonl_parquet` |
| JSONL 读官方样例 | `ctest -R file_sql_jsonl_parquet` | 通过 | 字段并集 6 列、`score` DOUBLE、`day` DATE、缺失字段为 NULL，与官方 `file_sql_basic.result` 一致 |
| Parquet 读官方样例 | 同上 | 通过 | `row_count=7 min=0 max=6 sum=21`，与官方 `file_sql_basic.result` 一致 |
| Parquet 页版本与编码 | `ctest -R file_sql_parquet` | 通过 | 20 个样本覆盖 DATA_PAGE_V1/V2、PLAIN/RLE/RLE_DICTIONARY、SNAPPY/UNCOMPRESSED、必填与可空列、多 Row Group、五种物理类型、多列与列裁剪 |
| 样本完整性 | `python3 .../file_sql/data/parquet/check_fixtures.py .../parquet` | 通过 | 20 个样本全部通过页覆盖检查 |
| 重扫 | 单元测试覆盖 | 通过 | `rescan` 后再次 `next_batch` 返回同样的行数 |
| 非法输入 | 单元测试覆盖 | 通过 | `sample_size != -1` 被拒绝 |
| JSONL 类型冲突 | 单元测试覆盖 | 通过 | 同一列里整数与浮点混合时统一为 DOUBLE，两个值都是 DOUBLE |
| JSONL 缺失字段 | 单元测试覆盖 | 通过 | 缺失字段补 NULL，另一行同位置有值 |
| JSONL 嵌套拒绝 | 单元测试覆盖 | 通过 | 嵌套对象与数组都被拒绝 |
| Parquet 列裁剪 | 单元测试覆盖 | 通过 | projection 里的列照常读取，未列出的列在行里是 NULL，schema 仍是文件的全部列 |
| 非法 projection | 单元测试覆盖 | 通过 | projection 里有文件没有的列时 `init` 报错，不再产出全 NULL 的行 |
| 初始化失败后调用 | 单元测试覆盖 | 通过 | `init` 失败后再 `next_batch` 返回错误且不产出行，不再段错误 |
| 新用例的有效性 | 临时破坏校验逻辑后重跑 | 通过 | 两个测试文件各报 3 条 FAIL，确认用例不是空跑 |

### Parquet 样本损坏的排查记录

`large_dict.parquet` 曾在第 2573 行读出 `234881034`。排查结论是**样本本身损坏，
读取器没有错**：

1. 读取器交给 Snappy 的压缩页字节与文件中的字节逐字节相同；
2. Snappy 解压的结果与独立的参考实现逐字节相同，长度同为 15911 字节；
3. `pyarrow` 读同一个文件得到**同样的错误值**，说明文件里的值流已经不对。

进一步比对发现，仓库中的样本是正确样本**丢掉第 11727 字节（`0x0d`）**后的产物
（21818 字节，正确样本为 21819 字节），该字节正是数值 2573 的最低字节。文件在复制
过程中丢了一个字节，magic 与 footer 都正常，因此读取器和 pyarrow 都无法察觉。

处理方式：

- 用正确样本替换 `large_dict.parquet`；
- 新增 `check_fixtures.py`，它不依赖任何第三方包，读取文件 footer 中的 Row Group
  元数据，遍历页头并验证页能无缝覆盖文件。丢字节的文件会报
  `the page at 5467 claims 15916 bytes and reaches past the footer`。
  该检查已能区分修复前后两份样本。

### 契约复核发现的两处缺陷

对着计划的测试矩阵逐条复核 ③ 和 ④ 时发现两个问题，都在 `411f2bc56` 修复：

1. **projection 里出现文件没有的列时，静默产出全 NULL 的行。**
   旧实现里 `projection` 只用来决定"哪些列值得读"，没有任何校验。列名写错时
   一列都匹配不上，于是不读任何列，行里全是 NULL——这是错误结果而不是诊断，
   计划明确禁止异常输入导致错误结果。现在 `init` 直接报错。

2. **`init` 失败后再调用 `next_batch` 会段错误。**
   读取器在 schema 建好之前就把"可用"标记置上了，schema 构建失败时读取器停在
   一个半成品状态，`next_batch` 接着读一个不存在的 Row Group，崩溃。这条路径
   原本被"projection 一定成功"的旧假设掩盖着，修好第 1 条之后立刻暴露。
   计划要求异常数据不得导致崩溃，现在标记只在完全可用时置上，且 `next_batch`
   会拒绝没有列的读取器。

同时把计划里列出但单测没覆盖的契约补进仓库的测试：JSONL 的整数与浮点混合成
DOUBLE、缺失字段补 NULL、拒绝嵌套对象与数组，以及 Parquet 的非法 projection 与
初始化失败后调用。新用例的有效性做过验证：临时去掉校验逻辑后，两个测试文件各报
3 条 FAIL，确认用例不是空跑。

### 未运行的检查

| 检查 | 原因 |
| --- | --- |
| `file_sql_basic.test` 端到端 | 基线没有实现，A 的表函数注册与 `enable_file_sql` 尚未发布；已部署集群验证到该用例报 `Unknown system variable 'enable_file_sql'`，说明数据部署与用例加载正常 |
| `file_sql_jsonl_parquet.test` 端到端 | 同上；该用例已提交，待公共框架就绪后运行 |
| ⑦ 双文件 JOIN | 需要 A 的原生扫描接口；本提交提供三个格式统一的扫描器接口与 JOIN 用例。远程 `lab2/file-discovery` 尚未发布 |
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
