# Cursos MS04 — comparação visual de 20/11/2026

Base: layout funcional documentado no protocolo e na galeria de 30/10/2026-r2.
Mantidos DM Sans local, menu, topbar, cartões, botões e tokens compartilhados.
Adicionadas telas de biblioteca, editor e estudo; nenhuma captura histórica foi
substituída. As novas imagens mostram somente dados fictícios.

O aluno vê leitura e navegação em duas colunas no desktop; no celular, a aula
vem antes do índice. Módulos podem ser recolhidos pelo controle nativo `details`.
Professor organiza os níveis com formulários e botões para subir/descer;
edições publicadas apresentam conteúdo sem controles de alteração.

As duas paletas usam o mecanismo existente, com valores claros/verde validados
no servidor da fixture QA. Não há tema alternativo independente. Avisos de
revisão passaram a usar os tokens de texto, superfície e borda neste módulo,
corrigindo o texto rosado com pouco contraste no fundo claro.

Inspecionadas visualmente bibliotecas de aluno/professor, leitura desktop/mobile,
edição de aula mobile, editor mobile claro, revisão administrativa, publicação
mobile e player antes do clique. Nas execuções finais, 40 capturas passaram nas
checagens automáticas de overflow e token dos avisos. Editor tem rolagem vertical
longa com grupos expandidos; não houve corte horizontal nos tamanhos testados.
Menu móvel conserva a rolagem horizontal interna já existente.

| Tela | Escuro desktop | Escuro celular |
| --- | --- | --- |
| Biblioteca do aluno | [Abrir](escuro-biblioteca-aluno-desktop.png) | [Abrir](escuro-biblioteca-aluno-mobile.png) |
| Aula de texto | [Abrir](escuro-aula-texto-desktop.png) | [Abrir](escuro-aula-texto-mobile.png) |
| Organização do professor | [Abrir](escuro-editor-professor-desktop.png) | [Abrir](escuro-editor-professor-mobile.png) |
| Edição da aula | [Abrir](escuro-editar-aula-desktop.png) | [Abrir](escuro-editar-aula-mobile.png) |
| Revisão | [Abrir](escuro-curso-em-revisao-desktop.png) | [Abrir](escuro-curso-em-revisao-mobile.png) |

| Tela | Claro desktop | Claro celular |
| --- | --- | --- |
| Aula de texto | [Abrir](claro-aula-texto-desktop.png) | [Abrir](claro-aula-texto-mobile.png) |
| Organização do professor | [Abrir](claro-editor-professor-desktop.png) | [Abrir](claro-editor-professor-mobile.png) |
| Avisos de revisão corrigidos | [Abrir](claro-curso-em-revisao-desktop.png) | [Abrir](claro-curso-em-revisao-mobile.png) |

O manifesto registra hashes, dimensões de viewport, commit-base e execução.
A versão inspecionada é o checkout local ainda sem commit, não o commit-base
isoladamente. Vídeo externo foi substituído no teste; reprodução real não foi
homologada. Detalhes funcionais e limites no [relatório](../../../testes/FRONTEND_CURSOS_MS04_2026-11-20.md).
