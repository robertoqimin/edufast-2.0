# B4 — Ensino superior: disciplinas e cursos da turma e extras

Data: 24/11/2026. Etapa B4 do [plano de melhoria](PLANO_MELHORIA_2026-11-22.md). Escopo
decidido pelo usuário: **estudo, testes de contrato e proposta de esquema**. A implementação
acontece só depois de o modelo ser aprovado. Nada aqui foi executado em banco.

## O que o usuário pediu

> Cada turma recebe da secretaria as disciplinas que vai cursar e os cursos. Também haverá
> cursos e disciplinas **extras** que o aluno ou a turma podem pegar: se a turma pegar, vale
> para todo mundo; se o aluno pegar, é só para ele.

## Como o sistema funciona hoje

- Tudo gira em torno do par **turma × disciplina** (`turmas_disciplinas`): avaliações e notas,
  chamadas, materiais, abas, cursos ofertados e a atribuição do professor.
- As listas de alunos da chamada e do diário são **os alunos da turma** (`alunos_turmas`).
- **Desde 24/11**, registrar a turma numa disciplina matricula todos os alunos dela
  (`alunos_disciplinas`), e quem entra na turma depois herda as disciplinas.
- **Cursos** são liberados por par turma × disciplina (`curso_ofertas`).

A parte "base da turma" do pedido **já existe**. Falta o extra.

## Modelo proposto: a oferta

Um **extra é uma oferta**: uma turma especial (`tipo = 'oferta'`) com **uma única
disciplina**, que pode ter os próprios materiais, abas, cursos, avaliações e chamadas. Exemplos:
"Robótica — eletiva — 2026/1" e "Inglês instrumental — 2026/2".

| Quem pega o extra | Como fica | Efeito |
| --- | --- | --- |
| **A turma** | A turma é inscrita na oferta (`turmas_ofertas`) | Todos os alunos atuais entram na oferta; quem entrar na turma depois também entra; quem sair da turma sai da oferta, a menos que tenha matrícula individual nela |
| **O aluno** | Matrícula individual na oferta (`alunos_turmas` com `via_turma_id` vazio) | Só ele entra |

**Por que este modelo:** o aluno da oferta está em `alunos_turmas` da oferta. Por isso
chamada, diário, boletim, materiais e cursos da oferta funcionam **sem mudar nenhuma regra de
acesso**. O aluno não ganha acesso às outras disciplinas de quem está na oferta, e as turmas
regulares não mudam.

**Alternativa descartada:** matrícula por disciplina dentro da turma regular. Exigiria
filtrar por disciplina as listas de chamada, diário, materiais e cursos, com impacto e risco
de vazamento maiores.

### Regras

1. A oferta tem **no máximo uma disciplina**. Registrar uma segunda é recusado.
2. **Inscrição da turma:** inscrever a turma na oferta matricula os alunos atuais e os futuros.
   Retirar a turma remove só quem entrou por ela. As notas e o histórico continuam no boletim.
3. **Matrícula individual:** vale só para o aluno. Se ele também está na oferta pela turma, a
   matrícula individual prevalece quando a turma sair.
4. **Inscrição pelo próprio aluno** (decisão 1): só em oferta **aberta** e **com vaga**. Nunca
   em turma regular. A última vaga é disputada com segurança, sem passar do limite.
5. **Vagas** (decisão 2): contam alunos individuais e alunos vindos de turma.
6. **Período letivo:** a oferta tem um período (ex.: `2026/1`), e o boletim agrupa por ele.
7. **Termos configuráveis** (decisão 3): a escola define os rótulos (Série ou Semestre;
   Turma, Oferta ou Eletiva), sem mudar regras.
8. **Professor:** é atribuído à oferta como a qualquer turma (Gestão acadêmica); nada muda.

### O que fica para depois

Curso de graduação e matriz curricular, pré-requisitos, créditos, equivalência,
transferência e diploma. A oferta não impede nenhum deles: um curso de graduação poderá
agrupar ofertas.

## Proposta de esquema (não executada)

[`Codigos/migrations/propostas/009_ofertas_extras.sql`](../../Codigos/migrations/propostas/009_ofertas_extras.sql),
PostgreSQL e transacional. Ela fica fora da pasta de migrations ativas até a aprovação.

| Mudança | Para quê |
| --- | --- |
| `turmas.tipo` (`regular`/`oferta`, padrão `regular`) | Distinguir turma e oferta. Turmas existentes ficam `regular` |
| `turmas.periodo_letivo` (texto, opcional) | Ex.: `2026/1` |
| `turmas.inscricao_aberta` (padrão falso) e `turmas.vagas` (opcional, maior que 0) | Inscrição pelo próprio aluno e limite |
| `alunos_turmas.via_turma_id` (opcional) | Vazio = matrícula direta; preenchido = entrou pela turma inscrita |
| Tabela `turmas_ofertas` (turma, oferta, única) | A turma inteira inscrita na oferta |
| Tabela `escola_termos` (chave, rótulo) | Rótulos configuráveis |

Não altera nenhum dado existente: só acrescenta colunas com valor padrão e tabelas novas.

## Contratos de teste (RED)

`.github/cicd/tests/b4_superior/test_contratos_superior.py`, com 10 contratos que **falham
hoje**, de propósito. A pasta não entra na regressão (não é pacote Python). Rodar à mão:

```bash
PYTHONPATH="Codigos:.github/cicd/tests" python -m unittest discover -s .github/cicd/tests/b4_superior -v
```

Quando a implementação for aprovada, os contratos passam para a regressão.

## Decisões pedidas ao usuário

| # | Decisão | Recomendação |
| --- | --- | --- |
| 1 | O aluno pode se inscrever **sozinho** num extra, ou só a secretaria inscreve? | Sim, em ofertas que a secretaria marcar como abertas, com vaga |
| 2 | Inscrição pelo aluno é imediata ou precisa de aprovação? | Imediata, com a secretaria podendo desfazer. Não há nota nem material envolvido no ato |
| 3 | Rótulos configuráveis já neste modelo? | Sim (série/semestre; turma/oferta/eletiva) |
| 4 | Implementar neste ciclo ou no próximo? | Próximo ciclo, depois da C1–C5, como o plano prevê |

## Decisões registradas (24/11/2026)

| # | Decisão do usuário |
| --- | --- |
| 1 | **Sim:** o aluno se inscreve sozinho em ofertas que a secretaria marcar como abertas, enquanto houver vaga |
| 2 | **Vale na hora:** inscrição imediata, e a secretaria pode desfazer |
| 3 | **Rótulos configuráveis:** série/semestre e turma/oferta/eletiva |
| 4 | **Próximo ciclo:** a implementação entra depois da frente de venda (C1–C5) |

Modelo aprovado. Na implementação, a proposta 009 passa por revisão final antes de ser
executada (AGENTS.md), e os 10 contratos entram na regressão.
