Set WshShell = CreateObject("WScript.Shell")
basedir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
python_path = chr(34) & basedir & "\.venv\Scripts\python.exe" & chr(34)
script_path = chr(34) & basedir & "\run_background.py" & chr(34)
WshShell.Run python_path & " " & script_path, 0
Set WshShell = Nothing
