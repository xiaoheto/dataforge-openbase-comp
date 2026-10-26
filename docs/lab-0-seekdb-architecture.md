# Lab 0：seekdb 架构导读

本文面向第一次接触完整数据库系统的同学。Lab 0 不要求实现新功能，而是帮助大家建立关于 seekdb 以及数据库系统的基础概念：知道 seekdb 如何启动，一条 SQL 如何被理解、规划和执行，以及遇到需求或错误时应从哪里开始查代码。

## 1. 学习目标

完成 Lab 0 后，应当能够：

- 解释 seekdb 主要源码模块的职责；
- 说明 SQL 从文本到结果所经历的 Parser、Resolver、Rewrite、Optimizer、CodeGen 和 Executor 阶段；
- 区分 Parse Tree、Resolved Statement、Logical Plan、Physical Plan 等中间表示；
- 从源码完成编译、部署、连接、执行 SQL 和清理实例；
- 使用 `EXPLAIN` 判断过滤、排序、投影和访问路径落在哪些算子中；
- 使用 `rg` 从需求、符号和测试反向定位可能需要修改的文件。

## 2. seekdb 是怎样的数据库

seekdb 的主体仍然是关系型数据库内核：用户通过 SQL 表达查询意图，数据库负责类型系统、NULL 语义、查询优化、事务和持久化。在此基础上，seekdb 增加了 AI Function，并支持 JSON、文本和向量等数据参与 SQL 查询。

这些扩展不是绕开 SQL 引擎的旁路服务。例如，一个 AI 函数同样需要：

- 在 Resolver/Expression 阶段检查参数和返回类型；
- 在 CodeGen 阶段生成运行时表达式；
- 在 Executor 中按行或按批求值；
- 遵守 SQL 的 `NULL`、错误和字符集语义；
- 通过自动化测试保证结果稳定。

### 2.1 单进程内核，而不是一组微服务

`src/observer/CMakeLists.txt` 使用 `add_executable(seekdb)` 定义主程序，并把 SQL、存储、日志及共享基础设施链接到同一个可执行文件。因此，下图中的方框主要表示进程内的职责边界，并不表示每个模块都是独立服务。

```text
MySQL 客户端
    │  MySQL Protocol / COM_QUERY
    ▼
observer：进程装配、网络、会话与协议入口
    │
    ├── sql：Parser → Resolver → Rewrite → Optimizer → Codegen → Executor/DAS
    │                                                      │
    ├── rootserver：Schema、DDL、索引构建、Fork 等本地控制面    │
    │                                                      ▼
    ├── pl：PL 与系统包                              storage：事务、LS、Tablet、
    │                                                Memtable、SSTable、Compaction
    └──────────────────────────────┬───────────────────────┘
                                   ▼
                         logservice：PALF、Apply、Replay

                 share / oblib：所有上层共同依赖的基础设施
```

Lab 1 和 Lab 2 的第一落点主要在 SQL 层，所以本文重点讲 SQL 的语义、计划和执行。网络协议、事务、LS/Tablet、MVCC、日志和 Compaction 会标出边界，但不展开其内部算法。

## 3. 仓库与源码地图

先按职责认识目录，再进入具体类和函数。第一次阅读时，不要从 src/ 第一行开始顺序通读。

### 3.1 仓库顶层

| 路径 | 作用 | 什么时候查看 |
| --- | --- | --- |
| `README.md` / `README_CN.md` | 项目定位和快速开始 | 第一次接触仓库 |
| `build.sh` | Unix 平台的统一构建入口 | 编译或增量构建 |
| `cmake/` | 构建选项、依赖和平台适配 | 构建失败或新增目标 |
| `deps/` | 仓库管理的第三方依赖和客户端 | 初始化依赖、寻找 obclient |
| `src/` | 数据库主体源码 | 功能开发和调试 |
| `unittest/` | C++ 单元测试目录；本分支中只有占位文件（见 11.1） | 一般不需要查看 |
| `tools/deploy/` | 本地部署、配置和 mysqltest 封装 | 启动实例、SQL 回归测试 |
| `docs/developer-guide/` | 官方开发说明 | 构建、测试和贡献流程 |

### 3.2 src/ 中的核心模块

