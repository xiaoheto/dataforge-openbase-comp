# 换行符规范化

把 git 工作区里被 CRLF 污染的文件恢复成 LF，且**不改动仓库内容**。

## 背景

仓库的 blob 本身是 LF，但工作区副本可能是 CRLF。通常是 clone 时全局
`core.autocrlf=true` 造成的；后来把本地配置改成 `core.autocrlf=false` 不会重写
已经存在的文件。

这个状态平时被 git 的 stat 缓存掩盖，但只要有人编辑某个 CRLF 文件并提交，
整个文件就会以 CRLF 进入 commit，评审时 diff 会从几十行膨胀到几千行。

## 用法

```bash
python3 tools/normalize-eol/normalize_eol.py projects/seekdb
```

脚本会：

1. 用 `git ls-files --eol` 找出「索引是 LF、工作区是 CRLF」的文件；
2. 跳过有真实本地改动的文件，不覆盖它们；
3. 用 `git checkout-index` 从索引重写这些文件，索引本身不变；
4. 还原原始 mtime，**增量构建不会因此重编任何单元**；
5. 刷新 git 的 stat 缓存，让 `git status` 恢复干净。

上游本来就用 CRLF 的文件（索引里就是 CRLF）会被跳过，内容不受影响。

脚本可以重复执行，已规范化的仓库会报告 `nothing to do`。

## 预防

新克隆的仓库先设置好这两个配置，避免再次污染：

```bash
git -C projects/seekdb config --local core.autocrlf false
git -C projects/seekdb config --local core.eol lf
```

提交前核对 diff 是否被换行符放大：

```bash
git -C projects/seekdb diff --cached --stat
git -C projects/seekdb diff --cached --ignore-all-space --stat
```

两条结果应一致。
