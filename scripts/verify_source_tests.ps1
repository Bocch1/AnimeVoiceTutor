$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$python = (& (Join-Path $PSScriptRoot 'resolve_runtime_python.ps1') -Role web | Select-Object -Last 1)
if (-not $python -or -not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw 'Web Python runtime missing. Run advanced\Setup AnimeVoiceTutor.cmd first.'
}

# Scope public-source regression checks to reviewed distribution tests only.
# This developer checkout may contain old backup tests and third-party engines.
# Those test suites must be run separately in their respective environments.
$releaseTests = @(
    'tests/test_browser_lifecycle_v086.py',
    'tests/test_character_packs_v012.py',
    'tests/test_current_application_contract.py',
    'tests/test_current_secret_greeting_cache.py',
    'tests/test_deepseek_fallback_v085.py',
    'tests/test_existing_asr_runtime_compat.py',
    'tests/test_first_run_setup_v013.py',
    'tests/test_first_run_windows_entrypoints_v013.py',
    'tests/test_voice_release_install_v013.py',
    'tests/test_first_run_pretrained_v013.py',
    'tests/test_local_asr_model_checker.py',
    'tests/test_product_v083.py',
    'tests/test_product_v084.py',
    'tests/test_public_distribution.py',
    'tests/test_public_source_contract.py',
    'tests/test_quick_setup_contract.py',
    'tests/test_public_source_builder.py',
    'tests/test_setup_cli_regression.py',
    'tests/test_source_distribution_smoke.py',
    'tests/test_v094.py',
    'tests/test_v095.py',
    'tests/test_v096.py',
    'tests/test_web_port_isolation_v0115.py'
)
$missingTests = @($releaseTests | Where-Object {
    -not (Test-Path -LiteralPath (Join-Path $root $_) -PathType Leaf)
})
if ($missingTests.Count -ne 0) {
    throw "Missing public regression tests: $($missingTests -join ', ')"
}

Push-Location -LiteralPath $root
try {
    & $python scripts/verify_public_source.py
    if ($LASTEXITCODE -ne 0) { throw 'Public source check failed.' }
    & $python -m pytest -q @releaseTests
    if ($LASTEXITCODE -ne 0) { throw 'Source regression tests failed.' }
    Write-Host 'Source verification passed. This does not verify GPU inference.'
} finally {
    Pop-Location
}
