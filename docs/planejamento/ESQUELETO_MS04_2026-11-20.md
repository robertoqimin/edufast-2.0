# Esqueleto e caminhos para implementar o MS04

Data: 20/11/2026. Base de código: `aedf8ad`. Continuação do
[estudo MS04](ESTUDO_MS04_CURSOS_MODULARES_2026-11-19.md).

Evolução do esqueleto: [backend e API implementados em 20/11](../testes/API_CURSOS_MS04_2026-11-20.md).
O restante deste documento registra a preparação inicial. Os serviços agora se
conectam ao blueprint `/api`. O [frontend e a demo ENEM](../testes/FRONTEND_CURSOS_MS04_2026-11-20.md)
também foram implementados em 20/11; ativação persistente e aceite manual continuam pendentes.

A arquitetura atual comporta o MS04 de forma incremental: cursos, hierarquia,
ofertas, conclusões, auditoria e aprovações já existem. Retomada persistida, aulas
em texto e versão dos rascunhos precisam de extensões. Essa compatibilidade
arquitetural não determina capacidade de usuários, latência ou consumo de memória;
esses limites dependem das medições previstas no MS05.

O pacote criado é um esqueleto isolado. Seus serviços têm assinaturas e recusam
execução com `NotImplementedError`; ainda não são importados pelas rotas, pelo
startup ou pelos modelos. O funcionamento atual permanece como base de comparação.

## Estrutura de arquivos

```text
api/app/services/
├── cursos.py                         base existente e contratos legados
└── cursos_ms04/
    ├── __init__.py                   fronteira do esqueleto ainda isolado
    ├── autoria.py                    salvar_rascunho
    ├── publicacao.py                 preparar_publicacao
    ├── retomada.py                   registrar_abertura
    └── conteudo.py                   validar_aula

api/migrations/propostas/
└── ms04_modelo.json                  proposta conceitual, sem SQL executável

.github/cicd/ms04/
├── catalogo.json                     serviços, rotas e cenários de aceite
└── verificar_esqueleto.py            leitura estática, sem banco
```

Os novos serviços recebem a sessão/transação do chamador. Ao implementá-los,
validar identidade e vínculos atuais no servidor e reutilizar as garantias
existentes de idempotência, versão e auditoria. Não interpretar `ator_id` fornecido
por um payload como identidade autenticada. Quem chama controla commit/rollback,
inclusive quando o serviço participa da transação de uma aprovação.

## Caminhos de integração

| Arquivo atual | Alteração prevista | Lote |
| --- | --- | --- |
| `api/app/services/cursos.py` | Conferir aluno na turma e disciplina; manter autoria, edição imutável e ordem da árvore | A |
| `api/app/routes/curso_routes.py` | Coordenar os serviços novos mantendo caminhos e contratos legados | B–E |
| `api/app/restauracao.py` | Tratar somente operações autorizadas de rascunhos; preservar interceptação acadêmica | B |
| `api/app/services/restauracao_context.py` | Compatibilizar snapshots e propostas docentes anteriores | B |
| `api/app/services/aprovacoes_service.py` | Novo pedido de publicação da versão exata, sem ampliar revisores | B |
| `api/app/models/curso_model.py` | Versão de agregado, tipo/corpo de aula e referência aos novos registros | B–D, após desenho do esquema |
| `api/app/templates/curso_biblioteca.html` | Biblioteca paginada e entrada de retomada por oferta | C/E |
| `api/app/templates/curso_editor.html` | Módulos/capítulos, versão e estados de revisão | B/D |
| `api/app/templates/curso_aprender.html` | Abertura explícita, conclusão separada e renderização por tipo | C/D |
| `api/app/routes/estudo_routes.py` | Ligação da disciplina para oferta autorizada de curso | E |
| `api/app/static/css/escola.css` | Apenas ajustes necessários nos componentes compartilhados | E |

Antes de tocar telas, ler `docs/PROTOCOLO_DESIGN.md` e preservar fontes,
tokens, menu e layout. Nenhuma nova página ou identidade visual é necessária para
começar o lote A. Os nomes apresentados continuam Curso → Módulo → Capítulo → Aula,
mapeados para `CursoModel`, `CapituloModel`, `TemaModel` e `AulaModel`, sem renomear
tabelas, IDs ou payloads legados.

## Caminhos HTTP

Os dez caminhos/métodos existentes catalogados continuam disponíveis, incluindo
`/cursos`, edição de estrutura, duplicação, estado, ofertas, aprendizagem e
conclusão. O esqueleto não registra endpoints de demonstração ou respostas de
sucesso provisórias. Os caminhos abaixo são propostas para os lotes seguintes:

| Método e caminho proposto | Finalidade | Requisitos |
| --- | --- | --- |
| `POST /cursos/<curso_id>/solicitar-publicacao` | Enviar versão do rascunho | Autor atual, versão, idempotência e snapshot; resposta 202 após persistência real |
| `GET /aprender/<oferta_id>/retomada` | Consultar último acesso do aluno | Oferta autorizada, sem alterar conclusão ou registrar visita |
| `POST /aprender/<oferta_id>/aulas/<aula_id>/abrir` | Registrar abertura e navegar | Aula da oferta, versão do cursor, idempotência; sessão com CSRF ou JWT |
| `POST /cursos/<curso_id>/aulas/<aula_id>/recursos` | Acrescentar material ao rascunho | Autor, versão do curso, tipo/limite válido e transação de arquivo |
| `GET /aprender/<oferta_id>/aulas/<aula_id>/recursos/<recurso_id>/arquivo` | Baixar apoio privado | Validar toda a cadeia; nunca redirecionar para documento pessoal |

