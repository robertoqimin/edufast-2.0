[CmdletBinding()]
param(
    [ValidateSet('Iniciar', 'Parar', 'Status')]
    [string]$Acao = 'Iniciar',
    [switch]$SemNavegador
)

$ErrorActionPreference = 'Stop'
$appDirectory = Join-Path $PSScriptRoot 'Códigos'
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw 'Instale e inicie o Docker Desktop antes de executar este script.'
}
if ($Acao -eq 'Iniciar' -and -not (Test-Path -LiteralPath (Join-Path $appDirectory '.env'))) {
    throw 'Copie Códigos/.env.example para Códigos/.env e configure as senhas. Consulte o README.'
}
Push-Location -LiteralPath $appDirectory
try {
    switch ($Acao) {
        'Iniciar' { & docker compose up -d --build }
        'Parar'   { & docker compose down }
        'Status'  { & docker compose ps }
    }
    $result = $LASTEXITCODE
    if ($result -eq 0 -and $Acao -eq 'Iniciar') {
        Write-Host 'Aplicação: http://localhost:5000 (acompanhe a inicialização com docker compose logs).'
        if (-not $SemNavegador) { Start-Process 'http://localhost:5000' }
    }
} finally {
    Pop-Location
}
exit $result
