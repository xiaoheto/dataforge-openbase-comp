# seekdb 从源码构建与部署

本文带你从零开始：获取课程代码、编译 seekdb、用 OBD 部署一个本地单机实例，并说明改完代码后如何让实例运行新版本、如何运行 mysqltest。后续所有 Lab 都在这个环境里开发和测试。

> **比赛基线：**`oceanbase/seekdb` 的 `2026-competition` 分支，当前固定提交为 `5bce9e06d`；该提交包含基线 `76f871eb5` 以及官方 2026 比赛测试。部署流程曾在 Ubuntu 24.04.2 LTS x86_64、seekdb 1.4.0.0、OBD 4.1.0 上验证。

文中命令默认在源码根目录执行，除非特别说明。

> 本文部署的是开发测试用的单机实例，不是生产部署方案。

## 0. 流程速览

熟悉流程后，搭建环境只需要下面几步。每一步的细节和注意事项见后文对应章节。

```bash
# 1. 初始化团队仓库中的 seekdb submodule（第 3 节）
git submodule update --init projects/seekdb
cd projects/seekdb

# 2. 首次编译（第 4 节）
./build.sh release --init --make -j8

# 3. 修复 OBD：修改 activate_obd.sh 一行，并给 OBD 插件打补丁（第 5 节）
#    插件补丁在每次执行 --init 之后都要重新打

# 4. 部署单机实例（第 6 节）
./tools/deploy/obd.sh prepare -b ./build_release -p /tmp/obtest
./tools/deploy/obd.sh deploy -c ./tools/deploy/single.yaml

# 5. 连接（第 7 节），端口以 tools/deploy/single.yaml 中的 mysql_port 为准
./deps/3rd/u01/obclient/bin/obclient -h127.0.0.1 -P<端口> -uroot -Dtest -A
```

日常开发的循环是"修改代码 → 增量编译 → 更新实例 → 测试"，见第 8、9 节。

## 1. 环境要求

| 项目 | 要求 |
| --- | --- |
| 操作系统 | Linux x86_64，推荐 Ubuntu 22.04 或 24.04（本文在 24.04 上实测） |
| CPU / 内存 | 编译并行度 `-jN` 与内存相关，建议每个编译任务留 2 GB 内存；16 GB 内存可先用 `-j8` |
| 磁盘 | 源码目录编译后约 16 GB（`build_release` 约 7 GB，`deps/3rd` 约 7.4 GB），实例数据目录约 2 GB；建议预留 30 GB 以上 |
| 网络 | 首次编译需要下载依赖包、Rust 工具链和 Cargo 依赖 |

开始前检查一下：

```bash
nproc
free -h
df -h . /tmp
```

## 2. 安装系统依赖

### 2.1 Ubuntu 软件包

```bash
sudo apt-get update
sudo apt-get install -y \
  git wget curl rpm rpm2cpio cpio make build-essential \
  binutils m4 file python3 libaio1t64 iproute2 lsof
```

Ubuntu 24.04 的 libaio 包名是 libaio1t64；Ubuntu 22.04 上请改为 libaio1。

编译器（GCC、LLVM）、CMake 等工具不需要自己安装，build.sh --init 会把仓库指定的版本下载到 deps/3rd。

### 2.2 Rust

seekdb 有一部分代码是 Rust。安装 rustup：

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source "$HOME/.cargo/env"
```

具体的 Rust 版本由仓库中的 rust/rust-toolchain.toml 固定（当前为 1.98.1），第一次编译时 rustup 会自动下载，不需要手动安装。网络较慢时，可以参考 seekdb 开发者文档中的安装工具链配置 rustup 和 crates.io 镜像。

## 3. 获取代码

团队仓库通过 submodule 固定 seekdb 比赛基线。在协调仓库根目录执行：

```bash
git submodule update --init projects/seekdb
cd projects/seekdb
git log -1 --oneline
```

单独研究官方仓库时，也可以直接克隆比赛分支：

```bash
git clone -b 2026-competition https://github.com/oceanbase/seekdb.git seekdb
```

建议在功能分支上做实验，`2026-competition` 保持干净，方便对照基线：

```bash
git switch -c my-lab
```

## 4. 编译

### 4.1 首次编译

```bash
./build.sh release --init --make -j8
```

- `release`：带调试信息的优化构建（RelWithDebInfo），产物在 `build_release/`。
- `--init`：下载并准备 `deps/3rd` 下的依赖（编译器、CMake、OBD、obclient 等）。只在第一次编译或依赖定义变化后需要。
- `--make`：配置完成后继续编译。
- `-j8`：并行编译任务数，按机器的核数和内存调整。内存不足时编译会被系统杀掉，表现为奇怪的编译错误，这时降低并行度重试。

参考耗时：实测机器上 -j16 约 12 分钟（机器上已有编译缓存）。第一次在新机器上编译通常会慢得多，请预留充足时间。

### 4.2 检查编译结果

```bash
./build_release/src/observer/seekdb -V
```

应看到类似输出，其中 BUILD_BRANCH 是你当前所在的分支：

```text
seekdb (OceanBase seekdb 1.4.0.0)

