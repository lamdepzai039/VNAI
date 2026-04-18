$WshShell = New-Object -ComObject WScript.Shell
$ShortcutPath = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\KICH_HOAT_AI.lnk"
$TargetPath = "c:\Users\TCOM\Documents\trae_projects\AI\KICH_HOAT_AI.vbs"
$WorkingDir = "c:\Users\TCOM\Documents\trae_projects\AI"

$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $TargetPath
$Shortcut.WorkingDirectory = $WorkingDir
$Shortcut.Save()

Write-Host "Startup shortcut created successfully at $ShortcutPath"
