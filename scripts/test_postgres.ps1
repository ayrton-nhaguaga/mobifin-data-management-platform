$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $projectRoot '.env'
$dbLine = Get-Content -LiteralPath $envPath | Where-Object { $_ -match '^POSTGRES_PASSWORD=' } | Select-Object -First 1
$testDbPassword = $dbLine.Substring('POSTGRES_PASSWORD='.Length)
if (-not $testDbPassword) { throw 'Configure POSTGRES_PASSWORD em .env' }
$env:TEST_DATABASE_URL = "postgresql+psycopg://mobifin:$testDbPassword@127.0.0.1:55432/mobifin_test?connect_timeout=5"
try {
    Push-Location (Join-Path $projectRoot 'backend')
    & (Join-Path $projectRoot '.venv/Scripts/python.exe') -m pytest -q
    $testExitCode = $LASTEXITCODE
} finally {
    Pop-Location
    Remove-Item Env:\TEST_DATABASE_URL -ErrorAction SilentlyContinue
}
exit $testExitCode
