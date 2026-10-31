# EducaFast

Antes de alterar interfaces, leia `Documentos/PROTOCOLO_DESIGN.md`. Reutilize tokens,
fontes locais, menu e layout compartilhado. Preserve autenticacao atual, aprovacoes
e garantias do banco. Migrations exigem revisao do usuario antes de executar.

## Preservacao do design

- A fonte visual canonica esta em `Documentos/PROTOCOLO_DESIGN.md` e na galeria
  `Documentos/design/README.md`. Nao substituir esse layout por outro tema ou
  prototipo sem pedido explicito do usuario.
- Reutilizar `design_system.css`, `app.css`, `escola.css`, `gestao_base.html` e os
  parciais `workspace_*`. Personalizacao usa os tokens validados pelo servidor.
- Capturas historicas em `Documentos/design/referencias/` nao sao sobrescritas:
  registrar nova pasta datada, manifesto e comparacao quando o visual mudar.
- Antes de publicar mudancas visuais, executar o verificador de protocolo e os
  testes pertinentes; inspecionar desktop e mobile e registrar falhas/limitacoes.
  Um resumo de uma execucao anterior nao comprova a aprovacao da versao atual.
- Nao versionar `.env`, bancos, uploads, chaves, caches ou logs locais. Migrations
  propostas podem ser versionadas, mas nao executadas sem revisao do usuario.
