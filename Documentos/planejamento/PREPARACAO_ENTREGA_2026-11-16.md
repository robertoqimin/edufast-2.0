# Preparação para entrega — EducaFast

Data: 16/11/2026. Semana de trabalho: 16 a 20/11/2026.
Base inspecionada: `7e996a167c5f40657eab12d9bde36e8af223e030`.

Objetivo solicitado: mapear funcionalidades e novas diretrizes para orientar as
implementações da semana e preparar o software para entrega. Este documento é um
plano de trabalho proposto, não uma homologação nem uma promessa de prazo.

## 1. Alvo e limites

**Públicos e primeira entrega definidos em 16/11:** ensino médio e superior, com
prioridade em usabilidade e baixo consumo de hardware; turmas, chamada confirmada
diretamente pelo professor, materiais, avisos, abas docentes e cursos modulares.
O [plano de implementação por entregas](ENSINO_MEDIO_SUPERIOR_2026-11-16.md)
detalha funcionalidades, diferenças entre segmentos e testes. A confirmação direta
substitui a diretriz anterior de aprovação de chamadas; foi implementada no MS01,
com SQLite/HTTP/navegador aprovados e validação MySQL ainda pendente.

**Alvo esclarecido pelo usuário em 16/11/2026: arquitetar e preparar um produto
para venda; colocar em servidor depois, caso consiga cliente.** A preparação
comercial é o foco atual. Provedor, domínio e implantação real ficam para a etapa
posterior e não impedem o desenvolvimento e a demonstração local do produto.

Preparar funcionalidades completas, qualidade verificável, demonstração com dados
fictícios e um pacote de instalação reproduzível. Preservar o isolamento por
instalação e a separação do painel Supremo. Recuperação e operação devem ser
previstas e ensaiadas localmente quando possível; a validação no servidor escolhido
será requisito antes do uso real. A agenda da semana não promete conclusão do
produto nem data de entrada em produção.

### Etapas de prontidão

| Etapa | Resultado | Dependência de servidor contratado |
| --- | --- | --- |
| A — Produto para apresentação e venda | Escopo claro, jornadas validadas, demonstração, documentação e limites comerciais explícitos | Não |
| B — Pacote preparado para instalação | Versão identificada, configuração por escola, provisionamento revisável, atualização e recuperação ensaiadas em ambiente isolado | Não; pode ser validado localmente com containers |
| C — Implantação do cliente | Infraestrutura dimensionada, domínio/HTTPS, backups externos, alertas, dados conferidos e aceite operacional | Sim, depois da definição do cliente/destino |

Na apresentação comercial, descrever o estado efetivamente validado. Estar pronto
para demonstração não significa que a instalação do cliente já foi homologada.

Manter como base as decisões de 11 e 12/11: aplicação e banco por escola; Supremo
em aplicação/banco central separados; frontend escolar integrado ao Flask.
Documentos anteriores que propõem conta global ou banco compartilhado precisam
ser conciliados antes de orientar novas implementações.

## 2. Mapa das funcionalidades

Legenda: **código identificado** significa presença de rotas/modelos, sem comprovar
o fluxo completo. **Evidência histórica** descreve execuções anteriores e não
aprova a versão candidata desta semana. A ativação depende do esquema de cada
instalação; não foi feita inspeção dos bancos persistentes neste levantamento.

