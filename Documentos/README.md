# Documentação do EduFast

[Apresentação do projeto](../README.md)

| Documento | Conteúdo |
| --- | --- |
| [Plano de melhoria — dezembro/2026](planejamento/PLANO_MELHORIA_2026-11-22.md) | Ativação do banco, unificação de notas e cursos, MS05, ensino superior e demo única para venda |
| [U1 — Clareza, acessibilidade e estado — 24/11](testes/U1_EXPERIENCIA_2026-11-24.md) | Mensagens corrigidas, erro amigável no navegador, acessibilidade 64/64 com auditoria no CI, estado de cada envio visível |
| [Plano de experiência do usuário — 24/11](planejamento/PLANO_UX_2026-11-24.md) | Diagnóstico medido (acessibilidade 56/64, 12 telas antigas, 81 mensagens sem acento), objetivos O1–O7 com metas e etapas U1–U5; estudar sem baixar |
| [C1 — Demo única — 24/11](testes/DEMO_COMPLETA_C1_2026-11-24.md) | `node infra/demo-completa.cjs start`: escola fictícia completa (notas, chamadas, materiais, abas, curso ENEM) e painel Supremo; tabela de logins |
| [B4 — Ensino superior: ofertas extras — 24/11](planejamento/ESTUDO_ENSINO_SUPERIOR_B4_2026-11-24.md) · [registro](testes/B4_ESTUDO_SUPERIOR_2026-11-24.md) | Disciplinas e cursos extras pegos pela turma inteira ou por um aluno; proposta 009 e contratos RED, aguardando aprovação |
| [Turma registrada na matéria — 24/11](testes/TURMA_MATERIA_2026-11-24.md) · [capturas](design/referencias/2026-11-24-turma-materia/COMPARACAO.md) | A secretaria registra a turma inteira na matéria e todos os alunos entram nela; quem entra depois herda as matérias; professor não traz matérias extras; retirada só sem histórico |
| [Roteiro da gravação do vídeo — 25/11](produto/GRAVACAO_VIDEO_2026-11-25.md) · [ensaio](testes/ENSAIO_GRAVACAO_2026-11-24.md) | Ambiente de gravação (escola vazia, porta 5070), roteiro Supremo → super admin → admin → professor → aluno ensaiado em 37 passos; matrícula nas disciplinas da turma corrigida |
| [B3 — Desempenho medido (MS05) — 23/11](testes/DESEMPENHO_B3_2026-11-23.md) · [capturas](design/referencias/2026-11-23-desempenho-b3/COMPARACAO.md) | Linha de base por perfil, N+1 corrigidos, diário da secretaria por turma, React removido; números antes/depois |
| [B2 — Interface única de cursos — 23/11](testes/CURSOS_INTERFACE_UNICA_B2_2026-11-23.md) | Com MS04 habilitado, `/aprendizagem` é o único caminho: páginas antigas redirecionam, gravações antigas respondem 410, progresso preservado |
| [B1 — Notas unificadas — 23/11](testes/NOTAS_UNIFICADAS_B1_2026-11-23.md) · [capturas](design/referencias/2026-11-23-notas-unificadas/COMPARACAO.md) | Professor lança só no diário (com aprovação), aluno vê só o boletim publicado, tabela antiga `notas` somente leitura e preservada |
| [A1 — Inventário de esquema — 22/11](testes/INVENTARIO_ESQUEMA_2026-11-22.md) | Relatório somente leitura de quais migrations estão aplicadas, parciais ou ausentes em cada banco |
| [A5 — Revisão das migrations — 23/11](planejamento/REVISAO_MIGRACOES_A5_2026-11-23.md) · [registro](testes/REVISAO_A5_2026-11-23.md) | Fichas de cada migration e decisões do usuário: tudo aprovado, quarentena geral na 002, nada executado |
| [Correções de segurança S1–S7 — 23/11](testes/SEGURANCA_CORRECOES_2026-11-23.md) | Limite de 5 tentativas no login, resposta única, regra de senha, CSP e proteção contra clickjacking, bibliotecas atualizadas |
| [Regressão, Postman e segurança — 22/11](testes/REGRESSAO_SEGURANCA_2026-11-22.md) | Regressão 291 testes, Postman nos dois bancos e revisão de segurança com 13 achados priorizados |
| [A4 — Aplicador e ensaio de atualização — 22/11](testes/APLICADOR_ENSAIO_2026-11-22.md) | Ferramenta revisada de aplicação com checksum, arquivos congelados e ensaio legado → v8 com backup e volta atrás |
| [A3 — Esquema base — 22/11](testes/ESQUEMA_BASE_2026-11-22.md) | Banco novo criado por um único SQL revisável, idêntico ao caminho legado + 001–008 |
| [A2 — Registro de migrations — 22/11](testes/REGISTRO_MIGRACOES_2026-11-22.md) | Proposta 008: registro de versões, detecção do passado e recusa de banco incompatível na inicialização |
| [Troca para PostgreSQL — 22/11](testes/MIGRACAO_POSTGRESQL_2026-11-22.md) | MySQL → PostgreSQL 17 em toda a plataforma, caminhos de arquivos corrigidos, pasta `Codigos/` sem acento e regressão comparada |
| [Backend e API MS04 — 20/11](testes/API_CURSOS_MS04_2026-11-20.md) | Rascunhos, publicação, retomada, texto/vídeo, recursos privados, SQL 007 e testes sem frontend |
| [Esqueleto MS04 e caminhos de implementação](planejamento/ESQUELETO_MS04_2026-11-20.md) | Serviços isolados, catálogo de rotas/aceite, modelo conceitual e início pelo lote A |
| [Estudo MS04 — cursos modulares](planejamento/ESTUDO_MS04_CURSOS_MODULARES_2026-11-19.md) | Diagnóstico atual, hierarquia confirmada, retomada, autoria, aulas sem vídeo e proposta de implementação |
| [Revisão para publicação — 19/11](testes/REVISAO_PRE_COMMIT_2026-11-19.md) | Compatibilidade com a main, API HTTP/Postman, regressão e validação visual atuais |
| [Abas da disciplina — 19/11](testes/ABAS_DISCIPLINA_2026-11-19.md) | MS03: autoria, ordenação, arquivamento, histórico e proposta SQL 006 |
| [Espaço da disciplina — 16/11](testes/ESPACO_DISCIPLINA_2026-11-16.md) | MS02: avisos, links, arquivos privados, publicação revisada e proposta SQL 005 |
| [Confirmação direta de chamada — 16/11](testes/CHAMADA_DIRETA_2026-11-16.md) | MS01: confirmação docente, correção com histórico, testes atuais e limites de MySQL |
| [Primeira versão — ensino médio e superior](planejamento/ENSINO_MEDIO_SUPERIOR_2026-11-16.md) | Turmas, confirmação docente de presença, materiais, abas, cursos modulares e entregas com testes |
| [Preparação para entrega — 16/11/2026](planejamento/PREPARACAO_ENTREGA_2026-11-16.md) | Mapa funcional, diretrizes propostas, prioridades, agenda da semana e critérios de liberação |
| [Protocolo de design](PROTOCOLO_DESIGN.md) | Layout, tokens, acessibilidade e portões de entrega |
| [Galeria visual preservada](design/README.md) | Prints desktop/celular e manifesto das referências |
| [Organização do Git](design/ORGANIZACAO_GIT.md) | Escopo dos commits, arquivos locais e revisão |
| [Entrega da restauração](testes/ENTREGA_RESTAURACAO.md) | Resultados executados e pendências conhecidas |
| [Arquitetura](arquitetura/ARQUITETURA.md) | Camadas, dados, requisições e evolução |
| [Estudo para várias escolas](arquitetura/ESTUDO_MULTIESCOLAS.md) | Estratégias de isolamento, organização dos dados, disponibilidade e evolução |
| [Instâncias por cliente — plano de aplicação](planejamento/INSTANCIAS_POR_CLIENTE_2026-11-11.md) | Mapeamento de banco, backend e frontend próprios, ações e critérios de aceite |
| [Duas escolas de teste](testes/DUAS_ESCOLAS_TESTE_2026-11-11.md) | Teste 01 e Teste 02, com 20 alunos, 5 professores e 3 matérias cada; acessos locais e evidências |
| [Frequência e atestados](testes/FREQUENCIA_2026-11-12.md) | Chamadas docentes com aprovação, faltas justificadas, relatório e migration para revisão |
| [Testes de API de frequência](testes/API_FREQUENCIA_2026-11-12.md) | Runner reproduzível em SQLite/MySQL e HTTP real, contratos e resultados |
| [Ambientes locais, nuvem e híbridos](../infra/README.md) | Geração de ambientes por escola, limites de tráfego e modelo de recuperação |
| [Revisão antes do commit](testes/REVISAO_PRE_COMMIT_2026-11-04.md) | Testes atuais, preservação visual e ambiente para avaliação manual |
| [Telas e UX/UI](produto/TELAS_E_UX.md) | Telas existentes, protótipos e critérios de experiência |
| [Execução](operacao/EXECUCAO.md) | Ambiente, configuração, comandos e persistência |
| [CI/CD e produção](../.github/cicd/README.md) | Testes, imagem, deploy e recuperação |
| [Roadmap](planejamento/ROADMAP.md) | Etapas, dependências e critérios de entrega |
| [Próxima versão](planejamento/PROXIMA_VERSAO.md) | Acadêmico e secretaria para várias escolas; isolamento, migração e backlog |
| [Desempenho](planejamento/DESEMPENHO.md) | Experiência em hardware modesto, orçamento de recursos e testes de carga |
| [Testes para revisão](testes/proxima-versao/README.md) | API, unitários e integração preparados antes da implementação |
| [Concorrência e repetição](testes/CONCORRENCIA.md) | Correções, comparação com a base, regressão e coleção Postman |
| [Planejamento anterior](planejamento/PLANEJAMENTO_EDUCAFAST.md) | Proposta histórica de cursos e gestão acadêmica |
| [Histórico de testes](testes/README.md) | Origem e limites dos logs preservados |
| [Arquivo CI2](arquivo/README.md) | Pacote histórico e suas dependências |