| 模块 | 主要职责 | 常用入口 |
| --- | --- | --- |
| `src/observer/` | `main`、`ObServer` 装配、网络、MySQL 协议、会话和进程生命周期 | `main.cpp`、`ob_server.cpp`、`mysql/obmp_query.cpp` |
| `src/sql/` | SQL 解析、语义解析、改写、优化、代码生成、执行和 DAS | `ob_sql.cpp` 及各阶段子目录 |
| `src/query/` | 从 SQL/Observer 中抽出的查询公共 API 和少量运行时实现 | `api/query/engine/`、`protocol/`、`scheduler/` |
| `src/storage/` | 事务访问、LS、Tablet、MemTable、SSTable、LOB、合并等 | `tx_storage/`、`ls/`、`tablet/`、`memtable/` |
| `src/data_plane/` | 从 SQL/Storage 中抽出的数据访问公共 API 和少量实现 | `api/data_plane/` 下的 `access/`、`transaction/`、`lob/` |
| `src/logservice/` | PALF 日志、Apply 和 Replay | `palf/`、`applyservice/`、`replayservice/` |
| `src/rootserver/` | Schema/DDL 等本地控制逻辑 | `ddl_task/` 等 |
| `src/share/` | Schema、配置、SCN、公共结构和跨模块接口 | `schema/`、`datum/` 等 |
| `src/pl/` | PL 解析、执行及系统包 | `parser/`、`sys_package/` |
| `src/oblib/` | 更底层的容器、内存、序列化、网络等基础库 | 按具体基础类型定位 |

### 3.3 SQL 子目录速查

```text
src/sql/
├── parser/          SQL 文本 → Parse Tree
├── resolver/        Parse Tree → 带语义的 Statement / RawExpr
├── rewrite/         保持语义的等价改写
├── optimizer/       访问路径、连接顺序、逻辑算子和成本估算
├── code_generator/  Logical Plan → Physical Plan / Expr
├── executor/        物理计划的启动和调度
├── engine/          物理算子与表达式实现
├── das/             SQL 执行层到数据访问层的桥梁
├── plan_cache/      执行计划缓存
└── ob_sql.cpp       串联 SQL 编译主流程的重要入口
```

## 4. 一条 SQL 如何穿过内核

以 MySQL 协议中的普通文本查询为例，主线可以压缩为：

```text
MySQL packet / COM_QUERY
  → observer/ob_srv_xlator.cpp：创建 ObMPQuery
  → observer/mysql/obmp_query.cpp：会话、事务和单语句处理
  → sql/ob_sql.cpp：ObSql::stmt_query / handle_text_query
      → Parser
      → Resolver
      → Rewrite
      → Optimizer
      → CodeGen
  → sql/ob_result_set.cpp：打开结果集和物理计划
  → sql/executor/ob_executor.cpp：创建并启动根算子
  → sql/engine + sql/das
  → storage
  → ResultSet / MySQL response
```

协议和会话层解决“哪个连接提交了什么请求”；SQL 编译层解决“这条语句是什么意思、怎样执行”；执行与数据访问层解决“怎样产生结果”。定位问题时先区分这三个问题，不要把它们混在一起。

### 4.1 各阶段的输入、输出与职责

| 阶段 | 主要输入 | 主要输出 | 负责的问题 | 关键路径 |
| --- | --- | --- | --- | --- |
| Parser | SQL 字符串 | `ParseResult` / `ParseNode` | 语法结构是否合法 | `src/sql/parser/` |
| Resolver | Parse Tree + Schema + Session | `ObStmt` / `ObDMLStmt` + `ObRawExpr` | 名称绑定、类型、语义合法性 | `src/sql/resolver/` |
| Rewrite | Resolved Statement | 等价的新 Statement / Expr | 化简和等价变换 | `src/sql/rewrite/` |
| Optimizer | Statement + Schema + Statistics | `ObLogPlan` / `ObLogicalOperator` 树 | 访问路径、算子顺序和成本 | `src/sql/optimizer/` |
| CodeGen | Logical Plan + RawExpr | `ObPhysicalPlan`、`ObOpSpec`、`ObExpr` | 生成可实例化的运行时描述 | `src/sql/code_generator/` |
| Executor | Physical Plan + 参数/会话 | `ObOperator` 树与 Row/Batch | 打开算子、拉取数据、返回结果 | `src/sql/executor/`、`src/sql/engine/` |

