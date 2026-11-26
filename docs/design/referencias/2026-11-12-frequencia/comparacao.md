# Frequência e atestados — comparação visual

Data: 12/11/2026. Base: `7c39bc0` mais a implementação de frequência.
Todas as capturas usam escola/alunos/professor fictícios em container separado.

As novas telas estendem `gestao_base.html` e usam `workspace_head`, menu, topbar,
DM Sans local, tokens e componentes `panel`, `course-form`, `school-fields`,
`course-table` e `course-scroll`. Não foi criado outro tema ou CSS independente.
Referência de composição: galeria de 30/10 r2 e marcas de 12/11. As capturas
históricas não foram substituídas.

Estados registrados: painel docente, chamada ainda não enviada, conferência
administrativa, atestado pendente de análise e relatório após aceite. Desktop
1440x1000 e mobile 390x844. O teste verifica ausência de overflow horizontal.

Inspeção visual: chamada mobile e relatório desktop sem cortes/sobreposições
observados. As linhas da chamada seguem a adaptação de tabelas do layout existente;
o formulário de 20 alunos exige rolagem vertical. A navegação mobile mantém sua
rolagem interna. Não há comprovação de usabilidade em aparelho físico nem estudo
de tempo para realizar chamada. As telas não representam habilitação nas escolas
persistentes, que aguarda migration revisada.
