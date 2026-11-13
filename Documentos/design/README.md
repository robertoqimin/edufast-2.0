# Referência visual EducaFast

Este catálogo preserva o design funcional recuperado do `Projeto-Educa-Fast`,
commit `cb27d3c`: DM Sans local, navegação lateral, barra superior, cartões e tema
escuro/ciano. A paleta clara/verde usa a personalização do mesmo sistema de tokens.

Leia o [protocolo obrigatório](../PROTOCOLO_DESIGN.md) antes de alterar interfaces.
As imagens abaixo usam somente contas e dados fictícios do ambiente manual.

## Galeria de 30/10/2026

| Tela | Desktop | Celular |
| --- | --- | --- |
| Login | [Abrir](referencias/2026-10-30-r2/login-desktop.png) | [Abrir](referencias/2026-10-30-r2/login-mobile.png) |
| Usuários e permissões do superperfil | [Abrir](referencias/2026-10-30-r2/usuarios-desktop.png) | [Abrir](referencias/2026-10-30-r2/usuarios-mobile.png) |
| Aparência | [Abrir](referencias/2026-10-30-r2/aparencia-desktop.png) | [Abrir](referencias/2026-10-30-r2/aparencia-mobile.png) |
| Regras e identidade da escola | [Abrir](referencias/2026-10-30-r2/regras-desktop.png) | [Abrir](referencias/2026-10-30-r2/regras-mobile.png) |
| Identidade personalizada | [Abrir](referencias/2026-10-30-r2/identidade-personalizada-desktop.png) | [Abrir](referencias/2026-10-30-r2/identidade-personalizada-mobile.png) |
| Aprovações administrativas | [Abrir](referencias/2026-10-30-r2/aprovacoes-desktop.png) | [Abrir](referencias/2026-10-30-r2/aprovacoes-mobile.png) |
| Painel administrativo | [Abrir](referencias/2026-10-30-r2/admin-desktop.png) | [Abrir](referencias/2026-10-30-r2/admin-mobile.png) |
| Painel do professor | [Abrir](referencias/2026-10-30-r2/professor-desktop.png) | [Abrir](referencias/2026-10-30-r2/professor-mobile.png) |
| Propostas do professor | [Abrir](referencias/2026-10-30-r2/propostas-docentes-desktop.png) | [Abrir](referencias/2026-10-30-r2/propostas-docentes-mobile.png) |
| Painel do aluno | [Abrir](referencias/2026-10-30-r2/aluno-desktop.png) | [Abrir](referencias/2026-10-30-r2/aluno-mobile.png) |
| Acesso negado | [Abrir](referencias/2026-10-30-r2/acesso-negado-desktop.png) | [Abrir](referencias/2026-10-30-r2/acesso-negado-mobile.png) |

[Diálogo de novo usuário](referencias/2026-10-30-r2/novo-usuario.png) ·
[Manifesto e hashes](referencias/2026-10-30-r2/manifesto.json)

![Usuários e permissões](referencias/2026-10-30-r2/usuarios-desktop.png)

## Situacao da validacao

O [painel do proprietário de 12/11](referencias/2026-11-12-plataforma/manifesto.json)
possui oito capturas novas, com [comparação e limites](referencias/2026-11-12-plataforma/comparacao.md),
preservando as referências escolares anteriores.

A revisao r2 passou na execucao completa do navegador: login, quatro perfis,
superperfil, formularios, identidade personalizada e acesso negado, em 1440×1000
e 390×844, sem erros JavaScript e sem rolagem horizontal na pagina.

A selecao da representacao HTML/JSON foi corrigida sem alterar a autorizacao:
acesso negado continua HTTP 403; os 18 contratos antigos da API foram repetidos
e passaram. O CI completo registrou 96 testes MySQL e 96 SQLite (15 cenarios
exclusivos de MySQL ignorados neste ultimo); a suite restaurada teve mais uma
rodada focada MySQL aprovada. Postman: 57 requisicoes e 65 assercoes aprovadas.

A [primeira referencia de 21 imagens](referencias/2026-10-30/manifesto.json),
anterior ao fechamento da pendencia visual, permanece preservada. A galeria
principal usa os 23 prints da r2, incluindo a tela de acesso negado.

[Relatorio e limites da entrega](../testes/ENTREGA_RESTAURACAO.md).
Configuracoes, bancos, logs e capturas temporarias continuam fora do Git.
