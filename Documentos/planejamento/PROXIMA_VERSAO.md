# Próxima versão — acadêmico e secretaria para várias escolas

[Roadmap](ROADMAP.md) · [Arquitetura atual](../arquitetura/ARQUITETURA.md)

Planejamento atualizado em 26/10/2026. Este documento define a próxima entrega; as funcionalidades propostas ainda não estão implementadas.

**Processo confirmado:** preparar e revisar os [testes de API, unitários e integração](../testes/proxima-versao/README.md) antes de implementar a próxima versão. A implementação funcional aguarda a leitura do usuário.

## Decisões confirmadas

- Prioridade: consolidar gestão acadêmica e secretaria.
- Público: várias escolas em uma mesma plataforma.
- Direção de experiência: agilidade, clareza e consistência de UX/UI.
- Diferencial confirmado: boa experiência em computadores e celulares modestos, com consumo controlado de recursos no servidor. [Requisitos e medição de desempenho](DESEMPENHO.md).
- A visão de gestão completa permanece, com RH, ponto, folha e financeiro em etapas posteriores.

## Proposta de versão inicial

Permitir que uma escola organize um período letivo, cadastre sua equipe e seus alunos, monte turmas, faça matrículas, atribua professores e acompanhe documentos e comunicados, preservando a separação entre instituições.

Fluxo principal de aceite:

**Criar escola → configurar período → vincular equipe → criar disciplinas e turmas → cadastrar aluno → matricular → atribuir professor → acompanhar pendências.**

O fluxo precisa ser demonstrado com duas escolas distintas, incluindo uma pessoa que participa das duas com permissões diferentes.

## Fronteira entre instituições

Proposta técnica: cada escola é um contexto isolado de dados, chamado de tenant. A primeira versão pode compartilhar banco e aplicação, com `escola_id` obrigatório nos registros pertencentes à instituição. Essa escolha precisa ser confirmada antes das migrações.

Unidade ou campus é uma possível subdivisão da escola, não uma segunda forma de representar o mesmo contexto. Redes mantenedoras, compartilhamento entre escolas e administração consolidada ficam fora desta primeira entrega.

| Informação | Regra proposta |
| --- | --- |
| Identidade de acesso | Conta global; uma pessoa pode participar de várias escolas |
| Participação | Vínculo explícito entre conta e escola, com estado e papéis locais |
| Perfil de aluno ou professor | Registro próprio em cada escola; não concede acesso por existir em outra |
| Escola ativa na navegação | Selecionada entre vínculos autorizados e revalidada no servidor |
| Cadastros e documentos | Pertencem a uma escola; consultas e operações aplicam esse escopo |
| Matrícula e código de turma | Unicidade conforme escola e período, sem impor unicidade global indevida |
| Acesso de suporte | Excepcional, explícito e auditado; sem acesso irrestrito por padrão |

Não confiar apenas no filtro da tela, no ID enviado pelo navegador ou em um campo de escola dentro do token. A conta precisa manter participação ativa e permissão para o recurso em cada requisição. Trocar de escola não transfere documentos, papéis ou autorizações.

## Perfis e permissões propostos

| Perfil | Responsabilidade |
| --- | --- |
| Administrador da plataforma | Criar e acompanhar instituições e acessos operacionais; sem acesso automático ao conteúdo acadêmico |
| Gestor da escola | Configurar a instituição e administrar sua equipe e permissões |
| Secretaria | Cadastros, matrículas, turmas e documentos da própria escola |
| Coordenação | Organização pedagógica, atribuições docentes e acompanhamento acadêmico |
| Professor | Turmas e disciplinas explicitamente atribuídas naquela escola |
| Aluno | Seus vínculos, atividades, notas e documentos naquela escola |
| Responsável — etapa posterior | Acesso mediante vínculo verificado com o aluno |

