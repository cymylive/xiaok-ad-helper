#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全局鼠标长按 -> 远程手机滚动。系统托盘常驻，右键菜单可退出。

不管焦点在哪个窗口，按住左键=手机上滑，按住右键=手机下滑，松开即停。
用法：小K广告助手  （或 python mouse_bridge.py 前台调试）
"""
import ctypes
import json
import os
import sys
import threading
import time
import urllib.request
from ctypes import wintypes

SERVER = "http://192.168.1.100:8080"   # 占位，实际以 config.json 为准
THRESHOLD_MS = 350
POLL_MS = 20


def _app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


APP_DIR = _app_dir()
LOG_FILE = os.path.join(APP_DIR, "bridge.log")
_CFG = os.path.join(APP_DIR, "config.json")
if os.path.exists(_CFG):
    try:
        with open(_CFG, encoding="utf-8") as _f:
            _c = json.load(_f)
        if _c.get("server"):
            SERVER = _c["server"] if _c["server"].startswith("http") else "http://" + _c["server"]
        if _c.get("threshold_ms"):
            THRESHOLD_MS = int(_c["threshold_ms"])
    except Exception as _e:
        pass


def _out(msg):
    line = time.strftime("%H:%M:%S ") + str(msg)
    try:
        print(line)
    except Exception:
        pass
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
shell32 = ctypes.WinDLL("shell32", use_last_error=True)

WH_MOUSE_LL = 14
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_RBUTTONDOWN = 0x0204
WM_RBUTTONUP = 0x0205

WM_APP = 0x8000
WM_TRAY = WM_APP + 1
WM_DESTROY = 0x0002
WM_COMMAND = 0x0111
WM_NULL = 0x0000

NIM_ADD, NIM_MODIFY, NIM_DELETE = 0, 1, 2
NIF_MESSAGE, NIF_ICON, NIF_TIP = 0x01, 0x02, 0x04
MF_STRING, MF_SEPARATOR, MF_GRAYED = 0x00, 0x800, 0x01
TPM_RIGHTBUTTON, TPM_RETURNCMD = 0x0002, 0x0100
LR_LOADFROMFILE, LR_DEFAULTSIZE = 0x0010, 0x0040
IMAGE_ICON = 1

ID_OPEN, ID_ON, ID_OFF, ID_EXIT = 1, 2, 3, 100

_tray_tip = "小K广告助手"


class MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("pt", wintypes.POINT),
        ("mouseData", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class GUID(ctypes.Structure):
    _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD),
                ("Data3", wintypes.WORD), ("Data4", ctypes.c_byte * 8)]


class NOTIFYICONDATAW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD), ("hWnd", wintypes.HWND), ("uID", wintypes.UINT),
        ("uFlags", wintypes.UINT), ("uCallbackMessage", wintypes.UINT),
        ("hIcon", wintypes.HICON), ("szTip", wintypes.WCHAR * 128),
        ("dwState", wintypes.DWORD), ("dwStateMask", wintypes.DWORD),
        ("szInfo", wintypes.WCHAR * 256), ("uVersion", wintypes.UINT),
        ("szInfoTitle", wintypes.WCHAR * 64), ("dwInfoFlags", wintypes.DWORD),
        ("guidItem", GUID), ("hBalloonIcon", wintypes.HICON),
    ]


WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, wintypes.HWND, wintypes.UINT,
                             ctypes.c_size_t, ctypes.c_ssize_t)


class WNDCLASSW(ctypes.Structure):
    _fields_ = [
        ("style", wintypes.UINT), ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int), ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE), ("hIcon", wintypes.HICON),
        ("hCursor", wintypes.HANDLE), ("hbrBackground", wintypes.HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR), ("lpszClassName", wintypes.LPCWSTR),
    ]


HOOKPROC = ctypes.CFUNCTYPE(ctypes.c_ssize_t, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)
user32.SetWindowsHookExW.restype = wintypes.HHOOK
user32.SetWindowsHookExW.argtypes = [ctypes.c_int, HOOKPROC, wintypes.HINSTANCE, wintypes.DWORD]
user32.CallNextHookEx.restype = ctypes.c_ssize_t
user32.CallNextHookEx.argtypes = [wintypes.HHOOK, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]
user32.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
kernel32.GetModuleHandleW.restype = wintypes.HMODULE
kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
user32.LoadImageW.restype = wintypes.HANDLE
user32.DefWindowProcW.restype = ctypes.c_ssize_t
user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]

user32.CreateWindowExW.restype = wintypes.HWND
user32.CreateWindowExW.argtypes = [
    wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
    ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
    wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, wintypes.LPVOID]
user32.RegisterClassW.restype = wintypes.ATOM
user32.RegisterClassW.argtypes = [ctypes.POINTER(WNDCLASSW)]
user32.CreatePopupMenu.restype = wintypes.HMENU
user32.AppendMenuW.argtypes = [wintypes.HMENU, wintypes.UINT, ctypes.c_size_t, wintypes.LPCWSTR]
user32.TrackPopupMenu.restype = wintypes.UINT
user32.TrackPopupMenu.argtypes = [wintypes.HMENU, wintypes.UINT, ctypes.c_int, ctypes.c_int,
                                  ctypes.c_int, wintypes.HWND, wintypes.LPVOID]
user32.DestroyMenu.argtypes = [wintypes.HMENU]
user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.PostQuitMessage.argtypes = [ctypes.c_int]
user32.TranslateMessage.argtypes = [ctypes.POINTER(wintypes.MSG)]
user32.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]
user32.LoadIconW.restype = wintypes.HICON
user32.LoadIconW.argtypes = [wintypes.HINSTANCE, wintypes.LPVOID]

shell32.Shell_NotifyIconW.restype = wintypes.BOOL
shell32.Shell_NotifyIconW.argtypes = [wintypes.DWORD, ctypes.POINTER(NOTIFYICONDATAW)]

_lock = threading.Lock()
_pressed = {}
_active = None
_enabled = False
_tray_hwnd = None
_wndproc_cb = None    # 必须持有 WNDPROC 引用，否则被 GC 导致崩溃


def _send(action, direction):
    payload = {"action": action}
    if direction:
        payload["dir"] = direction
    req = urllib.request.Request(
        SERVER + "/cmd",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        urllib.request.urlopen(req, timeout=2).read()
    except Exception:
        pass


def _set_bridge(on):
    req = urllib.request.Request(
        SERVER + "/bridge",
        data=json.dumps({"on": bool(on)}).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        urllib.request.urlopen(req, timeout=3).read()
        return True
    except Exception:
        return False


def _watch_switch():
    global _enabled
    last = None
    while True:
        try:
            r = urllib.request.urlopen(SERVER + "/bridge", timeout=2)
            on = bool(json.loads(r.read().decode()).get("on"))
            _enabled = on
            if on != last:
                _out("全局捕获已" + ("开启" if on else "关闭"))
                _update_tip()
                last = on
        except Exception:
            if last is not False:
                _out("服务端不可达，暂停捕获")
                _update_tip()
                last = False
            _enabled = False
        time.sleep(0.5)


def _monitor():
    global _active
    while True:
        time.sleep(POLL_MS / 1000.0)
        now = time.time()
        with _lock:
            cur = None
            if _enabled:
                for btn in ("left", "right"):
                    t0 = _pressed.get(btn)
                    if t0 is not None and (now - t0) * 1000 >= THRESHOLD_MS:
                        cur = "up" if btn == "left" else "down"
                        break
        if cur != _active:
            if _active is not None:
                _send("stop", None)
            if cur is not None:
                _send("start", cur)
            _active = cur


def _hook(nCode, wParam, lParam):
    if nCode == 0 and _enabled:
        if wParam == WM_LBUTTONDOWN:
            with _lock:
                _pressed["left"] = time.time()
        elif wParam == WM_RBUTTONDOWN:
            with _lock:
                _pressed["right"] = time.time()
        elif wParam in (WM_LBUTTONUP, WM_RBUTTONUP):
            key = "left" if wParam == WM_LBUTTONUP else "right"
            with _lock:
                _pressed.pop(key, None)
    return user32.CallNextHookEx(None, nCode, wParam, lParam)


# ---------- 托盘 ----------

def _icon_path():
    base = getattr(sys, "_MEIPASS", APP_DIR)
    p = os.path.join(base, "icon.ico")
    return p if os.path.exists(p) else None


def _load_icon():
    p = _icon_path()
    h = 0
    if p:
        h = user32.LoadImageW(None, p, IMAGE_ICON, 0, 0, LR_LOADFROMFILE | LR_DEFAULTSIZE)
    if not h:
        h = user32.LoadIconW(None, ctypes.c_void_p(32512))
    return h


def _update_tip():
    global _tray_hwnd
    if not _tray_hwnd:
        return
    state = "已开启" if _enabled else "已关闭"
    nid = NOTIFYICONDATAW()
    nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
    nid.hWnd = _tray_hwnd
    nid.uID = 1
    nid.uFlags = NIF_TIP
    nid.szTip = "小K广告助手 - " + state
    shell32.Shell_NotifyIconW(NIM_MODIFY, ctypes.byref(nid))


def _show_menu(hwnd):
    menu = user32.CreatePopupMenu()
    state = "已开启" if _enabled else "已关闭"
    user32.AppendMenuW(menu, MF_STRING | MF_GRAYED, 0, "状态：" + state)
    user32.AppendMenuW(menu, MF_SEPARATOR, 0, None)
    user32.AppendMenuW(menu, MF_STRING, ID_OPEN, "打开控制台")
    user32.AppendMenuW(menu, MF_STRING, ID_ON, "启用控制")
    user32.AppendMenuW(menu, MF_STRING, ID_OFF, "停用控制")
    user32.AppendMenuW(menu, MF_SEPARATOR, 0, None)
    user32.AppendMenuW(menu, MF_STRING, ID_EXIT, "退出")

    pt = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    user32.SetForegroundWindow(hwnd)
    cmd = user32.TrackPopupMenu(menu, TPM_RIGHTBUTTON | TPM_RETURNCMD,
                                pt.x, pt.y, 0, hwnd, None)
    user32.PostMessageW(hwnd, WM_NULL, 0, 0)
    user32.DestroyMenu(menu)

    if cmd == ID_OPEN:
        import webbrowser
        try:
            webbrowser.open(SERVER + "/c")
        except Exception:
            pass
    elif cmd == ID_ON:
        _set_bridge(True)
    elif cmd == ID_OFF:
        _set_bridge(False)
    elif cmd == ID_EXIT:
        user32.PostMessageW(hwnd, WM_DESTROY, 0, 0)


def _wndproc(hwnd, msg, wParam, lParam):
    if msg == WM_TRAY:
        low = lParam & 0xFFFF
        if low in (WM_RBUTTONUP, WM_LBUTTONUP):
            if low == WM_RBUTTONUP:
                _show_menu(hwnd)
            else:
                import webbrowser
                try:
                    webbrowser.open(SERVER + "/c")
                except Exception:
                    pass
        return 0
    if msg == WM_DESTROY:
        user32.PostQuitMessage(0)
        return 0
    return user32.DefWindowProcW(hwnd, msg, wParam, lParam)


def _create_tray():
    global _tray_hwnd, _wndproc_cb
    hinst = kernel32.GetModuleHandleW(None)
    cls_name = "ScrollBridgeTrayWnd"
    wc = WNDCLASSW()
    _wndproc_cb = WNDPROC(_wndproc)        # 保存引用防 GC
    wc.lpfnWndProc = _wndproc_cb
    wc.hInstance = hinst
    wc.lpszClassName = cls_name
    user32.RegisterClassW(ctypes.byref(wc))
    hwnd = user32.CreateWindowExW(0, cls_name, cls_name, 0, 0, 0, 0, 0, None, None, hinst, None)
    if not hwnd:
        return None

    nid = NOTIFYICONDATAW()
    nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
    nid.hWnd = hwnd
    nid.uID = 1
    nid.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
    nid.uCallbackMessage = WM_TRAY
    nid.hIcon = _load_icon()
    nid.szTip = "小K广告助手 - 已关闭"
    if not shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(nid)):
        return None
    _tray_hwnd = hwnd
    return hwnd


def _remove_tray():
    if not _tray_hwnd:
        return
    nid = NOTIFYICONDATAW()
    nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
    nid.hWnd = _tray_hwnd
    nid.uID = 1
    shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(nid))


def main():
    global SERVER, THRESHOLD_MS
    args = sys.argv[1:]
    if "--host" in args:
        SERVER = "http://" + args[args.index("--host") + 1]
    if "--threshold" in args:
        THRESHOLD_MS = int(args[args.index("--threshold") + 1])

    threading.Thread(target=_monitor, daemon=True).start()
    threading.Thread(target=_watch_switch, daemon=True).start()

    proc = HOOKPROC(_hook)
    hook = user32.SetWindowsHookExW(WH_MOUSE_LL, proc, kernel32.GetModuleHandleW(None), 0)
    if not hook:
        _out("SetWindowsHookEx 失败，错误码 %d" % ctypes.get_last_error())
        sys.exit(1)

    _out("全局鼠标钩子已启动，目标 " + SERVER)

    hwnd = _create_tray()
    if not hwnd:
        _out("托盘创建失败，转为无界面后台运行")
    else:
        _out("已驻留系统托盘，右键图标可退出")

    msg = wintypes.MSG()
    while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
        user32.TranslateMessage(ctypes.byref(msg))
        user32.DispatchMessageW(ctypes.byref(msg))

    _remove_tray()
    _out("已退出")


if __name__ == "__main__":
    main()
