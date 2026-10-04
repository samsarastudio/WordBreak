param([string]$Python='', [string]$Blender='C:\Program Files\Blender Foundation\Blender 4.5\blender.exe')
$ErrorActionPreference='Stop'
$projectRoot=Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
try { $running=(Invoke-RestMethod 'http://127.0.0.1:8787/health' -TimeoutSec 2).ok } catch { $running=$false }
if(-not $running){
 if(-not $Python){
  $bundled=Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
  if(Test-Path -LiteralPath $bundled){$Python=$bundled}else{$Python=(Get-Command python -ErrorAction Stop).Source}
 }
 if(-not (Test-Path -LiteralPath $Blender)){throw 'Install Blender or pass -Blender with its executable path.'}
 New-Item -ItemType Directory -Force -Path (Join-Path $projectRoot 'Logs') | Out-Null
 $arguments='"{0}" --host 0.0.0.0 --blender "{1}"' -f (Join-Path $PSScriptRoot 'server.py'),$Blender
 $service=Start-Process -FilePath $Python -ArgumentList $arguments -WorkingDirectory $projectRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $projectRoot 'Logs/car-catalog-server.log') -RedirectStandardError (Join-Path $projectRoot 'Logs/car-catalog-server-error.log') -PassThru
 $service.Id | Set-Content (Join-Path $projectRoot 'Logs/car-catalog-server.pid')
 for($attempt=0;$attempt -lt 20;$attempt++){try{Invoke-RestMethod 'http://127.0.0.1:8787/health' -TimeoutSec 1 | Out-Null;break}catch{Start-Sleep -Milliseconds 250}}
}
Write-Host ('Admin token: open '+(Join-Path $PSScriptRoot 'data/admin-token.txt'))
Start-Process 'http://127.0.0.1:8787/admin'
