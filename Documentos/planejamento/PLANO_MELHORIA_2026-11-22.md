# Plano de melhoria — dezembro de 2026

Data: 22/11/2026. Base inspecionada: commit «docs: atualiza README com estado atual do produto» (branch `feature/instancias-clientes-nuvem`).
Horizonte: 4 semanas, de 23/11 a 18/12/2026.
Frentes escolhidas pelo usuário: **ativação do banco**, **produto** e **pronto para vender**.
Manutenção (consolidação de documentos, migração de controllers antigos) fica fora deste ciclo.

Este é um plano de trabalho, não uma promessa de prazo. Migrations continuam sendo
propostas e só são executadas após revisão do usuário, conforme `AGENTS.md`.

> **Atualização em 22/11/2026:** o banco foi trocado para **PostgreSQL 17** antes da A2,
> a pedido do usuário. Ver [relatório da troca](../testes/MIGRACAO_POSTGRESQL_2026-11-22.md).

### Andamento

| Item | Situação | Evidência |
| --- | --- | --- |
| A1 | Concluído em 22/11 | [Inventário de esquema](../testes/INVENTARIO_ESQUEMA_2026-11-22.md) |
| Troca para PostgreSQL | Concluída em 22/11 (fora do plano original, pedido do usuário) | [Relatório](../testes/MIGRACAO_POSTGRESQL_2026-11-22.md) |
| A2 | Proposta 008 pronta para revisão em 22/11; não executada em banco persistente | [Registro de migrations](../testes/REGISTRO_MIGRACOES_2026-11-22.md) |
| A3 | Esquema base v8 pronto para revisão em 22/11; iniciador e escolas de teste já o usam | [Esquema base](../testes/ESQUEMA_BASE_2026-11-22.md) |
| Segurança | Revisão em 22/11 e correções S1–S7 em 23/11 (fora do plano original, pedido do usuário) | [Revisão](../testes/REGRESSAO_SEGURANCA_2026-11-22.md) · [Correções](../testes/SEGURANCA_CORRECOES_2026-11-23.md) |
| A5 | Concluída em 23/11: base v8, 001–008 e banco central aprovados; 002 com quarentena geral; e-mails com maiúsculas tratados na importação. Nada executado | [Revisão das migrations](REVISAO_MIGRACOES_A5_2026-11-23.md) |
| A4 | Redefinida com o usuário (bancos de teste já nascem na v8): aplicador revisado e ensaio de atualização do legado com backup e volta atrás, em 22/11 | [Aplicador e ensaio](../testes/APLICADOR_ENSAIO_2026-11-22.md) |
| B1 | Concluída em 23/11: painéis de professor e aluno leem o diário acadêmico; formulário antigo aposentado (410); nenhuma gravação em `notas`; aprovação por ação mantida | [Notas unificadas](../testes/NOTAS_UNIFICADAS_B1_2026-11-23.md) |
| B2 | Concluída em 23/11: com MS04 habilitado, menu aponta para `/aprendizagem`, páginas antigas redirecionam e as 7 gravações antigas respondem 410 (sem proposta); progresso preservado | [Interface única de cursos](../testes/CURSOS_INTERFACE_UNICA_B2_2026-11-23.md) |
| B3 | Concluída em 23/11: linha de base medida (30 páginas, 2 vCPU/2 GB); frequência 172→16 e boletim 96→20 consultas; `/academico` 422→53 KiB; React removido (−250 a 300 ms com CPU 4× lenta). Metas de consulta, peso e LCP cumpridas; gravações e carga ficam pendentes | [Desempenho B3](../testes/DESEMPENHO_B3_2026-11-23.md) |
| B4 | Estudo entregue em 24/11: extras como **ofertas** (turma inteira ou aluno), proposta 009 não executada e 10 contratos RED. **Modelo aprovado**: inscrição do aluno em ofertas abertas, imediata; rótulos configuráveis; implementação no próximo ciclo | [Estudo B4](ESTUDO_ENSINO_SUPERIOR_B4_2026-11-24.md) |
| C1 | Concluída em 24/11: `node infra/demo-completa.cjs start|reset` sobe o Colégio Horizonte (5095) completo e o painel Supremo (5093); 44 páginas verificadas na interface. Oferta do superior entra com a implementação da B4 | [Demo única](../testes/DEMO_COMPLETA_C1_2026-11-24.md) |
| C2 | Coberta pela gravação de 15 min feita pelo usuário (24/11) com `scripts/gravar-demo.ps1` | [Roteiro da gravação](../produto/GRAVACAO_VIDEO_2026-11-25.md) |
| UX | Prioridade a partir de 24/11: objetivos O1–O7 e etapas U1–U5; C3–C5 adiadas | [Plano de UX](PLANO_UX_2026-11-24.md) |

