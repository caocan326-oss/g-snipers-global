# Pull the newest host dump off production onto this machine.
# Destination stays outside the git repo (sibling of the clone).
$ErrorActionPreference = "Stop"
$repoRoot = Split-Path $PSScriptRoot -Parent
$dest = Join-Path (Split-Path $repoRoot -Parent) "g-snipers-db-offsite"
New-Item -ItemType Directory -Force -Path $dest | Out-Null
$latest = ssh -o BatchMode=yes g-snipers-server "ls -1t /opt/g-snipers-db-exports/gsnipers-db-*.dump 2>/dev/null | head -1"
if (-not $latest) {
    throw "服务器上还没有 dump。先在生产跑 deploy/backup-postgres.sh。"
}
$latest = $latest.Trim()
$name = Split-Path $latest -Leaf
Write-Host "pulling $latest"
scp -o BatchMode=yes "g-snipers-server:${latest}" (Join-Path $dest $name)
Get-Item (Join-Path $dest $name) | Format-List FullName, Length, LastWriteTime
