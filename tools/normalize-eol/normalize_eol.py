#!/usr/bin/env python3
"""Normalize the working tree of a git repository to LF line endings.

The upstream blobs stay untouched: only files whose index entry is LF while the
working tree copy is CRLF are rewritten from the index. Upstream files that
really are CRLF keep their CRLF, so the repository content never changes.

The original modification times are restored afterwards, so an incremental
build does not see a single changed source file.

Usage:
    python3 normalize_eol.py [repo_path]
"""
import os
import subprocess
import sys


def git(repo, args, **kwargs):
    return subprocess.run(["git", "-C", repo] + args, capture_output=True, **kwargs)


def main():
    repo = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
    if not os.path.exists(os.path.join(repo, ".git")):
        print("not a git repository: %s" % repo)
        return 2

    print("repository: %s" % repo)
    print("core.autocrlf=%s  core.eol=%s" % (
        git(repo, ["config", "--local", "--get", "core.autocrlf"]).stdout.decode().strip() or "(unset)",
        git(repo, ["config", "--local", "--get", "core.eol"]).stdout.decode().strip() or "(unset)"))

    # Polluted files: the index holds LF, the working tree copy holds CRLF.
    polluted = []
    for record in git(repo, ["ls-files", "--eol", "-z"]).stdout.split(b"\0"):
        if not record:
            continue
        parts = record.decode("utf-8", "surrogateescape").split(None, 3)
        if len(parts) >= 4 and parts[0] == "i/lf" and parts[1] == "w/crlf":
            polluted.append(parts[3])
    print("polluted files: %d" % len(polluted))
    if not polluted:
        print("nothing to do")
        return 0

    # Keep the files that carry real local edits, they must not be overwritten.
    reported = set()
    for record in git(repo, ["status", "--porcelain", "-z"]).stdout.split(b"\0"):
        if not record:
            continue
        text = record.decode("utf-8", "surrogateescape")
        if text[:2] != "??":
            reported.add(text[3:])
    local_edits = reported - set(polluted)
    targets = [p for p in polluted if p not in local_edits]
    print("real local edits, kept untouched: %d %s" % (len(local_edits), sorted(local_edits)[:5]))
    print("files to normalize: %d" % len(targets))
    if not targets:
        return 0

    stamps = {}
    for path in targets:
        try:
            info = os.stat(os.path.join(repo, path))
            stamps[path] = (info.st_atime_ns, info.st_mtime_ns)
        except OSError:
            pass

    # Rewrite the working tree copies from the index, the index itself is not touched.
    result = subprocess.run(
        ["git", "-C", repo, "checkout-index", "-f", "-z", "--stdin"],
        input=("\0".join(targets)).encode("utf-8", "surrogateescape") + b"\0",
        capture_output=True)
    if result.returncode != 0:
        print(result.stderr.decode(errors="replace")[:2000])
        return 1

    # Restore the modification times so an incremental build stays up to date.
    for path, (atime, mtime) in stamps.items():
        try:
            os.utime(os.path.join(repo, path), ns=(atime, mtime))
        except OSError:
            pass

    # Refresh the stat cache. The content matches the index, so this is a no-op
    # for the index itself, it only makes git stop reporting the files.
    subprocess.run(["git", "-C", repo, "add", "--pathspec-from-file=-",
                    "--pathspec-file-nul", "--"],
                   input=("\0".join(targets)).encode("utf-8", "surrogateescape") + b"\0",
                   capture_output=True)
    if local_edits:
        subprocess.run(["git", "-C", repo, "reset", "-q", "--"] + local_edits,
                       capture_output=True)

    remaining = 0
    for path in targets:
        try:
            with open(os.path.join(repo, path), "rb") as handle:
                if b"\r" in handle.read():
                    remaining += 1
        except OSError:
            pass
    print("normalized: %d, still holding CR: %d" % (len(targets), remaining))
    return 0 if remaining == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