REVISION: 2-5bce9e06d1281347ad61344e4b01fab9158c58a2
BUILD_BRANCH: 2026-competition
BUILD_FLAGS: RelWithDebInfo
```

### 4.3 增量编译

之后修改代码只需要增量编译，不要再加 --init：

```bash
./build.sh release --make -j8
```

新增 `.cpp` 或 `.h` 文件时，还要把它登记到所在模块的 `*_source_inventory.bzl` / `*_header_inventory.bzl`（例如 `src/sql/sql_source_inventory.bzl`），否则不会被编译。

## 5. 修复 OBD（必做）

### 5.1 为什么要修

OBD 是 OceanBase 的部署工具，--init 会把它安装到 deps/3rd。当前 2026-competition 分支和这个版本的 OBD 配合时有三个问题，不修复就无法部署：

- **OBD 工作目录算错。**`tools/deploy/activate_obd.sh` 使用了一个未定义变量，把 OBD 工作目录算成 `/tools/deploy`，`prepare` 报 `mkdir: cannot create directory '/tools': Permission denied`。
- **OBD 插件查询已删除的系统表。**插件仍然查询 `oceanbase.__all_server`，而 seekdb 1.4 已经没有这张表：`deploy`/`start` 会一直停在 `Wait for seekdb init`，mysqltest 报 `Failed to get root server`。
- **OBD 传入已废弃的启动参数。**OBD 启动 seekdb 时会带上 `system_memory`、`__min_full_resource_pool_memory`、`local_ip` 三个参数，seekdb 1.4 不认识它们，直接启动失败。

第 1 个问题改源码中的一行脚本即可（5.2）；后两个问题在 OBD 插件里修（5.3）。

### 5.2 修正 activate_obd.sh

在源码根目录执行：

```bash
sed -i 's|^export OBD_HOME=${_OBD_HOME:-$DIR/tools/deploy}$|export OBD_HOME=${_OBD_HOME:-$DEPLOY_PATH}|' tools/deploy/activate_obd.sh
grep -n '^export OBD_HOME' tools/deploy/activate_obd.sh
```

应输出：

```text
90:export OBD_HOME=${_OBD_HOME:-$DEPLOY_PATH}
```

这个文件受 Git 管理，修改后 git status 会显示它。它只影响部署，与实验内容无关；提交实验代码时不要把它混进去，可以单独提交，或者在提交前用 git restore tools/deploy/activate_obd.sh 还原（还原后再部署前需要重新执行上面的命令）。

### 5.3 给 OBD 插件打补丁

补丁修改三个插件文件：

- `seekdb/1.0.0/display.py`、`mysqltest/3.1.0/init.py`：旧查询失败（错误码 1146，表不存在）时，改用 seekdb 1.4 提供的 `V$OB_SERVER_STAT` 等视图；
- `seekdb/1.0.0/start_pre.py`：启动 seekdb 时不再传入上面三个已废弃的参数。

在源码根目录整段复制执行下面的命令：

```diff
cd deps/3rd/usr/obd/plugins
patch -p1 --forward <<'EOF'
--- a/mysqltest/3.1.0/init.py
+++ b/mysqltest/3.1.0/init.py
@@ -31,7 +31,17 @@
         while True:
             try:
                 return cursor.fetchone('select * from oceanbase.__all_server where status = \'active\' and with_rootserver=1', raise_exception=True)
