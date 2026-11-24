# B3 — MS05: desempenho e usabilidade medidos

Data: 23/11/2026. Branch `feature/melhoria-dezembro`, a partir do commit
«feat: aposenta interface antiga de cursos com MS04 (B2)». Etapa B3 do
[plano de melhoria](../planejamento/PLANO_MELHORIA_2026-11-22.md), com as metas de
[DESEMPENHO.md](../planejamento/DESEMPENHO.md).

## Como foi medido

**Servidor** (`python .github/cicd/run_desempenho.py --nome <execucao>`):
- PostgreSQL 17 descartável com **0,5 vCPU / 512 MiB** e aplicação com **1,5 vCPU / 1,5 GiB**,
  ou seja, o orçamento de 2 vCPU e 2 GB do `DESEMPENHO.md`, em modo produção.
- Banco criado pelo **esquema base v8**, como numa escola nova.
- Massa sintética determinística (`.github/cicd/desempenho/massa.py`, escala padrão):
  - 10 turmas, 350 alunos, 8 disciplinas e professores;
  - 40 períodos, 640 avaliações e 16.800 notas;
  - 1.600 chamadas e 56.000 presenças;
  - 8 cursos em 80 ofertas, com 4.178 progressos;
  - 40 comunicados e 20 solicitações pendentes.
- Para cada página da jornada de cada perfil: 3 aquecimentos e **30 amostras**, com p50/p95,
  número de consultas SQL por requisição, tamanho do HTML e peso inicial (HTML + CSS + JS
  próprios, com gzip, como o gateway entrega).
- O tempo é medido no processo da aplicação. Isso exclui a rede e o servidor WSGI, e inclui
  rotas, banco, templates e serialização.

**Navegador** (`node .github/cicd/desempenho/medir_navegador.cjs <url> <saida.json> 5`):
- Edge com **CPU 4× mais lenta**, **5 Mbit/s de download, 1 Mbit/s de upload e +150 ms**
  (perfil "computador modesto + rede limitada"), cache frio a cada execução.
- Mediana de 5 execuções.
- Servidor da escola de teste local, sem gzip: os bytes transferidos são brutos.

Limitação: o perfil é simulado no mesmo computador; ainda falta uma rodada em equipamento
real, como o `DESEMPENHO.md` prevê.

## Linha de base (antes) e resultado (depois)

Consultas SQL, p50/p95 em milissegundos e HTML em KiB. As páginas não alteradas variam alguns
milissegundos entre as execuções: é ruído do host, com o mesmo código.

| Perfil | Página | Consultas | p50 (ms) | p95 (ms) | HTML (KiB) |
| --- | --- | --- | --- | --- | --- |
| secretaria | `/admin/dashboard` | 15 → 15 | 16.9 → 20.6 | 20.8 → 27.5 | 18 → 18 |
| secretaria | `/admin/banco-de-dados` | 15 → 15 | 19.2 → 20.7 | 69.4 → 25.5 | 127 → 127 |
| secretaria | `/admin/turmas` | 16 → 16 | 22.9 → 30.4 | 33.8 → 53.8 | 104 → 104 |
| secretaria | `/admin/disciplinas` | 12 → 12 | 14.3 → 16.4 | 17.4 → 28.3 | 23 → 23 |
| secretaria | `/admin/alunos/1` | 12 → 12 | 13.7 → 14.6 | 14.7 → 19.5 | 18 → 18 |
| secretaria | `/admin/professores/1` | 16 → 16 | 22.6 → 26.0 | 36.3 → 36.3 | 26 → 26 |
| secretaria | `/solicitacoes` | 11 → 11 | 15.0 → 22.7 | 19.6 → 31.2 | 25 → 25 |
| secretaria | `/academico` | 16 → 15 | 98.1 → 20.3 | 139.8 → 23.4 | 422 → 53 |
| secretaria | `/academico/avaliacoes/1` | 19 → 19 | 19.3 → 23.3 | 24.9 → 35.4 | 14 → 14 |
| secretaria | `/academico/alunos/1/boletim` | 96 → 20 | 65.4 → 27.3 | 73.3 → 37.7 | 28 → 28 |
| secretaria | `/frequencia` | 14 → 14 | 25.1 → 25.5 | 56.4 → 54.3 | 50 → 50 |
| secretaria | `/frequencia/relatorio` | 12 → 12 | 15.8 → 16.9 | 18.7 → 20.1 | 11 → 11 |
| secretaria | `/aprendizagem` | 17 → 17 | 19.8 → 20.2 | 24.9 → 25.0 | 13 → 13 |
| secretaria | `/admin/comunicados` | 10 → 10 | 12.1 → 12.9 | 13.6 → 15.4 | 16 → 16 |
| secretaria | `/mensagens` | 12 → 12 | 14.9 → 16.5 | 20.9 → 21.4 | 51 → 51 |
| professor | `/professor/dashboard` | 24 → 24 | 41.3 → 50.0 | 74.9 → 103.5 | 221 → 221 |
| professor | `/academico` | 17 → 15 | 21.9 → 23.3 | 24.5 → 51.8 | 38 → 39 |
| professor | `/academico/avaliacoes/1` | 21 → 21 | 21.4 → 23.9 | 30.6 → 29.7 | 11 → 11 |
| professor | `/frequencia` | 172 → 16 | 96.2 → 27.8 | 105.6 → 53.7 | 26 → 26 |
| professor | `/frequencia/turmas/101/chamada` | 17 → 17 | 18.2 → 22.4 | 23.3 → 36.3 | 19 → 19 |
| professor | `/estudos` | 13 → 13 | 18.4 → 30.5 | 21.0 → 44.6 | 9 → 9 |
| professor | `/aprendizagem` | 18 → 18 | 20.9 → 25.8 | 28.1 → 33.9 | 8 → 8 |
| professor | `/solicitacoes` | 11 → 11 | 20.0 → 23.3 | 29.5 → 32.2 | 56 → 56 |
| aluno | `/aluno/dashboard` | 101 → 25 | 69.2 → 29.3 | 113.8 → 61.1 | 32 → 32 |
| aluno | `/boletim` | 96 → 20 | 68.8 → 26.1 | 76.3 → 59.9 | 25 → 25 |
| aluno | `/frequencia` | 13 → 13 | 14.6 → 17.1 | 19.5 → 25.4 | 8 → 8 |
| aluno | `/aprendizagem` | 22 → 22 | 37.3 → 40.6 | 54.1 → 57.6 | 11 → 11 |
| aluno | `/aprendizagem/ofertas/1` | 32 → 32 | 29.9 → 30.2 | 62.4 → 45.7 | 11 → 11 |
| aluno | `/estudos` | 12 → 12 | 21.1 → 23.8 | 41.6 → 35.4 | 8 → 8 |
| aluno | `/aluno/disciplinas/1` | 14 → 14 | 16.1 → 18.2 | 18.0 → 25.8 | 9 → 9 |

