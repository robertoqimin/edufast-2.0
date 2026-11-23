# Diagnóstico da versão atual — 05/11/2026

## Identificação e método

- Base: commit `b6d952b1aedd99aa8e42065f027b1df56bdabf13`.
- Diretório inicialmente sem alterações; esta avaliação acrescenta testes em `test_runtime_limits.py` e este relatório. Os resultados descrevem a base com essas alterações locais, não um novo commit publicado.
- Ambiente: Windows, Docker Desktop 4.70.0 / Engine 29.4.0, Compose 5.1.2. Aplicação em Python 3.12 no container; executor local Python 3.14.3; Node 22.16.0.
- Projeto descartável: `edufast-ci-80d27de000`; imagem `edufast-ci-80d27de000:tested`.
- Nenhuma migration executada. Os testes recriam exclusivamente esquemas descartáveis a partir dos modelos; isso não valida atualização de um banco legado.
- Método: requisitos observáveis → testes por camada → execução reproduzível → evidências e limitações. Referências conceituais: [SWEBOK — requisitos](https://swebokwiki.org/Chapter_1%3A_Software_Requirements) e [testes](https://swebokwiki.org/Chapter_4%3A_Software_Testing).

## Mapa dos cenários e evidências

| Área | Evidência executável | Comportamento verificado |
| --- | --- | --- |
| Regras e entradas | `test_admin_characterization.py`, `test_runtime_limits.py` | Validação de campos, limites inclusivos, padrão e configuração inválida |
| Login e permissões | `test_application.py`, `test_approvals_security.py` | Login real, senha inválida, JWT adulterado, sessão, revogação e restrições por perfil |
| Cadastros e turmas | `test_application.py`, `test_concurrency.py` | Persistência, duplicidades, vínculos e versões conflitantes |
| Transações | `test_concurrency.py`, `test_approvals_security.py` | Reversão de falha documental, efeitos de aprovação e preservação de estado |
| Notas e atividades | `test_approvals_security.py`, coleção Postman | Proposta docente, aprovação administrativa e efeito persistido |
| Arquivos | `test_concurrency.py`, `test_approvals_security.py`, coleção Postman | Propriedade, download autorizado, repetição e arquivos físicos |
| Fluxo administrativo/secretaria | Coleção Postman, perfil atual `admin` | Alterar cadastros, solicitar documentos, publicar comunicado e aprovar propostas |
| Fluxo professor | Coleção Postman, login real | Propor nota e alteração, atividade e resposta documental, com aprovação |
| Fluxo aluno | Coleção Postman, login real | Responder solicitação documental e tratar repetição |
| Operação | `ci.py` | Imagem, HTTPS, saúde, cookie, backup/restauração e persistência de uploads |

As camadas se sobrepõem: um teste de API pode verificar banco e transação. Os totais não representam requisitos distintos nem percentual de cobertura.

## Resultados

| Execução | Resultado |
| --- | --- |
| Regressão SQLite | 101 descobertos: 86 aprovados, 15 ignorados por exigirem concorrência MySQL; sem falhas |
| Regressão MySQL | 101 testes aprovados, sem ignorados ou falhas, em 338,582 s |
| Verificações operacionais | Aprovadas: imagem, 11 testes de bloqueios/deploy simulado, HTTPS, CA, HSTS, cookie seguro, login, dump/restauração MySQL e uploads após recriação do app |
| Limites, versão final do arquivo | 5 testes aprovados em Python 3.12 / SQLite |
| Fluxo HTTP Postman/Newman 6.2.1 | 57 requisições, 65 asserções, nenhuma falha; conferência final dos registros e arquivos aprovada |
| Caracterização do executor | 7 testes aprovados |
| Proteção de submissão JavaScript | 4 testes aprovados |
| Protocolo estático de design | Aprovado; não equivale à inspeção visual |

O fluxo HTTP complementar utilizou Python 3.14.3 em ambiente virtual próprio, SQLite e servidor temporários. A equivalência com o runtime Linux de produção é limitada; a regressão principal utiliza Python 3.12 no container.

Em limites foram verificados: padrão quando a variável não existe; extremos 1 e 32 aceitos; valores fora da faixa, vazio, decimal e texto rejeitados; pool esgotado com 503, `Retry-After: 5` e `Cache-Control: no-store`, seguido de recuperação para 200; corpo com 1024 bytes aceito, 1025 rejeitado com 413 sem atingir o efeito posterior à leitura, seguido de nova requisição válida. O caso do pool usa QueuePool SQLite isolado inclusive na suíte MySQL; não mede saturação de conexões do servidor MySQL. O limite de corpo não é um teste de limitação da taxa de requisições.

Os dois testes novos de configuração passaram na regressão SQLite. A asserção adicional de ausência de processamento e recuperação após 413 foi acrescentada durante a execução principal e confirmada separadamente na execução final dos cinco testes; não se deve atribuí-la retroativamente à primeira rodada SQLite.

## Reprodução e artefatos locais

```powershell
$env:GITHUB_SHA = git rev-parse HEAD
py .github/cicd/ci.py
py .github/cicd/test_ci_characterization.py
py Codigos/tests/verificar_protocolo_design.py
node --test .github/cicd/test_submission.cjs
& ./.ci-results/diagnostico-2026-11-05/venv/Scripts/python.exe .github/cicd/run_postman.py --newman .ci-results/diagnostico-2026-11-05/tools/node_modules/newman/bin/newman.js
```

O comando do fluxo pressupõe dependências do aplicativo instaladas no ambiente virtual e Newman 6.2.1 na pasta indicada. Esses auxiliares estão em `.ci-results`, ignorado pelo Git. Logs, dumps, certificados e relatórios brutos ficam locais e não devem ser versionados.

- Log principal: `.ci-results/diagnostico-2026-11-05/ci.log`.
- Resumo operacional: `.ci-results/summary.json`.
- Fluxo HTTP: `.ci-results/diagnostico-2026-11-05/http.log` e `.ci-results/mutations/postman.json`.
- Testes finais de limites: `.ci-results/diagnostico-2026-11-05/runtime-final.log`.
- Identificação e hash SHA-256 do teste final: `.ci-results/diagnostico-2026-11-05/metadata.json`; alteração testada em `tests.patch`.

## Pendências e limites da conclusão

1. Inspeção em navegador desktop/mobile e aceitação com usuários não foram executadas. Os fluxos comprovam comportamento HTTP, não usabilidade, layout ou execução integral do JavaScript no navegador.
2. O fluxo de secretaria usa o perfil administrativo existente; não demonstra um novo papel institucional de secretaria.
3. O inventário encontrou rotas adicionais de avaliações, publicação, boletim e reconciliação em `academico_routes.py`. A suíte executada não demonstra cobertura completa desses caminhos; a aprovação dos testes não homologa integralmente esse módulo.
4. Isolamento entre escolas, testes futuros TDD, carga, migração de legado e implantação remota não integram esta evidência.
5. Há avisos de depreciação (`datetime.utcnow`), recurso não fechado (`ResourceWarning`) e formatação do Caddyfile. Registrar como investigação/manutenção; não foram falhas de asserção. A execução não demonstra se o aviso de recurso decorre da fixture ou do caminho da aplicação.

## Parecer

A regressão e os fluxos HTTP selecionados estão aprovados na versão identificada, sem falha impeditiva observada nesses cenários. O diagnóstico automatizado está concluído. A homologação integral permanece pendente: falta comprovar cobertura dos caminhos acadêmicos adicionais e executar aceitação visual desktop/mobile e com usuários. Essas lacunas bloqueiam a declaração de homologação completa; não impedem a revisão documental dos contratos da próxima etapa.
