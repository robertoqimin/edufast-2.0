# Validação local — 26/10/2026

Ambiente: Windows com Docker Desktop, containers Linux, Python 3.12 na imagem e MySQL 8.4. Comando: `python .github/cicd/ci.py`.

| Verificação | Resultado |
| --- | --- |
| Contratos da aplicação em SQLite | 18 testes aprovados |
| Mesmos contratos em MySQL | 18 testes aprovados |
| Configuração, proveniência e cenários do deploy | 11 testes aprovados |
| Workflows GitHub Actions / Actionlint | Aprovado |
| Scripts Bash / ShellCheck e sintaxe | Aprovado |
| Imagem Gunicorn sem root | Construída e executada |
| App e banco sem portas publicadas | Configuração verificada |
| Configuração Caddy de produção | Validada |
| Comunicação proxy → app → MySQL | Exercitada com login e healthcheck |
| HTTPS com CA local confiável | Aprovado |
| Certificado sem CA confiável | Rejeitado conforme esperado |
| HSTS e cookie seguro | Verificados |
| Dump e restauração MySQL | Registro de prova restaurado |
| Backup/restauração de uploads | Arquivo de prova restaurado |
| Recriação do app | Upload preservado e healthcheck aprovado |
| Limpeza do CI | Containers e volumes do projeto descartável removidos |

As simulações de deploy executam o script Bash real com Docker e HTTPS substituídos por comandos controlados. Verificam sucesso, falha no download, retomada da imagem anterior após falha no backup, ausência de downgrade automático após falha ao iniciar e rejeição de uma resposta de saúde com release diferente.

Resultados detalhados locais: `.ci-results/summary.json`, `.ci-results/containers.log` e `ci-local.log`, ignorados no Git. O workflow repete a validação em Linux e preserva seus próprios artefatos; o resultado remoto deve ser conferido na aba Actions.

Não houve implantação em servidor externo nem emissão de certificado para um domínio real. SSH remoto, DNS, certificado público, recursos da hospedagem e recuperação no ambiente contratado exigem homologação posterior. Estes resultados não são uma auditoria completa da aplicação nem teste de carga.
