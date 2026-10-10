# 架构说明

## 整体数据流

```
电脑端 (Windows)                手机端 (Termux)
─────────────                  ─────────────

全局鼠标钩子                       HTTP 服务 (:8080)
  WH_MOUSE_LL                      ├─ /m   显示页（轮询 /state）
    │                              ├─ /c   控制台
    ├─ 按下左键 ──┐                ├─ /state  增量状态
    ├─ 按下右键 ──┤                ├─ /text   发文本
    │             │                ├─ /cmd    滚动指令
    └─ 松开 ──────┘                ├─ /bridge 开关
                  │                ├─ /allow  白名单
    阈值判定 350ms │                └─ /presets 预设
                  ▼
        POST /cmd {start,dir}
        POST /cmd {stop}      ──────────────▶  更新事件队列
                                                │
        GET /bridge (500ms)  ◀──────────────  返回开关状态
                                                │
        GET /state (80ms)    ◀──────────────  返回增量事件
                                                │
                                              手机页收到 start
                                              setInterval 16ms
                                              scrollBy(speed)
```

## 关键设计

### 1. 指令与滚动解耦

电脑端只在按下/松开时各发**一条**指令，不持续发请求：

| 时机 | 发送 |
|---|---|
| 按住超过阈值 | `POST /cmd {action:start, dir:up/down}` |
| 松开 | `POST /cmd {action:stop}` |

手机端收到 `start` 后自己用 `setInterval(16ms)` 连续 `scrollBy`，收到 `stop` 停止。

**好处**：滚动丝滑不吃网络，电脑端几乎零开销。

### 2. 增量轮询

手机页每 80ms 拉一次 `/state?since=N&tver=M`：

- `since`：只要 seq > since 的事件（滚动指令），避免重复
- `tver`：文本版本号，没变就不下发文本，**长文本不重复传**

### 3. 长按阈值

`threshold_ms`（默认 350）防止单击误触。按住时间超过阈值才触发滚动。

鼠标按下时记录时间戳，一个 20ms 轮询线程检查是否超时。

### 4. 全局钩子的实现

用 Windows 低级鼠标钩子 `WH_MOUSE_LL`：

```python
user32.SetWindowsHookExW(WH_MOUSE_LL, proc, hinst, 0)
```

- 不管焦点在哪个窗口都能捕获
- **不阻止**原生事件（`CallNextHookEx` 透传），拖拽/选择照常
- 回调函数必须持有全局引用，否则被 GC 导致崩溃

### 5. 系统托盘

纯 ctypes 调 Win32 API（无 pystray 等依赖）：

1. `RegisterClassW` + `CreateWindowExW` 建隐藏窗口
2. `Shell_NotifyIconW(NIM_ADD)` 加托盘图标
3. `WM_APP+1` 消息处理点击
4. `CreatePopupMenu` + `TrackPopupMenu` 弹右键菜单

### 6. 设备白名单

`/allow` 设置允许的电脑 IP（逗号分隔）。所有 POST 校验来源 IP，非白名单返回 403。

**`/allow` 接口自身豁免校验** —— 否则设错 IP 后无法恢复。

## 线程模型（电脑端）

```
主线程     GetMessageW 消息循环（托盘事件）
线程 1     _monitor   20ms 轮询，检测长按超时 → 发指令
线程 2     _watch_switch  500ms 轮询 /bridge 同步开关
钩子回调   由系统在钩子线程调用，只记录时间戳（不阻塞）
```

## 状态对象（手机端）

```python
_st = {
    "text": "",        # 当前文本
    "tver": 0,         # 文本版本号（变化时 +1）
    "speed": 1200,     # 滚动速度 px/s
    "seq": 0,          # 事件序号
    "events": [],      # 事件队列（上限 200）
    "bridge": False,   # 全局钩子开关
    "allow": "",       # IP 白名单
    "presets": {},     # 文本预设
}
```
