[CmdletBinding()]
param(
    [ValidateSet('Iniciar', 'Parar', 'Status')]
    [string]$Acao = 'Iniciar',
    [switch]$SemNavegador
)

$entryScript = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../SamusChat/Educafast/iniciar-educafast.ps1'))
if (-not (Test-Path -LiteralPath $entryScript)) {
    $entryScript = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../SamusChat/Projeto-Educa-Fast/iniciar-educafast.ps1'))
}
if (-not (Test-Path -LiteralPath $entryScript)) {
    Write-Error 'Não encontrei o projeto em SamusChat/Educafast nem no caminho anterior.'
    exit 1
}
& $entryScript @PSBoundParameters
exit $LASTEXITCODE
