# 小K广告助手 · 手机文本投屏 + 电脑鼠标远程滚动

用电脑鼠标长按控制手机页面上下滚动 —— 把手机当副屏看文本/题目/文档。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 这是什么

一个局域网内的小工具，解决「想用手机看长文本，但不想一直用手划」的问题：

- **手机**跑一个零依赖 HTTP 服务，显示文本（**两种装法**：Termux 脚本 / 或直接装 APK）
- **电脑**（Windows）跑一个全局鼠标钩子，长按左键/右键 → 远程控制手机滚动
- 电脑端有**系统托盘**常驻，控制台网页里开关

不管电脑当前焦点在哪个窗口，按住鼠标左键=手机上滑，右键=手机下滑，松开即停。

## 特性

- 零第三方依赖：两端都只用 Python 标准库
- 全局鼠标钩子：不受焦点限制，不干扰正常拖拽/选择
- **左右键同时长按**：一键切换手机屏幕常亮（按一次关、再按一次开）
- 系统托盘常驻：右键菜单可启用/停用/退出
- 单文件 exe：免装 Python，复制即用
- 文本投屏：粘贴任意长度文本，手机上即时显示
- 预设题目：常用文本保存为预设，一键载入
- 设备白名单：只允许指定电脑 IP 控制，防误连
- 打开 Termux 自动启动（termux-services 托管）
- **Android APK**：不想装 Termux 可直接装 APK，前台服务常驻，效果一致
- **GitHub Actions 自动编译**：push 代码自动出 APK 和 exe，发布到 latest Release

## 架构

```
┌──────────────┐   HTTP (局域网)   ┌──────────────┐
│  电脑 Windows  │ ────────────────▶ │  手机 Termux   │
│              │                    │              │
│ 全局鼠标钩子   │  POST /cmd        │  HTTP 服务    │
│ 系统托盘      │  POST /text       │  显示页 /m     │
│              │  GET  /state      │  控制台 /c     │
└──────────────┘ ◀──────────────── └──────────────┘
```

- **长按左键** → 发 `start up` → 手机持续上滑
- **松开** → 发 `stop` → 手机停止
- **左右键同时按住** → 发 `/keep` → 切换手机屏幕常亮（此期间不滚动）
- 手机端收到 `start` 后自己按 16ms 定时器平滑滚动，不吃网络

## 目录结构

```
.
├── client/                  # 电脑端（Windows）
│   ├── mouse_bridge.py      # 核心：全局鼠标钩子 + 系统托盘
│   ├── launch_bridge.py     # 后台启动器
│   ├── setup.ps1            # 一键部署脚本
│   ├── config.example.json  # 配置模板
│   ├── make_icon.py         # 生成托盘图标
│   └── icon.ico
├── android/                 # 手机端 APK（Kotlin + Chaquopy 嵌入 Python）
│   ├── app/src/main/python/ # 复用 scroll_web.py（零改动）
│   ├── app/src/main/java/   # MainActivity + ServerService
│   └── README.md
├── server/                  # 手机端（Termux）
│   ├── scroll_web.py        # 核心：HTTP 服务 + 前端页面
│   ├── termux-service/run   # termux-services 服务脚本
│   ├── bashrc-snippet.sh    # 打开 Termux 自动启动
│   ├── start.sh             # 备选：tmux 启动
│   └── tools/               # SSH 部署工具（可选）
├── .github/workflows/       # GitHub Actions 自动编译 APK / exe
└── docs/
```

## 快速开始

### 手机端（方式一：APK，推荐）