**Metas do `DESEMPENHO.md`:**
- **Consulta comum, p95 até 500 ms:** cumprida em todas as 30 páginas, antes e depois.
  O maior p95 depois é 103,5 ms (painel do professor).
- **Recursos iniciais até 300 KiB:** cumprida. O peso inicial com gzip vai de 16 a 75 KiB por
  página; depois da troca do React, as páginas antigas perderam mais 45 KiB.
- **Conteúdo visível até 3 s no perfil limitado:** cumprida. O pior caso medido é 0,9 s.
- **Memória:** pico de 258 MiB no processo da aplicação, dentro do limite de 1,5 GiB.
- **Gravação comum, p95 até 1 s:** não medida nesta etapa; fica registrada como pendência.
  A medição cobriu as páginas de consulta das jornadas.

## Problemas encontrados e corrigidos

1. **Frequência do professor: 172 consultas por página.** O painel verificava a permissão
   de **cada par turma×disciplina da escola**, um por vez.
   - **Correção:** `frequencia_service.pares_permitidos()` aplica a mesma regra de `scope()`
     em consultas fixas.
   - **Resultado:** 172 → 16 consultas, p50 de 96 → 28 ms.
   - **Garantia:** um teste compara as duas versões para administrador, professor com
     atribuição ativa, inativa ou de outro professor, vínculo antigo sem atribuição e aluno.
2. **Boletim: 96 consultas.** Afetava o boletim do aluno, o da secretaria e o painel do aluno,
   que usa o boletim desde a B1. Eram três ou mais consultas por período×disciplina, e a regra
   do período era repetida a cada grupo.
   - **Correção:** avaliações, notas, regras e políticas buscadas em lote (`regras_periodos()`
     e `resumo_anual()` em lote), com a mesma saída.
   - **Resultado:** 96 → 20 consultas, p50 de 69 → 26 ms; painel do aluno de 101 → 25 consultas.
3. **`/academico` da secretaria: 422 KiB de HTML** com todas as turmas, e o template
   percorria períodos × avaliações para cada oferta.
   - **Correção:** agrupamento feito no servidor, e a secretaria vê **uma turma por vez**, com
     o seletor "Turma exibida" (a primeira por padrão). O professor continua vendo todas as
     suas turmas, com filtro opcional. O formato JSON não mudou.
   - **Resultado:** 422 → 53 KiB e p50 de 98 → 20 ms.