Decisões do usuário em 22/11: o módulo acadêmico (`academico_notas`) passa a ser a única
fonte de notas (B1); a demo única inclui escola e painel Supremo (C1).
Em 23/11 (B1): manter a **aprovação por ação** no diário, ou seja, cada lançamento, correção e
publicação do professor continua sendo uma solicitação aprovada pela secretaria.

## 1. Diagnóstico

| # | Constatação | Evidência | Impacto |
| --- | --- | --- | --- |
| D1 | MS01–MS04 e o painel Supremo só funcionam em bancos de demonstração | Migrations 002–007 e `control_plane/migrations/001_central.sql` pendentes; módulos respondem 503 sem as tabelas | Nada do que foi entregue desde outubro está disponível numa instalação persistente |
| D2 | Não há registro confiável da versão do esquema | `educafast_migracoes` (criada pela 003) tem apenas `versao`; 004–007 não gravam nela; cada módulo confere suas tabelas isoladamente | Impossível dizer com segurança em que versão cada escola está; atualizar várias escolas fica arriscado |
| D3 | Banco novo exige aplicar 7 scripts em sequência | `Codigos/migrations/001`–`007` | Instalar um cliente novo é lento e sujeito a erro |
| D4 | Dois sistemas de notas convivem | Painéis de professor/aluno usam `NotaModel` (`notas`, sem período); o módulo acadêmico usa `academico_notas` com períodos, avaliações e boletim, mais uma tela de reconciliação | Professor pode lançar no lugar errado; aluno pode ver números divergentes |
| D5 | Dois sistemas de cursos convivem | `curso_routes.py` (estrutura antiga) e `cursos_web_routes.py`/`cursos_api_routes.py` (MS04), com troca por `cursos_ms04.comum.habilitado` | Duas interfaces para a mesma tarefa; dívida dobrada |
| D6 | Superior sem matrícula por disciplina como regra de acesso | `alunos_disciplinas` existe, mas o acesso ao conteúdo exige turma **e** disciplina (MS02) | Não dá para vender o superior com oferta por disciplina sem turma fixa |
| D7 | Usabilidade e desempenho não medidos (MS05) | Plano MS05 "a fazer"; metas de `DESEMPENHO.md` provisórias | "Leve e ágil" é uma promessa ainda sem números |
| D8 | Demonstração fragmentada | 4 demos em portas e credenciais diferentes (5050, 5081/5082, 5092, 5093) | Apresentar a um cliente exige trocar de ambiente várias vezes |
| D9 | Material comercial com protótipos, não telas reais | README usa SVGs conceituais; não há roteiro nem guia do usuário | Dificulta mostrar o produto que existe de fato |

## 2. Objetivo do mês

Ao final de 18/12/2026, ter uma **versão candidata identificada** que:

1. Pode ser instalada do zero em PostgreSQL por um caminho único e registra sua versão de esquema.
2. Tem um caminho de atualização revisado e ensaiado em cópia para as escolas que já existem.
3. Tem um único sistema de notas e um único sistema de cursos em uso nas telas.
4. Tem jornadas por perfil medidas e corrigidas (MS05) e o desenho do superior definido.
5. Pode ser demonstrada com **um comando, um endereço e uma escola fictícia completa**, com roteiro e guia.

## 3. Frente A — Ativação do banco

