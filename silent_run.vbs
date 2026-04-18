Set WshShell = CreateObject("WScript.Shell")
strPath = WScript.Arguments(0)
WshShell.Run chr(34) & strPath & chr(34), 0
Set WshShell = Nothing