| ID | Área / perfis | Funcionalidades identificadas | Evidência e lacuna para entrega |
| --- | --- | --- | --- |
| F01 | Acesso / todos | Login, sessão, JWT, revogação, restrições por perfil | Regressão histórica em `test_application.py` e `test_approvals_security.py`; repetir na candidata e conferir matriz de acesso |
| F02 | Secretaria / admin | Cadastros de alunos/professores, turmas, disciplinas e vínculos | Diagnóstico de 05/11 com fluxos HTTP; homologar rotina completa e erros com usuário |
| F03 | Aprovações / admin e professor | Propostas e decisões administrativas, controle de versão e repetição | Evidências históricas de transações/concorrência; conferir pendências e correções sem efeitos duplicados |
| F04 | Documentos / perfis autorizados | Solicitação, envio e download | Evidência histórica de propriedade e arquivos; validar fluxo e recuperação junto dos uploads |
| F05 | Comunicação / escola | Comunicados e mensagens | Código em rotas/controllers e diagnóstico HTTP; revisar alcance por perfil e usabilidade |
| F06 | Identidade e administração / superadmin escolar | Usuários, perfis, layout, identidade, calendário e políticas escolares | `gestao_routes.py`, `escola_routes.py`; validar opções permitidas, acessos e preservação de histórico |
| F07 | Cursos / professor, aluno e administração | Biblioteca, capítulos/temas/aulas, ofertas, duplicação, estados e progresso | `curso_routes.py`, `curso_model.py` e restauração; definir inclusão na oferta comercial e testar jornada ponta a ponta |
| F08 | Acadêmico / administração, professor e aluno | Períodos, avaliações, notas, publicação, boletim e reconciliação de legado | `academico_routes.py`; diagnóstico registra lacuna de cobertura integral. Prioridade de homologação |
| F09 | Frequência / professor e administração | Código atual: chamada por turma/matéria com aprovação e relatório/CSV | Testes de 12/11 são históricos; novo requisito: confirmação direta docente (MS01); migration 004 continua adiada nas escolas Teste 01/02 |
| F10 | Atestados / aluno e administração | Envio cifrado, decisão, download restrito e falta justificada | Mesma entrega de frequência; validar ativação e recuperação da chave/arquivo. Aceite não converte falta em presença |
| F11 | Privacidade / titular e administração | Aviso, pedidos, exportação e resposta administrativa | `privacidade_routes.py`, `privacidade_model.py`; conferir fluxo, permissões e política operacional com a escola |
| F12 | Instalações / operador | Ambientes separados, duas escolas sintéticas, geração e atualização por cliente | `infra/` e relatório de duas escolas; falta aceite operacional da instalação real |
| F13 | Supremo / proprietário | Login exclusivo, escolas, diretório de pessoas, receitas/despesas manuais e auditoria | Relatório de 12/11 com testes e navegador; esquema central proposto e operação real pendente |
| F14 | Operação / operador | CI/CD, checagem de esquema, scripts e guias de backup/recuperação | Existem verificações históricas; falta comprovar recuperação por cliente e central na candidata e ambiente escolhidos |
| F15 | Expansão futura | RH, ponto de colaboradores, folha e financeiro escolar completo | Planejados/protótipos. Financeiro manual do Supremo não implementa estes módulos |

Fontes principais: [diagnóstico de 05/11](../testes/DIAGNOSTICO_2026-11-05.md),
[restauração](../testes/ENTREGA_RESTAURACAO.md),
[duas escolas](../testes/DUAS_ESCOLAS_TESTE_2026-11-11.md),
[frequência/API](../testes/API_FREQUENCIA_2026-11-12.md) e
[painel Supremo](../testes/PAINEL_SUPREMO_2026-11-12.md).

## 3. Diretrizes para as próximas implementações

Diretrizes existentes obrigatórias:

- Preservar autenticação, aprovações, transações, idempotência e garantias do banco.
- Seguir o [protocolo de design](../PROTOCOLO_DESIGN.md), reutilizando tokens,
  fontes locais, menu, layout e componentes compartilhados.
- Executar migrations somente depois da revisão do usuário. Preparar SQL, destino,
  diferenças de esquema, backup e ensaio antes de solicitar a revisão final.
- Não versionar segredos, bancos, uploads, caches ou logs locais.
- Manter o Supremo separado do superadmin escolar; não deduzir acesso irrestrito
  a documentos ou contas a partir da hierarquia dos perfis.

Diretrizes propostas para esta semana:

1. Priorizar o fechamento dos fluxos existentes. Acrescentar módulos apenas se
   forem necessários ao alvo de entrega definido pelo usuário.
2. Dar a cada tarefa um ID, perfil afetado, comportamento esperado, dependências
   e evidência de aceite. Estados: a fazer, em andamento, em revisão, validado e
   bloqueado; registrar o motivo do bloqueio.
3. Distinguir código pronto, teste aprovado, esquema disponível e aceite do usuário.
   Uma condição não substitui as outras.
4. Manter uma versão candidata identificada por commit e imagem. Correções
   posteriores exigem repetir as verificações afetadas antes da liberação.
5. Registrar falhas por impacto: P0 impede o fluxo essencial, expõe dados, perde
   dados ou compromete isolamento; P1 compromete uma tarefa do escopo; P2 é melhoria
   que permite executar a tarefa com alternativa documentada. Reavaliar com o usuário.
6. Exigir estados claros de vazio, erro, sucesso, pendência e conflito nos fluxos
   tocados, com acesso por teclado e inspeção desktop/mobile quando visual.
7. Encerrar cada dia registrando entregas, falhas, decisões e a próxima tarefa.
   Não usar contagem de testes como percentual de prontidão do produto.