O atual `UsuarioModel.tipo` é global e não representa esse modelo. A migração deverá introduzir papéis por participação e remover sua utilização como autorização global nas rotas convertidas. Não converter professores em administradores de todas as escolas nem conceder permissões pelo simples cadastro da conta.

## Escopo funcional

| Área | Entrega da próxima versão | Critério de aceite |
| --- | --- | --- |
| Escolas | Cadastro institucional, estado e seleção de contexto | Usuário só lista e seleciona escolas autorizadas |
| Equipe e acesso | Convite/vínculo, papéis e revogação | Convite não concede papel em outra escola; revogação bloqueia novas requisições |
| Períodos | Ano/período letivo com estados e regras de fechamento | Turmas e matrículas preservam seu contexto histórico |
| Pessoas | Cadastros locais de alunos e docentes; responsáveis em cadastro, se necessário | Busca e edição não revelam cadastros externos |
| Turmas | Criação, consulta, composição e arquivamento | Histórico preservado; operação repetida não duplica vínculo |
| Matrículas | Vínculo do aluno ao período/turma e mudanças de estado | Transferência encerra um vínculo e cria outro com histórico |
| Docência | Atribuição explícita professor + oferta da disciplina + turma | Vínculos separados não autorizam combinações não atribuídas |
| Documentos | Solicitação, envio, situação e consulta autorizada | Download e arquivos de perfil respeitam a escola e o vínculo |
| Comunicação | Comunicados com destinatários e contexto claros | Só o público autorizado consulta o comunicado |
| Painel | Pendências e atalhos derivados dos dados da escola ativa | Indicadores abrem listas com filtros correspondentes |

Notas e atividades existentes precisam continuar funcionando durante a evolução. A ampliação do histórico por período exige migração própria; a chave atual aluno/disciplina não comporta repetição da mesma disciplina em períodos diferentes.

## Entidades e integridade propostas

| Entidade | Função |
| --- | --- |
| Escola | Instituição e estado operacional |
| ParticipacaoEscola | Conta, escola, estado e papéis locais |
| ConviteEscola | Destinatário, escola, papéis permitidos, validade e utilização única |
| PeriodoLetivo | Calendário e estado vinculados à escola |
| Matricula | Aluno, turma/período, situação e histórico de movimentações |
| OfertaDisciplina | Disciplina oferecida em uma turma e período |
| AtribuicaoDocente | Professor autorizado para a oferta |
| EventoAuditoria | Ator, escola, ação, recurso e resultado, sem conteúdo sensível desnecessário |

Entidades existentes recebem escopo institucional conforme sua responsabilidade. Chaves e restrições devem impedir vínculos cruzados no banco, por exemplo referenciando pares `(escola_id, id)` e definindo unicidade local. Apenas adicionar uma coluna ou um filtro genérico não resolve toda a autorização.

Arquivos devem ter proprietário e escola identificados no banco, nomes internos não previsíveis e entrega por rota autorizada. Listagens, exportações, relatórios, tarefas em segundo plano e eventuais caches também precisam carregar e aplicar o contexto institucional.

## Sequência de implementação

| Ordem | Entrega revisável | Evidência para avançar |
| --- | --- | --- |
| 1 | Mapa de rotas, dados, arquivos e regras de acesso; decisão de modelo de escolas | Todas as entradas existentes classificadas como globais ou institucionais |
| 2 | Migrações versionadas e ensaio de conversão de uma instalação legada | Banco novo e cópia sintética do legado migrados; integridade conferida |
| 3 | Participações, seleção de escola e autorização centralizada | Duas escolas e conta com papéis diferentes sem vazamento entre contextos |
| 4 | Conversão integral das rotas, arquivos e consultas existentes | URLs diretas, downloads e entradas antigas também aplicam isolamento |
| 5 | Períodos, matrículas e atribuição docente explícita | Fluxo acadêmico completo com histórico e validações |
| 6 | Painel de secretaria e componentes compartilhados | Navegação por teclado, celular, mensagens e estados validados |
| 7 | Homologação e piloto | CI aprovado, restauração ensaiada e tarefas reais demonstradas |

