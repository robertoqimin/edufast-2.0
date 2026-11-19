# Abas da disciplina — MS03

Data: 19/11/2026. Base `85aed361bd819ff26f6803b2c07595286fdf1f77` mais alterações
locais MS02/MS03, sem novo commit ou publicação nesta retomada. A árvore já
continha o MS02 ao iniciar; esses arquivos foram preservados e estendidos.

## Comportamento entregue

Professor com acesso à oferta cria abas, renomeia e define ordem numérica
(0–9999, menor primeiro, empate por ID de criação). Avisos e Materiais de estudo
permanecem como abas padrão. A autoria das novas abas é preservada: outro
professor não altera nem acrescenta conteúdos à aba do autor. Administração
autorizada pode organizar essas abas; aluno apenas consulta.

Ao preparar um novo rascunho, o autor escolhe uma aba própria ou a aba padrão do
tipo de conteúdo. Seleção pode vir da aba aberta. Sem escolha, mantém o
comportamento MS02. Conteúdos históricos não são movidos ou convertidos.
Não há movimentação de conteúdos existentes, drag-and-drop ou restauração de
abas arquivadas nesta versão. O nome é texto escapado, sem aceitar código executável.

Criar/organizar a aba não publica seus rascunhos: a publicação continua sujeita à
solicitação e decisão administrativa existentes. Aluno lê somente conteúdo
publicado, com os vínculos de turma e disciplina conferidos. As abas ativas podem
estar vazias; isso não libera rascunhos. Não foram alteradas aprovação de notas,
autenticação, matrícula ou regras do Supremo.

Arquivar retira a aba e seus conteúdos do acesso dos alunos, inclusive por URL
direta e download. Preserva o estado original de publicação do conteúdo,
associações, arquivos cifrados e histórico. Autor/admin mantêm a consulta de
histórico. Novos conteúdos e publicação de rascunhos em aba arquivada são recusados,
inclusive decisões de solicitações pendentes. Não há exclusão em cascata.

Edição e arquivamento exigem versão atual; outro envio com versão antiga retorna
409. Idempotência é persistida por operação/ator; repetição exata não gera outra
aba ou auditoria. CSRF e autorização são conferidos no servidor. Auditoria de aba
registra nome, ordem, estado, versão e ator em cada alteração. Gravação e auditoria
participam da mesma transação, com teste de rollback em falha sintética.

## Esquema proposto e compatibilidade

[Proposta 006](../../Códigos/migrations/006_abas_disciplina.sql), compilada offline
do metadata MySQL, acrescenta `estudo_secoes`, `estudo_conteudo_secao` e
`estudo_secao_auditoria`. Associação separada evita alterar as tabelas do MS02.
Depende da proposta 005 e de usuários/ofertas existentes. Nenhuma migration foi
executada e nenhum banco persistente foi conectado durante esta retomada.

Sem as três tabelas novas, MS02 continua funcionando e a ação de organização fica
indisponível. Esquema parcialmente presente bloqueia o conteúdo com 503 para não
ignorar associações/arquivamento. Startup em produção valida tabelas presentes e
não executa DDL. O teste de ausência do MS02 também remove primeiro os dependentes
do MS03, respeitando chaves estrangeiras no MySQL.

Antes de ativar: revisão do usuário das propostas 005/006, destino e esquema,
backup consistente de banco/uploads/chave e ensaio de recuperação. DDL MySQL pode
deixar estado parcial; não repetir às cegas. Reverter para código anterior ao MS03
após ativação precisa de revisão, pois versões antigas não conhecem a restrição
de arquivamento da aba. Não remover tabelas ou arquivos automaticamente.
Procedimento: [migrations](../../Códigos/migrations/README.md).

## Verificação atual

Windows, Python 3.14.3, SQLite em memória, Node e Edge headless. Dados inteiramente
fictícios. Testes usam `EDUFAST_TEST_DISPOSABLE=1`; o navegador usa a fixture
`frequencia_visual_fixture.py --local`, loopback 5091 e uploads temporários.

