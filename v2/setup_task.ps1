# Eagle到Jellyfin标签同步 - 计划任务设置脚本
# V2.1 自动化版本
# 
# 此脚本用于创建Windows计划任务，实现自动同步
# 新版本特性：自动检测标签删除，无需手动参数
# 
# 使用方法: 
#   以管理员身份运行PowerShell，然后执行:
#   .\setup_task.ps1
#

# 检查管理员权限
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "错误: 需要管理员权限来创建计划任务" -ForegroundColor Red
    Write-Host "请以管理员身份运行PowerShell" -ForegroundColor Yellow
    exit 1
}

# 获取当前脚本所在目录
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$parentDir = Split-Path -Parent $scriptDir
$mainScript = Join-Path $parentDir "main.py"

# 检查main.py是否存在
if (-not (Test-Path $mainScript)) {
    Write-Host "错误: 找不到main.py文件" -ForegroundColor Red
    Write-Host "路径: $mainScript" -ForegroundColor Yellow
    exit 1
}

# 获取Python路径
$pythonPath = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $pythonPath) {
    Write-Host "错误: 找不到Python" -ForegroundColor Red
    Write-Host "请确保Python已安装并添加到PATH环境变量" -ForegroundColor Yellow
    exit 1
}

Write-Host "找到Python: $pythonPath" -ForegroundColor Green
Write-Host "同步脚本: $mainScript" -ForegroundColor Green

# 任务配置
$taskName = "EagleToJellyfin_TagSync_V2"
$taskDescription = "自动同步Eagle标签到Jellyfin媒体库（V2.1自动化版）"

# 询问用户设置
Write-Host "`n请选择同步频率:" -ForegroundColor Cyan
Write-Host "1. 每天一次（凌晨3点） - 推荐"
Write-Host "2. 每4小时一次"
Write-Host "3. 每2小时一次"
Write-Host "4. 每小时一次"
Write-Host "5. 自定义"
$choice = Read-Host "请输入选项 (1-5, 默认1)"

# 设置触发器
switch ($choice) {
    "1" {
        # 每天凌晨3点 - 推荐
        $trigger = New-ScheduledTaskTrigger -Daily -At 3:00AM
        Write-Host "设置为: 每天凌晨3点执行（推荐）" -ForegroundColor Green
    }
    "2" {
        # 每4小时
        $trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Hours 4) -RepetitionDuration ([TimeSpan]::MaxValue)
        Write-Host "设置为: 每4小时执行一次" -ForegroundColor Green
    }
    "3" {
        # 每2小时
        $trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Hours 2) -RepetitionDuration ([TimeSpan]::MaxValue)
        Write-Host "设置为: 每2小时执行一次" -ForegroundColor Green
    }
    "4" {
        # 每小时
        $trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Hours 1) -RepetitionDuration ([TimeSpan]::MaxValue)
        Write-Host "设置为: 每小时执行一次" -ForegroundColor Green
    }
    "5" {
        # 自定义
        $hours = Read-Host "请输入执行间隔（小时）"
        if ($hours -match '^\d+$' -and [int]$hours -gt 0) {
            $trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Hours ([int]$hours)) -RepetitionDuration ([TimeSpan]::MaxValue)
            Write-Host "设置为: 每${hours}小时执行一次" -ForegroundColor Green
        } else {
            Write-Host "无效输入，使用默认设置: 每天凌晨3点" -ForegroundColor Yellow
            $trigger = New-ScheduledTaskTrigger -Daily -At 3:00AM
        }
    }
    default {
        Write-Host "无效选项，使用默认设置: 每天凌晨3点" -ForegroundColor Yellow
        $trigger = New-ScheduledTaskTrigger -Daily -At 3:00AM
    }
}

# 询问日志级别
Write-Host "`n请选择日志级别:" -ForegroundColor Cyan
Write-Host "1. WARNING - 只记录警告和错误（推荐日常使用）"
Write-Host "2. INFO - 记录详细信息"
Write-Host "3. DEBUG - 记录所有调试信息"
$logChoice = Read-Host "请输入选项 (1-3, 默认1)"

$logLevel = switch ($logChoice) {
    "2" { "INFO" }
    "3" { "DEBUG" }
    default { "WARNING" }
}
Write-Host "设置日志级别为: $logLevel" -ForegroundColor Green

