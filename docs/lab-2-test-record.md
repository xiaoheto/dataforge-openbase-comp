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
| 单元测试 | `ctest --test-dir /tmp/build_fs_test`，6 个用例全部通过（types、path、csv、parquet、jsonl_parquet、adapters） |

## 成员 C：JSONL 与 Parquet

### 分支与提交

| 分支 | 提交 | 内容 | 状态 |
| --- | --- | --- | --- |
| `lab2/jsonl-parquet` | `d960b0fa9` | ③ JSONL 读取、④ Parquet 读取 | 已推送 |
| `lab2/jsonl-parquet` | `309ec9b94` | ④ Parquet 补齐 DATA_PAGE_V1 与字典编码 | 已推送 |
| `lab2/jsonl-parquet` | `790f728bd` | 修复损坏的 Parquet 样本，并加入样本完整性检查 | 已推送 |
| `lab2/jsonl-parquet` | `10e288402` | 设计文档补上样本完整性检查的说明 | 已推送 |
| `lab2/jsonl-parquet` | `411f2bc56` | 拒绝不存在的 projection 列，修复初始化失败后的段错误，补齐契约用例 | 已推送 |
| `lab2/jsonl-parquet` | `3eeb92ebb` | 单页大小单独设限，Row Group 中途失败时停止，补齐资源上限用例 | 已推送 |

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
| 资源上限 | 单元测试覆盖 | 通过 | `max_row_groups`、`max_rows`、`max_columns`、`max_line_bytes` 超出时返回 `RESOURCE_LIMIT` |
| 小批次 | 单元测试覆盖 | 通过 | 批次上限 64 字节时 `large_dict.parquet` 仍完整读出 5000 行且顺序正确 |
| 单页上限 | 单元测试覆盖 | 通过 | 解压后单页的大小由 `max_page_bytes` 单独限制，不再借用批次上限 |
| Row Group 中途失败 | 单元测试覆盖 | 通过 | 页面解不开时停止，不再带着只读了一半的 Row Group 继续，不再越界崩溃 |
| 文件变化 | 单元测试覆盖 | 通过 | 扫描期间文件被改动时返回 `FILE_CHANGED` |
| 新用例的有效性 | 临时破坏校验逻辑后重跑 | 通过 | 两个测试文件各报 3 条 FAIL，确认用例不是空跑 |
| 崩溃用例的有效性 | 去掉"停止在失败处"的修复后重跑 | 通过 | `file_sql_parquet` 段错误，确认用例能覆盖该缺陷 |

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

### 资源上限复核发现的两处缺陷

逐条核对计划里"资源上限"与"不得崩溃"的要求时发现两个问题，都在 `3eeb92ebb` 修复：

1. **批次上限被当成了单页大小的上限。**
   读取器把 `max_batch_bytes` 同时当作"一次返回多少行"和"解压后一页最多多大"。
   但文件的一页可以比一批行大，于是只要批次上限被调小，任何 snappy 文件就完全
   读不出来（报 `cannot decompress the parquet page values`）。现在单页大小由
   自己的 `max_page_bytes` 限制。

2. **读到一个 Row Group 的中间失败时，读取器继续用那个只读了一半的 Row Group。**
   行的数量已经设好了，下一次 `next_batch` 不会重读这个组，于是去读一个根本没
   填过的列块，越界崩溃。现在失败就停：下一次调用同样报错，`rescan` 之后从头再来。

复现方式：把 `unsupported_encoding.parquet`（数据页声明了读取器不支持的编码）
放进样本目录，读到那一页时失败；去掉修复后单测直接段错误。

JSONL 一侧复核后没有同类问题：它一次只读一条记录，没有"半个 Row Group"的状态，
`next_record` 在失败后直接返回记录下来的错误，`rescan` 会清掉。

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

成员 A 的 `lab2/file-discovery` 已存在于远程，成员 B 的 `lab2/csv` 提供 CSV 读取与
类型推断。两个分支都从 `2026-competition` 出发，集成记录见下一节。

## 集成：框架与格式模块的接合

