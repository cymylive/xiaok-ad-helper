# 电脑端一键部署（右键 → 用 PowerShell 运行，或 powershell -ExecutionPolicy Bypass -File setup.ps1）
$ErrorActionPreference = "Stop"
$dir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $dir

Write-Host "=== 文本投屏 - 电脑端部署 ===" -ForegroundColor Cyan

# 1. 检查 Python
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) {
    Write-Host "[X] 未找到 python，请先安装 Python 3 并勾选 Add to PATH" -ForegroundColor Red
    Write-Host "    下载: https://www.python.org/downloads/" -ForegroundColor Yellow
    exit 1
}
Write-Host "[OK] Python: $($py.Source)" -ForegroundColor Green

# 2. 检查 config.json
if (-not (Test-Path "$dir\config.json")) {
    Write-Host "[!] 缺少 config.json，创建默认配置..." -ForegroundColor Yellow
    '{"server":"http://192.168.1.100:8080","threshold_ms":350}' | Out-File -Encoding utf8 "$dir\config.json"
}
$cfg = Get-Content "$dir\config.json" -Raw | ConvertFrom-Json
Write-Host "[OK] 目标手机: $($cfg.server)" -ForegroundColor Green

# 3. 测试连通性
Write-Host ""
Write-Host "测试连接手机..." -ForegroundColor Cyan
try {
    $r = Invoke-WebRequest -Uri "$($cfg.server)/bridge" -TimeoutSec 5 -UseBasicParsing
    Write-Host "[OK] 手机服务可达 ($($r.StatusCode))" -ForegroundColor Green
} catch {
    Write-Host "[!] 无法连接手机服务，请确认:" -ForegroundColor Yellow
    Write-Host "    1. 手机已打开 Termux 且服务已启动" -ForegroundColor Yellow
    Write-Host "    2. 手机和电脑在同一 WiFi" -ForegroundColor Yellow
    Write-Host "    3. config.json 里的 IP 正确" -ForegroundColor Yellow
}

# 4. 设置开机自启
$answer = Read-Host "是否设置开机自启? (y/n)"
if ($answer -eq "y") {
    $ws = New-Object -ComObject WScript.Shell
    $startup = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup"
    $lnk = $ws.CreateShortcut("$startup\小K广告助手.lnk")
    $lnk.TargetPath = (Get-Command python).Source
    $lnk.Arguments = '-X utf8 "' + $dir + '\mouse_bridge.py"'
    $lnk.WorkingDirectory = $dir
    $lnk.WindowStyle = 7
    $lnk.Description = "全局鼠标长按控制手机滚动"
    $lnk.Save()
    Write-Host "[OK] 已设置开机自启" -ForegroundColor Green
}

Write-Host ""
Write-Host "=== 部署完成 ===" -ForegroundColor Cyan
Write-Host "启动方式:"
Write-Host "  python launch_bridge.py     (后台启动)" -ForegroundColor Gray
Write-Host "  python mouse_bridge.py      (前台启动，看日志)" -ForegroundColor Gray
Write-Host ""
Write-Host "然后浏览器打开 $($cfg.server)/c 点『开启全局鼠标控制』"