| Verificação | Resultado |
| --- | --- |
| Novos contratos `test_estudo_abas` | 11 testes: 10 aprovados, 1 concorrente MySQL ignorado |
| Regressão final `.github/cicd/tests` | 190 testes: **168 aprovados, 22 MySQL ignorados**, nenhuma falha; 84,512 s |
| Navegador `verificar_estudos.cjs` | MS02/MS03 aprovados, 28 capturas, sem erros JavaScript/overflow horizontal |
| Protocolo estático de design | Aprovado, incluindo novo template e manifestos |
| Sintaxe Node e revisão de whitespace | Aprovadas |

Log da rodada final: `.ci-results/abas-2026-11-19/regressao-final.log`. A primeira
rodada terminou com 18 erros e 20 cenários ignorados por ausência de `tzdata` no
caminho de importação do ambiente de teste. Não foi usada como aprovação.
A rodada final usou a dependência local já existente em `.ci-results/test-tzdata`,
com leitura fora do sandbox por restrição de acesso dessa pasta; não houve mudança
na regra de fuso do produto. Avisos de recursos não fechados/depreciações de suítes
existentes continuam no log, sem falhas de asserção na rodada final.

Os contratos incluem autoria, recusas de aluno/outro docente/oferta alheia,
perda de atribuição, idempotência, versão antiga, rollback, nomes escapados,
rascunhos privados, publicação pendente após arquivamento, download revogado e
preservação de arquivo/associação. Ausência e esquema parcial são exercitados sem
DDL de startup. Concorrência de renomeação/arquivamento exige MySQL descartável.

Navegador: execução completa `2026-11-19T14-55-39-351Z`, em 1440×1000 e 390×844.
Repetiu aviso/link/arquivo e revisão do MS02; criou, renomeou, alterou ordem e
arquivou aba; selecionou a aba no formulário; verificou que o aluno não vê
rascunho, vê após aprovação e perde acesso direto após arquivamento. Testou Tab
entre campos. Inspeção da folha de contato e de organização desktop/mobile e
formulário mobile em tamanho integral sem novos cortes/sobreposições.

[Manifesto com hashes das 28 capturas e fontes](../design/referencias/2026-11-19-abas-disciplina/manifesto.json)
e [comparação visual](../design/referencias/2026-11-19-abas-disciplina/comparacao.md).
As capturas históricas não foram sobrescritas. Reutilizados tokens, fontes locais,
menu, layout e componentes; nenhum CSS/JS ou pacote de interface novo.

### Reprodução

Usar o Python com dependências da aplicação/testes. Definir `DB_URL=sqlite:///:memory:`,
`APP_ENV=development`, `SECRET_KEY` sintética de 32+ caracteres,
`EDUFAST_TEST_DISPOSABLE=1` e `PYTHONPATH` com `Códigos`, `.github/cicd/tests` e a
dependência local `tzdata` quando necessária no Windows.

```powershell
python -m unittest test_estudo_abas -v
python -m unittest discover -s .github/cicd/tests -v
python Códigos/tests/verificar_protocolo_design.py
node --check Códigos/tests/verificar_estudos.cjs
```

Para navegador: iniciar fixture nova com `EDUFAST_FREQUENCIA_VISUAL=1`, SQLite em
memória e chave Fernet sintética, conforme relatório MS02. Definir
`PLAYWRIGHT_MODULE` para o Playwright local e executar
`node Códigos/tests/verificar_estudos.cjs`. O executor cria dados; repetir apenas
com fixture nova. Evidências brutas permanecem em `.ci-results/estudos-visual`.

## Pendências e próxima tarefa

Docker Engine indisponível nesta máquina. MySQL, concorrência real, aplicação das
propostas em esquema legado e runtime Linux continuam sem homologação. Não houve
teste de carga, RAM/CPU/latência, leitor de tela ou paletas personalizadas.
As listas de conteúdo mantêm paginação de 25 itens; o seletor e a tela de abas
listam as seções da oferta, sem promessa de desempenho para muitas abas.

MS03 está implementado e validado no ambiente descartável; ativação persistente,
MySQL e aceite do usuário permanecem separados. Próximo lote: **MS04**, consolidar
cursos/módulos/capítulos/aulas e retomada do aluno, reaproveitando os modelos
existentes. MS05 e os demais critérios de entrega comercial continuam no plano.