| ID | Trabalho | Saída | Aceite |
| --- | --- | --- | --- |
| A1 | Inventário de esquema somente leitura: estender `schema_preflight.py` para detectar quais das propostas 001–007 estão presentes, parciais ou ausentes | Relatório por instalação, sem expor dados pessoais | Detecta corretamente bancos sintéticos em cada estágio (vazio, até 003, até 007, parcial) |
| A2 | Propor **008 — registro de versão**: completar `educafast_migracoes` (descrição, checksum, data de aplicação) e fazer cada migration registrar sua linha | SQL proposto e regra de verificação na inicialização | App recusa iniciar com esquema mais novo que o código ou com checksum divergente; nada é executado sem revisão |
| A3 | **Esquema base para banco novo**: gerar um SQL único equivalente a 001–008 aplicadas em sequência | `migrations/base/esquema_v8.sql` | CI compara o resultado da base com o resultado sequencial em PostgreSQL e não encontra diferenças |
| A4 | Ensaio de atualização: aplicar 002–008 numa **cópia** dos volumes das escolas Teste 01/02 e do banco central | Relatório com tempos, problemas e rollback ensaiado | Regressão completa passa sobre a cópia; backup/restauração de banco + uploads + `DATA_ENCRYPTION_KEY` recupera os dados |
| A5 | **Sessão de revisão com o usuário**: uma ficha por migration (o que cria, riscos, dados afetados, como reverter) | Fichas + decisão registrada | Usuário aprova, rejeita ou pede ajuste em cada uma. Execução em banco persistente só depois disso |

Decisão necessária em A5: a 002 coloca os professores antigos em quarentena, porque o
banco antigo não registra como cada um foi admitido. É preciso definir a lista de
professores confiáveis antes de aplicá-la.

## 4. Frente B — Produto

| ID | Trabalho | Saída | Aceite |
| --- | --- | --- | --- |
| B1 | **Unificar notas** no módulo acadêmico: painéis de professor e aluno passam a ler/gravar `academico_notas`; `notas` fica somente leitura e entra pela reconciliação existente | Telas atualizadas; nenhuma nova gravação em `notas` | Professor lança só por avaliação/período; aluno vê apenas o boletim publicado; notas antigas aparecem para reconciliação, nunca são apagadas; aprovação de notas preservada |
| B2 | **Aposentar a interface antiga de cursos** quando o MS04 estiver habilitado: menus e links apontam só para `/aprendizagem`; rotas antigas de edição ficam somente leitura | Um caminho de cursos por instalação | Cursos antigos continuam legíveis; a primeira edição adota a versão MS04 (comportamento já existente); progresso preservado |
| B3 | **MS05 — usabilidade e desempenho**: percorrer as jornadas de cada perfil, medir consultas por página, peso de CSS/JS, tempo de resposta e memória; corrigir os piores casos | Relatório com números antes/depois e correções | Metas de `DESEMPENHO.md` confirmadas ou revisadas com dados; inspeção 1440×1000 e 390×844 pelo protocolo de design |
| B4 | **Desenho do ensino superior**: oferta de disciplina por período com matrícula individual, termos configuráveis (série/semestre) | Estudo + contratos de teste (RED) + proposta de esquema | Usuário aprova o modelo. Implementação completa fica para o ciclo seguinte, salvo se sobrar capacidade |

B1 e B2 não dependem da execução das migrations: são desenvolvidos e testados em
bancos descartáveis, como nas entregas anteriores.

## 5. Frente C — Pronto para vender

