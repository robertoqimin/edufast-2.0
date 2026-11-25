# C1 — Demonstração única: escola completa e painel Supremo

Data: 24/11/2026. Branch `feature/melhoria-dezembro`, a partir do commit
«docs: registra aprovacao do modelo de ofertas extras (B4)». Etapa C1 do
[plano de melhoria](../planejamento/PLANO_MELHORIA_2026-11-22.md).

## Como usar

```bash
node infra/demo-completa.cjs start    # sobe a escola (5095) e o painel Supremo (5093)
node infra/demo-completa.cjs reset    # apaga só a escola da demo e recria do zero
node infra/demo-completa.cjs stop     # para, mantendo os dados
node infra/demo-completa.cjs status
```

O comando imprime os endereços e a tabela de logins. A senha de todos os perfis da escola é
`Demo-EduFast-2026!`, e a do Supremo é `Plataforma-teste-2026!`. Somente dados fictícios.

## O que a escola de demonstração traz

| Item | Conteúdo |
| --- | --- |
| Identidade | Colégio Horizonte (sigla CH) |
| Contas | Super admin (direção), secretaria, 3 professores (Matemática, Língua Portuguesa, Biologia) e 12 alunos |
| Organização | Turma 1º ano A (ensino médio, 2026) com as 3 disciplinas registradas e professores atribuídos; 36 matrículas nas disciplinas |
| Calendário e boletim | Calendário 2026 e regra bimestral aplicada à turma pelas telas do super admin |
| Notas | 12 avaliações (prova e trabalho por disciplina, no 1º e no 2º bimestre) com 144 notas publicadas; 1º bimestre fechado |
| Frequência | 30 chamadas confirmadas e 360 presenças |
| Espaço da disciplina | 3 abas e 8 materiais publicados (avisos, apostila e roteiro em PDF, imagem e links), enviados pelos professores e aprovados pela secretaria pelas rotas reais |
| Cursos | Matemática para o ENEM (12 aulas) montado, publicado com aprovação e ofertado à turma pelas rotas reais |
| Comunicados | 2 comunicados da secretaria |
| Painel Supremo | Demonstração com duas escolas fictícias, pessoas e financeiro |

## Implementação

- **`Codigos/demo_completa.py`:**
  - só aceita o banco descartável `edufast_demo_completa`, com `EDUFAST_DEMO_COMPLETA=1`;
  - cria o esquema base v8 se o banco estiver vazio e recusa o banco se já houver contas;
  - contas e organização entram direto no banco; calendário, regras, abas, materiais (com
    arquivos cifrados), aprovações e o curso passam pelas rotas do sistema.
- **`Codigos/enem_demo_server.py`:** a montagem do curso do ENEM virou a função
  `montar_curso_enem`, reutilizada pela demo. A demo ENEM existente continua igual.
- **`infra/demo-completa.cjs`:**
  - usa o compose do ambiente manual com projeto (`edufast-demo-completa`), banco, volumes,
    segredos (`.ci-results/demo-completa/.env`) e porta (5095) próprios;
  - não toca no ambiente manual, nas escolas Teste 01/02 nem na escola de gravação.
- **`Codigos/tests/verificar_demo_completa.cjs`:** verificação pela interface no Edge.

## Verificações

| Verificação | Resultado |
| --- | --- |
| `start` do zero | Escola pronta em um comando, com a tabela de logins |
| Contagem no banco | 17 contas, 36 matrículas, 4 períodos (1 fechado), 12 avaliações, 144 notas, 30 chamadas, 360 presenças, 3 abas, 8 materiais publicados, 1 curso ofertado, 2 comunicados, 0 solicitações pendentes |
| `reset` | Escola recriada do zero com os mesmos dados |
| Interface (`verificar_demo_completa.cjs`) | **44 páginas**: Supremo, super admin, secretaria, professora e aluno, em desktop e celular. Conteúdo esperado presente, sem erro de JavaScript e sem rolagem horizontal |
| Suíte completa local | 343 testes aprovados (43 pulados, os mesmos de antes) |
| Protocolo de design e `infra/test_demo.cjs` | Aprovados |

**Ajuste durante a etapa:** na primeira rodada, o aviso de boas-vindas ficou dentro de uma
aba temática e o aluno não o via na aba "Avisos". A massa passou a deixar os avisos na aba
geral e os materiais nas abas temáticas, e a verificação passou.

## Limitações

- **Ensino superior:** o plano previa uma "oferta de superior" na demo, mas o modelo foi
  aprovado na B4 para implementação no próximo ciclo. A demo será ampliada quando as ofertas
  existirem.
- **Painel Supremo:** é a demonstração em memória já existente (duas escolas fictícias). Ele
  não lista o Colégio Horizonte, porque a sincronização de pessoas é feita pelo operador.
- **Notas e chamadas:** foram criadas direto no banco como dados de demonstração, sem
  aprovação de cada lançamento. O fluxo real com aprovação está coberto pelos testes e pela
  demonstração do vídeo.

## Próxima etapa

C2: roteiro de demonstração de 15 minutos. Pode reaproveitar `scripts/demo_video.cjs`.
