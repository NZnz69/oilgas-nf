# NF 一键安装向导 v0.1.1（Windows PowerShell 5.1+）
# 用法：解压 NF 仓库后，在本目录运行  .\install.ps1
# 流程：环境检测 -> 部署 Skill -> 尝试注册 -> 生成 MCP 配置 -> 引擎自检
# 原则：资产来自本包；运行环境（Python/平台注册/账号）在本机构建；任何一步失败不中断，最后汇总。

$ErrorActionPreference = "Continue"
$RepoRoot = $PSScriptRoot
$SkillName = "oilgas-nf-expert"
$Results = @()

function Add-Step($name, $status, $detail) {
    $script:Results += [PSCustomObject]@{ Step = $name; Status = $status; Detail = $detail }
    $mark = "  "
    if ($status -eq "OK") { $mark = "[OK]  " }
    elseif ($status -eq "WARN") { $mark = "[WARN]" }
    elseif ($status -eq "FAIL") { $mark = "[FAIL]" }
    Write-Host ("{0} {1}: {2}" -f $mark, $name, $detail)
}

Write-Host "=============================================="
Write-Host " NF (油气储运智能辅助系统) 一键安装 v0.1.1"
Write-Host "=============================================="

# ---------- Step 0 环境检测 ----------
Write-Host "`n--- Step 0 环境检测 ---"
$py = Get-Command python -ErrorAction SilentlyContinue
$PythonCmd = "python"
if ($py) {
    $pyVer = (& $PythonCmd --version) 2>&1
    Add-Step "Python 检测" "OK" "$pyVer（PATH 中的 python）"
} else {
    # v0.1.1 新增：回退探测 TeleAgent Desktop 内置 Python 运行时（覆盖未单独安装 Python 的用户）
    $bundled = Join-Path $HOME ".local\share\TeleAgent\runtimes\python\python.exe"
    if (Test-Path $bundled) {
        $PythonCmd = $bundled
        $pyVer = (& $PythonCmd --version) 2>&1
        Add-Step "Python 检测" "OK" "$pyVer（TeleAgent 内置运行时：$bundled）"
    } else {
        Add-Step "Python 检测" "FAIL" "未找到 python。请安装 Python 3.10+（python.org，勾选 Add to PATH）或先安装 TeleAgent Desktop，再重跑本脚本"
    }
}

if ($env:TELEAGENT_CONFIG_DIR) {
    $SkillRoot = Join-Path $env:TELEAGENT_CONFIG_DIR "skills"
    Add-Step "TeleAgent 配置目录" "OK" $SkillRoot
} else {
    # v0.1.1 新增：自动探测多用户配置目录 users\*\skills（普通 PowerShell 窗口里环境变量通常未设置）
    $candidates = @()
    $usersRoot = Join-Path $HOME ".config\TeleAgent\users"
    if (Test-Path $usersRoot) {
        $candidates = @(Get-ChildItem $usersRoot -Directory -ErrorAction SilentlyContinue |
            ForEach-Object { Join-Path $_.FullName "skills" } |
            Where-Object { Test-Path $_ })
    }
    if ($candidates.Count -eq 1) {
        $SkillRoot = $candidates[0]
        Add-Step "TeleAgent 配置目录" "OK" "自动探测：$SkillRoot"
    } elseif ($candidates.Count -gt 1) {
        $SkillRoot = $candidates[0]
        Add-Step "TeleAgent 配置目录" "WARN" "发现多个用户配置目录，使用第一个：$SkillRoot"
    } else {
        $SkillRoot = Join-Path $HOME ".config\TeleAgent\skills"
        Add-Step "TeleAgent 配置目录" "WARN" "未探测到 TeleAgent 技能目录。若未安装 TeleAgent Desktop，请先安装并登录后重跑；若安装在非常规位置，请手动把 skill\oilgas-nf-expert 复制到你的技能目录"
    }
}

# ---------- Step 1 部署 Skill ----------
Write-Host "`n--- Step 1 部署 Skill ---"
$srcSkill = Join-Path $RepoRoot "skill\$SkillName"
$dstSkill = Join-Path $SkillRoot $SkillName
if (Test-Path $srcSkill) {
    if (-not (Test-Path $SkillRoot)) { New-Item -ItemType Directory -Path $SkillRoot -Force | Out-Null }
    if (Test-Path $dstSkill) {
        Add-Step "Skill 部署" "WARN" "目标已存在同名技能，跳过复制（如需更新请先手动删除：$dstSkill）"
    } else {
        Copy-Item -Path $srcSkill -Destination $dstSkill -Recurse
        Add-Step "Skill 部署" "OK" "已复制到 $dstSkill"
    }
} else {
    Add-Step "Skill 部署" "FAIL" "包内缺少 skill\$SkillName，包不完整"
}