-            except:
+            except Exception as e:
+                if e.args and e.args[0] == 1146:
+                    try:
+                        # seekdb 1.4 exposes server addresses through
+                        # V$OB_SERVER_STAT instead of __all_server.
+                        return cursor.fetchone(
+                            'select SVR_IP as svr_ip, SQL_PORT as inner_port '
+                            'from oceanbase.V$OB_SERVER_STAT limit 1',
+                            raise_exception=True)
+                    except Exception:
+                        pass
                 if load_snap:
                     time.sleep(0.1)
                     continue
--- a/seekdb/1.0.0/display.py
+++ b/seekdb/1.0.0/display.py
@@ -61,7 +61,21 @@
     try:
         while True:
             try:
-                servers = cursor.fetchall('select * from oceanbase.__all_server', raise_exception=True, exc_level='verbose')
+                try:
+                    servers = cursor.fetchall('select * from oceanbase.__all_server', raise_exception=True, exc_level='verbose')
+                except Exception as e:
+                    # seekdb 1.4 no longer exposes __all_server.  Build the
+                    # fields consumed below from the replacement server view.
+                    if e.args[0] != 1146:
+                        raise e
+                    servers = cursor.fetchall(
+                        "select SVR_IP as svr_ip, "
+                        "SUBSTRING_INDEX(VERSION(), '-v', -1) as build_version, "
+                        "SQL_PORT as inner_port, 'zone1' as zone, "
+                        "'ACTIVE' as status "
+                        "from oceanbase.V$OB_SERVER_STAT",
+                        raise_exception=True,
+                        exc_level='verbose')
                 if servers:
                     stdio.print_list(servers, ['ip', 'version', 'port', 'zone', 'status'],
                         lambda x: [x['svr_ip'], x['build_version'].split('_')[0], x['inner_port'], x['zone'], x['status']], title=cluster_config.name)
@@ -79,7 +93,13 @@
                         "cmd": cmd
                     }

-                    var = cursor.fetchone('select unix_timestamp(gmt_create) as gmt_create from oceanbase.__all_virtual_sys_variable limit 1',  raise_exception=True, exc_level='verbose')
+                    try:
+                        var = cursor.fetchone('select unix_timestamp(gmt_create) as gmt_create from oceanbase.__all_virtual_sys_variable limit 1', raise_exception=True, exc_level='verbose')
+                    except Exception as e:
+                        # __all_sys_variable is the seekdb 1.4 replacement.
+                        if e.args[0] != 1146:
+                            raise e
+                        var = cursor.fetchone('select unix_timestamp(gmt_create) as gmt_create from oceanbase.__all_sys_variable limit 1', raise_exception=True, exc_level='verbose')
                     if var:
                         cid = int(var['gmt_create'] * 1000)
                         unique_id = Codec.encoding(cid, servers[0]['build_version'])
--- a/seekdb/1.0.0/start_pre.py
+++ b/seekdb/1.0.0/start_pre.py
@@ -34,7 +34,9 @@
     not_cmd_opt = [
         'home_path', 'obconfig_url', 'root_password', 'proxyro_password', 'scenario',
         'redo_dir', 'clog_dir', 'ilog_dir', 'slog_dir', '$_zone_idc', 'production_mode',
-        'obshell_port', 'zone', 'appname'
+        'obshell_port', 'zone', 'appname',
+        # seekdb 1.4 rejects these obsolete parameters at startup.
+        'system_memory', '__min_full_resource_pool_memory', 'local_ip'
     ]
     need_bootstrap=False
     get_value = lambda key: "'%s'" % server_config[key] if isinstance(server_config[key], str) else server_config[key]
