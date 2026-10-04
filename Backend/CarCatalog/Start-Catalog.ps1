param([string]$ListenAddress='127.0.0.1',[int]$Port=8787,[string]$Python='python',[string]$Blender='C:\Program Files\Blender Foundation\Blender 4.5\blender.exe')
$ErrorActionPreference='Stop'
& $Python (Join-Path $PSScriptRoot 'server.py') --host $ListenAddress --port $Port --blender $Blender
