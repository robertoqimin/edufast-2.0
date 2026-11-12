# Regression checks with mocked Docker; no containers or real databases are used.
$ErrorActionPreference = 'Stop'
$repository = Split-Path $PSScriptRoot -Parent
$temporary = Join-Path ([IO.Path]::GetTempPath()) ('edufast-launcher-' + [guid]::NewGuid().ToString('N'))
$originalPort = $env:EDUFAST_MANUAL_PORT
$global:manualCalls = New-Object 'System.Collections.Generic.List[object]'
$global:rejectSchema = $false
function global:docker {
    $global:LASTEXITCODE = 0
    $global:manualCalls.Add(@($args))
    if ($global:rejectSchema -and $args -contains '-c') { $global:LASTEXITCODE = 1 }
}
function global:Invoke-WebRequest { return @{ StatusCode = 200 } }
function Assert-True($condition, $message) { if (-not $condition) { throw $message } }
try {
    New-Item -ItemType Directory -Path $temporary | Out-Null
    Copy-Item (Join-Path $repository 'iniciar-educafast.ps1') $temporary
    $launcher = Join-Path $temporary 'iniciar-educafast.ps1'
    $env:EDUFAST_MANUAL_PORT = '5999'
    & $launcher -PrepararBancoNovo -SemNavegador -Porta 5050
    $configPath = Join-Path $temporary '.ci-results/manual-restaurado/.env'
    $first = [IO.File]::ReadAllText($configPath)
    $lines = $first.Trim().Split("`n")
    Assert-True ($lines.Count -eq 7) 'Expected seven separate configuration values.'
    foreach ($name in @('SECRET_KEY', 'DB_PASSWORD', 'MYSQL_ROOT_PASSWORD')) {
        Assert-True ($first -match "(?m)^$name=[a-f0-9]{64}`r?$") "Invalid generated secret: $name"
    }
    Assert-True ($env:EDUFAST_MANUAL_PORT -eq '5999') 'Caller environment was not restored.'
    Assert-True ([bool]($global:manualCalls | Where-Object { $_ -contains 'prepare' })) 'Explicit schema preparation missing.'
    & $launcher -SemNavegador
    Assert-True ([IO.File]::ReadAllText($configPath) -ceq $first) 'Credentials were overwritten.'
    Assert-True ([bool]($global:manualCalls | Where-Object { $_ -contains 'ensure' })) 'Normal start must validate existing schema.'
    & $launcher -Acao CriarAdmin -SuperAdmin
    Assert-True ([bool]($global:manualCalls | Where-Object { $_ -contains '--super-admin' })) 'Super admin CLI not delegated.'
    & $launcher -Acao Parar
    Assert-True (($global:manualCalls | Where-Object { $_ -contains '-v' }).Count -eq 0) 'Stopping must preserve volumes.'
    $global:rejectSchema = $true
    $before = $global:manualCalls.Count
    $failed = $false
    try { & $launcher -PrepararBancoNovo -SemNavegador } catch { $failed = $true }
    Assert-True $failed 'Schema error must stop startup.'
    $after = @($global:manualCalls | Select-Object -Skip $before)
    Assert-True (($after | Where-Object { $_ -contains '--no-build' }).Count -eq 0) 'App started after schema failure.'
    Assert-True ($env:EDUFAST_MANUAL_PORT -eq '5999') 'Failure did not restore environment.'
    Write-Host 'OK: configuration, preservation, explicit schema, admin, stop and failure handling.'
} finally {
    [Environment]::SetEnvironmentVariable('EDUFAST_MANUAL_PORT', $originalPort, 'Process')
    Remove-Item Function:\docker -ErrorAction SilentlyContinue
    Remove-Item Function:\Invoke-WebRequest -ErrorAction SilentlyContinue
    # Only the verified per-test temporary directory is removed.
    $resolved = [IO.Path]::GetFullPath($temporary)
    $tempRoot = [IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\') + '\'
    if ($resolved.StartsWith($tempRoot, [StringComparison]::OrdinalIgnoreCase) -and
        ([IO.Path]::GetFileName($resolved)).StartsWith('edufast-launcher-')) {
        Remove-Item -LiteralPath $resolved -Recurse -Force
    }
}
