# 从本机把当前 main 同步到生产 /opt/g-snipers-overseas
# 原因：北京轻量访问 GitHub HTTPS 会卡住，服务器上不要 git pull origin
# 用法（本机仓库根目录）：
#   powershell -File deploy/sync-from-local.ps1
# 可选：-Rebuild  重新构建镜像

param(
    [switch]$Rebuild
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$branch = (git rev-parse --abbrev-ref HEAD).Trim()
if ($branch -ne "main") {
    throw "只从 main 发版。当前分支是 $branch"
}

git status -sb
$bundle = Join-Path $env:TEMP "g-snipers-main.bundle"
git bundle create $bundle main
scp -o BatchMode=yes $bundle g-snipers-server:/tmp/g-snipers-main.bundle

$compose = if ($Rebuild) { "docker compose up -d --build" } else { "docker compose up -d" }
$remote = @(
    "set -e"
    "cd /opt/g-snipers-overseas"
    "git fetch /tmp/g-snipers-main.bundle main"
    "git checkout -f -B main FETCH_HEAD"
    "git update-ref refs/remotes/origin/main HEAD"
    "git log -1 --format='%H %s'"
    "git status -sb"
    "test -f .env"
    $compose
    "docker compose ps"
) -join "; "

ssh -o BatchMode=yes g-snipers-server $remote
