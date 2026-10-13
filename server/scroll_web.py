#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""局域网文本投屏 + 电脑长按鼠标左右键远程滚动（零依赖，Termux 可直接跑）。

手机打开 http://<IP>:8080/m   显示文本
电脑打开 http://<IP>:8080/c   粘贴文本 / 设速度 / 长按左键上滑、长按右键下滑
"""
import json
import os
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

PORT = 8080
MAX_EVENTS = 200
DEFAULT_SPEED = 1200          # px/秒，按住时的滚动速度
PRESET_FILE = os.path.join(os.path.expanduser("~"), "scroll_presets.json")


def _lan_ip():
    """获取本机局域网 IP（用于提示电脑端该访问哪个地址）。"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
        finally:
            s.close()
        if ip and not ip.startswith("127."):
            return ip
    except Exception:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None):
            ip = info[4][0]
            if ip and not ip.startswith("127.") and ":" not in ip:
                return ip
    except Exception:
        pass
    return "127.0.0.1"

_lock = threading.Lock()
_st = {"text": "", "tver": 0, "speed": DEFAULT_SPEED, "seq": 0,
       "events": [], "bridge": False, "allow": "", "presets": {}}


def load_presets():
    try:
        with open(PRESET_FILE, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            _st["presets"] = {str(k): str(v) for k, v in data.items()}
    except Exception:
        _st["presets"] = {}


def save_presets():
    try:
        tmp = PRESET_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(_st["presets"], f, ensure_ascii=False)
        os.replace(tmp, PRESET_FILE)
    except Exception:
        pass


def snapshot(since, tver):
    with _lock:
        evs = [e for e in _st["events"] if e["seq"] > since]
        text = _st["text"] if tver != _st["tver"] else None
        return {"tver": _st["tver"], "text": text, "speed": _st["speed"],
                "seq": _st["seq"], "events": evs}


def push_event(payload):
    with _lock:
        _st["seq"] += 1
        ev = dict(payload)
        ev["seq"] = _st["seq"]
        _st["events"].append(ev)
        if len(_st["events"]) > MAX_EVENTS:
            _st["events"] = _st["events"][-MAX_EVENTS:]


HOME = """<!DOCTYPE html>
<html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>文本投屏</title>
<style>
body{margin:0;padding:40px 20px;background:#141414;color:#e8e8e8;
 font-family:system-ui,-apple-system,"Microsoft YaHei",sans-serif;}
a{display:block;margin:14px 0;padding:16px 20px;background:#1e1e1e;color:#9ad;
 border-radius:10px;text-decoration:none;font-size:17px;border:1px solid #2a2a2a;}
a:hover{background:#252525;}
p{color:#777;font-size:13px;}
</style></head><body>
<h2 style="color:#9ad;font-weight:600">文本投屏</h2>
<a href="/m">手机端显示页  /m</a>
<a href="/c">电脑端控制台  /c</a>
<p>手机打开 /m，电脑打开 /c，在 /c 里粘贴文本，然后长按鼠标左/右键控制手机滚动。</p>
</body></html>"""


PHONE = """<!DOCTYPE html>
<html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>投屏</title>
<style>
html,body{margin:0;padding:0;background:#111;color:#e8e8e8;
 font-family:system-ui,-apple-system,"Noto Sans CJK SC","Microsoft YaHei",sans-serif;}
#bar{position:fixed;left:0;right:0;top:0;height:32px;line-height:32px;
 padding:0 12px;font-size:12px;background:rgba(0,0,0,.7);color:#7ab;
 z-index:9;overflow:hidden;white-space:nowrap;}
#addr{position:fixed;left:0;right:0;top:32px;height:30px;line-height:30px;
 padding:0 12px;font-size:13px;background:rgba(20,60,110,.95);color:#8cf;
 z-index:9;overflow:hidden;white-space:nowrap;text-align:center;font-weight:600;}
#content{padding:78px 16px 60vh;font-size:19px;line-height:1.9;
 white-space:pre-wrap;word-break:break-word;}
#empty{position:fixed;inset:0;display:flex;align-items:center;justify-content:center;
 color:#555;font-size:15px;}
</style></head><body>
<div id="bar">连接中...</div>
<div id="addr">电脑端访问 <b>__LAN_URL__</b></div>
<div id="empty">暂无文本，请在电脑端粘贴并发送</div>
<div id="content"></div>
<script>
var since = 0, tver = -1, curSpeed = 1200;
var scrolling = null, scrollTimer = null;
var bar = document.getElementById('bar');
var content = document.getElementById('content');
var empty = document.getElementById('empty');

function render(t) {
  content.textContent = t;
  empty.style.display = t ? 'none' : 'flex';
}

function startScroll(dir) {
  stopScroll();
  scrolling = dir;
  scrollTimer = setInterval(function () {
    var px = curSpeed * 0.016;          // 16ms 一帧
    window.scrollBy(0, dir === 'up' ? -px : px);
  }, 16);
}

function stopScroll() {
  if (scrollTimer) { clearInterval(scrollTimer); scrollTimer = null; }
  scrolling = null;
}

function poll() {
  fetch('/state?since=' + since + '&tver=' + tver)
    .then(function (r) { return r.json(); })
    .then(function (s) {
      if (s.tver !== tver) { tver = s.tver; render(s.text || ''); }
      curSpeed = s.speed || 1200;
      if (s.events && s.events.length) {
        for (var i = 0; i < s.events.length; i++) {
          var e = s.events[i];
          if (e.action === 'start') startScroll(e.dir);
          else if (e.action === 'stop') stopScroll();
        }
      }
      since = s.seq;
      bar.textContent = '已连接 | 速度 ' + curSpeed + 'px/s | '
        + (scrolling === 'up' ? '↑ 上滑中' : scrolling === 'down' ? '↓ 下滑中' : '待命')
        + ' | 文本 ' + content.textContent.length + ' 字';
    })
    .catch(function () { bar.textContent = '连接中断，重试中...'; })
    .then(function () { setTimeout(poll, 80); });
}
render('');
poll();
</script></body></html>"""


DESK = """<!DOCTYPE html>
<html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>控制台</title>
<style>
body{margin:0;padding:20px;background:#141414;color:#e8e8e8;
 font-family:system-ui,-apple-system,"Microsoft YaHei",sans-serif;}
h1{font-size:18px;margin:0 0 14px;font-weight:600;color:#9ad;}
textarea{width:100%;height:30vh;box-sizing:border-box;background:#1e1e1e;color:#e8e8e8;
 border:1px solid #333;border-radius:8px;padding:12px;font-size:15px;line-height:1.7;
 resize:vertical;font-family:inherit;}
.row{margin:12px 0;display:flex;gap:12px;align-items:center;flex-wrap:wrap;}
button{background:#2b6cb0;color:#fff;border:0;border-radius:6px;padding:9px 18px;
 font-size:14px;cursor:pointer;}
button:hover{background:#3182ce;}
input[type=number]{width:100px;background:#1e1e1e;color:#e8e8e8;border:1px solid #333;
 border-radius:6px;padding:8px;}
#pad{margin-top:16px;padding:26px;border:2px dashed #3a3a3a;border-radius:12px;
 text-align:center;user-select:none;cursor:default;}
#pad .big{font-size:17px;margin-bottom:10px;}
#pad .k{color:#9ad;font-weight:600;}
#state{margin-top:10px;font-size:22px;font-weight:700;color:#4a9;height:30px;}
#msg{margin-top:12px;font-size:13px;color:#888;min-height:20px;}
</style></head><body>
<h1>电脑控制台 <span id="ver" style="font-size:12px;color:#666;font-weight:400">loading</span></h1>
<div class="row" id="presetBar">
  <span style="font-size:13px;color:#888">预设：</span>
  <span id="presetList" style="display:flex;gap:8px;flex-wrap:wrap"></span>
  <input id="presetName" type="text" placeholder="预设名称" style="background:#1e1e1e;color:#e8e8e8;border:1px solid #333;border-radius:6px;padding:8px;width:130px">
  <button id="savePreset">保存为预设</button>
</div>
<textarea id="txt" placeholder="在这里粘贴文本（长度不限），点『发送到手机』"></textarea>
<div class="row">
  <button id="send">发送到手机</button>
  <label>滚动速度 <input id="speed" type="number" value="1200" min="100" max="10000" step="100"> px/秒</label>
  <button id="saveSpeed">保存速度</button>
  <span id="msg"></span>
</div>
<div class="row">
  <button id="toggle" style="font-size:16px;padding:12px 28px;background:#666">开启全局鼠标控制</button>
  <span style="font-size:13px;color:#888">开启后：不管焦点在哪，按住左键=手机上滑，按住右键=手机下滑</span>
</div>
<div class="row">
  <label>允许的设备IP <input id="allow" type="text" style="width:200px;background:#1e1e1e;color:#e8e8e8;border:1px solid #333;border-radius:6px;padding:8px" placeholder="留空=允许所有"></label>
  <button id="saveAllow">保存</button>
  <button id="useMe">用本机IP</button>
  <span id="me" style="font-size:13px;color:#7ab"></span>
</div>
<div id="pad">
  <div class="big">在下方空白处 <span class="k">按住鼠标左键</span> = 手机上滑 &nbsp;|&nbsp; <span class="k">按住鼠标右键</span> = 手机下滑</div>
  <div>松开即停。文本框内左键仍是正常选择文字。</div>
  <div id="state">待命</div>
</div>
<div id="dbg" style="position:fixed;right:8px;bottom:8px;max-width:460px;background:rgba(0,0,0,.85);color:#7f7;font:11px/1.5 monospace;padding:6px 8px;border-radius:6px;white-space:pre-wrap;pointer-events:none;z-index:99">（诊断面板：在页面上按一下鼠标，这里会显示事件）</div>
<script>
var txt = document.getElementById('txt');
var speedEl = document.getElementById('speed');
var msg = document.getElementById('msg');
var stateEl = document.getElementById('state');

function flash(t) {
  msg.textContent = t;
  setTimeout(function () { if (msg.textContent === t) msg.textContent = ''; }, 1600);
}

function post(url, body) {
  return fetch(url, {method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(body)}).then(function (r) { return r.json(); });
}

document.getElementById('send').onclick = function () {
  post('/text', {text: txt.value}).then(function () {
    flash('已发送 ' + txt.value.length + ' 字');
  });
};

document.getElementById('saveSpeed').onclick = function () {
  var v = parseInt(speedEl.value, 10) || 1200;
  post('/config', {speed: v}).then(function () { flash('速度已设为 ' + v + 'px/s'); });
};

var holding = 0;   // 0=无 1=左键 2=右键

function isFormEl(t) {
  if (!t) return false;
  var n = t.tagName;
  return n === 'TEXTAREA' || n === 'INPUT' || n === 'BUTTON' || n === 'LABEL' || n === 'A';
}

document.addEventListener('mousedown', function (e) {
  if (isFormEl(e.target)) return;          // 表单控件上保持原生行为
  if (e.button !== 0 && e.button !== 2) return;
  e.preventDefault();
  if (holding) return;
  holding = e.button === 0 ? 1 : 2;
  var dir = e.button === 0 ? 'up' : 'down';
  stateEl.textContent = dir === 'up' ? '↑ 上滑中...' : '↓ 下滑中...';
  post('/cmd', {action: 'start', dir: dir});
});

document.addEventListener('mouseup', function (e) {
  if (!holding) return;
  if ((holding === 1 && e.button !== 0) || (holding === 2 && e.button !== 2)) return;
  holding = 0;
  stateEl.textContent = '待命';
  post('/cmd', {action: 'stop'});
});

window.addEventListener('blur', function () {
  if (!holding) return;
  holding = 0;
  stateEl.textContent = '待命';
  post('/cmd', {action: 'stop'});
});

document.addEventListener('contextmenu', function (e) {
  if (isFormEl(e.target)) return;
  e.preventDefault();
});

fetch('/config').then(function(r){return r.json();}).then(function(s){
  speedEl.value = s.speed;
});

// 设备白名单
var allowEl = document.getElementById('allow');
var meEl = document.getElementById('me');

function loadAllow() {
  fetch('/allow').then(function(r){return r.json();}).then(function(s){
    allowEl.value = s.allow || '';
    meEl.textContent = '本机IP: ' + s.you + (s.allow ? '' : '（当前允许所有设备）');
  });
}
document.getElementById('saveAllow').onclick = function () {
  post('/allow', {allow: allowEl.value}).then(function(r){
    if (r.ok) { flash(r.allow ? '仅允许 ' + r.allow : '已允许所有设备'); loadAllow(); }
    else { flash('失败: ' + r.err); }
  });
};
document.getElementById('useMe').onclick = function () {
  allowEl.value = meEl.textContent.replace('本机IP: ', '').split('（')[0].trim();
};
loadAllow();

// 全局鼠标控制开关
var toggleBtn = document.getElementById('toggle');
function applyToggle(on) {
  toggleBtn.textContent = on ? '关闭全局鼠标控制' : '开启全局鼠标控制';
  toggleBtn.style.background = on ? '#2f855a' : '#666';
}
toggleBtn.onclick = function () {
  var on = toggleBtn.textContent.indexOf('开启') === 0;
  post('/bridge', {on: on}).then(function (r) {
    applyToggle(r.on);
    flash(r.on ? '全局控制已开启' : '全局控制已关闭');
  });
};
fetch('/bridge').then(function(r){return r.json();}).then(function(s){ applyToggle(s.on); });

// 预设管理（按钮式，点击即载入）
var presetName = document.getElementById('presetName');
var presetList = document.getElementById('presetList');
var presetCache = {};

function renderPresets(list) {
  presetCache = list || {};
  var names = Object.keys(presetCache).sort();
  presetList.innerHTML = '';
  if (!names.length) {
    presetList.innerHTML = '<span style="font-size:13px;color:#666">（暂无，粘贴文本后填名称保存）</span>';
    return;
  }
  names.forEach(function (n) {
    var b = document.createElement('button');
    b.textContent = n;
    b.style.cssText = 'background:#2a4a6a;padding:8px 14px;position:relative';
    b.onclick = function () { loadPreset(n); };
    var del = document.createElement('span');
    del.textContent = ' ×';
    del.title = '删除此预设';
    del.style.cssText = 'color:#f88;font-weight:700;margin-left:4px;cursor:pointer';
    del.onclick = function (ev) {
      ev.stopPropagation();
      if (!confirm('确定删除预设「' + n + '」？')) return;
      post('/presets', {name: n, delete: true}).then(function (r) {
        if (r.ok) { renderPresets(r.presets); flash('已删除：' + n); }
      });
    };
    b.appendChild(del);
    presetList.appendChild(b);
  });
}

function loadPreset(n) {
  txt.value = presetCache[n] || '';
  presetName.value = n;
  post('/text', {text: txt.value}).then(function () {
    flash('已载入并发送：' + n + '（' + txt.value.length + ' 字）');
  });
}

document.getElementById('savePreset').onclick = function () {
  var n = presetName.value.trim();
  if (!n) { flash('请先填预设名称'); return; }
  post('/presets', {name: n, text: txt.value}).then(function (r) {
    if (r.ok) { renderPresets(r.presets); flash('已保存预设：' + n); }
    else { flash('失败：' + r.err); }
  });
};

fetch('/presets').then(function(r){return r.json();}).then(function(s){ renderPresets(s.presets); });

document.getElementById('ver').textContent = 'v2.3';
var dbgEl = document.getElementById('dbg');
var dbgLines = [];
function dlog(s) {
  dbgLines.push(new Date().toTimeString().slice(0, 8) + '  ' + s);
  if (dbgLines.length > 7) dbgLines.shift();
  dbgEl.textContent = dbgLines.join(String.fromCharCode(10));
}
document.addEventListener('mousedown', function (e) {
  dlog('mousedown btn=' + e.button + ' target=' + (e.target.tagName || '?') + (e.target.id ? '#' + e.target.id : ''));
}, true);
document.addEventListener('mouseup', function (e) {
  dlog('mouseup btn=' + e.button);
}, true);
document.addEventListener('contextmenu', function (e) {
  dlog('contextmenu prevented=' + e.defaultPrevented);
}, true);
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _raw(self, body, ctype, code=200):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code=200):
        self._raw(json.dumps(obj, ensure_ascii=False).encode("utf-8"),
                  "application/json; charset=utf-8", code)

    def _html(self, s):
        self._raw(s.encode("utf-8"), "text/html; charset=utf-8")

    def do_GET(self):
        u = urlparse(self.path)
        path, q = u.path, parse_qs(u.query)
        if path in ("/", "/index.html"):
            self._html(HOME)
        elif path == "/m":
            self._html(PHONE.replace("__LAN_URL__", "http://%s:%d/c" % (_lan_ip(), PORT)))
        elif path == "/c":
            self._html(DESK)
        elif path == "/state":
            since = int((q.get("since") or ["0"])[0])
            tver = int((q.get("tver") or ["-1"])[0])
            self._json(snapshot(since, tver))
        elif path == "/info":
            ip = _lan_ip()
            self._json({"ip": ip, "port": PORT,
                        "url": "http://%s:%d/c" % (ip, PORT)})
        elif path == "/config":
            with _lock:
                self._json({"speed": _st["speed"]})
        elif path == "/bridge":
            with _lock:
                self._json({"on": _st["bridge"]})
        elif path == "/allow":
            with _lock:
                self._json({"allow": _st["allow"], "you": self.client_address[0]})
        elif path == "/presets":
            with _lock:
                self._json({"presets": _st["presets"]})
        else:
            self._raw(b"not found", "text/plain; charset=utf-8", 404)

    def do_POST(self):
        path = urlparse(self.path).path
        with _lock:
            allow = _st["allow"]
        # /allow 自身豁免校验，否则一旦设错 IP 将无法恢复
        if allow and path != "/allow":
            ip = self.client_address[0]
            allowed = [x.strip() for x in allow.split(",") if x.strip()]
            if ip not in allowed:
                self._json({"ok": False, "err": "device %s not allowed" % ip}, 403)
                return
        try:
            n = int(self.headers.get("Content-Length") or 0)
            data = json.loads((self.rfile.read(n) if n else b"{}").decode("utf-8") or "{}")
        except Exception as exc:                                  # noqa: BLE001
            self._json({"ok": False, "err": str(exc)}, 400)
            return

        if path == "/text":
            with _lock:
                _st["text"] = str(data.get("text", ""))
                _st["tver"] += 1
            self._json({"ok": True})
        elif path == "/config":
            try:
                speed = max(100, min(10000, int(data.get("speed", 1200))))
            except Exception:                                     # noqa: BLE001
                speed = 1200
            with _lock:
                _st["speed"] = speed
            self._json({"ok": True, "speed": speed})
        elif path == "/bridge":
            with _lock:
                _st["bridge"] = bool(data.get("on"))
                val = _st["bridge"]
            self._json({"ok": True, "on": val})
        elif path == "/allow":
            with _lock:
                _st["allow"] = str(data.get("allow", "")).strip()
                val = _st["allow"]
            self._json({"ok": True, "allow": val, "you": self.client_address[0]})
        elif path == "/presets":
            name = str(data.get("name", "")).strip()
            if not name:
                self._json({"ok": False, "err": "name required"}, 400)
                return
            with _lock:
                if data.get("delete"):
                    _st["presets"].pop(name, None)
                else:
                    if "text" not in data:
                        self._json({"ok": False, "err": "text required"}, 400)
                        return
                    _st["presets"][name] = str(data.get("text", ""))
                snap = dict(_st["presets"])
            save_presets()
            self._json({"ok": True, "presets": snap})
        elif path == "/cmd":
            action = data.get("action")
            if action == "start":
                d = data.get("dir")
                if d not in ("up", "down"):
                    self._json({"ok": False, "err": "dir must be up/down"}, 400)
                    return
                push_event({"action": "start", "dir": d})
            elif action == "stop":
                push_event({"action": "stop"})
            else:
                self._json({"ok": False, "err": "action must be start/stop"}, 400)
                return
            self._json({"ok": True})
        else:
            self._json({"ok": False, "err": "not found"}, 404)

    def log_message(self, fmt, *args):
        pass


def main():
    load_presets()
    srv = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print("serving on 0.0.0.0:%d" % PORT)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
