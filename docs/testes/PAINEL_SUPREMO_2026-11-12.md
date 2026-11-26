# Validação do painel central — 12/11/2026

Base `5a9c42c`, com a implementação do painel central que integra esta entrega.
Ambiente: Windows/PowerShell, Docker Engine 29.4, Python 3.12 em container,
MySQL 8.4 descartável, SQLite descartável e Edge headless em perfil isolado.

## Resultados da versão entregue

| Verificação | Resultado |
| --- | --- |
| API central em MySQL: `node .github/cicd/run_platform_api.cjs edufast-platform:test` | 18 aprovados, sem ignorados; inclui gravações concorrentes reais |
| SQLite: `python -m unittest test_restauracao test_two_school_demo test_control_plane -v` | 36 executados, 33 aprovados, três cenários exclusivos de MySQL ignorados |
| Infra: `node --test infra/test_environments.cjs infra/test_manage.cjs infra/test_demo.cjs infra/test_platform.cjs` | 20 aprovados |
| Navegador: `node api/tests/verificar_plataforma.cjs` | Login/logout móvel, escolas, pessoas, paginação e totais aprovados; oito capturas |
| Protocolo de design e actionlint | Aprovados |

Os testes Python exigem `EDUFAST_TEST_DISPOSABLE=1`. Para repetir SQLite no Docker,
montar o checkout somente para leitura em `/repo`, usar diretório `/repo`,
`PYTHONPATH=/repo/api:/repo/.github/cicd/tests`, `DB_URL=sqlite:///:memory:` e
uma `SECRET_KEY` sintética de importação escolar com pelo menos 32 caracteres.
O painel recebe sua própria chave nos fixtures, independente da escolar.
Não executar os testes contra bancos de escolas ou o banco central persistente.

O runner MySQL cria um projeto Compose com UUID, sem portas públicas, valida o
destino descartável e remove somente seus próprios containers/rede ao terminar.
O resultado final foi 18/18, com limpeza concluída. Os cenários verificam conta
única, CSRF, revogação de sessão, lockout, separação de contas escolares, isolamento
das chaves de integração, substituição atômica de pessoas, duplicatas, snapshots
antigos, busca/paginação, centavos inteiros, períodos, idempotência, cancelamento
auditado e concorrência em cadastros e lançamentos.

O cenário de integração lê dois bancos escolares **novos em memória**, com os
fixtures Teste 01 e 02: 20 alunos, cinco professores e um administrador em cada.
Nenhuma senha, CPF, documento ou atestado integra o diretório enviado ao central.

Foram identificadas e corrigidas durante a validação: invalidação do CSRF por
requisição de favicon anônima; restrição MySQL de CHECK sobre coluna de incremento;
precisão da data usada contra replay; serialização MySQL de somas como texto;
ausência do botão de saída na navegação móvel. Os resultados acima se referem às
execuções posteriores às correções aplicáveis, não às tentativas que falharam.

## Limites e evidências

[Capturas e manifesto](../design/referencias/2026-11-12-plataforma/manifesto.json)
e [comparação visual](../design/referencias/2026-11-12-plataforma/comparacao.md).
Os logs temporários e o banco de demonstração não são versionados.

O financeiro é manual e fictício na demonstração. Não foram testados provedor de
pagamento, cobranças automáticas, SSH de produção, DNS real, certificado real,
carga, backup/restauração central ou disponibilidade em nuvem. O publicador no
host teve seu direcionamento Docker/HTTPS testado com transportes simulados;
os diretórios reais dos fixtures foram validados pela API central em SQLite/MySQL.

A revisão de infraestrutura verifica redes/volumes/segredos e preservação de
instalações anteriores. Não foi feito deploy do painel em nuvem nesta execução.
As telas escolares tiveram regressão HTTP, sem nova inspeção visual escolar.
Apenas a identidade padrão central foi inspecionada, pois não há personalização
visual do painel nesta versão.

O esquema central permanece como [proposta SQL](../../api/control_plane/migrations/001_central.sql)
para revisão do usuário. Nenhuma migration foi aplicada a bancos persistentes,
incluindo os ambientes Teste 01 e 02 existentes.
