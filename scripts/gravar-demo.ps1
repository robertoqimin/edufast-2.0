[CmdletBinding()]
param(
    # 1 = ritmo padrao (cerca de 15 min ou mais); 1.5 = mais lento.
    [ValidateRange(0.3, 4)]
    [double]$Ritmo = 1,
    # Pula a confirmacao (uso por quem ja sabe que a escola de gravacao sera apagada).
    [switch]$SemConfirmar
)
# Demonstracao automatica para gravar a tela. Apaga e recria SOMENTE a escola de gravacao
# (projeto edufast-gravacao, porta 5070) e reinicia o painel Supremo de demonstracao.
# O ambiente manual (5050) e os demais bancos nao sao tocados.
# Docker escreve avisos no stderr; no PowerShell 5.1 isso nao pode virar erro fatal.
# Cada comando e conferido pelo codigo de saida.
$ErrorActionPreference = 'Continue'
function Confirm-Exit([string]$etapa) { if ($LASTEXITCODE -ne 0) { throw "Falha em: $etapa (codigo $LASTEXITCODE)." } }
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

& docker info --format '{{.ServerVersion}}' 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Docker indisponivel. Abra o Docker Desktop, aguarde iniciar e execute novamente.' }

if (-not $SemConfirmar) {
    $resposta = Read-Host 'Isto apaga a escola de gravacao (porta 5070) e recomeca do zero. Continuar? (s/N)'
    if ($resposta -notin @('s', 'S', 'sim', 'SIM')) { Write-Host 'Nada foi alterado.'; return }
}

$envFile = Join-Path $root '.ci-results/gravacao/.env'
if (Test-Path $envFile) {
    & docker compose --project-name edufast-gravacao --env-file $envFile -f api/docker-compose.yml -f scripts/compose.manual.yml down -v 2>&1 | Out-Null
    Confirm-Exit 'apagar a escola de gravacao'
}
powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root 'iniciar-educafast.ps1') -Ambiente Gravacao -PrepararBancoNovo -SemNavegador 2>&1 | Select-String 'Aplicacao pronta'
$saude = try { (Invoke-WebRequest -Uri 'http://localhost:5070/healthz' -UseBasicParsing -TimeoutSec 10).StatusCode } catch { 0 }
if ($saude -ne 200) { throw 'A escola de gravacao nao respondeu em http://localhost:5070.' }
& node infra/platform-demo.cjs stop 2>&1 | Out-Null
& node infra/platform-demo.cjs start 2>&1 | Select-String 'DEMONSTRACAO'
Confirm-Exit 'iniciar o painel Supremo'

Write-Host ''
Write-Host 'Tudo pronto. COMECE A GRAVAR A TELA AGORA.' -ForegroundColor Cyan
for ($i = 10; $i -gt 0; $i--) { Write-Host "Iniciando em $i..."; Start-Sleep -Seconds 1 }
& node scripts/demo_video.cjs $Ritmo
if ($LASTEXITCODE -ne 0) { throw 'A demonstracao foi interrompida. Veja a mensagem acima.' }
