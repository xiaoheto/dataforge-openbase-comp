# 交付说明（2026-11-17 晚）

这份文档写给接手的人：现在交付了什么、证据在哪里、还差什么、下一步做什么。
Lab 的详细测试记录在 [lab-2-test-record.md](lab-2-test-record.md)，本文只写结论和待办。

## 1. 一句话结论

代码已经完成并推送，提测的 PR 也已经开到官方仓库（`oceanbase/seekdb#2689`）。
公开的官方用例全部跑绿。剩下的是**隐藏用例**和**三个已知功能缺口**，其中 JOIN 的缺口最可能
被隐藏用例撞到，必须先修。

## 2. 交付物在哪

| 交付物 | 位置 | 状态 |
| --- | --- | --- |
| 提测 PR | [`oceanbase/seekdb#2689`](https://github.com/oceanbase/seekdb/pull/2689) | OPEN，`dba9cd3cf`，132 文件 +11019/-612 |
| PR 头分支 | `xiaoheto/seekdb:competition/seekdb-lab1-lab2` | 已推送，`dba9cd3cf` |
| 同样内容的分支 | `xiaoheto/seekdb:2026-competition` | 已推送，`dba9cd3cf` |
| 团队内部仓库 | `xiaoheto/seekdb-2026`（**独立仓库，不是 fork**） | 18 个分支，`2026-competition` = `dba9cd3cf` |
| 父仓库 | `xiaoheto/dataforge-openbase-comp:main` | `65d986e`，submodule 指向 `dba9cd3cf` |

> **两个仓库的区别要记住**：`xiaoheto/seekdb-2026` 是团队自己建的独立仓库（GitHub 上
> `fork: false`），**GitHub 不允许从独立仓库向官方仓库开 PR**（报 `head ref must be a branch`）。
> 真正的 fork 是 `xiaoheto/seekdb`（`fork: true`，`parent` 是 `oceanbase/seekdb`），PR 必须从这里开。
> 团队的分支同时推了两边，内容一致。

## 3. 提测口径（这一条之前搞错过）

官方赛题的提测方式是**向官方仓库 `oceanbase/seekdb` 的 `2026-competition` 分支提 PR**，
评测平台按 PR 的头提交评测。证据：官方仓库里其他队伍的提测 PR 都是这个形态。

| PR | 头分支 | 队伍 | CLA |
| --- | --- | --- | --- |
| [#2689](https://github.com/oceanbase/seekdb/pull/2689) | `competition/seekdb-lab1-lab2` | **我们** | 未签 |
| [#2681](https://github.com/oceanbase/seekdb/pull/2681) | `competition/seekdb-ai-enhancement` | justinwills | 未签 |
| [#2547](https://github.com/oceanbase/seekdb/pull/2547) | `codex/file-sql-2026-competition` | sysylfqmqt | 已签 |
| [#2523](https://github.com/oceanbase/seekdb/pull/2523) | `feat/file-as-database` | au9ovo | 未签 |
| [#2516](https://github.com/oceanbase/seekdb/pull/2516) | `2026-competition` | jafive-li | 未签 |

教师邮件里“英雄榜查不到队伍成绩”的原因就在这里：**提测之前 fork 到官方是 0 个 PR**，
平台没有可评测的提交。PR 开出来之后这一条才成立。

`license/cla` 需要**本人**在 <https://cla-assistant.io/oceanbase/seekdb?pullRequest=2689>
登录 GitHub 后签一次（法律协议不能代签）。别的队伍也有没签的，看起来不是评分的硬门槛，
但签掉更稳妥。

## 4. 两个 Lab 的完成情况

### Lab 1：AI 函数增强（60 分）

六个子题全部实现：`AI_PROMPT` 的类型与模板、`AI_EMBED` 单行语义、`AI_COMPLETE` 请求与响应、
Ollama Provider、`AI_RERANK` 结果正确性、`AI_EMBED` 跨行批量；端点另外支持了 `max_concurrency`。

### Lab 2：文件即数据库（50 分）

| 评分项 | 分 | 状态 |
| --- | ---: | --- |
| ① SQL 接口与文件发现 | 7 | 通过。`read_csv`/`read_json`/`read_ndjson`/`read_parquet`/`glob`，第二个位置参数报 `1064`，`DESCRIBE` 给出官方期望的六列 |
| ② CSV 读取 | 10 | 通过 |
| ③ JSONL 读取 | 7 | 通过 |
| ④ Parquet 读取 | 6 | 通过 |
| ⑤ 确定性类型推断 | 6 | 通过，推断的列与官方样例一致 |
| ⑥ 单文件 SQL | 6 | 通过。投影、聚合、具名选项、`ORDER BY`、`LIMIT`、`GROUP BY`/`HAVING`、`WHERE`（逐行求值）、`COPY` |
| ⑦ 双文件 JOIN | 4 | **有缺口**，见第 6 节第 1 条 |
| ⑧ 安全、稳定性与工程质量 | 4 | 部分。路径校验、开关默认关闭、计划里的路径为 C 字符串都做了；隐藏测试未跑，一次崩溃的根因未定位 |

## 5. 实测证据

构建（Ubuntu 24.04，clang++-17）：

```bash
cd projects/seekdb
./build.sh release --make -j3      # 0 error，产出 build_release/src/observer/seekdb
```

部署：

```bash
export OBD_DEV_MODE=1
tools/deploy/obd.sh stop -n single
cp build_release/src/observer/seekdb /home/zining/seekdb-data/seekdb1/bin/seekdb
tools/deploy/obd.sh start -n single
```

官方用例（提测分支上跑的同一套）：

```bash
tools/deploy/obd.sh mysqltest -n single --disable-reboot \
  --test-dir ./mysql_test/test_suite/file_sql/t \
  --result-dir ./mysql_test/test_suite/file_sql/r --test-set file_sql_basic
```

| 用例 | 结果 |
| --- | --- |
| `file_sql_basic`（**官方**） | 通过，整条文件，包括第 44 行的 `DESCRIBE` 六列和第 57 行的 `COPY` 导出读回 |
| `file_sql_jsonl_parquet`（自建） | 通过 |
| `ai_function` 全套 12 个 | 通过 |
| `ai_column` 5 个 | 通过 |
| 格式模块单元测试 | 通过（含 47 项路径检查） |

> 跑 AI 用例需要两件事：`tools/mock-ai-service/mock_ai_service.py 8000` 起服务，
> 并且 **observer 不能带 `http_proxy` 环境变量**（带了请求会被发给代理，
> `ai_function_ollama` 与 `ai_function_rerank` 会失败）。这是环境问题，不是代码问题。

## 6. 已知缺口（按风险排序）

### 1. JOIN 的 ON 条件里引用左表列会失败（高风险）

现象：JOIN 的 ON 条件里，带表别名的列引用解析失败。

```sql
-- 失败：Unknown column 'p.c1' in 'on clause'
select p.c1, c.name from read_parquet('...') p left join read_csv('...') c on p.c1 = c.id;

-- 成功：CSV 在左边就没问题
select c.id, p.c1 from read_csv('...') c left join read_parquet('...') p on p.c1 = c.id;
```

已定位到的规律（用不同列数的 CSV 反复试出来的）：

| 左表列数 × 右表列数 | 结果 |
| --- | --- |
| 2 × 8、3 × 8、4 × 8、6 × 8、7 × 8、8 × 8 | 失败 |
| 5 × 任意 | 成功 |
| 任意 × 2 | 成功 |
| 相同列数 × 相同列数 | 成功 |

也就是说“左表恰好 5 列”才正常，其余大部分组合失败。根因还没定位，
怀疑与文件表列的 column id 取值有关（文件表的列 id 用的是列在文件里的下标，
两个文件表的下标会撞）。

影响：官方用例 `file_sql_basic` 里没有 JOIN，**公开用例不受影响**；
但其他队伍扩展的官方用例里有 `parquet left join csv`，隐藏用例很可能也有，⑦ 的 4 分会丢。

### 2. `COPY <表名> TO '文件'` 没实现（中高风险）

我们只支持 `COPY (select ...) TO '文件' (...)`。另外两支队伍都支持 `COPY <表名> TO`，
他们的扩展用例里就有：

```sql
create table t (id bigint, name varchar(32));
insert into t values (4, 'Delta');
copy t to '/tmp/table_export.csv' (format csv, header, nullstr 'NULL');
```

### 3. `COPY` 的选项只有 `format`/`header`/`nullstr`（中风险）

另外两支队伍还支持 `delimiter`、`quote`、`escape`。读取函数那边的选项我们是全的
（`header`、`sample_size`、`format`、`nullstr`、`delimiter`、`quote`、`escape`、`skip_blank_lines`），
导出这边缺三个。

### 4. `DESCRIBE` 只支持文件表的 `select *`（中风险）

`describe select id, name from read_csv(...)` 会报列不存在；`describe` 一个不是文件表的
语句报 `1235`。官方用例只用了 `describe select * from read_csv(...)`，已通过。

### 5. 表头行的列名带逗号时没按 CSV 加引号（低风险）

### 6. 一次崩溃的根因没定位（低风险，但影响 ⑧）

`ERROR 2013 Lost connection`，发生在集群刚新建、observer 被重建时，没有栈也没有 core，
见 [lab-2-test-record.md](lab-2-test-record.md) 的记录。

### 7. round2 的归属没有确认（最高风险，但不是代码问题）

如果评测已经切到 round 2（MiniVectorDB + JSONL stdio 协议的新任务），
上面所有工作都不算分。**这一条只能问老师。**

## 7. 待办清单与分工

分工按**代码层**和**评分项**分开：一个改动落在谁的代码里由谁写，
对应的评分项由谁验证和出证据。剩下的口子全在框架层（解析器、解析层、执行计划、算子），
这部分只有一个人能安全地改；但证据、用例和跨格式验证要分给对应评分项的负责人，
最后一天不能把活都堆在一个人身上。

| 优先级 | 事项 | 写代码 | 出用例与证据 | 验收方式 |
| --- | --- | --- | --- | --- |
| P0 | 签 CLA | — | 队长本人 | <https://cla-assistant.io/oceanbase/seekdb?pullRequest=2689> |
| P0 | 问老师 round2 归属与提测口径 | — | 队长本人 | 邮件/微信回复 |
| P0 | 修 JOIN 的 ON 条件列引用 | A（解析层的列解析） | C（⑦ 的归属人） | `parquet left join csv` 跑通，官方用例仍全绿 |
| P1 | 支持 `COPY <表名> TO` | A（语法与解析层） | C | 建表 → copy → `read_csv` 读回 |
| P1 | `COPY` 补 `delimiter`/`quote`/`escape` | A（选项解析） | C | 导出后读回的值一致 |
| P2 | `DESCRIBE` 支持 select 的结果列 | A（解析层） | B（类型推断的归属人） | `describe select id, name from read_csv(...)` 给出两列 |
| P2 | `header = false` 时的列名（`_c1` 还是 `column0`） | — | B | 与官方 DuckDB 行为对齐，或确认隐藏用例的期望 |
| P2 | 复现 2013 崩溃 | A | 谁手上有 observer 日志/core 谁做 | 有栈或有 core，或能证明与代码无关 |

### 为什么代码都在框架层，证据却要分出去

Lab 2 的分工是：A 负责 ①⑥⑧（表函数注册、执行计划接入、聚合下推、开关与路径校验），
B 负责 ②⑤（CSV 与类型推断），C 负责 ③④⑦（JSONL、Parquet、跨格式 JOIN）。
剩下的四个口子**代码**全在框架层，所以写代码只能集中在一个人身上；
但**验证**必须分给评分项的归属人：

- ⑦ 的 4 分归 C，而 JOIN 的 bug 在 A 的解析层 —— A 定位并改解析层，C 写
  `parquet left join csv` 的回归用例并核对结果，两边都要动。
- C 还应该做一件对隐藏用例最有用的事：**照另外两支队伍的做法扩展官方用例文件**
  （他们把 `GROUP BY`/`HAVING`、`read_ndjson`、`glob('*.csv')`、`describe ... header = false`、
  copy 覆盖已存在文件、`copy <表名>` 都加进了 `file_sql_basic.test`）。
  官方用例文件本身不要改，加到团队自己的 `file_sql_jsonl_parquet.test` 里，
  这样既不改官方的期望，又能提前撞出隐藏用例的形状。
- B 核对 CSV 侧的边界：无表头时的列名、重复列名改名、字段内换行、NULL。

### 改完代码之后

谁改谁推，而且**两个仓库都要推**，否则 PR 不会更新：

```bash
git push xiaoheto/seekdb competition/seekdb-lab1-lab2   # 真 fork，PR #2689 的头
git push origin 2026-competition                          # 团队内部仓库
```

推完跑一遍官方用例再推，**不要把没验证的提交推到 PR 上**：

```bash
tools/deploy/obd.sh mysqltest -n single --disable-reboot \
  --test-dir ./mysql_test/test_suite/file_sql/t \
  --result-dir ./mysql_test/test_suite/file_sql/r \
  --test-set file_sql_basic,file_sql_jsonl_parquet
```

## 8. 分支与提交地图

```text
oceanbase/seekdb
└── 2026-competition (5bce9e06d, 官方基线)
    └── PR #2689 头分支 competition/seekdb-lab1-lab2 = dba9cd3cf
        ├── da79cb218 merge(lab1): the AI function enhancements of Lab 1
        │   └── lab1/integration（六个子题 + max_concurrency）
        └── 8adec58b6 merge(lab2): the file table of Lab 2
            ├── 24285a0c1 lab2/integration（框架 + CSV + JSONL + Parquet + JOIN）
            └── 3f37702b9 merge(lab2): the copy and the describe of a file table
                ├── 105ece7d1 fix: copy 写表头（三处缺陷）
                └── bdd8c9cd5 feat: describe 给出 schema 六列
                    └── dba9cd3cf merge: nullstr 生效 + describe 的 glob
```

团队的内部分支（都在 `xiaoheto/seekdb-2026`，内容与上面一致）：
`lab1/integration`、`lab1/ai-prompt`、`lab1/ai-embed-single`、`lab1/ai-embed-batch`、
`lab1/ai-rerank`、`lab1/ollama`、`lab1/ai-endpoint-max-concurrency`、
`lab2/integration`、`lab2/csv`、`lab2/jsonl-parquet`、`lab2/file-discovery`、
`lab2/parse-error-code`、`lab2/copy`、`lab2/copy-nullstr`。

## 9. 恢复工作的最短路径

```bash
cd projects/seekdb
git fetch origin
git checkout competition/seekdb-lab1-lab2   # 与提测 PR 同一个提交
./build.sh release --make -j3

# 跑官方用例
python3 ../tools/mock-ai-service/mock_ai_service.py 8000 &   # AI 用例需要
export OBD_DEV_MODE=1
tools/deploy/obd.sh mysqltest -n single --disable-reboot \
  --test-dir ./mysql_test/test_suite/file_sql/t \
  --result-dir ./mysql_test/test_suite/file_sql/r --test-set file_sql_basic
```

改了代码之后要同时推两个地方，PR 才会更新：

```bash
git push xiaoheto/seekdb competition/seekdb-lab1-lab2   # 真 fork，PR 的头
git push origin 2026-competition                          # 团队内部仓库
```

父仓库的 submodule 指针要跟着更新（`git -C projects/seekdb checkout 2026-competition` 后
`git add projects/seekdb`）。

> 生成的 parser 文件（`src/sql/parser/sql_parser_mysql_mode_tab.c/h`）在 `.gitignore` 里，
> 改了 `sql_parser_mysql_mode.y` 之后要在构建机上重新生成，评测机也会自己生成：
>
> ```bash
> cd src/sql/parser
> export PATH=$PWD/../../../deps/3rd/usr/local/oceanbase/devtools/bin/:$PATH
> export BISON_PKGDATADIR=$PWD/../../../deps/3rd/usr/local/oceanbase/devtools/share/bison
> bison -v -Werror -d sql_parser_mysql_mode.y -o sql_parser_mysql_mode_tab.c
> ```
>
> 需要 bison 2.4.1；`gen_parser.sh` 还要 flex，本机没有 flex，所以只跑 bison，
> 词法文件沿用旧的。