这些名称不是要求背诵的词汇表，而是调试时的重要边界：如果前一种表示正确、后一种表示第一次出错，首要排查点就是负责这次转换的阶段。

## 5. SQL 编译阶段详解

### 5.1 Parser：从字符序列得到语法树

Parser 识别关键字、标识符、常量、运算符和子句之间的父子关系。例如：

```sql
SELECT price * quantity AS amount
FROM orders
WHERE status = 'paid';
```

会形成包含 SELECT 列表、表、乘法表达式和比较谓词的树。此时 Parser 可以发现括号不匹配或关键字位置错误，但通常还不知道：

- `orders` 是否真实存在；
- `price` 和 `quantity` 分别是什么类型；
- 当前用户是否有权限访问这些列。

关键位置：

- `src/sql/parser/ob_parser.cpp`、`ob_parser.h`：Parser 封装；
- `src/sql/parser/sql_parser_mysql_mode.y`：MySQL 模式语法规则；
- `src/sql/parser/parse_node.h`：语法节点；
- `src/sql/ob_sql.cpp`：创建 `ObParser` 并调用 `parse()` 的主流程。

一个很有用的对照是：SELEC 1 在 Parser 就会失败，而 SELECT missing_column FROM existing_table 语法正确，通常要到 Resolver 才会失败。

### 5.2 Resolver：让名字、类型和表达式拥有含义

Resolver 结合 Schema 和 Session 上下文完成：

- 将表名和列名绑定到具体对象 ID；
- 解析 `*`、别名和可能歧义的列引用；
- 推导表达式参数与返回类型；
- 插入必要的隐式类型转换；
- 检查聚合、窗口、分组等 SQL 语义约束；
- 生成 `ObStmt`/`ObDMLStmt` 和 `ObRawExpr`。

例如，amount > '100' 是否允许、字符串应转换为何种数值类型、比较结果使用什么 Collation，都不是纯语法问题。

关键位置：

- `src/sql/resolver/ob_resolver.cpp`：Resolver 总入口；
- `src/sql/resolver/dml/`、`ddl/`、`cmd/`：不同语句类别；
- `src/sql/resolver/expr/`：表达式解析、类型推导和 `ObRawExpr`；
- `src/share/schema/`：解析时依赖的 Schema 信息；
- `ObSql::generate_stmt()`：在 SQL 主流程中装配 Resolver 上下文。

Lab 1 中许多“支持新参数类型”“明确 NULL 语义”类任务会跨越 Resolver 和 Expression：前者决定类型元数据，后者决定运行时值。

### 5.3 Rewrite：做保持语义的等价变换

Rewrite 接收已经具有语义的 Statement，并把它改写为更适合优化的等价形式。例如：

```sql
WHERE enabled = 1 AND 1 = 1
```

可以化简为：

```sql
WHERE enabled = 1
```

实际改写还可能涉及常量传播、谓词移动、子查询变换、投影裁剪、Join 消除等。它可以改变表达式或语句的形状，但必须保持结果、NULL、重复行、顺序约束和错误边界等语义。

关键位置：

- `src/sql/rewrite/ob_transformer_impl.cpp`：组织 Rewrite 流程；
- `src/sql/rewrite/ob_transform_*.cpp`：具体规则；
- `ObSql::transform_stmt()`：SQL 主流程中的调用边界。

若“原始语句语义正确，但改写后结果发生变化”，应先固定一个最小 SQL，对照改写规则的前置条件，而不是直接修改 Executor。

### 5.4 Optimizer：选择一棵逻辑计划

同一条 SQL 往往有多种等价执行方式。例如两表 Join 可以交换顺序；过滤可以在 Join 前执行；查询可以选择全表扫描或索引扫描。Optimizer 会结合 Schema、统计信息和成本模型比较候选计划，并生成逻辑算子树。

Optimizer 主要考虑：

- 表和索引访问路径；
- Join 顺序与 Join 算法；
- 谓词、排序、聚合和 `LIMIT` 的位置；
- 估算行数、CPU、IO、网络与内存成本；
- 算子的分区与并行属性。

关键位置：

- `src/sql/optimizer/ob_optimizer.cpp`：优化入口；
- `src/sql/optimizer/ob_log_plan.cpp`：逻辑计划；
- `src/sql/optimizer/ob_logical_operator.h`：逻辑算子基类；
- `src/sql/optimizer/ob_log_*.cpp`：各类逻辑算子；
- `ObSql::optimize_stmt()`：SQL 主流程中的调用边界。

