# -*- coding: utf-8 -*-
"""Android 端 Python 入口。

由 ServerService.kt 在后台线程调用：
    Python.getModule("main").callAttr("start_server", filesDir)
"""
import os
import threading


def start_server(files_dir=None):
    """把 scroll_web 的 HTTP 服务跑在后台守护线程里。"""
    import scroll_web

    # Android 上 ~ 不可写，把预设文件重定向到 app 私有目录
    if files_dir:
        try:
            os.makedirs(files_dir, exist_ok=True)
        except Exception:
            pass
        scroll_web.PRESET_FILE = os.path.join(files_dir, "scroll_presets.json")

    t = threading.Thread(target=scroll_web.main, daemon=True)
    t.start()
    return "started"


if __name__ == "__main__":
    start_server()
