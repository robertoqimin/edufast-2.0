# U1 — Clareza, acessibilidade e estado visível

Data: 24/11/2026. Branch `feature/melhoria-dezembro`, a partir do commit
«docs: traca plano de experiencia do usuario (UX) com linha de base medida». Etapa U1 do
[plano de UX](../planejamento/PLANO_UX_2026-11-24.md) (objetivos O4, O5 e O6).

## Resultado das metas

| Meta | Antes | Depois |
| --- | --- | --- |
| O4 — mensagens sem acento ou jargão | 81 de 290 | **0** (144 mensagens corrigidas); nomes internos de campo trocados por nomes legíveis ("Confira o campo título.") |
| O4 — formulários respondendo JSON cru no navegador | 8 rotas | **0**: página de erro amigável com a mensagem, o mesmo código HTTP e "Voltar e corrigir"; clientes de API continuam recebendo JSON |
| O5 — páginas sem violações WCAG 2.1 AA (axe-core) | 56 de 64 | **64 de 64** |
| O5 — auditoria no CI | Não havia | Job `acessibilidade` no `ci.yml`: sobe a demo completa e reprova se houver qualquer violação |
| O6 — estado visível | "rascunho" cru; nada sobre aprovação ou liberação | "Rascunho — só você vê", "Aguardando aprovação da secretaria", "Publicado para a turma"; editor de curso explica que falta a secretaria liberar para a turma |
| O6 — menu dos painéis antigos | Destacava sempre a primeira aba | Acompanha a aba aberta (classe e `aria-pressed`) |
| O6 — confirmação de envio | Envios do professor no painel antigo não davam retorno | Aviso "Solicitação enviada para aprovação." nas 12 telas antigas, pelo parcial único `partials/avisos.html`; avisos de erro com estilo de erro também no layout padrão |
| Detalhe — nome do admin | Pedido e descartado | Campo oculto para administrador |

## Mudanças

- **Mensagens:** literais de mensagem em 20 arquivos (`MutationConflict`, `abort`, `erro`,
  `mensagem`, `flash`), revisados com dicionário fechado. O que está entre `{}` em f-strings
  nunca é alterado. Mensagem dividida em duas linhas corrigida à mão.
- **`api/app/views/respostas.py`:** `resposta_erro` e `pagina_erro`. O botão "Voltar e
  corrigir" só aponta para caminhos do próprio site; um `Referer` externo é ignorado (teste
  cobre). Também usado pelos tratadores globais de `MutationConflict` e `StaleDataError`.
- **Acessibilidade:**
  - nomes acessíveis no formulário de atividade do professor;
  - contraste corrigido com o token `--muted` (validado pelo servidor) em vez de cores fixas:
    rodapé do login, selo "Protegido", rodapé da lista e nota de mensagens.
- **Estado:**
  - `estudo_routes.disciplina` passa as publicações pendentes (`aguardando`);
  - rótulos de estado no Espaço da disciplina;
  - aviso no editor de cursos;
  - `shell_react.js` atualiza a aba ativa.
- **CI e auditoria:** `api/tests/auditar_acessibilidade.cjs` aceita
  `AUDIT_CHANNEL=chromium` (no CI não há Edge) e sai com erro se houver violações.

## Testes

**Novos:** `test_u1_experiencia.py`, com 9 casos:
- guarda que impede mensagens sem acento de voltarem;
- página de erro com volta ao formulário;
- API continua em JSON;
- "voltar" nunca leva a outro site;
- confirmação de envio na tela;
- rótulos acessíveis e menu;
- nome de admin oculto;
- estados "Rascunho" e "Aguardando aprovação";
- aviso do curso sem turma.

**Atualizados:** 3 testes que conferiam o texto antigo, sem acento.

**Resultados:**
- suíte completa: **352 testes** aprovados, em SQLite de arquivo e em memória (43 pulados, os
  mesmos de antes);
- protocolo de design, `test_submission.cjs` (3), `test_ci_characterization.py` e
  `next_stage.py --check` aprovados;
- auditoria de acessibilidade: 64 de 64 páginas;
- verificação da demo pela interface: 44 páginas, 0 falhas;
- YAML do workflow validado, com os jobs `validar` e `acessibilidade`.

**Ainda não comprovado:** o job `acessibilidade` com Chromium em Linux só roda de verdade no
GitHub Actions, num pull request. Localmente a auditoria foi validada com o Edge.

## Inspeção visual

[Capturas de 24/11 — U1](../design/referencias/2026-11-24-u1-experiencia/manifesto.json), em
1440×1000 e 390×844: menu com a aba certa, página de erro e cadastro de admin sem nome.

## Observado para a U5

As telas antigas mostram "Educa Fast" no caminho do topo em vez do nome da página. Isso será
resolvido na migração para o layout padrão.

## Próxima etapa

U2 — estudar sem baixar (O7).
