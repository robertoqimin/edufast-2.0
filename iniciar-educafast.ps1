[CmdletBinding()]
param(
    [ValidateSet('Iniciar', 'Parar', 'Status', 'Logs', 'CriarAdmin')]
    [string]$Acao = 'Iniciar',
    [switch]$SemNavegador,
    [switch]$PrepararBancoNovo,
    [switch]$SuperAdmin,
    [ValidateSet('Atual', 'Restaurado')]
    [string]$Ambiente = 'Restaurado',
    [ValidateRange(1024, 65535)]
    [int]$Porta = 5050
)

$ErrorActionPreference = 'Stop'
$appDirectory = Join-Path $PSScriptRoot ('C' + [char]0x00f3 + 'digos')
$manualName = if ($Ambiente -eq 'Restaurado') { 'manual-restaurado' } else { 'manual' }
$manualProject = if ($Ambiente -eq 'Restaurado') { 'edufast-manual-restaurado' } else { 'edufast-manual' }
if ($Ambiente -eq 'Atual' -and -not $PSBoundParameters.ContainsKey('Porta')) { $Porta = 5000 }
$localDirectory = Join-Path $PSScriptRoot ('.ci-results/' + $manualName)
$envFile = Join-Path $localDirectory '.env'
$composeFile = Join-Path $appDirectory 'docker-compose.yml'
$overrideFile = Join-Path $PSScriptRoot 'scripts/compose.manual.yml'
if ($PrepararBancoNovo -and $Acao -ne 'Iniciar') { throw '-PrepararBancoNovo exige -Acao Iniciar.' }
if ($SuperAdmin -and $Acao -ne 'CriarAdmin') { throw '-SuperAdmin exige -Acao CriarAdmin.' }

function New-LocalSecret {
    $bytes = New-Object byte[] 32
    $random = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $random.GetBytes($bytes) } finally { $random.Dispose() }
    return ([BitConverter]::ToString($bytes)).Replace('-', '').ToLowerInvariant()
}

function New-EncryptionKey {
    $hex = New-LocalSecret
    $bytes = New-Object byte[] 32
    for ($index = 0; $index -lt 32; $index++) { $bytes[$index] = [Convert]::ToByte($hex.Substring($index * 2, 2), 16) }
    return ([Convert]::ToBase64String($bytes)).Replace('+', '-').Replace('/', '_')
}

