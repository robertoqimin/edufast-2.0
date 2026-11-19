# Espaço da disciplina — MS02

Data: 16/11/2026. Base `85aed36` mais alterações locais deste lote. O commit
`85aed36`, da etapa anterior, foi publicado em `feature/instancias-clientes-nuvem`
com autorização do usuário. O novo módulo deste relatório ainda não foi publicado.

## O que foi implementado

Menu **Espaço da disciplina**, rota `/estudos`, com ofertas organizadas por turma,
matéria e ano. Cada disciplina tem abas fixas **Avisos** e **Materiais de estudo**.
Listas paginadas no servidor, com 25 registros por página, sem buscar conteúdo de
todas as disciplinas no navegador.

Professor autorizado prepara e edita seus próprios rascunhos: aviso em texto,
link HTTPS ou PDF/PNG/JPEG de até 5 MiB. O formulário mostra só os campos do tipo
escolhido. O JavaScript local tem 688 bytes e é carregado apenas no cadastro;
a validação e autorização continuam no servidor, inclusive sem JavaScript.
Nenhuma biblioteca de interface nova foi adicionada.

Rascunhos não aparecem aos alunos. Professor solicita publicação; administração
confere pelo painel existente de solicitações, com link para abrir o conteúdo, e
aprova ou rejeita. Uma edição posterior invalida a aprovação da versão anterior.
Administradores também podem publicar diretamente. Nesta etapa, o novo tipo de
publicação é administrativo; o papel de revisor docente continua atendendo seus
tipos de materiais anteriores, sem ganhar nova permissão automaticamente.

Conteúdo publicado não é editado diretamente. Uma nova edição deve ser preparada
em outro rascunho. Arquivar retira o conteúdo dos alunos e preserva o registro,
o arquivo e a auditoria. Edição/arquivamento exigem versão; gravações usam
idempotência persistida e transação. A auditoria registra criação, edição,
publicação, arquivamento e downloads.

## Acesso e arquivos

- Aluno precisa de vínculo tanto com a turma quanto com a disciplina e matrícula
  não inativa/trancada/cancelada. Acesso conferido também no detalhe e no download.
- Professor precisa de atribuição ativa na oferta quando houver gestão explícita.
  Pares legados só são usados em turmas ainda não adotadas e ofertas sem atribuições.
  Outro professor não pode editar/publicar rascunho do autor.
- Turmas arquivadas não são listadas nem liberam novos acessos neste módulo.
- Materiais usam `uploads/materiais_estudo`, nomes aleatórios e cifra com
  `DATA_ENCRYPTION_KEY`, separados dos documentos pessoais/atestados.
- Download é anexo, com autorização, auditoria, `no-store` e `nosniff`.
  Arquivos não são servidos por URL pública nem pelo fluxo de documentos pessoais.
- Verificação inicial de assinatura e limite de tamanho não é antivírus ou
  validação do conteúdo pedagógico. Não há envio de Word/ZIP/vídeo nesta etapa.
- Links só aceitam HTTPS, sem credenciais ou caracteres de controle. O servidor
  não busca esses endereços; abertura é externa, com `noopener noreferrer`.

Os vínculos atuais de aluno/turma e aluno/disciplina são reutilizados. Isso não
constitui a modelagem completa de matrícula por oferta/créditos/pré-requisitos do
ensino superior; essa diferença continua no plano de produto.

## Esquema e ativação

[Proposta SQL 005](../../Códigos/migrations/005_espaco_disciplina.sql): duas tabelas,
`estudo_conteudos` e `estudo_auditoria`, compiladas offline dos modelos. Não altera
contas, vínculos, documentos antigos ou aprovações existentes.

**Nenhuma migration foi executada em banco persistente**, incluindo escolas Teste
01/02. Sem as novas tabelas, `/estudos` retorna 503; o startup mantém a aplicação
escolar funcionando sem criá-las. Tabelas opcionais existentes continuam validadas
em produção. Não usar a implementação como autorização para executar o SQL.

Antes da ativação: revisão do usuário, identificação do destino, conferência de
esquema e dependências, backup recuperável de banco/uploads/chave e ensaio no
destino isolado. DDL MySQL pode deixar estado parcial e não deve ser repetido às
cegas. Guia: [migrations](../../Códigos/migrations/README.md).

## Verificações

Ambiente: Windows, Python 3.14.3, SQLite descartável, Node e Edge headless. Dados
inteiramente fictícios. Nenhuma conexão a banco escolar persistente. O servidor
do navegador foi iniciado pela fixture com `--local`, em memória e só no loopback.

