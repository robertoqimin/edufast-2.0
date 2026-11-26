# Estudo: EducaFast para várias escolas

Data: 04/11/2026. Base examinada: commit `fb840c6`, árvore inicialmente limpa.
Status: proposta para discussão; não autoriza migrations ou ativação de várias escolas.

## Direção de implementação escolhida após o estudo

Em 04/11/2026, o usuário pediu preparar ambientes independentes no mesmo servidor,
controle de tráfego e possibilidade de operação local, nuvem ou híbrida. A base em
[`infra/`](../../infra/README.md) segue aplicação, banco e arquivos por escola,
com gateway comum. Essa é a direção atual da preparação; o banco compartilhado
abaixo permanece uma alternativa estudada, não a implementação escolhida.
O híbrido inicial define um único escritor por escola e recuperação em outro
ambiente; sincronização bidirecional e failover automático não estão implementados.

## Conclusão proposta

Manter uma aplicação modular com uma versão comum para todas as escolas. Começar com banco compartilhado e isolamento institucional explícito somente após converter e testar integralmente os caminhos de acesso. Projetar a possibilidade de mover uma escola ou um grupo de escolas para outra instalação independente quando capacidade, contrato ou risco justificarem.

Essa é uma recomendação para o projeto, não uma descrição de capacidade já entregue. Não há medição nesta análise que permita prometer quantidade de escolas, custo mensal ou disponibilidade.

## Evidência local e limites

- `api/app/models/usuario_model.py`: email único global, `tipo` global, estado e versão de autenticação; relações de aluno/professor com `uselist=False`. Isso precisa evoluir para participação por escola, preservando identidade e revogação.
- Busca textual nos modelos por `escola_id`, `instituicao_id` e `tenant` não encontrou esses identificadores. Existir `escola_model.py` com identidade e políticas não comprova isolamento entre escolas.
- `api/app/database.py`: uma engine; em produção, `init_db()` inspeciona esquema sem executar DDL. Preservar essa garantia.
- `api/app/__init__.py`: fábrica Flask, tratamento de conflitos, CSRF e `/healthz` que consulta banco. Healthcheck não comprova funcionamento dos fluxos acadêmicos.
- `docs/planejamento/PROXIMA_VERSAO.md` já propõe conta global, participação local, integridade institucional e testes de duas escolas.
- `docs/arquitetura/ARQUITETURA.md` contém trechos históricos sobre CDN, criação automática de tabelas e ausência de entidades restauradas. Não usar esses trechos como inventário atual sem revisão específica.

Inspeção estática parcial, sem auditoria completa de autorização, teste de carga, teste de recuperação ou homologação operacional.

## Como sistemas grandes permanecem operacionais