| ID | Trabalho | Saída | Aceite |
| --- | --- | --- | --- |
| C1 | **Demo única**: `node infra/demo-completa.cjs start` cria uma escola fictícia com turma de ensino médio, oferta de superior, chamadas, avisos, materiais, abas, curso ENEM, notas e boletim; painel Supremo opcional | Um endereço e uma tabela de logins por perfil | Sobe do zero em um comando; `reset` recria os dados; não toca nos bancos persistentes |
| C2 | **Roteiro de demonstração** de 15 minutos: secretaria → professor → aluno → Supremo | `Documentos/produto/ROTEIRO_DEMO.md` | Executado de ponta a ponta na versão candidata, sem passos quebrados |
| C3 | **Guia curto do usuário** por perfil: entrar, rotina, aprovações, arquivos, suporte | `Documentos/produto/GUIA_USUARIO.md` | Revisado pelo usuário; linguagem sem termos técnicos |
| C4 | **Descrição da oferta**: módulos incluídos, opcionais e futuros; requisitos de implantação; limitações conhecidas (sem preços inventados) | `Documentos/produto/OFERTA.md` | Coerente com a tabela de funcionalidades do README |
| C5 | **Capturas reais** das telas da demo, em nova pasta datada de `Documentos/design/referencias/`, e troca dos SVGs conceituais do README pelas telas reais (os SVGs de RH/folha continuam como "planejado") | Manifesto + comparação | Protocolo de design cumprido; capturas antigas preservadas |

## 6. Cronograma

| Semana | Ativação | Produto | Venda |
| --- | --- | --- | --- |
| 1 — 23 a 27/11 | A1 inventário; A2 proposta 008 | B1 desenho e testes de caracterização das notas | C1 esqueleto da demo única |
| 2 — 30/11 a 04/12 | A3 esquema base; A4 ensaio em cópia | B1 implementação; B2 | C1 dados completos |
| 3 — 07 a 11/12 | **A5 sessão de revisão com o usuário** | B3 medição e correções; B4 estudo | C2 roteiro |
| 4 — 14 a 18/12 | Ativação nas escolas de teste, se aprovada em A5 | B3 fechamento; regressão completa | C3, C4, C5; **versão candidata** |

Ao fim de cada semana: registrar entregas, falhas (P0/P1/P2), decisões e próxima
tarefa em `Documentos/testes/`, com commit, ambiente e comando.

## 7. Critérios de aceite do ciclo

- CI completo (SQLite + PostgreSQL + HTTP + protocolo de design) aprovado na versão candidata.
- Instalação do zero pelo esquema base e atualização pela sequência 002–008 resultam no mesmo esquema.
- Backup e restauração ensaiados com banco, uploads e chave de criptografia.
- Nenhuma tela grava em `notas` nem usa a edição antiga de cursos quando o MS04 está habilitado.
- Relatório do MS05 com números medidos, não estimados.
- Demo única executável por quem não participou do desenvolvimento, seguindo o roteiro.
- Nenhuma migration executada em banco persistente sem a aprovação registrada em A5.

## 8. Decisões que dependem do usuário

| Quando | Decisão |
| --- | --- |
| Semana 1 | Confirmar que o módulo acadêmico (`academico_notas`) passa a ser a única fonte de notas |
| Semana 1 | Demo única inclui o painel Supremo ou ele fica numa demonstração separada? |
| Semana 3 | Aprovar ou ajustar cada migration (A5), incluindo a lista de professores confiáveis da 002 |
| Semana 3 | Aprovar o modelo do ensino superior (B4) e decidir se a implementação entra neste ciclo |
| Semana 4 | Aceite da versão candidata e do material comercial |

Também seria útil fazer o merge do PR atual `feature/instancias-clientes-nuvem` → `main`
antes de iniciar, para que o ciclo parta de uma `main` atualizada.

## 9. Riscos

| Risco | Mitigação |
| --- | --- |
| Ensaio A4 revela incompatibilidade nas migrations antigas | Corrigir a proposta antes de A5; o atraso afeta a ativação, não a demo (que usa banco novo) |
| Unificação de notas altera números exibidos | Testes de caracterização antes de mudar; reconciliação explícita, sem conversão silenciosa |
| MS05 encontra problemas maiores que o tempo disponível | Corrigir P0/P1 e registrar o restante com números para o próximo ciclo |
| Escopo do superior crescer | B4 limitado a estudo e contratos neste ciclo |
| Migration com falha no meio | PostgreSQL desfaz a proposta inteira (BEGIN/COMMIT); ainda assim aplicar em cópia primeiro, com backup consistente |

## 10. Fora deste ciclo

Consolidação da documentação, migração dos controllers antigos para services,
remoção de `style=` inline, RH, ponto, folha, financeiro escolar, contratação de
servidor e implantação real.