| Verificação final | Resultado |
| --- | --- |
| Descoberta geral `.github/cicd/tests` | 179 testes: **158 aprovados, 21 exclusivos de MySQL ignorados**; nenhuma falha, 103,620 s |
| Novos contratos `test_estudos.py`, dentro da rodada geral | 19 testes: 18 aprovados, 1 concorrente de MySQL ignorado |
| Navegador `verificar_estudos.cjs` | Aprovado; 16 capturas, sem erros JavaScript ou overflow horizontal da página |
| Protocolo estático e sintaxe dos scripts novos | Aprovados |
| Revisão de diff | Sem erros de whitespace; arquivos locais fora do lote |

Log da rodada final: `.ci-results/estudos-2026-11-16/regressao-entrega.log`.
As tentativas anteriores falharam conforme os ajustes abaixo; seus resumos não
foram usados como aprovação. A correção do painel central foi incluída nesta
rodada final, que confirmou o teste de startup sem DDL.

O navegador concluiu criação e publicação de aviso, arquivo e link, recusa de
rascunho/download pelo aluno antes da aprovação, revisão administrativa, leitura
do aluno e download do PDF fictício. Testou Tab entre campos, ocultação dos campos
irrelevantes e ausência de erros JavaScript/overflow horizontal nas telas capturadas.

[16 capturas e hashes](../design/referencias/2026-11-16-espaco-disciplina/manifesto.json)
e [comparação visual](../design/referencias/2026-11-16-espaco-disciplina/comparacao.md).
Execução final do navegador: `2026-11-16T20-09-04-893Z`, em 1440×1000 e 390×844.
Protocolo estático estendido para os novos templates `estudo_*` e aprovado.

### Reprodução

Usar Python com dependências da aplicação/testes. Nesta máquina foi usado
`.ci-results/diagnostico-2026-11-05/venv/Scripts/python.exe`. Configuração obrigatória
de teste: `DB_URL=sqlite:///:memory:`, `APP_ENV=development`, chave sintética com
32+ caracteres, `EDUFAST_TEST_DISPOSABLE=1` e `PYTHONPATH` com `Códigos` e
`.github/cicd/tests`. A descoberta completa recria somente o banco descartável.

```powershell
python -m unittest test_estudos -v
python -m unittest discover -s .github/cicd/tests -v
python Códigos/tests/verificar_protocolo_design.py
```

Para navegador: gerar chave Fernet sintética, definir `EDUFAST_FREQUENCIA_VISUAL=1`
e iniciar `python .github/cicd/tests/frequencia_visual_fixture.py --local` com
SQLite em memória. Em outro terminal, configurar `PLAYWRIGHT_MODULE` para o
Playwright local e rodar `node Códigos/tests/verificar_estudos.cjs`. Repetir sempre
com servidor sintético novo, pois o cenário cria conteúdos.

### Ajustes encontrados na validação

A primeira descoberta geral falhou por falta de `tzdata` no Python/Windows usado
pelo painel central. A dependência foi instalada somente em pasta local ignorada.
Seus arquivos exigiram execução com acesso de leitura fora do sandbox para a
regressão; não foi alterada a configuração de fuso do produto.

Depois apareceu um vazamento de conexão no caminho em que o painel central recusa
um banco ainda sem esquema. A conexão mantinha o arquivo SQLite temporário aberto
no Windows. O caminho agora chama `engine.dispose()` antes de propagar a falha;
a validação de esquema e a recusa de startup permanecem. O teste existente de
startup sem DDL exercita esse comportamento, sem relaxar sua asserção.

As tentativas de navegador ajustaram o seletor do tipo de conteúdo e a espera pela
execução do script de melhoria progressiva. Só a execução final está na nova galeria.
Logs anteriores e arquivos de ambiente permanecem em `.ci-results`, fora do Git.

## Pendências e limites

Docker Engine indisponível; MySQL, concorrência real e runtime Linux não foram
homologados neste lote. O teste concorrente de edição exige MySQL descartável.
SQL gerado e testes SQLite não comprovam aplicação da migration em MySQL legado.

Sem teste de carga ou medição de RAM/CPU/latência; paginação e script pequeno não
são garantia de capacidade. A identidade padrão foi inspecionada; outras paletas
não receberam nova homologação. Há avisos de depreciação/recursos não fechados em
suítes antigas, a registrar separadamente dos resultados de asserção.

Abas criadas pelo professor (MS03), conteúdo modular ampliado de cursos (MS04) e
validação de desempenho em hardware modesto (MS05) continuam como próximas entregas.
