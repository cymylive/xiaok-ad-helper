# 小K投屏 · Android 版

电脑端 exe + 手机 APK，不需要 Termux，装完即用，效果与 Termux 版完全一致。

## 使用

1. 下载 `app-debug.apk`（见本仓库 Releases 或 Actions Artifacts）
2. 手机安装后打开「小K投屏」，应用会自动在后台启动 HTTP 服务（前台通知常驻）
3. 手机浏览器/应用内 WebView 显示 `/m` 页面
4. 电脑端打开浏览器 `http://<手机IP>:8080/c` 控制台，粘贴文本 → 发送
5. 点「开启全局鼠标控制」，按住鼠标左键=手机上滑，右键=手机下滑

## 与 Termux 版的差异

| 项 | Termux 版 | APK 版 |
|---|---|---|
| 安装 | 需装 Termux + Python + 部署脚本 | 直接装 APK |
| 启动 | 手动/开机自动 | 前台服务常驻，随 app 启动 |
| 网络权限 | 系统级 | Android 清单内声明 |
| 预设存储 | `~/scroll_presets.json` | app 私有目录（`filesDir`） |
| 协议 | 与电脑端 exe 完全一致 | **完全一致** |

## 构建

本仓库已配置 GitHub Actions，push 到 `main` 分支且改动 `android/` 目录时自动编译 APK，
产物在 Actions → 对应 run → Artifacts 下载；打 tag 会自动发布到 Release。

### 本地构建（需要 Android SDK + JDK 17）

```bash
cd android
gradle wrapper --gradle-version 8.5
./gradlew assembleDebug
# 产物: app/build/outputs/apk/debug/app-debug.apk
```

## 技术栈

- **Kotlin + AndroidX**：MainActivity 承载 WebView，ServerService 前台服务
- **Chaquopy 15.0.1**：把 CPython 3.11 嵌入 APK，直接跑现有 `scroll_web.py`（零依赖标准库）
- **前台服务**：Android 8+ 必须前台化，避免省电策略杀后台
- **明文 HTTP 允许**：`network_security_config.xml` 放开局域网 http 访问
