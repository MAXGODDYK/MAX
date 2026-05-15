$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$partsDir = Join-Path -Path $root -ChildPath "project_zip_parts"
$zipPath = Join-Path -Path $root -ChildPath "tabachnaya-smes-project.zip"
$outDir = Join-Path -Path $root -ChildPath "project"
$expectedBase64Length = 50444

if (-not (Test-Path -LiteralPath $partsDir)) {
    throw "Archive parts folder was not found: $partsDir"
}

$parts = Get-ChildItem -LiteralPath $partsDir -Filter "project.zip.b64.part*" | Sort-Object Name
if ($parts.Count -eq 0) {
    throw "Archive parts project.zip.b64.part* were not found."
}

$base64 = New-Object System.Text.StringBuilder
foreach ($part in $parts) {
    $text = (Get-Content -LiteralPath $part.FullName -Raw -Encoding ASCII).Trim()

    # Repair two known transport truncations from the GitHub connector upload.
    if ($part.Name -eq "project.zip.b64.part02" -and $text.Length -eq 6999) {
        $text = $text.Insert(2583, "d")
    }
    if ($part.Name -eq "project.zip.b64.part04" -and $text.Length -eq 6927) {
        $text += "8kqXQ7qP6tQ4dMUV9/LGl9NG+09FBJRIdSowOpyODhZcpPmm+WvG5pTwNRYdHB6J96dGkkmRF"
    }

    [void]$base64.Append($text)
}

if ($base64.Length -ne $expectedBase64Length) {
    throw "Wrong Base64 archive size: $($base64.Length), expected $expectedBase64Length"
}

[System.IO.File]::WriteAllBytes($zipPath, [Convert]::FromBase64String($base64.ToString()))
New-Item -ItemType Directory -Path $outDir -Force | Out-Null
Expand-Archive -LiteralPath $zipPath -DestinationPath $outDir -Force

Write-Host "Done. Project restored to: $outDir"
Write-Host "Run the app with: $outDir\run_app.bat"