8. Manter uma base única de código. Configurar identidade e instalação por escola,
   sem criar versões divergentes do produto para cada cliente.
9. Separar funcionalidades entregues, opcionais e futuras na oferta comercial.
   Registrar necessidades de implantação e suporte; preços e compromissos de
   disponibilidade dependem de definição posterior, sem estimativas inventadas.

## 4. Backlog de preparação

Todos os itens abaixo começam **a fazer**. Responsável técnico proposto: desenvolvimento;
decisões de escopo e aceite: usuário/responsável da escola; operação real: operador
a designar. Prioridade não implica defeito confirmado no código.

| ID | Prioridade | Trabalho | Dependência | Critério de aceite |
| --- | --- | --- | --- | --- |
| E01 | P0 | Definir público inicial, perfis e módulos do produto para venda | Preparação comercial confirmada; demais decisões pendentes | Proposta de valor, tipo de escola, módulos essenciais/opcionais/futuros e jornada demonstrável explícitos |
| E02 | P0 | Conciliar README, roadmap e contratos antigos com a arquitetura atual | E01 | Fonte atual indicada; cursos/frequência/Supremo não descritos como inexistentes; propostas futuras separadas |
| E03 | P0 | Preparar instalação reproduzível e revisão de migrations | E01, ambiente descartável | Versão de código/esquema, configuração e ensaio documentados; aplicação em banco persistente continua dependente de revisão do usuário |
| E04 | P0 | Homologar acesso, papéis e isolamento de duas escolas | E01, ambiente descartável | Login/revogação e recusas por perfil; cookies/JWT/arquivos cruzados recusados; contas escolares não administram o Supremo |
| E05 | P0 | Homologar jornada secretaria → professor → aluno | E01, E03 no ambiente de teste | Cadastro → turma/matéria → vínculo → atividade/nota → aprovação → consulta; repetição e falha preservam dados |
| E06 | P0 se incluído | Fechar cobertura de períodos, avaliações, publicação e boletim | E01, E05 | Regra de nota/período definida; professor restrito à oferta; aluno vê apenas boletim autorizado; fechamento/reconciliação conferidos |
| E07 | P0 | Implementar e homologar confirmação direta docente e preservar análise de atestados | E03 em ambiente descartável, MS01 | Chamada confirmada pelo professor → relatório; correção versionada; atestado continua sob análise; falta justificada correta; arquivo restrito e sem duplicações |
| E08 | P0 se incluído | Homologar Supremo e integração do diretório | E01, esquema central de teste | Cadastro e sincronização por escola; snapshot antigo recusado; totais/cancelamento conciliados; nenhuma senha/documento sincronizado |
| E09 | P0 do pacote | Ensaiar backup e restauração de escola e central incluído em ambiente local isolado | E03, destino isolado | Banco, uploads e chaves recuperados; permissões/contagens/arquivos conferidos; outra escola preservada; tempos e limitações registrados |
| E10 | P1 | Revisar interface dos fluxos do escopo | E05–E08 conforme inclusão | Protocolo estático + inspeção desktop/mobile e teclado; capturas novas com manifesto/comparação, sem sobrescrever históricas |
| E11 | Preparar agora; P0 antes do uso real | Documentar requisitos operacionais e checklist de futura implantação | E01/E09 para o plano; cliente/destino para execução real | Agora: requisitos e procedimentos revisáveis. Depois: DNS/TLS, backup externo, alertas, capacidade e suporte validados no destino |
| E12 | P0 | Fechar versão demonstrável e pacote de entrega | Itens aplicáveis às etapas A/B acima | Regressão e jornadas aprovadas; demonstração fictícia reproduzível, guia e limitações; aceite de produto separado do aceite operacional futuro |

Cursos, privacidade, documentos e comunicação entram na jornada E05 ou recebem
cenários próprios conforme o escopo E01. Não omitir uma área prometida por não
ter um item de implementação separado nesta tabela.

Preparar E09/E11 desde o início da semana: procedimentos de instalação, atualização,
backup, recuperação e requisitos de monitoramento. Provedor, domínio, destino
externo dos backups e responsáveis operacionais serão definidos na implantação.
Backup precisa incluir banco/uploads consistentes e recuperação restrita das chaves;
uma cópia isolada do banco não comprova recuperação de documentos cifrados.

Antes de receber dados reais, registrar com cada cliente: escopo contratado,
responsável pela implantação, regras de acesso, importação e conferência dos dados,
retenção, atendimento de pedidos de privacidade, canal/horário de suporte e resposta
a incidentes. Definir metas operacionais antes de prometer disponibilidade ou
capacidade. Este planejamento não constitui avaliação de conformidade legal.