EXPLAIN 是观察 Optimizer 结果的第一工具。它比根据 SQL 文本猜测执行方式更可靠。

### 5.5 CodeGen：把逻辑计划变为可运行描述

CodeGen 不是把 SQL 编译为机器码。这里的“代码生成”主要是把逻辑算子和 ObRawExpr 转换为执行阶段使用的：

- `ObPhysicalPlan`；
- 物理算子规格 `ObOpSpec`；
- 运行时表达式 `ObExpr`；
- 列位置、求值函数和执行所需元数据。

关键位置：

- `src/sql/code_generator/ob_code_generator.cpp`；
- `src/sql/code_generator/ob_static_engine_cg.cpp`；
- `src/sql/code_generator/ob_static_engine_expr_cg.cpp`；
- `ObSql::code_generate()`。

当 EXPLAIN 中的逻辑关系正确，但执行时算子字段、表达式或输出列接错时，CodeGen 是重要边界。

## 6. 执行阶段与 Expression 子系统

### 6.1 Executor 如何启动算子树

ObResultSet::open() 最终进入物理计划打开流程；ObExecutor::execute_plan() 根据计划类型创建根 ObOperator。运行时算子通常通过以下接口工作：

```text
open()
  → get_next_row()      单行路径
  → get_next_batch()    批量路径
close()
```

上层算子从子算子拉取数据。例如 Sort 会从 Scan 获取行，完成排序后再把结果交给上层。真正的数据访问继续通过 DAS 进入存储层；本文不展开 Tablet、MemTable 和 SSTable 的内部读路径。

关键位置：

- `src/sql/ob_result_set.cpp`：打开结果集和计划；
- `src/sql/executor/ob_executor.cpp`：创建并启动根算子；
- `src/sql/engine/ob_operator.cpp`：算子生命周期和 Row/Batch 接口；
- `src/sql/engine/table/`、`sort/`、`join/`、`aggregate/`：具体算子；
- `src/sql/das/`：SQL 算子到数据访问层的桥梁。

### 6.2 Expression 为什么是后续 Lab 的重点

SELECT 列表、WHERE 谓词、函数参数、Join 条件和排序键最终都包含表达式。Expression 横跨编译与执行两个阶段：

```text
SQL function call
  → Resolver 创建并推导 ObRawExpr 类型
  → CodeGen 生成 ObExpr，挂接求值函数
  → Executor 中 eval() / eval_batch()
  → ObDatum 或一批 Datum
```

实现或修改一个函数时，至少检查以下四类问题：

- **类型推导：**允许哪些 SQL 类型，返回什么类型和长度，字符集或 Collation 是什么；
- **运行时求值：**如何读取参数、处理错误并构造结果；
- **NULL 与特殊类型：**`NULL` 是否短路，LOB/JSON 是否需要专用读取接口；
- **Row/Batch 一致性：**批量求值时 skip、已求值标记和行下标是否正确。

常用路径：

- `src/sql/engine/expr/ob_expr.h`、`ob_expr.cpp`：表达式运行时框架；
- `src/sql/engine/expr/ob_expr_*.cpp`：普通 SQL 函数和运算符；
- `src/sql/engine/expr/ob_expr_ai/`：AI Function；
- `src/sql/code_generator/ob_static_engine_expr_cg.cpp`：`ObRawExpr` 到 `ObExpr` 的生成。

一个函数“能被 Parser 识别”不代表它已经正确实现。Parser 只看到调用形状；参数类型、NULL、LOB、JSON 和批量结果对应关系通常在后续阶段决定。

## 7. 如何阅读 EXPLAIN

假设一条查询包含过滤、降序和 LIMIT：

```sql
EXPLAIN
SELECT id, title
FROM articles
WHERE score >= 80
ORDER BY score DESC
LIMIT 5;
```

在没有可用 score 索引时，计划只有两层：

