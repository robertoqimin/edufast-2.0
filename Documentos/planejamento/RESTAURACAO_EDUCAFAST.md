# Restauração funcional e visual — 30/10/2026

Referência: Samucau1/Projeto-Educa-Fast, commit local `cb27d3c`, conferido com
o protocolo e a navegação publicados no GitHub. A cópia fonte em
`../SamusChat/Educafast` será somente lida; contém alterações locais que não serão removidas.

Foram consultados registros locais das conversas de 22 e 23/10, limitados aos
pedidos deste projeto. Eles confirmam gestão de usuários, cursos reutilizáveis,
múltiplos vínculos docentes, regras do boletim por escola e protocolo visual.
Não existe acesso geral à pesquisa do histórico remoto do ChatGPT nesta sessão.

Plano autorizado pelo pedido de restauração:

1. Recuperar protocolo, tokens, fontes e componentes locais, sem CDN; integrar
   os formulários atuais sem retirar idempotência, versões ou CSRF.
2. Recuperar superperfil: usuários/perfis e personalização validada da escola.
   Adaptar o papel histórico `superadmin` ao contrato atual `super_admin`.
3. Recuperar calendários, regras institucionais, cursos, diário, boletim e
   privacidade. Manter as gravações docentes sujeitas à aprovação administrativa;
   a capacidade de revisor continua limitada a materiais da própria disciplina.
4. Preparar SQL separado para tabelas restauradas. Não executar migration nem
   atualizar esquemas existentes sem revisão do usuário. Testes usam schemas novos.
5. Executar protocolo estático, testes de permissão/aprovação, testes originais
   compatíveis, API/regressão e CI; registrar limitações da verificação visual.

A personalização clara/verde deve usar o sistema original de tokens, sem um
segundo CSS de identidade fixo. A referência também inclui o padrão escuro/ciano.
Não haverá restauração por sobreposição dos módulos atuais de autenticação,
download, concorrência, serviços extraídos ou inicialização do banco.