## 5. Sequência proposta para a semana

| Dia | Foco | Saída verificável |
| --- | --- | --- |
| Segunda, 16/11 | Escopo comercial e diagnóstico dirigido | Alvo produto para venda confirmado; proposta E01; requisitos de instalação; problemas reproduzíveis priorizados |
| Terça, 17/11 | Rotina escolar e permissões | E04/E05 exercitados; correções essenciais e cenários acadêmicos E06 |
| Quarta, 18/11 | Frequência, atestados e central conforme escopo | E07/E08 exercitados; revisão de propostas de esquema preparada, sem execução automática |
| Quinta, 19/11 | Recuperação local, experiência e pacote | Ensaio E09, inspeção E10 e checklist de implantação E11 documentado |
| Sexta, 20/11 | Regressão e demonstração comercial | Versão identificada, roteiro de demonstração, guia, pendências e avaliação de prontidão para apresentação |

Agenda proposta, sujeita a capacidade e falhas encontradas. Se itens P0 não forem
concluídos, registrar nova previsão ou reduzir explicitamente o escopo com o
usuário. Não remover garantias ou declarar aceite para cumprir uma data.

## 6. Critérios de prontidão

Para apresentar o produto e preparar seu pacote (etapas A/B):

- Cada funcionalidade prometida tem cenário executado na candidata e aceite do
  responsável; nenhum P0 ou P1 do escopo permanece aberto sem resolução de escopo.
- Testes pertinentes rodam em ambiente descartável, com MySQL para contratos que
  dependem dele. Testes que criam/recriam tabelas não usam conexões persistentes.
- Evidência identifica data, commit/imagem, ambiente, comando, resultado, cenários
  ignorados e limitações. Resultados de outubro/12 de novembro são referências.
- Propostas de migrations e plano de implantação/recuperação estão disponíveis
  para revisão; instalação e recuperação são ensaiadas em ambiente descartável.
  Ativar em banco persistente depende de revisão do usuário e validação por destino.
- Mudanças visuais cumprem o protocolo e têm inspeção atual em 1440×1000 e 390×844.
- Guia curto cobre início, perfis, rotina, aprovações, arquivos e como pedir suporte.
  Limitações conhecidas acompanham a entrega.
- Demonstração usa dados fictícios e permite mostrar uma jornada completa por
  perfil; apresentação distingue módulos existentes e planejados.

Antes de operar com dados reais no servidor do cliente (etapa C):

- HTTPS, credenciais próprias, backup externo com rotina/retenção definidas,
  recuperação ensaiada no destino, alertas, capacidade medida, suporte e
  responsabilidades definidos. Validar monitoramento e acionamento do responsável.
- Compatibilidade do esquema, migrations revisadas, importação de dados quando
  necessária e aceite operacional registrados por instalação.

## 7. Decisões que ainda precisam ser fechadas

1. Público definido: ensino médio e superior; detalhar regras de matrícula por
   disciplina e estrutura curricular necessárias ao primeiro cenário superior.
2. Rotina e conteúdo definidos no plano MS00–MS05; fechar alcance de notas/boletim
   e do painel central na demonstração comercial.
3. Quais regras de nota, período e calendário compõem a configuração inicial?
4. Como será apresentada a oferta: módulos incluídos, opcionais, implantação e suporte?

Na etapa de implantação, após haver cliente: quantidade de escolas/usuários,
destino/domínios, responsável operacional, volume esperado, janela de manutenção,
responsáveis pelo aceite e metas de perda de dados/tempo de recuperação.

Enquanto essas decisões não estiverem registradas, este plano orienta levantamento
e preparação, sem presumir contratação de infraestrutura ou ativação de bancos.

## 8. Registro deste levantamento

Em 16/11 foram lidos documentos, inventariados arquivos e inspecionadas rotas,
modelos e histórico recente do Git. A árvore estava limpa no início. Não foram
executados testes funcionais, servidores, migrations, deploy, carga ou inspeção
visual nesta tarefa documental. Nenhum resultado histórico foi revalidado aqui.

Esclarecimento final de escopo em 16/11: o usuário quer arquitetar um produto para
venda e só depois, caso consiga cliente, colocá-lo em servidor. Esta definição
substitui a interpretação anterior de implantação comercial imediata. E01 permanece
parcialmente definido; E09 é ensaio local do pacote e E11 separa documentação atual
da execução operacional futura. Não houve execução de migrations, contratação ou deploy.
