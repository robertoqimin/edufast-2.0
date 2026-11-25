# B4 — Registro do estudo do ensino superior

Data: 24/11/2026. Branch `feature/melhoria-dezembro`, a partir do commit
«feat: registra a turma inteira na materia».

## Entregas

| Entrega | Arquivo |
| --- | --- |
| Estudo do modelo, regras e decisões pedidas | [ESTUDO_ENSINO_SUPERIOR_B4_2026-11-24.md](../planejamento/ESTUDO_ENSINO_SUPERIOR_B4_2026-11-24.md) |
| Proposta de esquema 009 (**não executada**) | `Codigos/migrations/propostas/009_ofertas_extras.sql` |
| 10 contratos de teste (RED) | `.github/cicd/tests/b4_superior/test_contratos_superior.py` |

**Modelo pedido pelo usuário:** a turma recebe da secretaria as disciplinas e os cursos (já
existe); extras (disciplinas e cursos) podem ser pegos pela turma inteira ou por um aluno.

**Proposta:** cada extra é uma **oferta**, uma turma especial de uma disciplina. A turma
inteira pode ser inscrita nela, e os alunos atuais e futuros entram juntos; o aluno também
pode se matricular sozinho. Diário, chamada, materiais, cursos e boletim da oferta funcionam
sem mudar regras de acesso.

## Verificações

- **Contratos:** os 10 falham hoje (`app.services.ofertas` não existe), como esperado para RED.
- **A proposta fica fora da pasta ativa:** `Codigos/migrations/propostas/` não entra no
  inventário de migrations, no registro nem no manifesto congelado da A5.
- **Regressão local:** 343 testes aprovados (43 pulados, os mesmos de antes). A pasta dos
  contratos não é descoberta pela regressão.
- **Banco e código:** nenhuma migration executada e nenhum código de produção alterado.

## Pendente

As 4 decisões do usuário listadas no estudo: inscrição pelo próprio aluno, aprovação ou
inscrição imediata, rótulos configuráveis e momento da implementação.
