# Comparação — abas da disciplina (MS03)

Data: 19/11/2026. Base `85aed36` mais alterações locais MS02/MS03.
As referências de 30/10, 12/11 e 16/11 permanecem preservadas.

O lote mantém `gestao_base.html`, menu/topbar, DM Sans local, os tokens e os
componentes `school-tabs`, `course-form`, `course-outline`, `panel` e `button`.
Não adiciona CSS, JavaScript ou dependências de interface. A nova tela Organizar
abas usa formulários HTML, com labels, CSRF, idempotência e versão.

Mudanças: ação Organizar abas na disciplina, abas docentes após as duas abas
padrão, seleção da aba ao preparar conteúdo e estados vazios/arquivados.
Ordenação por número, com desempate pela criação. Rascunhos continuam privados
até aprovação; arquivamento explica a revogação de acesso, preservando histórico.

As 28 capturas são da execução completa `2026-11-19T14-55-39-351Z`, Edge headless,
SQLite em memória, dados fictícios, em 1440×1000 e 390×844. O manifesto registra
hashes das imagens e dos fontes relevantes. O navegador repetiu a jornada MS02
e acrescentou criação/renomeação/ordenação/arquivamento de aba, seleção no
rascunho, publicação revisada e recusa de acesso direto após arquivamento.
Sem erros JavaScript ou rolagem horizontal na página. Tab entre nome e ordem
foi exercitado; o formulário mantém foco visível nos componentes compartilhados.

Inspeção da folha de contato das 28 imagens e, em tamanho integral, da organização
desktop/mobile e do formulário mobile com seleção de aba: sem novos cortes ou
sobreposições. O menu móvel conserva a rolagem interna do layout compartilhado.
A tela de organização cresce verticalmente conforme os formulários existentes.
Somente a identidade padrão foi inspecionada; paletas personalizadas e testes com
leitor de tela não foram homologados neste lote.

Não há drag-and-drop, restauração de abas arquivadas ou movimentação de conteúdos
antigos nesta etapa. Conteúdo existente continua nas abas padrão; a nova
associação é definida ao criar o rascunho. Propostas 005/006 aguardam revisão.
Resultados e limites: [relatório MS03](../../../testes/ABAS_DISCIPLINA_2026-11-19.md).