# 创建任务动作
# 使用 pythonw.exe 而不是 python.exe 来静默运行（无窗口）
$pythonwPath = $pythonPath -replace 'python\.exe$', 'pythonw.exe'
if (-not (Test-Path $pythonwPath)) {
    Write-Host "警告: 找不到pythonw.exe，将使用python.exe（会有窗口弹出）" -ForegroundColor Yellow
    $pythonwPath = $pythonPath
} else {
    Write-Host "使用pythonw.exe进行静默运行（无窗口）" -ForegroundColor Green
}

$arguments = "`"$mainScript`" sync --log-level $logLevel"
$action = New-ScheduledTaskAction -Execute $pythonwPath -Argument $arguments -WorkingDirectory $parentDir

# 创建任务设置
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2) `
    -MultipleInstances IgnoreNew `
    -Hidden  # 隐藏任务运行时的窗口

# 创建任务主体（使用当前用户，后台运行）
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType S4U

# 删除已存在的同名任务
$existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existingTask) {
    Write-Host "`n发现已存在的任务，正在删除..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}

# 注册新任务
Write-Host "`n正在创建计划任务..." -ForegroundColor Cyan
try {
    Register-ScheduledTask `
        -TaskName $taskName `
        -Description $taskDescription `
        -Action $action `
        -Trigger $trigger `
        -Settings $settings `
        -Principal $principal `
        -Force | Out-Null
    
    Write-Host "`n✓ 计划任务创建成功!" -ForegroundColor Green
    Write-Host "`n任务详情:" -ForegroundColor Cyan
    Write-Host "  任务名称: $taskName"
    Write-Host "  执行命令: pythonw `"$mainScript`" sync --log-level $logLevel"
    Write-Host "  Python路径: $pythonwPath"
    Write-Host "  工作目录: $parentDir"
    Write-Host "  日志级别: $logLevel"
    Write-Host "  运行模式: 静默后台运行（无窗口弹出）" -ForegroundColor Green
    Write-Host "`n新版本特性:" -ForegroundColor Green
    Write-Host "  ✓ 自动检测标签删除"
    Write-Host "  ✓ 自动选择合适的刷新模式（ReplaceAllMetadata 或 标准模式）"
    Write-Host "  ✓ 无需手动指定参数"
    Write-Host "  ✓ 完全自动化运行"
    
    # 询问是否立即测试运行
    Write-Host "`n是否立即测试运行一次？(Y/N)" -ForegroundColor Yellow
    $testRun = Read-Host
    if ($testRun -eq 'Y' -or $testRun -eq 'y') {
        Write-Host "`n正在运行同步任务..." -ForegroundColor Cyan
        Start-ScheduledTask -TaskName $taskName
        Write-Host "任务已启动，请查看任务计划程序了解运行状态" -ForegroundColor Green
        $logFile = Join-Path $scriptDir 'sync_v2.log'
        Write-Host "日志文件: $logFile" -ForegroundColor Cyan
        
        # 等待几秒查看日志
        Write-Host "`n等待5秒后显示日志..."  -ForegroundColor Cyan
        Start-Sleep -Seconds 5
        
        if (Test-Path $logFile) {
            Write-Host "`n最新日志（最后30行）:" -ForegroundColor Cyan
            Write-Host "========================================" -ForegroundColor DarkGray
            Get-Content $logFile -Tail 30
            Write-Host "========================================" -ForegroundColor DarkGray
        }
    }
    
    Write-Host "`n提示:" -ForegroundColor Yellow
    Write-Host "  - 可在'任务计划程序'中查看和管理此任务"
    Write-Host "  - 任务路径: 任务计划程序库 → $taskName"
    Write-Host "  - 日志文件位于: $logFile"
    Write-Host "  - 要手动运行: Start-ScheduledTask -TaskName '$taskName'"
    Write-Host "  - 要删除任务: Unregister-ScheduledTask -TaskName '$taskName'"
    Write-Host "  - 要查看日志: Get-Content '$logFile' -Tail 50"
    
} catch {
    Write-Host "`n✗ 创建计划任务失败: $_" -ForegroundColor Red
    exit 1
}

Write-Host "`n按任意键退出..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
