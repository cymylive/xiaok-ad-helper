#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""push.py —— 用 dulwich 推送到 GitHub，绕过 Windows git 的 schannel TLS 故障。

本机 git push 报 schannel SEC_E_INVALID_TOKEN / curl 35 server closed abruptly，
但 Python 的 TLS 栈可用，所以改用纯 Python 的 dulwich 推送。

用法：
    set GITHUB_TOKEN=ghp_xxx
    python -X utf8 push.py "提交说明"

前提：pip install dulwich
"""
import base64
import os
import ssl
import subprocess
import sys
import time

OWNER = "cymylive"
REPO_NAME = "xiaok-ad-helper"
HERE = os.path.dirname(os.path.abspath(__file__))
GIT = r"E:\Git\cmd\git.exe"
RETRIES = 6


def git(*args, check=True):
    r = subprocess.run([GIT] + list(args), cwd=HERE,
                       capture_output=True, text=True, encoding="utf-8")
    if check and r.returncode != 0:
        raise SystemExit("git %s 失败:\n%s%s" % (" ".join(args), r.stdout, r.stderr))
    return r.stdout.strip()


def _install_ssl_patch():
    """让 dulwich 用不校验证书的 SSL（本机 TLS 被中间层干扰），并保留 Basic 认证。"""
    import urllib3
    from dulwich import client as dc

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    def make_manager(*a, **kw):
        return urllib3.PoolManager(cert_reqs="CERT_NONE", ssl_context=ctx)

    dc.default_urllib3_manager = make_manager
    urllib3.disable_warnings()


def main():
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        raise SystemExit("请先设置环境变量 GITHUB_TOKEN")

    if git("status", "--porcelain"):
        msg = sys.argv[1] if len(sys.argv) > 1 else "chore: 自动同步"
        git("add", "-A")
        git("commit", "-m", msg)
        print("[提交]", msg)
    else:
        print("[提交] 无改动")

    branch = git("rev-parse", "--abbrev-ref", "HEAD")
    head = git("rev-parse", "HEAD")
    print("[本地] %s -> %s" % (branch, head[:8]))

    _install_ssl_patch()
    from dulwich import porcelain
    from dulwich.client import HttpGitClient

    refspec = ("refs/heads/%s:refs/heads/%s" % (branch, branch)).encode()
    auth = base64.b64encode(("%s:x-oauth-basic" % token).encode()).decode()

    # 多种策略依次尝试
    strategies = [
        ("URL内嵌token", dict(url="https://%s@github.com/%s/%s.git" % (token, OWNER, REPO_NAME))),
        ("username/password", dict(url="https://github.com/%s/%s.git" % (OWNER, REPO_NAME),
                                   username=token, password="")),
        ("HTTP Basic 头", None),  # 特殊处理
    ]

    last = None
    for attempt in range(1, RETRIES + 1):
        for name, kw in strategies:
            try:
                if kw is None:
                    client = HttpGitClient.from_parsedurl(
                        __import__("urllib.parse", fromlist=["urlparse"]).urlparse(
                            "https://github.com/%s/%s.git" % (OWNER, REPO_NAME)))
                    client._http_headers = {"Authorization": "Basic " + auth}
                    result = client.send_pack(
                        "/%s/%s.git" % (OWNER, REPO_NAME),
                        lambda refs: {refspec},
                        None,
                        progress=None,
                    )
                else:
                    result = porcelain.push(HERE, refspecs=[refspec], **kw)
                refs = getattr(result, "refs", None) or getattr(result, "ref_status", None)
                print("[完成] 推送成功（%s，第 %d 轮）" % (name, attempt))
                if refs:
                    for k, v in refs.items():
                        kk = k.decode() if isinstance(k, bytes) else k
                        vv = v.decode() if isinstance(v, bytes) else v
                        print("   %s -> %s" % (kk, str(vv)[:8]))
                return
            except Exception as e:
                last = "%s: %s: %s" % (name, type(e).__name__, e)
                print("[尝试] %s -> %s" % (name, type(e).__name__))
        time.sleep(2)
    raise SystemExit("推送失败：%s" % last)


if __name__ == "__main__":
    main()
