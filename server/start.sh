#!/data/data/com.termux/files/usr/bin/bash
# 启动/重启 文本投屏服务（tmux 托管，SSH 断开也不停）
cd /data/data/com.termux/files/home || exit 1
pkill -f scroll_web.py 2>/dev/null
tmux kill-session -t scroll 2>/dev/null
sleep 0.5
tmux new-session -d -s scroll 'cd /data/data/com.termux/files/home && python3 scroll_web.py 2>&1 | tee scroll_web.log'
sleep 2
echo "=== tmux ==="
tmux ls 2>&1
echo "=== local ==="
python3 -c "import urllib.request;print(urllib.request.urlopen('http://127.0.0.1:8080/',timeout=5).status)" 2>&1