成员 A 的 `lab2/file-discovery` 与成员 C 的 `lab2/jsonl-parquet` 都从
`2026-competition`（`5bce9e06d`）出发，两个分支各自新增的同名文件会冲突。
集成在 `lab2/integration` 分支上完成，未推送。

### 提交

| 提交 | 内容 |
| --- | --- |
| `429371fcb` | 合并 A 的框架到 C 的格式模块，解掉 4 处冲突 |
| `bc9b69063` | 适配层：把 C 的 JSONL 与 Parquet 接进 A 的框架接口 |

设计说明：`projects/seekdb/docs/file-sql-integration.md`。

集成之后的修改都在 `lab2/jsonl-parquet` 分支上，通过 PR 合入 `lab2/integration`，
集成分支只接受经过评审的 PR。PR 的地址：

<https://github.com/xiaoheto/seekdb-2026/compare/lab2/integration...lab2/jsonl-parquet>

### 解掉的 4 处冲突

| 文件 | 处理 |
| --- | --- |
| `file_sql_types.h` | `ScalarRow` 别名属于共享的类型模块，保留在此 |
| `file_sql_csv.h` | 删除 CSV 模块里的别名副本 |
| `sql_source_inventory.bzl` | 取两边源文件的并集 |
| `unittest/sql/engine/basic/CMakeLists.txt` | 取两边测试目标的并集 |

### 接口接合中发现的四处问题

**一、框架的选项缺少模块需要的字段。** 框架的 `FileScanOptions` 里没有资源上限，
也没有 projection，模块各自的选项无法被框架表达。框架选项增加了 `FileScanLimits
limits` 与 `projection`，取值与模块原本自己使用的默认值相同，行为不变。

**二、文件结束的表示方式不一致（会导致查询挂死）。** 三个模块报告"读完"的方式不同：

| 模块 | `next_batch` 在文件末尾的返回 |
| --- | --- |
| CSV | `FileCode::END` |
| JSONL | OK，行数为 0 |
| Parquet | OK，行数为 0 |

框架的执行算子只把 `END` 当作扫描结束，而 `inner_get_next_row` 在批次用完后会继续
取下一批。若 JSONL 或 Parquet 在文件末尾返回 OK 加空批次，算子会永远取空批次，
查询挂死。适配层把空批次统一翻译成 `END`。

**三、`rescan` 的返回值被丢弃。** 框架接口把 `rescan` 声明成 `void`，A 的 CSV
适配器直接丢弃了模块返回的状态。`rescan` 会失败（例如文件被替换导致 seek 失败），
丢弃状态会让失败变成静默的错误结果。接口改为返回 `FileStatus`，三个适配器都透传。

**四、适配层的注册。** JSONL 与 Parquet 的扫描器在加载时通过
`register_file_scanner` 注册自己，注册幂等，解析器与执行算子不需要改动。

### 模块级验证结果

| 检查 | 命令 | 结果 | 备注 |
| --- | --- | --- | --- |
| 适配器与全部格式模块的编译 | 用 `build_release` 的真实编译参数逐个编译 `file_sql_*` 与算子 | 通过 | `file_sql_reader`、`file_sql_adapters`、`file_sql_scan`、`file_sql_path`、`file_sql_types`、`file_sql_csv`、`file_sql_jsonl`、`file_sql_parquet`、`ob_file_table_op`、`ob_dml_resolver` 全部 OK |
| 类型推断 | `test_file_sql_types` | 通过 | 610 checks |
| 路径校验 | `test_file_sql_path` | 通过 | 47 checks |
| CSV 读取 | `test_file_sql_csv` | 通过 | 3224 checks |
| Parquet 读取 | `test_file_sql_parquet` | 通过 | 20 个样本全部通过 |
| JSONL 与 Parquet | `test_file_sql_jsonl_parquet` | 通过 | 官方样例的形状与 `file_sql_basic.result` 一致 |
| **框架与模块的接合** | `test_file_sql_adapters` | 通过 | 新增用例，见下 |

### 新增用例 `test_file_sql_adapters`

该用例通过框架的接口驱动 JSONL 与 Parquet 两个模块，覆盖：