EOF
cd -
```

成功时输出：

```text
patching file mysqltest/3.1.0/init.py
patching file seekdb/1.0.0/display.py
patching file seekdb/1.0.0/start_pre.py
```

如果提示 Reversed (or previously applied) patch detected! Skipping patch.，说明之前已经打过补丁，可以忽略。

### 5.4 注意事项

deps/3rd 不受 Git 管理。每次重新执行 ./build.sh release --init 后，依赖会被重新安装，需要再打一次插件补丁（5.2 的修改在源码里，不受影响）。

打完补丁后，部署日志里仍会先出现一行 [ERROR] OBD-5000: select * from oceanbase.__all_server ... execute failed。这是插件先尝试旧查询留下的记录，只要随后出现 Execute initialize sql ok 就说明一切正常。

## 6. 部署单机实例

### 6.1 准备部署文件

```bash
./tools/deploy/obd.sh prepare -b ./build_release -p /tmp/obtest
```

- `-b ./build_release`：把刚编译的 seekdb 复制到 `tools/deploy/bin/seekdb`，部署时使用这个副本。
- `-p /tmp/obtest`：实例的数据根目录，实例装在 `/tmp/obtest/seekdb1`。`/tmp` 可能被系统清理，想长期保留数据就换成自己的目录，例如 `$HOME/seekdb-data`。

首次执行时会生成部署配置 tools/deploy/single.yaml。已存在的 single.yaml 不会被覆盖，以后修改端口或目录请直接编辑这个文件。

输出中的以下内容可以忽略，不影响部署：

```text
[ERROR] `.../deps/3rd/usr/obd/...` and `.../tools/deploy/.obd/...` are the same file
Installing .../tools/timezone_V1.log FAIL
No such file: .../tools/timezone_V1.log
```

### 6.2 确认端口

```bash
grep -E 'mysql_port|home_path' tools/deploy/single.yaml
```

SQL 端口不是常见示例中的 10000，而是按用户 UID 计算的：100 * (UID % 500) + 10000。这样同一台机器上的不同用户不会冲突。例如 UID 为 1001 时端口是 10100。后文用 <端口> 表示这里看到的 mysql_port。

也可以在 prepare 时用 --port 10100 显式指定。部署前确认端口没有被占用：

```bash
ss -ltn | grep ':<端口> '
```

没有输出表示端口空闲。

### 6.3 部署并启动

```bash
./tools/deploy/obd.sh deploy -c ./tools/deploy/single.yaml
```

部署名取自 YAML 文件名，这里是 `single`。这条命令会安装二进制、启动 seekdb、等待初始化完成，并执行初始化 SQL（创建用户 `admin`，密码 `admin`，以及数据库 `test`）。实测约半分钟。成功时输出的关键部分：

```text
single deployed
Start seekdb ok
seekdb program health check ok
Wait for seekdb init ok
+----------------------------------------------+
|                    seekdb                    |
+-----------+---------+-------+-------+--------+
| ip        | version | port  | zone  | status |
+-----------+---------+-------+-------+--------+
| 127.0.0.1 | 1.4.0.0 | 10100 | zone1 | ACTIVE |
+-----------+---------+-------+-------+--------+
single running
Execute initialize sql ok
```

启动过程中还会出现一些资源检查提示，开发环境下都可以忽略：

- `[ERROR] OBD-1007: ... "open files" must not be less than 20000`：文件句柄上限偏低。实例仍会正常启动；想消除提示，可以在部署前执行 `ulimit -n 65535`（提示无权限时说明系统硬上限较低，忽略即可）。
- `[WARN] OBD-1007 core file size / stack size`、`OBD-2000 not enough memory`、`OBD-1012 clog and data use the same disk`、`OBD-2003 not enough disk space`：这些是按生产环境标准给出的建议。

如果一直停在 Wait for seekdb init，或者 seekdb 启动失败，多半是第 5.3 节的插件补丁没有打上。

## 7. 连接与验证

使用仓库自带的 obclient（兼容 MySQL 客户端，mysql 命令也可以连接）：

```bash
# root 用户，默认无密码
./deps/3rd/u01/obclient/bin/obclient -h127.0.0.1 -P<端口> -uroot -Dtest -A

# 或使用初始化创建的 admin 用户
./deps/3rd/u01/obclient/bin/obclient -h127.0.0.1 -P<端口> -uadmin -padmin -Dtest -A
```

连接后执行：

```sql
SELECT VERSION();
CREATE TABLE t1 (id INT PRIMARY KEY, v VARCHAR(20));
INSERT INTO t1 VALUES (1, 'hello'), (2, 'seekdb');
SELECT * FROM t1;
```

退出客户端用 \q 或 exit。

查看实例状态：

```bash
./tools/deploy/obd.sh display -n single
```

## 8. 改完代码后更新实例

这是日常开发中最容易出错的一步，请先读懂原因。

### 8.1 为什么 reinstall 不可靠

OBD 安装时使用的是 tools/deploy/bin/seekdb 的副本。它打包时只记录了指向这个文件的符号链接，所以每次编译出的"安装包"在 OBD 看来都一样。结果是：

- `obd.sh reinstall` 常常输出 `Noting to do.`，实例里的二进制没有被替换；
- `obd.sh restart` 只是重启，也不会换成新二进制。

因此不要依赖 reinstall，按下面的步骤手动替换。

### 8.2 替换二进制（保留数据）

```bash
./build.sh release --make -j8                       # 1. 增量编译