# ---------- Step 2 尝试注册 Skill ----------
Write-Host "`n--- Step 2 注册 Skill ---"
$registrar = Join-Path $SkillRoot "skill-creator\scripts\add_skill_remote.py"
$skillMd = Join-Path $dstSkill "SKILL.md"
if ((Test-Path $registrar) -and (Test-Path $skillMd) -and $py) {
    $out = (& $PythonCmd $registrar $skillMd) 2>&1 | Out-String
    if ($out -match "success") {
        Add-Step "Skill 注册" "OK" "已通过平台注册接口注册"
    } else {
        Add-Step "Skill 注册" "WARN" "注册接口返回异常，通常重启桌面端后会自动加载技能目录；若未加载，请在 TeleAgent 中说「帮我注册 skill\$SkillName\SKILL.md」"
    }
} else {
    Add-Step "Skill 注册" "WARN" "未找到平台注册脚本（skill-creator 技能），请重启 TeleAgent Desktop；若技能未出现在列表，请在 TeleAgent 对话中让智能体注册 $skillMd"
}

# ---------- Step 3 生成 MCP 配置 ----------
Write-Host "`n--- Step 3 计算引擎（MCP）配置 ---"
$runPy = Join-Path $RepoRoot "engine\run.py"
if (Test-Path $runPy) {
    $json = @{
        mcpServers = @{
            "oilgas-calc" = @{
                command = $PythonCmd
                args    = @($runPy)
            }
        }
    } | ConvertTo-Json -Depth 5
    Write-Host "`n请复制以下 JSON，在 TeleAgent Desktop 中注册 MCP："
    Write-Host "  左下角头像 -> 工具设置 -> MCP 配置 -> 添加 -> 粘贴 -> 保存"
    Write-Host $json
    $jsonPath = Join-Path $RepoRoot "mcp-config.generated.json"
    $json | Out-File -FilePath $jsonPath -Encoding utf8
    Add-Step "MCP 配置" "OK" "已生成并打印（同时保存到 mcp-config.generated.json），请按上方指引粘贴到工具设置"
} else {
    Add-Step "MCP 配置" "FAIL" "包内缺少 engine\run.py，包不完整"
}

# ---------- Step 4 引擎依赖与自检 ----------
Write-Host "`n--- Step 4 引擎依赖与自检 ---"
if ($py) {
    $hasMcp = (& $PythonCmd -c "from mcp.server.mcpserver import MCPServer; print('yes')") 2>&1
    if ("$hasMcp" -match "yes") {
        Add-Step "MCP 依赖" "OK" "mcp SDK 已安装"
    } else {
        Write-Host "正在安装 mcp 依赖（需要网络，约 1-2 分钟）..."
        (& $PythonCmd -m pip install "mcp>=2.0.0" --quiet --disable-pip-version-check) 2>&1 | Out-Null
        $hasMcp2 = (& $PythonCmd -c "from mcp.server.mcpserver import MCPServer; print('yes')") 2>&1
        if ("$hasMcp2" -match "yes") {
            Add-Step "MCP 依赖" "OK" "已自动安装 mcp SDK"
        } else {
            Add-Step "MCP 依赖" "FAIL" "mcp SDK 安装失败，请手动执行：python -m pip install mcp"
        }
    }
    $selftest = Join-Path $RepoRoot "engine\selftest.py"
    if (Test-Path $selftest) {
        $out = (& $PythonCmd $selftest) 2>&1 | Out-String
        if ($LASTEXITCODE -eq 0 -and $out -match "FAIL=0") {
            Add-Step "引擎自检（12 项基准）" "OK" "全部通过：引擎在此机器上计算正确"
        } else {
            Add-Step "引擎自检（12 项基准）" "FAIL" "存在未通过项，请把 engine\selftest.py 输出发给维护者"
            Write-Host $out
        }
    }
} else {
    Add-Step "引擎自检" "WARN" "跳过（无 Python）"
}

# ---------- 汇总 ----------
Write-Host "`n=============================================="
Write-Host " 安装汇总"
Write-Host "=============================================="
$Results | Format-Table -AutoSize | Out-String | Write-Host
$fails = @($Results | Where-Object { $_.Status -eq "FAIL" }).Count
if ($fails -gt 0) {
    Write-Host "存在 $fails 个 FAIL 项，请按上方 Detail 处理后重跑 install.ps1"
    exit 1
} else {
    Write-Host "安装完成。最后一步（约 30 秒）："
    Write-Host " 1. 重启 TeleAgent Desktop（加载 Skill）"
    Write-Host " 2. 按 Step 3 打印的 JSON 在工具设置中注册 MCP"
    Write-Host " 3. 试一句话：「帮我算：流量100m3/h、内径300mm、长度50km、粗糙度0.05mm、密度850kg/m3、黏度20mPa.s 的沿程压降」"
    Write-Host " 4. 详细设计文档见 docs\ 目录（痛点与解决方案 / 实施路线图 / 分发部署方案）"
    Write-Host "首次使用会询问身份（学生/教师/运维/设计）。知识库当前为白盒空置，专业内容会如实回答「未收录」——请提供规范/教材文件灌入。"
}