```text
=====================================================
|ID|OPERATOR         |NAME    |EST.ROWS|EST.TIME(us)|
-----------------------------------------------------
|0 |TOP-N SORT       |        |1       |3           |
|1 |└─TABLE FULL SCAN|articles|1       |3           |
=====================================================
Outputs & filters:
-------------------------------------
  0 - output([articles.id], [articles.title]), filter(nil), rowset=16
      sort_keys([articles.score, DESC]), topn(5)
  1 - output([articles.id], [articles.score], [articles.title]), filter([articles.score >= 80]), rowset=16
      access([articles.id], [articles.score], [articles.title]), partitions(p0)
      is_index_back=false, is_global_index=false, filter_before_indexback[false],
      range_key([articles.id]), range(MIN ; MAX)always true
```

（表结构为 articles(id BIGINT PRIMARY KEY, title VARCHAR(64), score INT)；估算行数和代价随数据变化。）

这并不表示 WHERE、SELECT 或 LIMIT 被忽略。SQL 子句与计划算子不是一一对应的：

- `score >= 80` 可以下推到 Scan，因此没有独立 Filter；
- `ORDER BY ... LIMIT 5` 可以合成 Top-N Sort；
- 简单投影可以记录在根算子的 `output` 中，不必建立独立 Project；
- 没有可用索引且范围为全部主键空间时，显示 Full Scan。

### 7.1 先自下而上读算子树

叶子节点决定数据从哪里来，上层节点依次加工数据。因此优先检查：

- Scan 使用了哪张表、哪个索引和哪些分区；
- Filter 在哪个算子执行；
- Join、Aggregate、Sort 等算子的顺序；
- 根节点最终输出哪些表达式。

### 7.2 Outputs & filters 常见字段

| 字段 | 含义 |
| --- | --- |
| `output(...)` | 当前算子向上层交付的表达式；中间算子可能输出最终 `SELECT` 列以外的排序键或 Join 键 |
| `filter(...)` | 在当前算子执行的谓词；`nil` 表示本层没有额外过滤 |
| `access(...)` | Scan 实际需要从数据访问层读取的列 |
| `sort_keys(...)` | 排序键、方向及 `NULL` 顺序等信息 |
| `topn(...)` | Sort 只需保留前 N 个候选 |
| `partitions(...)` | 本计划访问的分区 |
| `range(...)` | 索引或主键扫描范围；`MIN ; MAX` 且 `always true` 通常表示完整范围 |
| `rowset=N` | 向量化执行记录的批处理行数，不是估算输出行数 |

## 8. 从源码构建并运行 seekdb

本节给出最短流程，帮助你把环境跑起来。依赖安装、每一步的预期输出和常见问题，见《seekdb 从源码构建与部署》。第一次搭建环境时请以那篇文档为准。

### 8.1 初始化代码与首次编译

团队仓库已通过 submodule 固定 seekdb 的 `2026-competition` 基线。先在协调仓库根目录初始化，再进入源码目录：

```bash
git submodule update --init projects/seekdb
cd projects/seekdb

./build.sh release --init --make -j8
./build_release/src/observer/seekdb -V
```

- `release` 当前使用带调试信息的优化构建（RelWithDebInfo）；
- `--init` 准备平台依赖（编译器、OBD、obclient 等，安装在 `deps/3rd`），第一次构建或依赖定义变化后使用；
- `--make` 在配置后继续编译；
- 主二进制位于 `build_release/src/observer/seekdb`，`-V` 输出中的 `BUILD_BRANCH` 应为当前分支。

后续只修改源码时进行增量构建：

```bash
./build.sh release --make -j8
```

`-j8` 只是示例。并行度应根据机器的 CPU、内存和负载调整；8 GiB 内存从 `-j2` 开始，并行度过高可能因内存不足失败。

### 8.2 用 OBD 部署本地实例

部署前必须先修复 OBD，命令见部署文档第 5 节：

- 修正 `tools/deploy/activate_obd.sh` 中的一行，否则 OBD 工作目录被算成 `/tools/deploy`，`prepare` 报权限错误；
- 给 `--init` 安装的 OBD 插件打补丁。插件仍在查询 seekdb 1.4 中已经不存在的系统表，还会传入 seekdb 不再接受的启动参数；不修复时部署会停在 `Wait for seekdb init` 或启动失败。每次重新执行 `--init` 后都要再打一次插件补丁。

修复后执行：

```bash
./tools/deploy/obd.sh prepare -b ./build_release -p /tmp/obtest
./tools/deploy/obd.sh deploy -c ./tools/deploy/single.yaml
```