./tools/deploy/obd.sh stop -n single                # 2. 停止实例
cp build_release/src/observer/seekdb tools/deploy/bin/seekdb      # 3. 更新部署副本
cp build_release/src/observer/seekdb /tmp/obtest/seekdb1/bin/seekdb   # 4. 更新实例中的二进制
./tools/deploy/obd.sh start -n single               # 5. 启动

/tmp/obtest/seekdb1/bin/seekdb -V                   # 6. 确认版本
```

第 4 步的路径是 single.yaml 中的 home_path 加上 /bin/seekdb，如果你改过数据目录要相应替换。

第 3 步不能省：后面运行 mysqltest 等命令时，OBD 可能按 tools/deploy/bin/seekdb 重新安装实例。如果这里还是旧版本，你的新代码会被悄悄换回旧版本。

seekdb -V 中的 REVISION 是最近一次 commit，未提交的修改不会改变它。想确认运行的确实是刚编译的文件，可以比较校验和：md5sum build_release/src/observer/seekdb /tmp/obtest/seekdb1/bin/seekdb。

### 8.3 重新部署（清空数据）

以下情况需要销毁实例并重新部署：

- 修改了系统变量的定义（例如 Lab 2 新增 `enable_file_sql`）。旧数据目录与新二进制不兼容，实例会启动失败。
- 实例状态混乱，想从干净的环境重新开始。

```bash
cp build_release/src/observer/seekdb tools/deploy/bin/seekdb
./tools/deploy/obd.sh deploy -c ./tools/deploy/single.yaml
```

> **注意：**`deploy` 会先销毁同名实例再重新部署，实例中的所有数据都会被删除。

## 9. 运行 mysqltest

mysqltest 是课程的主要自动化测试方式。在 tools/deploy 目录下执行：

```bash
cd tools/deploy

# 运行一个用例
./obd.sh mysqltest -n single --disable-reboot \
  --test-dir ./mysql_test/test_suite/ai_function/t \
  --result-dir ./mysql_test/test_suite/ai_function/r \
  --test-set ai_prompt

# 运行一个测试套件
./obd.sh mysqltest -n single --disable-reboot --suite ai_function