Para formulários, a abertura pode salvar e responder com redirecionamento 303
para a leitura existente; JSON pode devolver o destino autorizado. A leitura
direta de uma URL não deve concluir aula. A retomada de links diretos e o fluxo
sem JavaScript fazem parte dos contratos do lote C e devem funcionar antes de
substituir a navegação atual. POST de abertura não é marcação de conclusão.

Decisões administrativas continuam no endpoint existente de solicitações;
não criar uma segunda autoridade de publicação. Os nomes finais dos novos
endpoints devem ser fechados com os contratos HTTP ao implementar cada lote.

## Ordem de implementação

| Ordem | Entrega | Arquivos de testes a acrescentar quando houver implementação | Dependências |
| --- | --- | --- | --- |
| 1 / A | Alinhar autorização de curso/oferta e fixar contratos do legado | `.github/cicd/tests/test_cursos_acesso.py` | Pode começar com o esquema atual |
| 2 / B | Rascunhos próprios, versão e publicação revisada | `.github/cicd/tests/test_cursos_autoria.py`, `test_cursos_publicacao.py` | Fechar política de autoria e proposta de versão |
| 3 / C | Última aula acessada por aluno/oferta, anterior/próxima e conclusão | `.github/cicd/tests/test_cursos_retomada.py` | Proposta de tabela de retomada e contrato sem JavaScript |
| 4 / D | Texto, YouTube legado e apoios privados | `.github/cicd/tests/test_cursos_conteudo.py` | Definir formatos, limites e duplicação de arquivos |
| 5 / E | Disciplina/biblioteca, percurso e leveza | `.github/cicd/cursos_http.cjs`, `api/tests/verificar_cursos.cjs` | Lotes anteriores, protocolo e inspeção desktop/mobile |

Esses caminhos de testes futuros não são arquivos vazios com aprovação simulada.
Os 16 cenários do catálogo estão **pendentes**. Ao implementar cada um, criar
asserções de comportamento com dados descartáveis, incluindo recusa, repetição,
rollback e concorrência MySQL quando necessária.

O primeiro incremento recomendado é o **MS04-A**: aluno sem vínculo com a
disciplina não acessa cursos dessa oferta, aula de outra oferta é recusada e
revogação preserva histórico. Esse trabalho pode começar sem criar tabelas novas.
Depois dele, consolidar o desenho de esquema B–D antes de gerar migrations.

## Evolução de banco

O [modelo conceitual](../../api/migrations/propostas/ms04_modelo.json) descreve:
versão positiva em curso; tipo/corpo e vídeo condicional em aula; retomada única
por aluno/oferta; recursos privados de aula se incluídos. Ele não é uma migration
e não reserva automaticamente a numeração 007.

Aulas publicadas e conclusões existentes mantêm suas identidades. O curso novo
continua uma nova edição; não recebe o progresso da anterior automaticamente.
Última aula acessada não pode ser reconstruída a partir de `concluida_em`, pois
isso descreve outra ação. Até definir duplicação/retenção dos arquivos, não
prometer exclusão física nem reaproveitar autorização de recursos MS02.

Quando houver SQL concreto, revisar destino, dependências e dados legados;
preparar backup consistente de banco/uploads/chave e ensaio isolado. Executar
migrations somente após revisão do usuário, conforme `AGENTS.md`. O startup não
deve alterar esquema nem ativar serviços incompletos.

## Verificação do esqueleto e regressão

Na raiz, sem dependências da aplicação ou conexão ao banco:

```powershell
python -S .github/cicd/ms04/verificar_esqueleto.py --check
```

O comando confere os arquivos, os quatro pontos de serviço, o mapeamento dos
modelos, dez rotas existentes, cinco propostas sem colisão e os IDs dos 16 cenários
pendentes. Também verifica que o pacote ainda não foi importado pelo runtime.
Isso aprova a organização do esqueleto, não as funcionalidades futuras.

Verificação em 20/11: comando estrutural aprovado com quatro serviços, dez rotas
existentes, cinco propostas e 16 cenários pendentes. A regressão focada abaixo
executou 18 testes em SQLite descartável: 17 aprovados e um exclusivo de MySQL
ignorado, em 7,120 s. Log local ignorado:
`.ci-results/ms04-esqueleto-2026-11-20/regressao-focada.log`. Há aviso de recurso
SQLite não fechado na suíte existente, sem falha de asserção nessa rodada.
Não houve execução de migrations, mudanças de tela ou nova rodada geral MySQL.

Para comparar a base de cursos e aprovações, usar ambiente descartável com
`DB_URL=sqlite:///:memory:`, `EDUFAST_TEST_DISPOSABLE=1`, chave sintética de 32+
caracteres e `PYTHONPATH` com `api` e `.github/cicd/tests`:

```powershell
python -m unittest test_course_outline test_restauracao -v
```

Antes de conectar um serviço, concluir seus contratos e testes SQLite/MySQL.
Mudanças de interface exigem capturas atuais, não apenas o resumo de uma execução
anterior. Registros de aprovação dos lotes ficam nos relatórios de testes.

## Decisões para os próximos lotes

Quatro níveis e última aula acessada estão confirmados. Permanecem como propostas
do estudo: rascunho com autoria direta e revisão na publicação; aula em texto com
apoios PDF/PNG/JPEG/link; navegação livre entre aulas publicadas. O esqueleto
separa essas decisões para não alterar a política atual antes de implementar o
lote correspondente. Elas não impedem começar os contratos e a autorização do A.

Não estão incluídos no primeiro MS04: vídeo hospedado no servidor, segundos
assistidos, provas/certificados, pagamento ou transferência automática de progresso
entre edições. Capacidade e tempos comerciais dependem de medição própria.