Confiabilidade resulta de controlar falhas e observar o serviço: metas explícitas, implantação gradual, recuperação testada e limites de consumo. Google descreve indicadores e objetivos de serviço e monitoramento de latência, tráfego, erros e saturação. Aplicar esses princípios não exige reproduzir a infraestrutura do Google. Fontes: [objetivos de serviço](https://sre.google/sre-book/service-level-objectives/) e [monitoramento](https://sre.google/sre-book/monitoring-distributed-systems/).

Aplicações replicadas permitem continuar atendendo se um processo falhar, desde que não dependam de arquivos ou estado exclusivos daquele processo. Réplicas no mesmo computador não protegem contra perda do computador. Banco, armazenamento, proxy e filas também podem ser pontos únicos de falha.

Tarefas demoradas, como exportação e envio de mensagens, podem ir para workers com fila persistente. Cada tarefa carrega escola, ator, operação e chave de idempotência; revalida acesso conforme a operação. Tentativas precisam de limite, intervalo crescente, variação aleatória e tratamento de falhas definitivas. A repetição só é segura quando o efeito é idempotente. Fonte: [AWS: limitar tentativas](https://docs.aws.amazon.com/wellarchitected/latest/framework/rel_mitigate_interaction_failure_limit_retries.html).

## Alternativas de isolamento

| Estratégia | Vantagem | Custo e risco | Adequação proposta |
| --- | --- | --- | --- |
| Aplicação e tabelas compartilhadas, `escola_id` | Menor custo inicial e atualizações centralizadas | Uma consulta sem escopo pode expor outra escola; restauração individual exige procedimento próprio | Candidata inicial, com barreiras e testes completos |
| Aplicação compartilhada, banco por escola | Separação dos dados e recuperação individual mais simples | Mais conexões, migrations e backups; roteamento incorreto continua perigoso | Contratos ou necessidades de isolamento superiores |
| Aplicação e banco por escola | Maior separação operacional | Mais recursos e automação; identidade e suporte continuam exigindo cuidado | Exigências específicas ou piloto isolado |
| Grupos independentes de escolas | Limita alcance de falhas e distribui capacidade | Exige diretório de localização e movimentação de escolas | Evolução após comprovar necessidade |

No MySQL, schema e database são equivalentes nesse contexto; não contar schema por escola como uma quarta garantia independente. Banco por escola no mesmo servidor continua compartilhando recursos e domínio de falha do servidor.

Microsoft e AWS descrevem o espectro entre compartilhamento, isolamento e modelos híbridos. A escolha envolve custo, desempenho, operação e alcance de falhas. Fontes: [armazenamento multitenant](https://learn.microsoft.com/en-us/azure/architecture/guide/multitenant/approaches/storage-data), [modelos AWS](https://docs.aws.amazon.com/solutions/multi-tenant-architectures-on-aws/) e [grupos independentes de implantação](https://learn.microsoft.com/azure/architecture/patterns/deployment-stamp).

## Organização dos dados

Cada escola é uma fronteira de autorização. Unidade/campus é subdivisão; uma mantenedora não ganha acesso ao conjunto das escolas implicitamente. Se redes forem necessárias, modelar associação e permissões explícitas.

Separar:

- Identidade global: conta, credenciais, autenticação e recuperação de acesso.
- Participação: conta + escola, estado e papéis locais. Uma pessoa pode ser professora na A e gestora na B.
- Dados locais: aluno, docente, turma, matrícula, período, oferta, notas, documentos, políticas e configurações da escola.
- Operação da plataforma: localização da escola, estado do serviço e configuração operacional, sem acesso acadêmico automático.

Identidade global não significa cadastro acadêmico global. Não unir pessoas por nome nem compartilhar dados entre escolas apenas porque emails coincidem. Convites e vinculação de contas exigem comprovação de identidade.

Regras propostas:

1. Contexto institucional derivado de participação ativa e revalidado pelo servidor. Subdomínio e IDs enviados pelo navegador apenas selecionam contexto; não concedem permissão.
2. Recurso deve pertencer à escola autorizada e atender ao papel e vínculo do ator. Professor precisa da atribuição correspondente; aluno acessa seus próprios registros.
3. Consultas institucionais centralizadas, sem fallback para consulta global quando faltar escola. Cobrir SQL direto, rotas antigas, arquivos, buscas, contagens, exportações e tarefas.
4. Banco impede relações cruzadas com chaves estrangeiras compostas, por exemplo `(escola_id, turma_id)` referenciando uma chave única correspondente na turma. Unicidade de matrícula e códigos definida por escola e período.
5. Índices seguem consultas reais, frequentemente iniciando por escola e filtros relevantes. Validar com planos de execução e carga representativa.
6. Caches e idempotência incluem contexto institucional e, quando necessário, usuário e permissões. Revogação não pode aguardar indefinidamente um cache expirar.
7. Arquivos privados têm proprietário e escola no banco, identificador interno e download autorizado. Prefixo de pasta não substitui autorização. URL temporária, se usada, tem duração e finalidade limitadas.
8. Histórico acadêmico referencia matrícula, oferta, período e versões aplicáveis das regras. Alterar a regra atual não deve recalcular silenciosamente boletins fechados.
9. Gravação e aprovação mantêm transações, controle de versão e idempotência. Não remover as proteções existentes durante a conversão.

## Organização do software

Manter inicialmente o monólito modular: identidade/acesso; instituições; secretaria; acadêmico; cursos; documentos/comunicação; auditoria/privacidade. RH e financeiro permanecem domínios futuros.

Rotas tratam HTTP; serviços executam casos de uso e transações; autorização aplica políticas; repositórios fazem consultas com escopo obrigatório. Evitar que cada rota reinvente autorização e que um módulo altere tabelas de outro sem contrato claro.

Uma base de código e um processo de atualização. Personalização por configuração validada e funcionalidades controladas por escola. Evitar ramificações de código permanentes por cliente. Preservar o protocolo visual e as aprovações atuais.

Extrair serviços distribuídos somente com evidência: necessidade de escala independente, isolamento de falha ou equipe capaz de operar o serviço. Distribuição acrescenta rede, consistência, implantação e diagnóstico.

## Operação, dados e disponibilidade

| Frente | Proposta | Evidência necessária |
| --- | --- | --- |
| Serviço | Definir disponibilidade e latência dos fluxos de login, consulta e gravação | Medição externa e testes sintéticos sem dados reais |
| Recuperação | Definir RPO (perda máxima de dados) e RTO (tempo para recuperar) | Restauração medida de banco e arquivos consistentes |
| Banco | Backups protegidos fora do servidor; avaliar recuperação pontual e alta disponibilidade | Recuperar em ambiente separado; simular falha e conferir integridade |
| Aplicação | Healthchecks, reinício, limites de conexões e eventual balanceamento | Falha de processo e de host testadas separadamente |
| Capacidade | Paginação, limites por escola, exportações controladas e quotas | Pico de matrículas/notas sem bloquear outras escolas |
| Entrega | Imagem versionada, piloto, observação e expansão gradual | Testes e rollback compatível com o esquema |
| Incidentes | Alertas acionáveis, responsável e procedimento de resposta | Exercício de incidente e registro de recuperação |

Replicação não substitui backup: exclusões e corrupção lógica podem ser replicadas. Recuperar uma escola em banco compartilhado normalmente exige restaurar uma cópia isolada e selecionar seus registros e arquivos com validação de dependências; não restaurar o banco inteiro sobre outras escolas ativas. Fonte: [AWS: exercícios de restauração](https://docs.aws.amazon.com/wellarchitected/2024-06-27/framework/rel_backing_up_data_periodic_recovery_testing_data.html).

Logs de diagnóstico devem conter identificadores de requisição e contexto suficiente, sem senhas, tokens, documentos ou conteúdo acadêmico desnecessário. Auditoria é registro próprio de quem fez o quê, em qual escola, quando e com qual resultado, com acesso e retenção controlados.

Definir inventário, finalidade, retenção, exclusão/exportação e acesso de suporte antes de dados reais. Dados de crianças e documentos merecem avaliação específica de privacidade. Este estudo não determina conformidade jurídica nem prazos legais de retenção.

## Caminho de evolução

1. Inventariar todas as entradas e classificar dados globais e institucionais; atualizar documentação histórica.
2. Definir escola, unidade, participação e papéis; registrar decisão de isolamento e necessidades do piloto.
3. Revisar contratos e testes de duas escolas antes de implementar. Incluir usuário nas duas com papéis distintos e revogação.
4. Preparar migrations e conversão com relatório de dados sem proprietário; revisão humana antes de qualquer execução. Não inferir propriedade nem atribuições históricas.
5. Converter integralmente consultas, gravações, aprovações, arquivos e trabalhos; negar entradas institucionais sem contexto.
6. Ensaiar migração e recuperação em ambientes descartáveis autorizados, com dados sintéticos. Validar MySQL, não apenas SQLite.
7. Executar carga com distribuição e picos plausíveis; medir erros, p95/p99, conexões, locks, CPU, memória, disco e fila. Registrar dataset e ambiente.
8. Fazer piloto controlado; habilitar múltiplas escolas somente após comprovar isolamento em todas as entradas e recuperação.
9. Replicar aplicação ou dividir grupos quando medições e objetivos justificarem; manter opção de ambiente dedicado.

## Decisões ainda abertas

Tipo e porte das escolas; usuários simultâneos e picos; orçamento; equipe de operação; disponibilidade e recuperação esperadas; necessidade de redes/campi; condições contratuais de isolamento; regras de matrícula e avaliação; política de suporte e dados.

Não dimensionar infraestrutura só por número de escolas: simultaneidade, consultas, arquivos e horários de pico determinam a carga. Um piloto pequeno em servidor único pode ser uma etapa deliberada, mas mantém indisponibilidade em falha desse servidor.
