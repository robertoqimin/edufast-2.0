# Protocolo de design EducaFast — v1

Data: 24/10/2026. Obrigatório para novas interfaces e alterações visuais deste repositório. Referência: `design_system.css`, `app.css`, `gestao_base.html`, `workspace_head.html`, menu, topbar e telas existentes de gestão. A identidade padrão permanece escura, com DM Sans, destaque ciano, cartões, bordas discretas e navegação lateral que se adapta ao móvel.

## 1. Composição

- Estender `gestao_base.html`; reutilizar menu, topbar, ícones e os estados de erro/sucesso existentes. Telas públicas com estrutura própria devem incluir `workspace_head.html`.
- Usar `page-heading`, `eyebrow`, `panel`, `button`, `button-primary`, `button-secondary`, `notice` e os componentes de formulário/tabela já existentes. Os módulos acadêmicos usam os componentes `course-*`, centralizados em `escola.css`.
- Hierarquia: título da página, descrição curta, ações primárias e cartões por assunto. Rascunho, pendência, bloqueio e estado vazio precisam ser compreensíveis.
- Evitar informações técnicas de banco, tokens, migração ou implementação no fluxo do usuário. Explicar consequências: aplicação de regras, proteção de histórico e alteração de acessos.

## 2. Tokens e personalização

Usar `--page`, `--surface`, `--surface-hover`, `--line`, `--text`, `--muted`, `--accent`, `--accent-soft`, `--school-radius`, `--school-space`, `--school-font` e `--school-button-text`. Novas cores de componente devem derivar desses tokens. Não copiar blocos independentes de estilos para cada página.

O superadmin pode alterar nome, sigla, subtítulo, cores, modo claro/escuro, DM Sans/fonte do dispositivo, espaçamento e raio dentro das opções suportadas. O sistema valida valores e contraste. Não aceitar CSS, HTML, JavaScript, URLs de fonte ou código arbitrário como configuração.

`workspace_head.html` é a única fronteira autorizada para emitir tokens dinâmicos em um bloco de estilo: valores vêm de enums, cores hexadecimais e textos previamente validados. Templates novos não devem usar `style=`, `<style>`, eventos inline ou CDN. Templates legados existentes têm exceções históricas; ao alterá-las, remover a exceção na área tocada quando viável.

## 3. Interação e acessibilidade

Todo campo tem label; botões descrevem sua ação; foco deve ser visível; controles devem funcionar por teclado. Erros preservam o estado persistido e explicam como revisar. Formulários de gravação usam CSRF. Mudanças concorrentes devem retornar conflito em vez de sobrescrever trabalho silenciosamente.

A validação interna exige contraste mínimo de 4,5 entre textos e superfície. Novos componentes devem usar esse contraste também no fundo da página e nos botões. Conferir desktop em 1440×1000 e móvel em 390×844: sem cortes, sobreposição ou rolagem horizontal na página; tabelas podem rolar dentro de seu contêiner. A navegação lateral móvel mantém o comportamento do EducaFast.

## 4. Portões de entrega

1. Antes da mudança: identificar os componentes de referência e os tokens necessários.
2. Implementar no layout compartilhado e executar `python api/tests/verificar_protocolo_design.py`.
3. Testar permissões e fluxo funcional relevante; o verificador estático não substitui testes de comportamento.
4. Capturar e inspecionar visualmente a interface padrão e a personalização exercitada, em desktop e móvel. Registrar limitações reais.
5. Registrar evidências com referência ao commit, revisar o diff e só então publicar.

Uma mudança não recebe aprovação visual apenas porque o CSS compila. Ajustar os componentes em caso de contraste ruim, corte, desalinhamento ou diferença injustificada em relação ao padrão EducaFast. Os testes de navegador específicos ficam em `tests/verificar_*.cjs`; relatórios em `docs/testes/`.

## 5. Preservação no Git — complemento v1.1, 30/10/2026

A referência deste protocolo é o projeto funcional `Samucau1/Projeto-Educa-Fast`,
commit `cb27d3c`. Os SVGs de apresentação em `docs/prototipo/edufast/` são conceitos
distintos e não substituem as telas funcionais recuperadas.

- [Galeria e catálogo das capturas](design/README.md): login, painéis, superperfil,
  aprovações e personalização, com referências desktop e celular.
- [Manifesto das referências de 30/10/2026](design/referencias/2026-10-30/manifesto.json):
  identifica arquivos, tamanhos e hashes SHA-256 para detectar alterações.
- [Revisão visual r2 aprovada](design/referencias/2026-10-30-r2/manifesto.json):
  23 capturas, incluindo acesso negado, sem substituir a primeira referência.
- `AGENTS.md` exige a leitura deste protocolo antes de alterar interfaces.
- O workflow `.github/workflows/ci.yml` executa
  `python api/tests/verificar_protocolo_design.py`.

Uma mudança intencional de identidade precisa registrar o pedido do usuário,
atualizar componentes/tokens compartilhados e criar novas capturas em outra pasta
datada. Não apagar nem substituir a referência anterior e não contornar testes de
permissão, CSRF ou concorrência para fazer uma tela funcionar.

Capturas são evidências visuais, não prova isolada de funcionamento. Registrar
qual execução passou, qual falhou e o que não foi verificado. Não reutilizar um
`resumo.json` antigo como aprovação de uma execução posterior incompleta.

Para voltar a uma versão, criar uma branch a partir do commit aprovado ou reverter
o commit responsável pela regressão. Não reescrever a `main`, não fazer force push
e não restaurar arquivos antigos de autenticação ou banco junto de uma correção visual.