cd -
```

一定要加 --disable-reboot。 不加时，obd.sh mysqltest 每次都会先销毁并重新部署实例：

- 实例中你手动创建的表、AI 模型等数据全部丢失；
- 使用的是 `tools/deploy/bin/seekdb`，如果没有按 8.2 更新它，测的就是旧代码；
- 重新初始化时偶尔会卡在 `init_user.sql` 的 `ANALYZE TABLE` 上约 10 分钟。

注意 --result-dir 写到 r 为止，OBD 会自动在后面加 mysql/。期望结果文件实际位于 r/mysql/<用例名>.result。

编写测试、用 --record 生成期望结果等更多用法，见各 Lab 的开发与测试手册。

## 10. 常见问题

### 10.1 实例管理命令

以下命令在源码根目录执行：

```bash
./tools/deploy/obd.sh list                     # 列出所有部署
./tools/deploy/obd.sh display -n single        # 查看状态
./tools/deploy/obd.sh stop -n single           # 停止
./tools/deploy/obd.sh start -n single          # 启动
./tools/deploy/obd.sh restart -n single        # 重启（不会更换二进制）
./tools/deploy/obd.sh destroy -n single        # 停止并删除实例数据
./tools/deploy/obd.sh destroy --rm -n single   # 同上，并删除 OBD 中的部署记录
```

destroy 会删除数据，执行前确认部署名。obd.sh sql、obd.sh pid、obd.sh less 等工具命令不支持 seekdb，请直接使用 obclient 和日志文件。

### 10.2 日志在哪里

| 日志 | 位置 |
| --- | --- |
| seekdb 服务日志 | `<home_path>/log/seekdb.log`，例如 `/tmp/obtest/seekdb1/log/seekdb.log` |
| OBD 日志 | `tools/deploy/.obd/log/obd` |
| 某次 OBD 命令的详细日志 | `./tools/deploy/obd.sh display-trace <Trace ID>`；Trace ID 在每次命令输出的末尾 |
| mysqltest 输出 | `tools/deploy/var/log/<用例名>.log` |

### 10.3 mkdir: cannot create directory '/tools': Permission denied

没有按 5.2 修正 tools/deploy/activate_obd.sh（或者修正后又被 git restore 还原了），OBD 工作目录被算成了 /tools/deploy。按 5.2 修正后重新执行 prepare 即可。不要用 sudo 创建 /tools。

### 10.4 一直停在 Wait for seekdb init、seekdb 启动失败，或报 Failed to get root server

第 5.3 节的 OBD 插件补丁没有打上，或者重新执行 --init 后补丁被覆盖了。先按 Ctrl+C 结束，然后：

```bash
./tools/deploy/obd.sh destroy -n single
# 按第 5.3 节打补丁
./tools/deploy/obd.sh deploy -c ./tools/deploy/single.yaml
```

### 10.5 连接 10000 端口被拒绝

端口按 UID 计算，以 tools/deploy/single.yaml 中的 mysql_port 为准（见 6.2）。

### 10.6 改了代码，但行为没有变化

按顺序检查：

- 增量编译是否成功；
- 是否按 8.2 替换了两处二进制（`reinstall` 不会替换）；
- 使用 `md5sum` 比较 `build_release` 和实例中的二进制；
- 是否连接到了正确的端口。

### 10.7 跑完 mysqltest，之前建的表不见了，或者测试卡了很久

没有加 --disable-reboot，实例被重新部署了。见第 9 节。

### 10.8 更新二进制后实例启动失败

查看 seekdb.log 中的第一处错误。如果修改了系统变量的定义，需要按 8.3 重新部署。

### 10.9 destroy 之后端口仍被占用

先确认占用端口的进程：

```bash
ss -ltnp | grep ':<端口> '
```

只有确认该进程是你自己的旧 seekdb 实例（看启动命令中的 --port 和 --base-dir）后，才执行 kill <PID>。不要按端口号直接结束不明进程，它可能属于同一台机器上的其他同学。

### 10.10 在同一账号下克隆了多份代码

OBD 的部署记录保存在 ~/.obd_dev/cluster/ 下，同一个用户的所有源码目录共用这些记录。而每份代码的 prepare 都会生成名为 single 的部署，在一份代码里 deploy 会覆盖另一份代码部署的实例。建议一个账号只保留一份工作代码；确实需要多份时，可以在其中一份里把 single.yaml 改名（例如 dev2.yaml，部署名随之变为 dev2），并修改其中的 mysql_port 和 home_path。

## 11. 涉及的文件

| 路径 | 作用 | 是否受 Git 管理 |
| --- | --- | --- |
| `build_release/src/observer/seekdb` | 编译产物 | 否 |
| `deps/3rd/` | `--init` 下载的依赖，包括 OBD 和 obclient | 否 |
| `tools/deploy/activate_obd.sh` | OBD 环境脚本，第 5.2 节修正 | 是 |
| `deps/3rd/usr/obd/plugins/seekdb/1.0.0/display.py`、`start_pre.py` | 第 5.3 节修补的 OBD 插件 | 否 |
| `deps/3rd/usr/obd/plugins/mysqltest/3.1.0/init.py` | 第 5.3 节修补的 OBD 插件 | 否 |
| `tools/deploy/single.yaml` | 部署配置：端口、数据目录等 | 否 |
| `tools/deploy/bin/seekdb` | OBD 部署使用的二进制副本 | 否 |
| `tools/deploy/.obd/` | OBD 工作目录和日志 | 否 |
| `tools/deploy/var/` | mysqltest 运行输出 | 否 |
| `~/.obd_dev/cluster/` | OBD 部署记录 | 仓库外 |
| `/tmp/obtest/seekdb1/` | 实例的二进制、日志和数据 | 仓库外 |

更多官方资料：获取代码、编译并运行 seekdb、安装工具链。
