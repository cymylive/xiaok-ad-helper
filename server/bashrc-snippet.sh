# === 打开 Termux 自动启动文本投屏服务 ===
# 追加到 ~/.bashrc
export SVDIR=$PREFIX/var/service
export LOGDIR=$PREFIX/var/log

if sv status scroll 2>/dev/null | grep -q "run:"; then
    echo "[投屏] 服务运行中 → http://<手机IP>:8080/c"
else
    service-daemon start >/dev/null 2>&1
    for i in 1 2 3 4 5; do
        sleep 0.4
        sv status scroll 2>/dev/null | grep -q "run:" && break
    done
    if sv status scroll 2>/dev/null | grep -q "run:"; then
        echo "[投屏] 服务已启动 → http://<手机IP>:8080/c"
    else
        echo "[投屏] 服务启动失败，请检查"
    fi
fi
