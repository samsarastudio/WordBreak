param([Parameter(Mandatory=$true)][string]$RequestPath)
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.IO.Compression.FileSystem
$job=Get-Content -LiteralPath $RequestPath -Raw | ConvertFrom-Json
$target=[IO.Path]::GetFullPath($job.target).TrimEnd('\')
$parent=[IO.Path]::GetDirectoryName($target)
$stage=Join-Path $parent ('.worldbreak-stage-'+[guid]::NewGuid().ToString('N'))
$backup=$target+'.previous-'+(Get-Date -Format 'yyyyMMddHHmmss')
$log=Join-Path ([IO.Path]::GetDirectoryName([IO.Path]::GetFullPath($RequestPath))) 'install.log'
$moved=$false
try {
 if($target -eq [IO.Path]::GetPathRoot($target).TrimEnd('\') -or -not (Test-Path -LiteralPath (Join-Path $target 'WorldBreakRush.exe'))){throw 'Not a game installation directory'}
 if((Get-FileHash -LiteralPath $job.archive -Algorithm SHA256).Hash.ToLowerInvariant() -ne $job.sha256){throw 'Update checksum mismatch'}
 $zip=[IO.Compression.ZipFile]::OpenRead($job.archive)
 try {
  if($zip.Entries.Count -gt 20000){throw 'Too many files'}
  [long]$total=0
  foreach($entry in $zip.Entries){
   $total+=$entry.Length
   $name=$entry.FullName.Replace('/','\')
   $path=[IO.Path]::GetFullPath((Join-Path $stage $name))
   if($total -gt 4294967296 -or $name.Contains(':') -or [IO.Path]::IsPathRooted($name) -or -not $path.StartsWith($stage+'\',[StringComparison]::OrdinalIgnoreCase) -or (($entry.ExternalAttributes -shr 16) -band 61440) -eq 40960){throw 'Unsafe update archive'}
  }
  [IO.Directory]::CreateDirectory($stage) | Out-Null
  foreach($entry in $zip.Entries){
   $path=[IO.Path]::GetFullPath((Join-Path $stage $entry.FullName))
   if($entry.FullName.EndsWith('/')){[IO.Directory]::CreateDirectory($path) | Out-Null;continue}
   [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($path)) | Out-Null
   [IO.Compression.ZipFileExtensions]::ExtractToFile($entry,$path,$false)
  }
 } finally {$zip.Dispose()}
 foreach($required in @('WorldBreakRush.exe','UnityPlayer.dll','WorldBreakRush_Data/globalgamemanagers','WorldBreakRush_Data/StreamingAssets/ApplyUpdate.ps1')){if(-not(Test-Path -LiteralPath (Join-Path $stage $required))){throw 'Incomplete game update'}}
 $running=Get-Process -Id $job.pid -ErrorAction SilentlyContinue
 if($running){if($running.Path -ne (Join-Path $target 'WorldBreakRush.exe')){throw 'Process identity changed'};if(-not $running.WaitForExit(60000)){throw 'Game is still running'}}
 # Both destinations are checked sibling paths; never overwrite an unknown backup.
 if([IO.Path]::GetDirectoryName($stage) -ne $parent -or [IO.Path]::GetDirectoryName($backup) -ne $parent -or (Test-Path -LiteralPath $backup)){throw 'Unsafe replacement paths'}
 Move-Item -LiteralPath $target -Destination $backup
 $moved=$true
 Move-Item -LiteralPath $stage -Destination $target
 'Update installed. Previous game retained at '+$backup | Set-Content -LiteralPath $log
 if($job.restart){Start-Process -FilePath (Join-Path $target 'WorldBreakRush.exe') -WorkingDirectory $target -WindowStyle Normal}
} catch {
 if($moved -and -not(Test-Path -LiteralPath $target) -and (Test-Path -LiteralPath $backup)){Move-Item -LiteralPath $backup -Destination $target}
 ('Update deferred; original game retained: '+$_.Exception.Message) | Set-Content -LiteralPath $log
 exit 1
}
