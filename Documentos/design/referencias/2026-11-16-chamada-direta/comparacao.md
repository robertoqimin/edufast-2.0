# Comparação — confirmação direta de chamada

Referência anterior: `../2026-11-12-frequencia/manifesto.json`. Capturas anteriores
preservadas. Pedido do usuário em 16/11: professor confirma diretamente a chamada.
Base `7e996a1` mais alterações locais; resultados vinculados a esta árvore de trabalho.

As 14 capturas novas vêm da execução Edge headless concluída em
`2026-11-16T18-28-58-348Z`, com dados fictícios e SQLite em memória.
O manifesto registra os hashes dos arquivos desta execução, sem reaproveitar
aprovação de execução anterior.

Mudanças: botão Confirmar chamada, orientação de registro imediato, estado visível
confirmada, ação Corrigir chamada e formulário de correção com motivo, elenco e
marcações anteriores. Administração consulta chamadas confirmadas sem botão de
aprovação. Formulários de atestado e relatório preservam o fluxo existente.

Layout, DM Sans local, tokens, navegação e componentes compartilhados preservados.
Desktop 1440×1000 e mobile 390×844 sem overflow horizontal na página nem erros JS
no cenário automatizado. Inspeção individual do formulário desktop e da
correção/conferência mobile, complementada pela folha de contato com todas as telas.
Não foram observados cortes ou sobreposições novos. As listas continuam longas;
atalhos para chamada e redução de repetição visual podem ser avaliados no lote de
usabilidade, sem presumir presença de alunos.

Validada somente a identidade padrão. Não houve alteração de tokens/paleta nem
nova inspeção de todas as personalizações. O relatório funcional e as limitações
de MySQL estão em `../../../testes/CHAMADA_DIRETA_2026-11-16.md`.