4. **React nas páginas antigas.** Painéis de admin, professor e aluno, cadastros, detalhes,
   turmas, disciplinas e comunicados carregavam React + ReactDOM (138 KiB de JS, 45 KiB
   comprimidos) só para copiar um `<template>` para a tela e ligar as abas.
   - **Decisão do usuário:** trocar por JavaScript simples.
   - **Correção:** `shell_react.js` monta o mesmo `div.react-shell` com o conteúdo do template
     e dispara o mesmo evento no mesmo momento. Os nomes foram mantidos, e os arquivos do
     React saíram de `static/vendor`.
   - **Resultado no Edge limitado:**

     | Página | Conteúdo visível (LCP) antes → depois | Transferido (bruto) |
     | --- | --- | --- |
     | `/professor/dashboard` | 1152 → **896 ms** | 290 → 151 KiB |
     | `/aluno/dashboard` | 1112 → **812 ms** | 276 → 136 KiB |
     | `/admin/dashboard` | 1120 → **832 ms** | 274 → 134 KiB |
     | Referência sem shell (`/academico`, `/boletim`, `/solicitacoes`) | ~690–730 ms, sem mudança | ~104–109 KiB |

   - **Mesma tela:** 32 capturas antes/depois (16 telas e abas × desktop e celular) foram
     comparadas pixel a pixel. **24 ficaram idênticas.** As 8 diferenças são horários de
     criação de registros, porque a escola de teste foi recriada entre as capturas
     (conferido lado a lado), ou 1 pixel do cursor de texto. Sem erros de JavaScript e sem
     rolagem horizontal. A jornada completa do professor (lançar, aprovar, publicar e o aluno
     ver) passou numa aba visível do Edge depois da troca.

## Testes

**Novos:** `test_desempenho_consultas.py`, com 4 guardas determinísticas:
- a regra em lote é igual à individual;
- o painel de frequência e o boletim **não ganham consultas** quando a escola cresce;
- o `/academico` da secretaria mostra uma turma por vez e o do professor mostra todas.

Rodados contra o código anterior, os três guardas de crescimento **falham** (frequência
20 → 64 consultas; boletim 25 → 73), o que confirma que pegam a regressão.

**Ferramentas versionadas:** `.github/cicd/run_desempenho.py`,
`.github/cicd/desempenho/massa.py`, `medir.py` e `medir_navegador.cjs`. Evidências das
medições em `.ci-results/desempenho/` (não versionado).

### Resultados

Bateria completa em containers sobre o código final, com o fonte conferido como inalterado
durante a regressão. **Todas as 9 etapas foram aprovadas na mesma execução.** Evidências em
`.ci-results/desempenho-b3-2026-11-23/`.

| Etapa | Resultado |
| --- | --- |
| Regressão SQLite | 329 testes aprovados, 43 pulados (os mesmos de antes) |
| Regressão PostgreSQL + concorrência real | 329 aprovados, 2 pulados |
| HTTP real | 117 verificações aprovadas |
| `ci.py`: imagem de produção (sem React), unitários, HTTPS, backup/restauração e uploads | Aprovado (11 unitários; 329 + 329 testes) |
| Piloto de duas escolas | Aprovado |
| API de frequência | 117 verificações aprovadas |
| Ensaio de atualização legado → v8 | Aprovado |
| Painel central (Supremo) | 18 testes aprovados |
| Postman SQLite / PostgreSQL | 66 requisições e 76 verificações, 0 falhas em cada |

Também passaram localmente:
- suíte completa (329 testes);
- verificador de protocolo de design;
- `test_submission.cjs` (3);
- `test_ci_characterization.py`, `next_stage.py --check` e `infra/verify.sh` (20 casos).

**Nota sobre o tempo do `ci.py`:** a etapa levou 17.607 s de relógio, contra cerca de 380 s
nas baterias anteriores. Os testes dentro dela tiveram duração normal (122 s em SQLite e
267 s em PostgreSQL). O tempo extra foi parada do host ou do Docker entre comandos, não
lentidão da aplicação. O resultado foi aprovado sem repetição.

## Inspeção visual

- Capturas novas e manifesto em
  [referências de 23/11 — B3](../design/referencias/2026-11-23-desempenho-b3/COMPARACAO.md).
- Seletor de turma em 1440×1000 e 390×844, sem rolagem horizontal, com os componentes
  existentes.
- Verificador de protocolo aprovado.

## Pendências registradas

- **Gravações (p95 até 1 s) e carga com sessões simultâneas** (1, 10 e 25) não foram medidas.
- **Rodada em equipamento real** (computador modesto e celular de entrada), com os perfis do
  `DESEMPENHO.md`.
- **Ainda grandes:** `/professor/dashboard` (221 KiB de HTML, lista os alunos de todas as
  turmas), `/admin/banco-de-dados` (127 KiB) e `/admin/turmas` (104 KiB). Estão dentro das
  metas na escala medida, mas crescem com a escola. Candidatos a paginação no próximo ciclo.
- Limitação já existente: o destaque do menu nas abas dos painéis (registrado na B1).

## Próxima etapa

B4 — desenho do ensino superior (estudo, contratos de teste e proposta de esquema para
aprovação).
