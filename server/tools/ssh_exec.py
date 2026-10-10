#!/usr/bin/env python3
"""通过 SSH 在 Termux 执行命令（需 pip install paramiko）。

用法：
    python ssh_exec.py "<命令>" --host HOST --password PASS
"""
import argparse
import paramiko


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("command")
    ap.add_argument("--host", required=True)
    ap.add_argument("--port", type=int, default=8022)
    ap.add_argument("--user", default="root")
    ap.add_argument("--password", required=True)
    args = ap.parse_args()

    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(args.host, args.port, args.user, args.password, timeout=15)
    stdin, stdout, stderr = c.exec_command(args.command)
    print(stdout.read().decode("utf-8", "replace"))
    err = stderr.read().decode("utf-8", "replace")
    if err.strip():
        print("[stderr]", err)
    c.close()


if __name__ == "__main__":
    main()
