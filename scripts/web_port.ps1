# Resolve the local Tutor WebUI port (Extractor may already own 8765).
$raw = [Environment]::GetEnvironmentVariable('AVT_WEB_PORT')
if ([string]::IsNullOrWhiteSpace($raw)) { $raw = '8767' }
[int]$port = 0
if (-not [int]::TryParse($raw, [ref]$port) -or $port -lt 1024 -or $port -gt 65535) {
    throw 'AVT_WEB_PORT must be a decimal integer from 1024 to 65535.'
}
if ($port -in @(8766, 9880)) { throw 'AVT_WEB_PORT conflicts with ASR/TTS ports 8766 and 9880.' }
Write-Output $port