- `create_file_scanner` 能拿到 JSONL 与 Parquet 的扫描器；
- 字段并集与官方样例一致（6 列、3 条记录）；
- Parquet 的形状与官方样例一致（1 列 `c1`、7 行、`min=0`、`max=6`、`sum=21`）；
- `rescan` 之后能重新读到全部数据，且 `rescan` 的状态被报告；
- 框架的资源上限能传到模块（超限时返回 `RESOURCE_LIMIT`）；
- 不存在的 projection 被拒绝，而不是产出全 NULL 的行；
- 文件末尾报告 `END`，而不是返回空批次。

用例的有效性做过验证：把适配层里"空批次转 `END`"的转换去掉后，用例报 8 条 FAIL，
确认这条用例覆盖的正是会挂死查询的那条路径。

### 未运行的检查

| 检查 | 原因 |
| --- | --- |
| `file_sql_basic.test` 端到端 | 用例的最后一段是 `COPY`，框架还没有实现 `COPY`，用例在那一段停下 |
| ⑦ 双文件 JOIN | 需要框架的原生扫描接口，本次接合提供了接口，接合后的 JOIN 待实现 |
| 隐藏测试覆盖的场景 | 官方 unit test 未随分支发布，已按其名称推断补充等价用例 |

### 已知限制

- 资源上限目前是框架里的常量，还没有做成会话变量。
- 框架的路径校验只在解析阶段做一次，执行阶段重新打开文件之前没有再校验一次，
  两次之间文件被换成指向别处的软链接不会被发现。
- 表函数的语句不可比较，计划缓存不会复用文件表语句的计划，每次执行都会重新推断
  Schema。
- 一个查询会把文件读三遍：解析阶段推断一次，算子执行时为了发现文件变化再推断一次，
  读数据时再读一遍。

## 端到端验证：部署集群并用 SQL 读取文件

`lab2/integration` 的代码在 localVM 上部署成集群之后，用 SQL 直接验证了
`read_csv`、`read_json`、`read_parquet`、具名选项和跨格式 JOIN。验证的过程中发现了
9 处框架与 SQL 层接合的缺陷，都已修复并提交。

### 部署

| 项目 | 记录 |
| --- | --- |
| 部署方式 | `tools/deploy/obd.sh prepare -b ./build_release -p /tmp/obtest`，再 `deploy -c ./tools/deploy/single.yaml` |
| 集群 | `single`，`127.0.0.1:10000`，租户 `oceanbase` |
| 构建 | `./build.sh release --make -j2` |

> 构建时必须设置 `M4=$HOME/opt/sysroot/usr/bin/m4`。bison 2.4.1 需要 `m4`，而这台
> 机器的 `/usr/bin/m4` 不存在，解析器生成会静默失败（退出码 141），
> `sql_parser_mysql_mode_tab.c` 不会更新，语法改动进不了二进制。

### 验证的结果

| 检查 | 结果 | 备注 |
| --- | --- | --- |
| `read_csv` 读 `basic.csv` | 通过 | 8 列 3 行，类型推断与官方样例一致，重复表头改名 `id__2`，多行引号正确 |
| `read_csv` 的聚合 | 通过 | `count=3`、`sum(id)=6`、`avg(score)=91.92`、`sum(active)=2` |
| `read_json`（`format = 'newline_delimited'`） | 通过 | 字段并集 6 列，缺失的字段是 NULL |
| `read_ndjson` 别名 | 通过 | 与 `read_json` 一致 |
| `read_parquet` | 通过 | `count=7`、`min(c1)=0`、`max(c1)=6`、`sum(c1)=21`，形状取自 footer |
| CSV + JSONL 内连接 | 通过 | 3 行 |
| CSV + JSONL 左连接 | 通过 | 每一行都保留 |
| CSV + Parquet 内连接 | 通过 | 3 行 |
| 具名选项 `header = true`、`sample_size = -1` | 通过 | 布尔值和整数都可以 |
| `glob()` | 通过 | 一列 `file`，值是文件的完整路径，模式匹配到的目录不算文件 |
| 官方 mysqltest `file_sql_jsonl_parquet.test` | 通过 | 结果记录在 `r/mysql/file_sql_jsonl_parquet.result` |

