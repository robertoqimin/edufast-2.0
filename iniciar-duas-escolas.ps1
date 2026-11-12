[CmdletBinding()]
param([switch]$SemNavegador, [switch]$SomenteAbrir)
$ErrorActionPreference = 'Stop'
if (-not $SomenteAbrir) {
    & node (Join-Path $PSScriptRoot 'infra/demo.cjs') start
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao iniciar escolas; nenhum dado foi apagado.' }
}
foreach ($port in @(5081, 5082)) {
    $url = "http://127.0.0.1:$port"
    $health = Invoke-WebRequest -Uri "$url/healthz" -UseBasicParsing -TimeoutSec 10
    if ($health.StatusCode -ne 200) { throw "Escola na porta $port indisponivel." }
    Write-Host "Escola: $url"
    if (-not $SemNavegador) { Start-Process -FilePath $url }
}
Write-Host 'Administradores: admin@teste01.local e admin@teste02.local'
Write-Host 'Senha inicial de demonstracao: Teste-escolas-2026!'
Write-Host 'Use o navegador externo. A previa do VS Code pode bloquear a sessao.'
