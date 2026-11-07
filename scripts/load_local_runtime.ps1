# Load optional machine-local paths. This file is never included in source archives.
$avtRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$avtLocal = Join-Path $avtRoot '.avt-local.ps1'
if (Test-Path -LiteralPath $avtLocal -PathType Leaf) {
    . $avtLocal
}
