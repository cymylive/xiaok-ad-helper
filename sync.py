#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sync.py —— 用 GitHub API 同步仓库（绕过 Windows git 的 schannel TLS 故障）。

本机 git push/fetch 报 schannel SEC_E_INVALID_TOKEN / curl 35，但 GitHub REST API
走 Python urllib 完全正常，所以用 API 做文件级同步。

用法：
    set GITHUB_TOKEN=ghp_xxx
    python -X utf8 sync.py status          # 查看本地与远程差异
    python -X utf8 sync.py push "说明"      # 上传本地改动到 GitHub
    python -X utf8 sync.py pull            # 下载远程改动到本地

前提：无（纯标准库）
"""
import base64
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.request

OWNER = "cymylive"
REPO = "xiaok-ad-helper"
BRANCH = "main"
HERE = os.path.dirname(os.path.abspath(__file__))

SKIP_DIRS = {".git", "__pycache__", "build", "dist", "便携版", "_gh"}
SKIP_FILES = {"client/config.json"}  # 本地配置（含真实手机 IP），不上传

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


def token():
    t = os.environ.get("GITHUB_TOKEN", "")
    if not t:
        raise SystemExit("请先设置环境变量 GITHUB_TOKEN")
    return t


def api(method, path, body=None, retries=4):
    """带重试的 API 调用（本机网络偶发 RemoteDisconnected）。"""
    url = "https://api.github.com" + path
    data = json.dumps(body).encode() if body is not None else None
    last = None
    for i in range(retries):
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Authorization", "Bearer " + token())
        req.add_header("User-Agent", "cymylive")
        req.add_header("Accept", "application/vnd.github+json")
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            r = urllib.request.urlopen(req, timeout=60, context=ctx)
            return r.status, json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            try:
                return e.code, json.loads(e.read().decode())
            except Exception:
                return e.code, None
        except Exception as e:
            last = e
            print("    [重试 %d/%d] %s" % (i + 1, retries, type(e).__name__))
            time.sleep(2)
    raise SystemExit("API 请求失败：%s" % last)


def remote_tree():
    """返回 {path: blob_sha}"""
    st, d = api("GET", "/repos/%s/%s/git/trees/%s?recursive=1" % (OWNER, REPO, BRANCH))
    if st != 200:
        raise SystemExit("获取远程树失败: %s" % st)
    return {t["path"]: t["sha"] for t in d.get("tree", []) if t["type"] == "blob"}


def local_files():
    out = {}
    for root, dirs, files in os.walk(HERE):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            full = os.path.join(root, f)
            rel = os.path.relpath(full, HERE).replace("\\", "/")
            if rel in SKIP_FILES or f.endswith(".log"):
                continue
            out[rel] = full
    return out


def cmd_status():
    rtree = remote_tree()
    lfiles = local_files()
    only_local = sorted(set(lfiles) - set(rtree))
    only_remote = sorted(set(rtree) - set(lfiles))
    print("仅本地有 (%d):" % len(only_local))
    for p in only_local:
        print("  +", p)
    print("仅远程有 (%d):" % len(only_remote))
    for p in only_remote:
        print("  -", p)
    print("共有文件:", len(set(lfiles) & set(rtree)))
    return 0


def cmd_push(message):
    rtree = remote_tree()
    lfiles = local_files()
    changed = []
    for rel, full in sorted(lfiles.items()):
        data = open(full, "rb").read()
        st, cur = api("GET", "/repos/%s/%s/contents/%s?ref=%s" % (OWNER, REPO, rel, BRANCH))
        need = True
        if st == 200:
            rsha = cur.get("sha")
            # 用 git blob sha 对比
            import hashlib
            header = b"blob %d\x00" % len(data)
            blob_sha = hashlib.sha1(header + data).hexdigest()
            if rtree.get(rel) == blob_sha:
                need = False
        if need:
            changed.append(rel)

    if not changed:
        print("无改动需要上传")
        return 0

    print("上传 %d 个文件:" % len(changed))
    for rel in changed:
        data = open(lfiles[rel], "rb").read()
        st, cur = api("GET", "/repos/%s/%s/contents/%s?ref=%s" % (OWNER, REPO, rel, BRANCH))
        body = {"message": message, "content": base64.b64encode(data).decode(), "branch": BRANCH}
        if st == 200:
            body["sha"] = cur["sha"]
        st2, res = api("PUT", "/repos/%s/%s/contents/%s" % (OWNER, REPO, rel), body)
        print("  %s %s" % ("OK " if st2 in (200, 201) else "FAIL", rel))
        if st2 not in (200, 201):
            print("     ", str(res)[:200])
    return 0


def cmd_pull():
    rtree = remote_tree()
    n = 0
    for rel in sorted(rtree):
        full = os.path.join(HERE, rel.replace("/", os.sep))
        st, d = api("GET", "/repos/%s/%s/contents/%s?ref=%s" % (OWNER, REPO, rel, BRANCH))
        if st != 200:
            continue
        content = base64.b64decode(d["content"])
        old = open(full, "rb").read() if os.path.exists(full) else None
        if old != content:
            os.makedirs(os.path.dirname(full), exist_ok=True)
            open(full, "wb").write(content)
            print("  更新", rel)
            n += 1
    print("拉取完成，更新 %d 个文件" % n)
    return 0


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    cmd = sys.argv[1]
    if cmd == "status":
        return cmd_status()
    if cmd == "push":
        return cmd_push(sys.argv[2] if len(sys.argv) > 2 else "chore: sync")
    if cmd == "pull":
        return cmd_pull()
    print("未知命令:", cmd)
    return 1


if __name__ == "__main__":
    sys.exit(main())