### 修复的缺陷

| 提交 | 缺陷 | 原因 |
| --- | --- | --- |
| `34b03b5da` | 表函数的参数多于一个时无法解析 | 参数列表用 `malloc_non_terminal_node` 建的，节点没有容量，`push_back_list` 越界；改用 `malloc_list_node` |
| `1a4892cd3` | 具名选项无法解析 | 词法分析器把 `=` 返回成 `COMP_EQ`，语法里用的是字符记号 `=`；选项名还要允许关键字（`format`） |
| `fix(plan-cache)` | 表函数语句在计划缓存下报语法错误 | 计划缓存把路径参数化，解析器在解析阶段读不到路径；参数的常量不再参数化 |
| `fix(file-table)` | 列数组越界，列也错位 | 规格用 `prepare_allocate` 填满了数组，之后又往里 push；改成按列下标放置，计划不用的列留空 |
| `fix(file-table)` | 计划里的路径是野指针 | 路径指向语句的内存，语句销毁之后算子读到的是垃圾；字符串拷进计划的内存 |
| `fix(rewrite)` | `min/max` 变换把列搬走 | 该变换会把表项的列项从语句里删掉，文件表的列不能删；对文件表跳过该变换 |
| `fix(resolver)` | 查不到文件表的列 | 解析器的两处表类型分支不认识文件表；`header` 选项不接受布尔值 |
| `fix(build)` | JSONL 与 Parquet 报告格式不支持 | `file_sql_adapters.cpp` 不在源文件清单里，链接器丢掉了适配层，扫描器从未注册 |
| `fix(parser)` | 计划缓存复用别的文件的计划 | 文件表的路径是计划的一部分，路径变了计划必须重做；路径不再参数化，语句不进计划缓存 |
| `feat(file-sql)` | `glob()` 报格式不支持 | 框架已有模式展开与 `secure_file_priv` 校验，缺的是接线：格式名、解析器的列、算子的展开 |

### 仍未解决

| 问题 | 现象 | 状态 |
| --- | --- | --- |
| `COPY` 没有实现 | `copy (select ...) to '...'` 报 1064 | 官方用例 `file_sql_basic.test` 的最后一段是 `COPY`，用例在那一段停下，录不出完整的结果 |
| 文件表上的 WHERE 条件恒为假 | `select ... from read_csv(...) where id > 1` 返回空集 | 条件被当成常量表达式，成了启动过滤，第一行不满足就结束扫描；已经定位到常量的标记，未修 |
| `DESCRIBE` 给的是执行计划 | `describe select * from read_csv(...)` 输出的是执行计划，不是列清单 | 这个版本里 `describe select * from (select 1 as a) t` 给的也是执行计划，所以不是文件表独有的问题；官方样例期望列清单 |
| `file_sql_basic.test` 录不了结果 | 用例的最后一段是 `COPY`，框架还没有实现 `COPY` | 依赖 `COPY` |

## 评分项对照

| 评分项 | 分 | 负责人 | 状态 |
| --- | ---: | --- | --- |
| ① SQL 接口与文件发现 | 7 | A | 通过：`read_csv`、`read_json`、`read_parquet`、`glob` 端到端通过 |
| ② CSV 读取 | 10 | B | 通过 |
| ③ JSONL 读取 | 7 | C | 通过 |
| ④ Parquet 读取 | 6 | C | 通过 |
| ⑤ 确定性类型推断 | 6 | B | 通过：推断的列与官方样例一致 |
| ⑥ 单文件 SQL | 6 | A | 部分通过：扫描、投影、聚合、具名选项通过，文件表上的 WHERE 条件未修，`COPY` 未实现 |
| ⑦ 双文件 JOIN | 4 | C | 通过：CSV + JSONL、CSV + Parquet |
| ⑧ 安全、稳定性与工程质量 | 4 | A | 部分通过：路径校验有效，单元测试通过，隐藏测试未运行 |
| **合计** | **50** | | |

> 官方文字同时出现 50 分与"沿用 30 分"，口径待确认；此处按评分表相加的 50 分记录。
