# B2 — Interface antiga de cursos aposentada

Data: 23/11/2026. Branch `feature/melhoria-dezembro`, a partir do commit
«feat: unifica notas no modulo academico (B1)». Etapa B2 do
[plano de melhoria](../planejamento/PLANO_MELHORIA_2026-11-22.md).

## Objetivo

Um único caminho de cursos por instalação. Quando o MS04 está habilitado (o caso de toda
escola criada pelo esquema base v8), menus e links apontam só para `/aprendizagem`, e as
rotas antigas de edição ficam somente leitura. Sem MS04, a interface antiga continua
funcionando como antes.

## Situação antes da B2

- As telas MS04 já gravavam só pela API `/api/...` e cobriam tudo o que a interface antiga
  fazia: criar, editar, duplicar, publicar com aprovação, liberar e revogar oferta, e concluir aula.
- As páginas antigas (`/cursos`, `/cursos/<id>`, `/aprender/<id>`) já mostravam as telas
  MS04, mas com o endereço antigo.
- **As sete gravações antigas continuavam ativas** com o MS04 habilitado: criar, estrutura,
  duplicar, estado, ofertas, revogar e concluir. Só recusavam cursos que já tinham versão MS04.
  Professores ainda podiam enviar propostas por elas.

## O que mudou

| Área | Agora (MS04 habilitado) |
| --- | --- |
| Menu "Biblioteca de cursos" / "Meus cursos" | Aponta para `/aprendizagem` e fica ativo nas páginas MS04 |
| `GET /cursos`, `/cursos/<id>`, `/aprender/<id>` | Redirecionam para `/aprendizagem`, `/aprendizagem/cursos/<id>` e `/aprendizagem/ofertas/<id>` (mantém `?aula=`), então favoritos antigos continuam funcionando |
| As 7 gravações antigas | **410** com a mensagem "A edição de cursos agora é feita em Aprendizagem (/aprendizagem)…", sem efeito |
| Professor enviando pela interface antiga | 410, **nenhuma proposta criada** |
| Propostas antigas de cursos ainda pendentes | Aprovar → 410, sem efeito; rejeitar funciona |
| `/admin/gestao-turmas` | Inalterada (não edita cursos) |
| Instalação sem MS04 | Tudo como antes |

**Como funciona:** o decorador `interface_ms04` envolve as próprias views antigas em
`api/app/routes/curso_routes.py`. Isso é necessário porque, quando o professor envia ou
a secretaria aprova uma proposta, a view é executada diretamente, sem passar por
`before_request`; com o decorador, a recusa vale nesses caminhos também. As ramificações
MS04 que ficavam embutidas nas páginas antigas foram removidas, porque o decorador já
redireciona. O menu usa a marca `cursos_ms04`, calculada uma vez por requisição em
`api/app/restauracao.py`, com a sessão já aberta.

**Aceites do plano:**
- **Cursos antigos legíveis:** abrem nas telas MS04.
- **Primeira edição adota a versão MS04:** comportamento que já existia. Rascunho antigo
  ganha versão na primeira edição; curso publicado é preservado, e a nova edição nasce por
  duplicação.
- **Progresso preservado:** o MS04 lê e grava a mesma tabela `curso_progressos`.

Sem migrations, sem mudança de banco e sem CSS novo.

## Testes

**Novos:** `test_cursos_interface_unica.py`, com 8 casos:
- páginas antigas redirecionam (incluindo `?aula=`);
- as 7 gravações antigas respondem 410 sem efeito;
- professor não cria proposta pela interface antiga;
- proposta antiga pendente só pode ser rejeitada;
- menu só aponta para `/aprendizagem` nos três perfis;
- curso antigo publicado continua legível, com progresso preservado, e a nova edição nasce
  por duplicação;
- rascunho antigo adota versão na primeira edição;
- sem MS04, a interface antiga continua criando cursos.

**Atualizados:**
- `test_restauracao.py`: os três testes de propostas da interface antiga passam a rodar no
  cenário "instalação sem MS04", onde ela continua valendo; a lista de telas usa `/aprendizagem`.
- `test_cursos_ms04.py`: endereços antigos de leitura trocados por `/aprendizagem`; gravações
  antigas agora esperam 410; a proposta antiga pendente é criada antes do MS04 e só pode ser
  rejeitada.
- `test_cursos_frontend.py`: confere o redirecionamento das páginas antigas.
- `cursos_http.cjs`: a rota antiga de estrutura espera 410.

### Resultados

Bateria completa em containers sobre o código final, com o fonte conferido como inalterado
durante a regressão. Evidências em `.ci-results/cursos-interface-unica-b2-2026-11-23/`.

| Etapa | Resultado |
| --- | --- |
| Regressão SQLite | 325 testes aprovados, 43 pulados (os mesmos de antes) |
| Regressão PostgreSQL + concorrência real | 325 aprovados, 2 pulados |
| HTTP real (inclui `cursos_http.cjs`) | 117 verificações aprovadas |
| `ci.py`: imagem de produção, HTTPS, backup/restauração e uploads | Aprovado (11 unitários; 325 + 325 testes) |
| API de frequência | 117 verificações aprovadas |
| Ensaio de atualização legado → v8 | Aprovado |
| Painel central (Supremo) | 18 testes aprovados |
| Postman SQLite / PostgreSQL | 66 requisições e 76 verificações, 0 falhas em cada |
| Piloto de duas escolas | Aprovado na repetição (34 s), ver nota abaixo |

Também passaram localmente: suíte completa em SQLite de arquivo e em memória (325 testes),
verificador de protocolo de design, `test_submission.cjs` (3), `test_ci_characterization.py`,
`next_stage.py --check` e `infra/verify.sh` (20 casos).

**Nota sobre o piloto:** na bateria, o piloto falhou com `spawnSync docker ETIMEDOUT`. Foi o
próprio comando do Docker que estourou o tempo, enquanto uma jornada no Edge rodava em
paralelo na mesma máquina. A B2 não altera o piloto nem a infraestrutura. Sem resíduos de
containers, ele foi repetido isoladamente e passou inteiro em 34 s
(`piloto-duas-escolas-repeticao.log`).

## Jornada real no Edge

Numa aba visível, na escola de teste descartável, com um curso criado pela interface antiga
(publicado, ofertado e com uma aula já concluída pelo aluno Bruno):
1. a professora clica em "Biblioteca de cursos" e chega a `/aprendizagem`;
2. o endereço antigo `/cursos` redireciona para `/aprendizagem`;
3. `/cursos/1` abre no editor MS04;
4. uma gravação pela rota antiga, com token CSRF válido, recebe **410** com a mensagem;
5. Bruno abre o link antigo `/aprender/1` e chega a `/aprendizagem/ofertas/1` com
   "1 de 2 aulas concluídas · 50%" e o ✓ na aula feita.

Nenhum erro de JavaScript.

Durante a preparação, a primeira tentativa deu 404 para o aluno. A causa estava na **massa
da escola de teste**, que não matriculava os alunos nas disciplinas (`alunos_disciplinas`).
A regra de acesso é a mesma na interface antiga (`cursos.acesso_oferta`) e no MS04, então
não houve regressão. A massa foi corrigida.

## Limitações

- O verificador de navegador `api/tests/verificar_cursos.cjs` (capturas do MS04) não faz
  parte da bateria e não foi executado. Ele abre `/cursos`, que agora redireciona para a
  mesma tela.
- Não houve mudança visual além do destino do link do menu; por isso não foi criada nova
  pasta de referências visuais.

## Próxima etapa

B3 — MS05: medir e corrigir usabilidade e desempenho por perfil.