- `prepare` 把刚编译的二进制复制到 `tools/deploy/bin/`，并在首次执行时生成部署配置 `tools/deploy/single.yaml`；
- `deploy` 读取 `single.yaml`，初始化并启动单机实例，部署名为 `single`；
- `/tmp/obtest` 适合临时实验，不适合保存重要数据。

SQL 端口不是文档示例中常见的 10000，而是按用户 UID 计算的 100 * (UID % 500) + 10000，每个人可能不同。先读取实际配置：

```bash
rg -n 'mysql_port:' tools/deploy/single.yaml
```

下文用 <端口> 表示这里看到的值。

### 8.3 打开 obclient 并执行 SQL

先在一个终端启动客户端：

```bash
./deps/3rd/u01/obclient/bin/obclient -h127.0.0.1 -P<端口> -uroot -Doceanbase -A
```

接下来就可以在 obclient 终端中输入 SQL，例如：

```sql
SELECT VERSION();

CREATE DATABASE IF NOT EXISTS lab0;
USE lab0;

CREATE TABLE kv (
  id BIGINT PRIMARY KEY,
  value VARCHAR(64)
);

INSERT INTO kv VALUES (1, 'hello'), (2, 'seekdb');
SELECT * FROM kv ORDER BY id;
EXPLAIN SELECT * FROM kv WHERE id = 2;
```

这组命令分别验证了连接、DDL、写入、查询和 EXPLAIN。最后一条按主键等值查询，计划中的算子是 TABLE GET，range[2 ; 2] 表示只读取主键为 2 的一行。

退出客户端用 \q。如果要清理本次教程创建的临时实例：

```bash
./tools/deploy/obd.sh destroy --rm -n single
```

destroy --rm 会删除该部署的数据。不要把它用于需要保留的实例。

### 8.4 修改代码后让实例运行新版本

obd.sh reinstall 和 obd.sh restart 都不会可靠地换上新编译的二进制。增量编译后按以下步骤替换（实例数据会保留）：

```bash
./tools/deploy/obd.sh stop -n single
cp build_release/src/observer/seekdb tools/deploy/bin/seekdb
cp build_release/src/observer/seekdb /tmp/obtest/seekdb1/bin/seekdb
./tools/deploy/obd.sh start -n single
```

第二个 cp 的目标是 single.yaml 中的 home_path 加上 /bin/seekdb。原因和其他情况的处理见部署文档第 8 节。

## 9. 使用 rg 定位代码

rg 是 ripgrep 的命令名。它会从指定目录递归搜索文本，默认显示命中的文件和内容，并遵守 .gitignore。大型仓库中，它比手动浏览目录更适合从类名、函数名、错误信息或 SQL 函数名建立调用链。Ubuntu 上用 sudo apt-get install ripgrep 安装。

基本格式是：

```text
rg [OPTIONS] PATTERN [PATH ...]
```

这里的方括号表示“可选项”，不是命令中需要输入的字符。例如：

```bash
rg -n 'ObSql::stmt_query' src/sql
```

表示在 src/sql 中搜索 ObSql::stmt_query，并显示行号。

### 9.1 常用选项

| 选项 | 作用 |
| --- | --- |
| `-n` | 显示行号 |
| `-F` | 把搜索模式当作普通字符串，而不是正则表达式 |
| `-C 3` | 同时显示命中位置前后 3 行 |
| `-l` | 只列出命中的文件名 |
| `-g '*.cpp'` | 只搜索匹配 glob 的文件 |
| `-i` | 忽略大小写 |
| `--files` | 列出会被 `rg` 搜索的文件，不搜索内容 |

### 9.2 从文件到调用链

```bash
# 1. 按文件名寻找可能的实现
rg --files src/sql | rg 'ob_expr_.*prompt'

# 2. 搜索核心类或符号；正则中的 | 表示“或”
rg -n 'ObExprAIPrompt|N_AI_PROMPT' src/sql

# 3. 看定义附近的上下文
rg -n -C 3 'calc_result_typeN' src/sql/engine/expr

# 4. 限定为 C++ 实现文件
rg -n -g '*.cpp' 'eval_ai_prompt' src/sql

# 5. 查找相邻自动化测试
rg -n -i 'ai_prompt\(' tools/deploy/mysql_test
```

推荐顺序是：

```text
需求中的名词
  → 可能的文件名
  → 核心符号定义
  → 调用者和被调用者
  → 最近的测试
  → 必要时再扩展到相邻模块
```