A conversão pode ser desenvolvida em partes, mas a oferta de várias escolas só deve ser habilitada quando todas as entradas institucionais estiverem protegidas. Uma rota antiga sem escopo invalida o isolamento.

## Migração dos dados existentes

1. Identificar a instituição proprietária dos dados e criar sua escola inicial; não distribuir automaticamente registros entre instituições.
2. Introduzir migrações versionadas antes de mudar o esquema persistente.
3. Criar e preencher escopos e vínculos em cópia de teste, com relatórios de registros sem proprietário e relações incompatíveis.
4. Revisar os papéis existentes e validar a conversão das contas com o responsável da instalação.
5. Revogar ou renovar sessões/tokens antigos na ativação do novo modelo; tokens legados não concedem acesso institucional por compatibilidade implícita.
6. Aplicar restrições definitivas somente após conferir os dados convertidos e os caminhos de acesso.
7. Preparar recuperação compatível de versão, banco e arquivos, preservando novas gravações conforme o procedimento definido.

## Testes obrigatórios da próxima entrega

- Conta da escola A não consulta, edita, exclui, vincula ou baixa recursos da B, mesmo alterando IDs na requisição.
- Pessoa presente nas duas escolas mantém seus papéis separados; trocar de contexto não amplia permissões.
- Revogar participação ou atribuição docente bloqueia a próxima operação, inclusive com sessão/token anterior.
- IDs de aluno, professor, turma e disciplina de escolas diferentes não formam relações válidas.
- Listas, buscas, contagens, exportações, arquivos de perfil e documentos não revelam dados externos.
- Cadastro público atual e todas as rotas de compatibilidade têm comportamento definido para o novo modelo; não criam vínculo privilegiado automaticamente.
- Repetir ou concorrer matrículas e convites não gera duplicidade ou uso múltiplo indevido.
- Notas e atividades mantêm funcionamento no contexto correto; registros históricos não são reatribuídos silenciosamente.
- As migrações passam em banco novo e legado sintético, com teste MySQL no CI; recuperação é ensaiada antes de dados reais.

Esses testes serão adicionados à base atual do CI. Os 47 testes já aprovados não comprovam isolamento entre escolas, porque esse recurso ainda não existe.

## Experiência proposta

- Escola ativa e período sempre visíveis no cabeçalho; troca de escola leva a uma página segura e limpa filtros e rascunhos incompatíveis.
- Tela inicial de seleção apenas quando houver mais de uma participação disponível.
- Painel da secretaria com pendências acionáveis: documentação, matrículas e vínculos incompletos.
- Cadastro por etapas curtas, com validação próxima ao campo e revisão antes de concluir matrícula.
- Detalhe da turma com alunos, ofertas e docentes; detalhe do aluno com matrícula e documentos.
- Componentes reutilizáveis de busca, filtros, tabelas, mensagens e formulários, com estados vazio, carregando, falha e acesso revogado.

## Fora desta versão

Folha de ponto, cálculo de folha de pagamento, execução de pagamentos, cobrança das escolas pelo uso da plataforma, integrações bancárias, portal de responsáveis, compartilhamento entre instituições e cursos com videoaulas permanecem no roadmap. Cobrança da plataforma às escolas e mensalidades escolares são domínios diferentes.

## Decisões para a próxima conversa

1. A primeira escola piloto será de ensino básico, cursos livres ou outro segmento? Isso orienta períodos, avaliação e matrícula.
2. Quem poderá cadastrar uma nova escola: somente a administração da plataforma ou também um gestor por solicitação?
3. Haverá um piloto com escolas parceiras antes da abertura comercial? O plano não presume prazo, preço ou capacidade de atendimento.

Nenhuma dessas decisões autoriza automaticamente compartilhamento de dados entre escolas. A prioridade seguinte é fechar o desenho institucional e o primeiro fluxo de secretaria antes de implementar as migrações.
