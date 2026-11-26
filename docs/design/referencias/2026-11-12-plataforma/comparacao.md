# Painel do proprietário — 12/11/2026

Pedido explícito do proprietário: login exclusivo, visão de todas as escolas,
pessoas e resultado financeiro por escola. Base: commit `5a9c42c`; os arquivos e
estas capturas integram o commit da entrega do painel central.

Reutilizados `gestao_base.html`, `workspace_head`, `workspace_sidebar`,
`workspace_topbar`, `design_system.css`, `app.css`, `escola.css` e DM Sans local.
O menu e a barra superior recebem conteúdo específico para o proprietário;
o ramo escolar permanece com os mesmos endpoints e permissões.

Oito capturas novas em 1440×1000 e 390×844: login, escolas/financeiro, pessoas e
cadastro/lançamentos. Não houve substituição de referências anteriores. O painel
mantém identidade escura/ciano, componentes de formulário, botões, foco e tabelas
do protocolo. As tabelas usam a adaptação móvel compartilhada. Inspeção visual
das telas e teste de largura não identificaram corte ou rolagem horizontal.
Há botão de saída na barra superior também no celular.

Login, logout móvel, paginação, filtro de escola, 52 contas e os totais fictícios
foram conferidos em navegador headless com perfil isolado. Não houve erros de
JavaScript. Os registros são sintéticos e os domínios `.example.test` não são
endereços de escolas ativadas. Não foi exercitada personalização de identidade
central: esta versão utiliza somente os tokens canônicos.

A comparação é com o layout funcional restaurado e a galeria de 30/10, e não com
os protótipos SVG. As telas escolares compartilhadas também passaram na regressão
HTTP de restauração; não foram recapturadas visualmente nesta entrega.