每次搜索都应缩小或验证一个假设。一次搜索整个仓库得到几千条结果，但不阅读上下文，通常没有帮助。

### 9.3 搜不到时怎么办

- 搜索用户可见的错误文本或 SQL 函数名；
- 去掉 `Ob`、下划线或大小写限制，尝试关键词；
- 使用 `rg --files` 搜文件名；
- 搜索注册表、Factory 或宏中的名称；
- 使用 `git log -S 'symbol' -- path` 查找引入或删除该符号的提交。

## 10. 从现象反推负责模块

| 现象或需求 | 第一检查位置 | 先收集的证据 |
| --- | --- | --- |
| 新语法不能识别 | Parser | 最小 SQL、语法规则、Parse Tree 是否产生 |
| 表名、列名或别名解析错误 | Resolver | Schema、绑定对象、语句类型 |
| 函数参数或返回类型错误 | Resolver / Expression | 类型推导、隐式转换、`NULL`/LOB/JSON |
| 等价改写改变结果 | Rewrite | 改写前后 Statement/Expr 和触发条件 |
| 访问路径或 Join 顺序异常 | Optimizer | `EXPLAIN`、统计信息、估算行数 |
| `EXPLAIN` 正确但执行结果错误 | CodeGen / Executor / Expr | Physical Spec、输出列、运行时 Datum |
| Row 正常、Batch 错位 | Executor / Expression | skip、evaluated 标记、行下标和批大小 |
| SQL 算子正确但读写数据异常 | DAS / Storage | Scan 参数、Tablet/事务上下文、存储日志 |
| 客户端无法连接或会话状态异常 | Observer / Protocol / Session | 端口、进程、协议日志和 Session |

最重要的问题始终是：哪一种表示最后还是正确的，哪一种表示第一次变错？

## 11. 测试体系与验证层次

不同测试回答不同问题，不能互相完全替代。

| 验证方式 | 适合回答的问题 | 典型位置或命令 |
| --- | --- | --- |
| 增量编译 | 代码能否通过当前构建 | `./build.sh release --make -j8` |
| SQL 冒烟 | 功能能否从客户端端到端工作 | 在 obclient 中执行最小 SQL |
| `EXPLAIN` | 优化器选择了什么计划 | 在 obclient 中执行 `EXPLAIN ...` |
| C++ unit test | 类、函数或模块边界是否正确 | 本分支未提供（见 11.1） |
| mysqltest | SQL 输出、错误和回归行为是否稳定 | `tools/deploy/mysql_test/` |

### 11.1 C++ 单元测试

