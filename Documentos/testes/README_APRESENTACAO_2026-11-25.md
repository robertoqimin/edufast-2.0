# README como apresentação do sistema

Data: 25/11/2026. Branch `feature/melhoria-dezembro`, a partir do commit «chore: registra
execucao visivel de U4 e U5 juntas no Edge». O usuário pediu que o README do GitHub fosse
uma apresentação do sistema, com as telas atuais. **Sem migration.**

## O que mudou

### README

- **Antes:** era uma ficha técnica sem nenhuma tela real. Mostrava "Usabilidade e desempenho"
  como "A fazer" (já feito na B3 e no plano de UX) e as migrations "001–007".
- **Agora é uma apresentação:**
  - proposta e diferenciais;
  - **Experimente**, com um comando (`node infra/demo-completa.cjs start`) e as contas
    fictícias;
  - **Tour pelas telas**, com 14 capturas reais por perfil:
    - direção;
    - secretaria (Turmas, aprovação em lote);
    - professora (chamada, diário);
    - aluno (painel, leitor de PDF, boletim, curso com videoaula);
    - celular;
    - Supremo.
- **Funcionalidades:** a tabela foi atualizada até a U5 e a U2b, e o ensino superior aparece
  como "modelo aprovado; implementação em seguida".
- **Situação:** "beta funcional, pronto para um piloto controlado". Ainda não há instalação
  de produção homologada, e as migrations 001–009 estão revisadas, mas ainda não foram
  aplicadas em banco real.
- **Próximos passos:** ensino superior (B4), passagem de ano, teste com pessoas (SUS) e RH,
  ponto, folha e financeiro.
- **Mantidos:** arquitetura (diagramas), outros ambientes, instalação própria, testes,
  tecnologias, estrutura, contribuição e licença.

### Capturas

- **Pasta nova:**
  [`2026-11-25-apresentacao-readme/`](../design/referencias/2026-11-25-apresentacao-readme/COMPARACAO.md),
  com manifesto (SHA-256), comparação e limitações. Nenhuma captura histórica foi alterada.
- **Script:** `Codigos/tests/capturar_apresentacao_readme.cjs` gera as capturas de novo a
  partir da demo recriada.
- **Galeria:** a pasta foi registrada em `Documentos/design/README.md`.

### Defeito encontrado na inspeção das capturas e corrigido

- **Sintoma:** na tela única de **Turmas** (U5), cada aluno matriculado aparecia numa linha,
  e a vírgula ficava sozinha na linha seguinte.
- **Causa:** o estilo herdado do layout transformava os links em blocos.
- **Correção:** a lista virou etiquetas (`ul.turma-alunos`) que quebram linha, só com tokens
  do design system. Cada nome continua levando ao detalhe do aluno, com foco visível.

### Configuração

- **Problema:** `Codigos/.env.example` não trazia a `DATA_ENCRYPTION_KEY`, que os arquivos,
  vídeos e textos cifrados exigem.
- **Correção:** o arquivo agora traz a variável e o comando que gera a chave, com o aviso de
  guardá-la junto do backup. O README cita a variável na instalação própria.

## Testes

| Verificação | Resultado |
| --- | --- |
| Suíte completa, SQLite | **393 OK** (43 pulados, só PostgreSQL) |
| Acessibilidade (axe-core), demo completa | **84 de 84** páginas sem violações |
| Demo completa pela interface (`verificar_demo_completa.cjs`) | **44 de 44** páginas, 0 falha |
| Capturas da apresentação | 14 de 14, 0 falha (sem rolagem horizontal, sem erro de JavaScript) |
| Protocolo de design | Aprovado |
| Links do README | Todos os 33 caminhos relativos existem |
| Inspeção visual | As 14 imagens foram revistas, e três foram reenquadradas: o diário no topo, o lote de Solicitações abaixo do filtro e o curso com a videoaula da professora no lugar do vídeo de terceiros do YouTube |

A regressão em PostgreSQL não foi repetida: a mudança é só de template e CSS e não toca o
banco.

## Observações

- O roteiro de capturas deixa pendente o lançamento do Simulado, para mostrar a aprovação em
  lote. Depois dele, a demo foi recriada com `node infra/demo-completa.cjs reset`.
- O README descreve o produto para o ensino médio. O ensino superior entra quando a B4 for
  implementada.

## Revisão de 25/11/2026: vitrine sem detalhes internos (pedido do usuário)

O usuário pediu para atualizar imagens, arquitetura e tecnologias **sem revelar detalhes que
exponham a integridade do sistema**.

- **Saiu:**
  - senhas e e-mails de demonstração (o comando da demo os mostra na tela);
  - os nomes dos mecanismos de segurança;
  - endereços, portas, rotas e variáveis de ambiente;
  - detalhes de pipeline, deploy, migrations e sincronização com o painel central;
  - a árvore de pastas e as versões das tecnologias.
- **Ficou:**
  - as 14 capturas atuais;
  - a arquitetura em blocos (aplicação por instituição, banco próprio, painel central);
  - os princípios de projeto em linguagem geral;
  - as tecnologias sem versão;
  - as funcionalidades, com **colégio e faculdade** como "em desenvolvimento".
- **Verificação:**
  - os 17 caminhos de imagens e links existem;
  - a busca por senhas, nomes de mecanismos, portas, rotas e variáveis não encontrou nada.
