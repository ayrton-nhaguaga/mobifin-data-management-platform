$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $projectRoot '.env'
if (Test-Path -LiteralPath $envPath) { Write-Host '.env existente preservado.'; exit 0 }
function New-LocalSecret {
    $bytes = New-Object byte[] 32
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
    return [BitConverter]::ToString($bytes).Replace('-', '').ToLower()
}
$dbSecret = New-LocalSecret
$jwtSecret = New-LocalSecret
$demoSecret = New-LocalSecret
@("POSTGRES_PASSWORD=$dbSecret", "JWT_SECRET=$jwtSecret", "DEMO_PASSWORD=$demoSecret") | Set-Content -LiteralPath $envPath -Encoding ASCII
Write-Host 'Configuração local criada em .env (ignorada pelo Git). Consulte DEMO_PASSWORD para iniciar sessão.'