上游 seekdb 用 Google Test 编写 C++ 单元测试，但课程使用的 2026-competition 分支没有包含单元测试：unittest/ 目录中只有占位文件，构建时也不会生成 *_tests 目标。官方文档 docs/developer-guide/*/unittest.md 描述的 make -C build_release sql_tests 等命令在本分支上无法使用。

因此，本课程的 Lab 以 SQL 冒烟测试和 mysqltest 作为主要验证手段。

### 11.2 mysqltest

mysqltest 通常由一份 .test 输入和一份 .result 预期输出组成。测试套件位于：

```text
tools/deploy/mysql_test/test_suite/<suite>/t/
tools/deploy/mysql_test/test_suite/<suite>/r/
```

在已经通过 OBD 部署名为 single 的实例后，在 tools/deploy 目录下运行相关 suite：

```bash
cd tools/deploy
./obd.sh mysqltest -n single --disable-reboot --suite expr
cd -
```

一定要加 --disable-reboot。 不加时，obd.sh mysqltest 会先销毁并重新部署实例，实例中已有的数据全部丢失，重新初始化有时还会卡住约 10 分钟。

也可以用 --test-dir、--result-dir 和 --test-set 只运行单个 case，命令示例见部署文档第 9 节。完整参数见官方文档 mysqltest.md。

对后续 Lab，优先运行“能够证明本次修改”的最小测试，再扩大到相邻 suite。仅仅编译成功不能证明 SQL 语义正确；仅仅手工执行一次也不能覆盖边界和回归。

## 12. 推荐的 Lab 开发流程

### 第 0 步：确认基线

- 记录当前分支和提交：`git status`、`git rev-parse --short HEAD`；
- 在未修改代码时完成构建和目标 SQL；
- 确认连接的是当前源码生成的二进制（见 8.4）。

### 第 1 步：把题目改写成可验证行为

列出正常、边界、NULL、非法输入和回归行为。对每一条写出最小 SQL，不要只保留自然语言描述。

### 第 2 步：复现并观察

保存实际结果、错误码、EXPLAIN 和必要日志。先确认问题真实存在，再猜测代码原因。

### 第 3 步：定位第一次失真的表示

依次判断：

```text
Parse Tree
  → Resolved Statement / RawExpr
  → Rewritten Statement
  → Logical Plan
  → Physical Spec / Expr
  → Row / Batch result
```

根据边界选择目录，再用 rg 建立最短调用链。

### 第 4 步：先读相邻实现和测试

同目录中的相似表达式、算子或 Reader 通常展示了项目约定的内存、错误码、NULL 和序列化方式。复制设计模式前要理解差异，不能针对测试值硬编码。

### 第 5 步：做最小、完整的修改

“最小”指不扩散到无关模块；“完整”指编译期类型、运行时行为、Row/Batch、错误处理和测试应一起考虑。

### 第 6 步：分层验证

推荐顺序：

```text
增量编译
  → 最小 SQL
  → 目标 mysqltest case
  → 相邻 suite
  → 更大范围回归
```

### 第 7 步：记录证据

记录执行过的命令、测试结果、未覆盖范围和已知限制。别人应能根据记录复现你的判断。

## 13. 常见问题与排查顺序

### 13.1 编译失败

- 检查首次构建是否使用 `--init`；
- 检查磁盘和内存：`df -h . /tmp`、`free -h`；
- 降低 `-j` 并发度；
- 从第一条真正的编译错误开始看，不要只看末尾汇总；
- 依赖元数据没有变化时，不要反复清空整个构建目录。

### 13.2 部署或连接失败

- 部署一直停在 `Wait for seekdb init` 或 seekdb 启动失败：OBD 插件补丁没有打上，或重新 `--init` 后被覆盖（见 8.2）；
- `prepare` 报 `mkdir: cannot create directory '/tools'`：没有修正 `activate_obd.sh`（见 8.2）；
- 读取 `tools/deploy/single.yaml` 中的实际 `mysql_port`；
- 检查是否已有同名 OBD 部署或端口占用；
- 检查配置中的 `home_path` 是否残留旧实例数据；
- 查看该实例 `log/seekdb.log` 的第一处错误；
- 核对 obclient 的主机、端口、用户和数据库名。

不要为解决端口冲突直接终止不明进程；先确认进程属于哪个实例。

### 13.3 修改后行为没有变化

- 确认修改已保存且增量构建成功；
- 确认按 8.4 替换了实例中的二进制（`reinstall`、`restart` 不会替换）；
- 用 `md5sum` 比较 `build_release/src/observer/seekdb` 与实例中的二进制；`seekdb -V` 的 `REVISION` 只反映最近一次 commit，看不出未提交的修改；
- 运行 mysqltest 时是否忘了 `--disable-reboot`（实例会被重新部署，用的是 `tools/deploy/bin/seekdb`）；
- 确认客户端连接到本次实例而不是旧端口；
- 注意计划缓存、旧数据和未重启进程可能保留旧状态。

### 13.4 结果错误但没有崩溃

先缩小 SQL：去掉投影、过滤、排序、LIMIT 或嵌套函数中的一个部分，找到最早偏离预期的组合。随后按“表示转换”定位，不要一开始就在所有算子中打印日志。

## 14. Lab 0 建议实践与完成检查

建议亲自完成以下操作，而不是只阅读文档：

- 用一条语法错误 SQL 和一条列名错误 SQL 区分 Parser 与 Resolver；
- 对一条含 `WHERE`、`ORDER BY` 和 `LIMIT` 的查询执行 `EXPLAIN`；
- 能解释计划中的 `output`、`filter`、`access`、`range` 和 `rowset`；
- 完成 Release 编译、OBD 部署和 obclient 连接；
- 使用 `rg` 从一个 SQL 函数名找到实现、注册位置和最近测试；
- 找到一个 Expression 的类型推导、`cg_expr` 和运行时求值函数；
- 记录实际端口、源码提交、构建命令和验证结果。

如果你能够不依赖课件完成以上清单，Lab 0 的目标就已经达成。