## Referências originais

O [painel do proprietário](planejamento/PAINEL_SUPREMO_2026-11-12.md) reúne escolas,
pessoas e financeiro; consulte também o [relatório de validação](testes/PAINEL_SUPREMO_2026-11-12.md).

Os documentos abaixo foram preservados como fontes históricas. Podem usar a identidade anterior “Secretaria Escolar DF” e não substituem a descrição atual do código.

- [Arquitetura original em PDF](Documentação%20de%20Arquitetura%20do%20Sistema.docx%20%2814%29.pdf)
- [Arquitetura em DOCX](documentacao-arquitetura-secretaria-df.docx)
- [Casos de uso em Markdown](Especificação%20de%20Casos%20de%20Uso.md)
- [Casos de uso em PDF](Especificação%20de%20Casos%20de%20Uso.pdf)
- [UX/UI em DOCX](Documentacao_UX_UI_SecretariaDF.docx)
- [Relatório de API em DOCX](relatorio-api-secretaria-df.docx)
- [Plano de negócios original](plano%20de%20negócios)

Mantenha documentação técnica em `arquitetura`, decisões de experiência em `produto`, instruções de execução em `operacao` e propostas futuras em `planejamento`. Resultados de novos testes devem informar commit, ambiente, comando e data, sem sobrescrever evidências históricas.

## Cursos MS04 — frontend e demonstração

[Teste manual de aluno/professor e resultados do frontend ENEM](testes/FRONTEND_CURSOS_MS04_2026-11-20.md).
