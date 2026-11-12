# Login nas escolas de teste — 11/11/2026

Referência de composição: `2026-10-30-r2/login-desktop.png` e `login-mobile.png`.
As referências anteriores permanecem intactas. O manifesto desta pasta contém
hashes das novas capturas e dos fontes testados, com base no commit `9756000` mais
as alterações de correção de acesso descritas no relatório de duas escolas.

O login mantém DM Sans, tokens, ilustração, campos, botão e layout responsivo
existentes. Os nomes Escola Teste 01/02 vêm da configuração de cada instalação.
A mudança perceptível é a orientação no componente de erro existente quando a
sessão não é conservada, além de aviso ao carregar dentro de iframe.

Foram inspecionados login desktop, mensagem de sessão bloqueada desktop/mobile e
painel administrativo mobile. Não foram observados cortes ou sobreposição nesses
estados. O teste também verificou ausência de overflow horizontal nas dez capturas.
Não há comparação pixel a pixel: nomes, contas e registros diferem da referência.

Capturas de erro usam bloqueio de conferência de sessão simulado em contexto de
navegador isolado. O aviso de iframe foi verificado em iframe local de teste; não
representa homologação do navegador interno do VS Code. Sem teste em aparelho
físico, sem teste de carga e sem promessa de funcionamento em prévias embutidas.
