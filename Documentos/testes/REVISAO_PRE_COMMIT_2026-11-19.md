# Revisão para publicação — MS02/MS03

Data: 19/11/2026. Destino autorizado: `Samucau1/edufast-2.0`, branch
`feature/instancias-clientes-nuvem`. Preparação local após integrar `origin/main`
`9092bb3` pelo merge `3d9bae0`. Integração sem conflitos e sem mudança adicional
nos arquivos do produto: a main continha merges da base anterior da branch.
Esta revisão acrescenta testes HTTP encadeados e os resultados atuais antes da
publicação. Os relatórios de implementação anteriores permanecem históricos.

## Escopo

Espaço da disciplina com avisos, links, arquivos cifrados e publicação revisada;
abas docentes com autoria, ordem, versão, auditoria e arquivamento; integração
com solicitações existentes; inicialização sem criar tabelas opcionais; correção
de descarte de conexão no startup recusado do painel central. Autenticação,
aprovação de notas e matrículas preservadas. As propostas SQL 005/006 são somente
para revisão: nenhuma migration executada em banco persistente.

O novo `estudos_http.cjs` é chamado pelo executor HTTP já usado no piloto da
branch. Assim, o CI exercita o fluxo JWT/multipart/download dos materiais e abas
junto aos cenários de frequência existentes, sem alterar a coleção Postman antiga.
Os testes Flask de estudos/abas são descobertos pela regressão SQLite/MySQL.

## Execuções atuais após integrar a main

| Verificação | Resultado local |
| --- | --- |
| Regressão completa `.github/cicd/tests` | 190 testes; **168 aprovados, 22 MySQL ignorados**, nenhuma falha; 82,682 s |
| Postman/Newman existente | **57 requisições e 65 asserções aprovadas**; registros e arquivos finais conferidos |
| HTTP real com JWT, servidor sintético novo | **63 verificações aprovadas**: 30 de frequência e 33 de estudos/abas |
| Navegador MS02/MS03 | **Aprovado**, 28 capturas desktop/mobile, sem erros JavaScript ou overflow horizontal |
| Contratos do executor CI | 7 aprovados, usando simulações; não representam execução Docker/HTTPS real |
| Submissão JavaScript | 4 aprovados |
| Infraestrutura dos contratos futuros (`next_stage.py --check`) | 5 aprovados; não executa os cenários funcionais futuros |
| Protocolo estático e sintaxe dos scripts novos | Aprovados |
| Diff/whitespace | Sem erros |

Ambiente: Windows, Python 3.14.3, SQLite descartável, Node e Edge headless.
`DB_URL=sqlite:///:memory:`, `EDUFAST_TEST_DISPOSABLE=1`, configurações/chaves
sintéticas; Postman usa SQLite em arquivo temporário próprio. A regressão utiliza
a dependência local `tzdata` com acesso de leitura fora do sandbox. Não houve
conexão a banco persistente, deploy ou publicação de imagem de produção.

Resultados brutos ignorados pelo Git:

- `.ci-results/pre-commit-2026-11-19/regressao.log`;
- `.ci-results/pre-commit-2026-11-19/postman.log` e `.ci-results/mutations/summary.json`;
- `.ci-results/pre-commit-2026-11-19/api-http.json`;
- `.ci-results/estudos-visual/2026-11-19T15-03-01-964Z/resumo.json`.

A execução de navegador desta revisão foi nova, com fixture nova após o teste
HTTP, em 1440×1000 e 390×844. As 28 capturas são idênticas em SHA-256 às da
[galeria MS03](../design/referencias/2026-11-19-abas-disciplina/manifesto.json),
assim como os oito fontes registrados naquele manifesto. Foram reinspecionadas
a organização mobile e a aba publicada desktop. Não foi reutilizado um resumo
antigo como aprovação e não foi necessário duplicar/sobrescrever as imagens.

O HTTP novo verifica login/JWT por perfil, autenticação ausente/inválida,
criação/renomeação/ordem de abas, idempotência, versão antiga, recusas de outro
autor e aluno, upload multipart e sua repetição, privacidade antes/durante revisão,
aprovação pelo fluxo existente, download com headers privados e revogação após
arquivamento. Histórico e arquivo continuam acessíveis ao autor autorizado.

## Limites e publicação

### Correção encontrada no primeiro CI remoto

O commit inicial `33757ce` passou no piloto remoto (MySQL/HTTPS por escola,
frequência/estudos HTTP e painel central). O CI completo, execução
`44550702134`, encontrou uma incompatibilidade no teste de startup central:
ele calculava a localização da proposta SQL a partir da profundidade da pasta
de testes. O runner monta essa pasta em `/tests`, causando `IndexError` antes de
comparar o SQL. A regressão Linux terminou com um erro e 22 cenários ignorados.

A localização passou a derivar do módulo `control_plane` efetivamente importado,
que acompanha a proposta SQL na imagem. A asserção de igualdade com o SQL gerado
e a recusa de DDL no startup foram mantidas. A validação focada repete a suíte
central com o arquivo de teste copiado para outro diretório: 18 testes, 16
aprovados e dois exclusivos de MySQL ignorados, sem erros (10,722 s). Log local:
`.ci-results/pre-commit-2026-11-19/central-relocated.log`.
Essa correção não altera o produto, as migrations ou as regras de aprovação.

A execução seguinte, `44551607581` no commit `4911941`, passou nos 190 testes
SQLite (22 ignorados). Em MySQL, 187 passaram, dois cenários concorrentes centrais
foram ignorados (a central usa SQLite nessa descoberta) e um teste falhou por
classificação da exceção: o banco recusou
corretamente metadados incompletos pela constraint `ck_estudo_recurso`, mas
PyMySQL expõe o código 3819 como `OperationalError`, enquanto SQLite usa
`IntegrityError`. O contrato agora exige explicitamente o nome da constraint,
o código 3819 no MySQL e ausência de registro após rollback. Não foram alteradas
as constraints nem a aceitação de arquivos do produto. Os demais casos MySQL,
incluindo concorrência de conteúdo e abas, passaram nessa rodada. O piloto
`44551600263` também foi aprovado por inteiro.
A suíte de estudos foi repetida localmente após esse ajuste: 19 testes, 18
aprovados e um concorrente MySQL ignorado, sem erros (7,567 s), em
`.ci-results/pre-commit-2026-11-19/estudos-final.log`.

Docker Engine indisponível localmente. Os 22 cenários de MySQL, concorrência real,
runtime Linux, imagem/HTTPS e restauração ficam para o CI remoto; nenhum resultado
remoto é presumido por esta revisão. Avisos de recursos não fechados nas suítes
existentes continuam no log local, sem falhas de asserção nesta rodada.

A branch já possui o PR [#3](https://github.com/Samucau1/edufast-2.0/pull/3).
O push atualiza esse PR e dispara os workflows aplicáveis. Conferir o resultado
da execução associada ao commit publicado antes de integrar a main. Merge do PR,
ativação persistente das propostas SQL e deploy não fazem parte deste commit.