从 [Releases](https://github.com/cymylive/xiaok-ad-helper/releases) 下载 `app-debug.apk` 直接安装，打开即用，**不需要 Termux**：

1. 手机装 `app-debug.apk`，打开「小K投屏」
2. App 会自动在后台启动 HTTP 服务（前台通知常驻，防省电杀）
3. 电脑浏览器打开 `http://<手机IP>:8080/c` 控制台
4. 粘贴文本 → 发送；点「开启全局鼠标控制」，按住左/右键控制滚动

协议与 Termux 版**完全一致**，电脑端 exe 无需改动。详见 [android/README.md](android/README.md)。

### 手机端（方式二：Termux）

```bash
# 1. 安装 Python 和服务管理
pkg install python termux-services

# 2. 部署服务文件
mkdir -p ~ && cp server/scroll_web.py ~/
mkdir -p $PREFIX/var/service/scroll
cp server/termux-service/run $PREFIX/var/service/scroll/run
chmod +x $PREFIX/var/service/scroll/run

# 3. 启用
export SVDIR=$PREFIX/var/service
sv-enable scroll && sv up scroll

# 4. （可选）打开 Termux 自动启动
cat server/bashrc-snippet.sh >> ~/.bashrc
```

### 电脑端（Windows）

**方式一：免安装 exe**（推荐）

1. 从 [Releases](../../releases) 下载 `xiaok-ad-helper.exe`
2. 放到任意目录，同目录建 `config.json`：
   ```json
   { "server": "http://<手机IP>:8080", "threshold_ms": 350 }
   ```
3. 双击运行，右下角托盘出现图标即成功

**方式二：源码运行**

```powershell
cd client
copy config.example.json config.json
# 编辑 config.json 填入手机 IP
python mouse_bridge.py
```

或用 `setup.ps1` 一键部署（自动检查 Python、测连通、可选开机自启）。

### 使用

1. 手机浏览器打开 `http://<手机IP>:8080/m`（显示页，保持前台）
2. 电脑浏览器打开 `http://<手机IP>:8080/c`（控制台）
3. 控制台粘贴文本 → 发送到手机，或载入预设
4. 点「开启全局鼠标控制」
5. **按住鼠标左键=手机上滑，按住右键=手机下滑**，松开即停
6. **左右键同时按住**=切换手机屏幕常亮（一次切换一次，再按一次恢复）

> 屏幕常亮开关在手机端 `/m` 页面顶部也有按钮，两边状态实时同步。
> 关掉常亮后手机若真息屏，WebView 轮询会暂停，需先手动点亮屏幕才能收到下次切换指令。

## 配置说明

`config.json`（电脑端）：

| 字段 | 默认 | 说明 |
|---|---|---|
| `server` | — | 手机服务地址，如 `http://192.168.1.100:8080` |
| `threshold_ms` | 350 | 按住多久算长按（毫秒），越小越灵敏 |

> 左右键「同时」按住超过 `threshold_ms` 才算双键手势，会切换屏幕常亮并暂停滚动。

控制台网页里可设：滚动速度（px/s）、设备 IP 白名单、文本预设。

## 接口

| 接口 | 方法 | 说明 |
|---|---|---|
| `/m` | GET | 手机显示页 |
| `/c` | GET | 电脑控制台 |
| `/state` | GET | 增量状态轮询（`?since=&tver=`） |
| `/text` | POST | 发送文本 `{text}` |
| `/config` | GET/POST | 滚动速度 `{speed}` |
| `/cmd` | POST | 滚动指令 `{action:start/stop, dir}` |
| `/bridge` | GET/POST | 全局钩子开关 `{on}` |
| `/keep` | GET/POST | 屏幕常亮 `{on}` 或 `{toggle:true}`（400ms 去抖） |
| `/allow` | GET/POST | 设备白名单 `{allow}` |
| `/presets` | GET/POST | 文本预设 `{name, text, delete}` |

## 托盘菜单

```
状态：已开启 / 已关闭
──────────────────
打开控制台
启用控制
停用控制
──────────────────
退出
```

## 常见问题

**长按没反应？**
检查：控制台里是否点了「开启全局鼠标控制」；托盘右键是否能选「启用控制」；手机服务是否在跑。

**单击也触发滚动？**
调大 `threshold_ms`，比如 500。

**拖拽文件被干扰？**
托盘右键 → 停用控制，用完再启用。

**换了电脑提示 403？**
新电脑 IP 变了，去手机控制台「允许的设备IP」更新白名单。

**提示服务端不可达？**
手机 Termux 没开 / 服务没起 / config.json 的 IP 不对 / 不在同一 WiFi。

## 环境要求

| 端 | 要求 |
|---|---|
| 电脑 | Windows 10/11，Python 3.8+（仅源码运行需要） |
| 手机 | Android，Termux + Python 3 |
| 网络 | 同一局域网 |

## 打包 exe

```powershell
pip install pyinstaller pillow
python client/make_icon.py
pyinstaller --onefile --windowed --name xiaok-ad-helper --icon client/icon.ico --add-data "client/icon.ico;." client/mouse_bridge.py
```

产物名必须用纯 ASCII：Windows 上 PyInstaller 处理中文 `--name` 会被截断（曾出现 `小K广告助手` 变成 `K.exe`）。

push 到 GitHub 后由 `.github/workflows/build-exe.yml` 在 `windows-latest` 上自动构建并发布到 latest Release。

## 维护者：同步到 GitHub

本机 Windows 的 git 推送会遇到 schannel TLS 故障（`SEC_E_INVALID_TOKEN` / `curl 35 server closed abruptly`），
而 GitHub REST API 走 Python urllib 正常。因此提供一个基于 API 的同步工具：

```bash
set GITHUB_TOKEN=ghp_xxx
E:\python\python-V\python3.14\python.exe -X utf8 sync.py status        # 查看差异
E:\python\python-V\python3.14\python.exe -X utf8 sync.py push "说明"    # 上传改动
E:\python\python-V\python3.14\python.exe -X utf8 sync.py pull          # 下载改动
```

纯标准库实现，无需第三方依赖。`client/config.json`（含真实手机 IP）自动跳过。

## License

MIT
