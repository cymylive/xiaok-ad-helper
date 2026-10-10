#!/usr/bin/env python3
"""通过 SSH 上传文件到 Termux（需 pip install paramiko）。

用法：
    python deploy.py <本地文件> <远程路径> --host HOST --password PASS
"""
import argparse
import paramiko


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("local")
    ap.add_argument("remote")
    ap.add_argument("--host", required=True, help="手机 IP")
    ap.add_argument("--port", type=int, default=8022)
    ap.add_argument("--user", default="root")
    ap.add_argument("--password", required=True)
    args = ap.parse_args()

    data = open(args.local, "rb").read()
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(args.host, args.port, args.user, args.password, timeout=15)
    stdin, stdout, stderr = c.exec_command("cat > " + args.remote)
    stdin.write(data)
    stdin.channel.shutdown_write()
    stdout.channel.recv_exit_status()
    c.close()
    print("uploaded", len(data), "bytes ->", args.remote)


if __name__ == "__main__":
    main()