function Invoke-ManualCompose {
    param([string[]]$DockerArguments)
    # Windows PowerShell 5.1 treats native progress on stderr as error records.
    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        & docker compose --project-name $manualProject --env-file $envFile -f $composeFile -f $overrideFile @DockerArguments
        $commandExit = $LASTEXITCODE
    } finally { $ErrorActionPreference = $previousPreference }
    if ($commandExit -ne 0) { throw "Docker Compose falhou (codigo $commandExit). Consulte -Acao Logs. Nenhum volume foi apagado." }
}
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw 'Instale e inicie o Docker Desktop antes de executar este script.'
}
$ErrorActionPreference = 'Continue'
try {
    & docker info --format '{{.ServerVersion}}' | Out-Null
    $dockerExit = $LASTEXITCODE
} finally { $ErrorActionPreference = 'Stop' }
if ($dockerExit -ne 0) { throw 'Docker indisponivel. Abra o Docker Desktop, aguarde iniciar e execute novamente.' }
if (-not (Test-Path -LiteralPath $envFile)) {
    if ($Acao -ne 'Iniciar') { throw 'Ambiente manual ainda nao preparado. Execute .\iniciar-educafast.ps1 -PrepararBancoNovo primeiro.' }
    New-Item -ItemType Directory -Path $localDirectory -Force | Out-Null
    $configuration = @(
        'SECRET_KEY=' + (New-LocalSecret)
        'DB_PASSWORD=' + (New-LocalSecret)
        'MYSQL_ROOT_PASSWORD=' + (New-LocalSecret)
        'DATA_ENCRYPTION_KEY=' + (New-EncryptionKey)
        'DB_NAME=edufast_manual'
        'DB_USER=edufast_manual'
        'DB_PORT=3306'
    ) -join "`n"
    # Never overwrite credentials, including on simultaneous launches.
    $stream = [System.IO.File]::Open($envFile, [System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::Write)
    try {
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($configuration + "`n")
        $stream.Write($bytes, 0, $bytes.Length)
    } finally { $stream.Dispose() }
    Write-Host "Configuracao local criada em .ci-results/$manualName/.env (ignorada pelo Git). Nao compartilhe esse arquivo."
}
$previousPort = [Environment]::GetEnvironmentVariable('EDUFAST_MANUAL_PORT', 'Process')
$env:EDUFAST_MANUAL_PORT = [string]$Porta
try {
    switch ($Acao) {
        'Iniciar' {
            Invoke-ManualCompose -DockerArguments @('config', '--quiet')
            Invoke-ManualCompose -DockerArguments @('build', 'app')
            Invoke-ManualCompose -DockerArguments @('up', '-d', '--wait', '--wait-timeout', '180', 'db')
            $schemaCommand = @'
import sys
from sqlalchemy import inspect
from app.database import Base, engine
from app import models
tables = set(inspect(engine).get_table_names())
if sys.argv[1] == 'prepare' or not tables:
    if tables:
        raise SystemExit('Banco ja contem tabelas. Nada alterado; inicie sem -PrepararBancoNovo. Migrations exigem revisao separada.')
    Base.metadata.create_all(engine)
    print('Esquema novo criado no banco isolado de teste manual.')
else:
    from config import Config
    from app.database import init_db
    Config.APP_ENV = 'production'
    init_db()
'@
            $mode = if ($PrepararBancoNovo) { 'prepare' } else { 'ensure' }
            Invoke-ManualCompose -DockerArguments @('run', '--rm', '--no-deps', '-T', '--entrypoint', 'python', 'app', '-c', $schemaCommand, $mode)
            Invoke-ManualCompose -DockerArguments @('run', '--rm', '--no-deps', '-T', '--entrypoint', 'python', 'app', 'manual_test_data.py')
            Invoke-ManualCompose -DockerArguments @('up', '-d', '--no-build', '--wait', '--wait-timeout', '180', 'app')
            $url = "http://localhost:$Porta"
            $ready = $false
            for ($attempt = 0; $attempt -lt 30; $attempt++) {
                try {
                    $health = Invoke-WebRequest -Uri "$url/healthz" -UseBasicParsing -TimeoutSec 3
                    if ($health.StatusCode -eq 200) { $ready = $true; break }
                } catch { }
                Start-Sleep -Seconds 2
            }
            if (-not $ready) { throw 'Aplicacao sem resposta saudavel. Confira .\iniciar-educafast.ps1 -Acao Logs.' }
            Write-Host "Aplicacao pronta: $url"
            Write-Host 'Contas locais: superadmin@teste.local, admin@teste.local, professor@teste.local, aluno@teste.local'
            Write-Host 'Senha inicial das contas novas: Teste-local-2026! (somente testes locais).'
            Write-Host 'Ambiente manual isolado. Parar nao apaga os dados.'
            if (-not $SemNavegador) { Start-Process $url }
        }
        'CriarAdmin' {
            $arguments = @('exec', 'app', 'flask', '--app', 'app:create_app()', 'create-admin')
            if ($SuperAdmin) { $arguments += '--super-admin' }
            Invoke-ManualCompose -DockerArguments $arguments
        }
        'Parar' { Invoke-ManualCompose -DockerArguments @('down') }
        'Status' { Invoke-ManualCompose -DockerArguments @('ps') }
        'Logs' { Invoke-ManualCompose -DockerArguments @('logs', '--tail', '100', 'app', 'db') }
    }
} finally {
    [Environment]::SetEnvironmentVariable('EDUFAST_MANUAL_PORT', $previousPort, 'Process')
}
