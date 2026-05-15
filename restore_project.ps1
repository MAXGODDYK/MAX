$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$partsDir = Join-Path -Path $root -ChildPath "project_zip_parts"
$zipPath = Join-Path -Path $root -ChildPath "tabachnaya-smes-project.zip"
$outDir = Join-Path -Path $root -ChildPath "project"

if (-not (Test-Path -LiteralPath $partsDir)) {
    throw "Не найдена папка с частями архива: $partsDir"
}

$parts = Get-ChildItem -LiteralPath $partsDir -Filter "project.zip.b64.part*" | Sort-Object Name
if ($parts.Count -eq 0) {
    throw "Не найдены части архива project.zip.b64.part*"
}

$base64 = New-Object System.Text.StringBuilder
foreach ($part in $parts) {
    [void]$base64.Append((Get-Content -LiteralPath $part.FullName -Raw -Encoding ASCII).Trim())
}

[System.IO.File]::WriteAllBytes($zipPath, [Convert]::FromBase64String($base64.ToString()))
New-Item -ItemType Directory -Path $outDir -Force | Out-Null
Expand-Archive -LiteralPath $zipPath -DestinationPath $outDir -Force

Write-Host "Готово. Проект распакован в: $outDir"
Write-Host "Для запуска открой: $outDir\run_app.bat"
