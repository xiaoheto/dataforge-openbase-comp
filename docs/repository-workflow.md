# 仓库与 submodule 协作规范

## 远程角色

每个项目保留两类远程：

- `origin`：`xiaoheto` 组织下的团队 fork，承载团队分支和 PR。
- `upstream`：OceanBase 官方仓库，只用于获取官方更新。

```bash
git -C projects/seekdb remote add upstream https://github.com/oceanbase/seekdb.git
git -C projects/powercontext remote add upstream https://github.com/oceanbase/powercontext.git

# 使用 HTTPS 拉取公开 fork，使用 SSH 推送团队改动
git -C projects/seekdb remote set-url --push origin git@github.com:xiaoheto/seekdb.git
git -C projects/powercontext remote set-url --push origin git@github.com:xiaoheto/powercontext.git
```

如果 `upstream` 已存在，不要重复添加；用 `git remote -v` 核对地址。

### 推送走 HTTPS（推荐）

`gh` CLI 已登录时，HTTPS 推送无需任何额外配置，且不受 SSH 端口被限速的影响。
fetch 与 push URL 可以不一致——拉取用公开 HTTPS，推送用带凭据的 HTTPS：

```bash
git -C projects/seekdb remote set-url --push origin https://github.com/xiaoheto/seekdb-2026.git
git -C projects/seekdb credential fill   # 能解析出 username/password 即凭据就绪
```

### SSH 推送异常时的排查

`git@github.com:` 形式的 push URL 固定走 22 端口，该端口常被出口网络限速，表现为
`ssh: connect to host github.com port 22: Connection timed out`。改走 443 端口入口：

```bash
git -C projects/seekdb remote set-url --push origin ssh://git@ssh.github.com:443/xiaoheto/seekdb-2026.git
ssh -o StrictHostKeyChecking=accept-new -T -p 443 git@ssh.github.com
```

`git@github.com:` 是 scp 语法，无法指定端口，因此必须写成 `ssh://` 形式。
`StrictHostKeyChecking=accept-new` 用于首次连接 `ssh.github.com` 时自动写入
`known_hosts`，避免 ssh 停在主机密钥确认提示上。

若 `ssh -v` 显示连接建立后卡在握手阶段，多半是 WSL2 的 NAT 出网问题（conntrack
耗尽或 MTU 失配），而非 GitHub 侧问题。在 `/etc/wsl.conf` 启用
`networkingMode=mirrored` 后执行 `wsl --shutdown` 可根治。

## 比赛基线

两个项目均使用 `2026-competition`，不使用 `master` 或 PowerContext 的 `2026-competition-ecosystem`。

```bash
git -C projects/seekdb fetch upstream
git -C projects/seekdb switch 2026-competition
git -C projects/seekdb merge --ff-only upstream/2026-competition

git -C projects/powercontext fetch upstream
git -C projects/powercontext switch 2026-competition
git -C projects/powercontext merge --ff-only upstream/2026-competition
```

同步官方更新后，先将比赛分支推送到团队 fork，再更新父仓库中的 submodule 指针。父仓库记录的是精确提交，不会自动漂移到远程最新代码。

## 分支与 PR

- `2026-competition`：只同步官方基线，不直接开发。
- `lab1/integration`：seekdb Lab 1 集成分支，只接受经过评审的 PR。
- 功能分支：`lab1/ai-prompt`、`lab1/ai-complete`、`lab1/ai-embed-single`、`lab1/ai-embed-batch`、`lab1/ollama`、`lab1/ai-rerank`。
- 每个 PR 只对应一个评分项，附构建命令、目标测试和实际结果，并由至少一名非作者评审。
- Part A 一次提交覆盖 `AI_PROMPT` 与 `AI_COMPLETE` 两个评分项，两者都依赖 `ob_ai_func_utils.cpp` 的模板替换逻辑，拆分会引入额外冲突。
- 公共 AI 工具代码使用小 PR 先行合并；依赖分支每天 rebase，避免长期并行修改同一区域。

## 换行符

seekdb 仓库的 `.gitattributes` 没有设置 `text`/`eol` 属性，因此行尾完全取决于本地配置。父仓库已设 `* text=auto eol=lf`，但该规则不作用于 submodule。

提交功能代码前，确认 seekdb 工作区使用 LF：

```bash
git -C projects/seekdb config --local core.autocrlf false
git -C projects/seekdb config --local core.eol lf
```

若改动文件的行尾被整体改写，diff 会从几十行膨胀到几千行，评审无法进行。提交前用下面两条命令核对：

```bash
git -C projects/seekdb diff --cached --stat
git -C projects/seekdb diff --cached --ignore-all-space --stat
```

两条结果应一致。

### 清理工作区的 CRLF 污染

clone 时若全局 `core.autocrlf=true`，工作区副本会是 CRLF 而仓库 blob 仍是 LF。
本地改成 `core.autocrlf=false` 不会重写已存在的文件，这个差异平时被 git 的 stat
缓存掩盖，直到有人编辑某个 CRLF 文件并提交，整个文件就会以 CRLF 进入 commit。

先确认污染范围：

```bash
git -C projects/seekdb ls-files --eol | awk '{print $1, $2}' | sort | uniq -c
```

`i/lf w/crlf` 的条目就是污染。`i/crlf w/crlf` 是上游原生 CRLF，不要动。

用工具清理，它会从索引重写工作区副本并还原 mtime，不改动仓库内容，也不会触发
增量重编：

```bash
python3 tools/normalize-eol/normalize_eol.py projects/seekdb
```

### 依赖分支必须 rebase 到 LF 干净的基线

Part A 的基线提交曾以 CRLF 落盘，`lab1/integration` 与依赖分支都必须 rebase 到
LF 干净的 `lab1/ai-prompt`（`4b9d8905c`）之上，否则 PR diff 会再次被换行符噪声淹没：

```bash
git -C projects/seekdb rebase --onto 4b9d8905c <旧基线提交> <功能分支>
```

若 `ob_ai_func_utils.cpp` 出现整文件冲突，说明基线换行符不同：取对方（被 rebase
的提交）版本，再用 `sed -i 's/\r$//'` 统一转 LF。语义内容不变，冲突标记应消失。

rebase 完成后必须核对语义一致性，确认改动没有丢失：

```bash
git -C projects/seekdb diff --ignore-cr-at-eol <原分支> <rebase后分支> --stat
```

输出为空即表示内容完全一致，仅换行符不同。

## 更新父仓库指针

功能代码合入项目 fork 后，在父仓库执行：

```bash
git -C projects/seekdb switch lab1/integration
git -C projects/seekdb pull --ff-only
git add projects/seekdb
git commit -m "chore: update seekdb lab 1 baseline"
```

PowerContext 使用相同步骤。不要用 `git submodule update --remote` 覆盖正在开发的功能分支。

## 日常检查

```bash
git status --short
git submodule status
git -C projects/seekdb status --short --branch
git -C projects/powercontext status --short --branch
```

父仓库显示 submodule 为修改状态时，先确认是未提交源码修改还是有意更新的提交指针，再决定提交。
