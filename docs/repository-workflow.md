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

### 推送超时：改走 443 端口

SSH 推送报 `ssh: connect to host github.com port 22: Connection timed out` 时，多半是
出口网络封禁或限速了 22 端口。改用 GitHub 的 443 端口入口：

```bash
git -C projects/seekdb remote set-url --push origin ssh://git@ssh.github.com:443/xiaoheto/seekdb-2026.git
ssh -T -p 443 git@ssh.github.com   # 出现 "Hi <user>! You've successfully authenticated" 即正常
```

`git@github.com:` 形式的 push URL 固定走 22 端口，无法指定端口，因此上面必须写成
`ssh://` 形式。拉取仍保持 HTTPS，不受影响。

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
