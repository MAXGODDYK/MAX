$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$appDir = Get-ChildItem -LiteralPath $root -Directory |
    Where-Object { Test-Path -LiteralPath (Join-Path -Path $_.FullName -ChildPath "app.py") } |
    Sort-Object Name |
    Select-Object -First 1

if (-not $appDir) {
    throw "app.py was not found in a project subfolder: $root"
}

$appDir = $appDir.FullName
$appPath = Join-Path -Path $appDir -ChildPath "app.py"

function Get-WorkingPython {
    $pyCommand = Get-Command py -ErrorAction SilentlyContinue
    if ($pyCommand) {
        $launcherOutput = & $pyCommand.Source -0p 2>$null
        foreach ($line in $launcherOutput) {
            if ($line -match "([A-Za-z]:\\.*\\python\.exe)$") {
                return $Matches[1]
            }
        }
    }

    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCommand) {
        $testOutput = & $pythonCommand.Source -c "import sys; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $testOutput) {
            return $testOutput[0]
        }
    }

    throw "Working Python was not found. Install Python 3.11+ or check the py command."
}

$pythonExe = Get-WorkingPython
$pythonwExe = Join-Path -Path (Split-Path -Parent $pythonExe) -ChildPath "pythonw.exe"
if (-not (Test-Path -LiteralPath $pythonwExe)) {
    $pythonwExe = $pythonExe
}

$desktop = [Environment]::GetFolderPath("Desktop")
function Get-Utf8Text([string]$base64) {
    return [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($base64))
}

$shortcutName = Get-Utf8Text "0J/QvtC00LHQvtGAINC40L3Qs9GA0LXQtNC40LXQvdGC0L7QsiDQuCDQutCw0LvRjNC60YPQu9GP0YLQvtGAINGB0LzQtdGB0LgubG5r"
$description = Get-Utf8Text "0JfQsNC/0YPRgdC6INC/0YDQuNC70L7QttC10L3QuNGPINC/0L7QtNCx0L7RgNCwINC40L3Qs9GA0LXQtNC40LXQvdGC0L7QsiDQuCDQutCw0LvRjNC60YPQu9GP0YLQvtGA0LAg0YHQvNC10YHQuA=="
$shortcutPath = Join-Path -Path $desktop -ChildPath $shortcutName

$wsh = New-Object -ComObject WScript.Shell
$shortcut = $wsh.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $pythonwExe
$shortcut.Arguments = ('"{0}"' -f $appPath)
$shortcut.WorkingDirectory = $appDir
$shortcut.Description = $description
$shortcut.IconLocation = "$pythonwExe,0"
$shortcut.Save()

Write-Host "Shortcut created: $shortcutPath"
