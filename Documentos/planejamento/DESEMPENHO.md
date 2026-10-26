# Desempenho em hardware modesto

[Próxima versão](PROXIMA_VERSAO.md) · [Roadmap](ROADMAP.md)

Requisito de produto acrescentado em 26/10/2026: o EduFast deve oferecer uma experiência ágil em equipamentos modestos e controlar o custo de infraestrutura para atender várias escolas. Este documento é um plano; ainda não há benchmark que comprove essas metas.

## Dois lados da experiência

1. **Equipamento da escola:** manter navegação, busca e preenchimento fluidos em computadores antigos e celulares de entrada, inclusive com conexão limitada.
2. **Servidor:** manter tempos de resposta previsíveis e consumo controlado de CPU, memória e banco, sem uma escola prejudicar desproporcionalmente as demais.

Servidor rápido não elimina processamento excessivo no navegador. Um frontend leve também não resolve consultas lentas ou filas de requisições. As medições precisam separar essas causas.

## Perfis iniciais de ensaio

Estes perfis são hipóteses para começar os testes, não requisitos mínimos homologados nem orientação de compra de servidor.

| Perfil | Condição inicial proposta |
| --- | --- |
| Computador modesto | Dois núcleos, 4 GB de RAM, vídeo integrado e navegador atualizado compatível |
| Celular de entrada | Android, 2–3 GB de RAM; modelo e versão registrados na execução |
| Rede limitada | 5 Mbit/s de download, 1 Mbit/s de upload e 150 ms de latência adicionada |
| Servidor de ensaio | Orçamento total de 2 vCPU e 2 GB de RAM para proxy, app e banco; disco e arquitetura registrados |

Aplicar limites agregados e por serviço, registrar o consumo e verificar viabilidade. Se esse orçamento não comportar a carga proposta, documentar o limite real e revisar o perfil. Não mascarar falta de memória com reinicializações ou swap excessivo.

Simulação de CPU/rede ajuda na repetibilidade, mas não substitui uma rodada em equipamento real. Registrar modelos, navegador e uso de cache. Confirmar esses perfis com a escola piloto.

## Metas iniciais propostas

Metas para discussão e revisão após a primeira linha de base. Não são SLA comercial ou desempenho medido da versão atual.

| Indicador | Meta inicial | Como avaliar |
| --- | --- | --- |
| Conteúdo principal visível | Até 3 s em pelo menos 75% das navegações do perfil de cliente/rede definido | Medir LCP em várias execuções, separando cache frio e quente |
| Resposta visual a interação | Até 200 ms em pelo menos 75% das interações representativas | Medir interação até próxima pintura, com aparelho/CPU documentado |
| API de consulta comum | p95 até 500 ms | Medir no perfil de servidor, com carga e dados definidos, sem incluir latência do cliente |
| Gravação comum | p95 até 1 s | Criar matrícula/cadastro com validações; excluir upload e exportações do grupo |
| Recursos iniciais | Até 300 KiB transferidos de HTML + CSS + JS comprimidos nas telas comuns | Somar recursos próprios e terceiros; imagens e documentos têm medição separada |
| Confiabilidade sob carga | Nenhum erro inesperado, acesso cruzado ou reinício por falta de memória no ensaio | Distinguir erros de validação esperados de falhas do serviço |

Para cada percentil, registrar número de amostras, duração e distribuição; médias isoladas não demonstram cumprimento da meta. Respostas 200 sem completar a tarefa também não contam como sucesso funcional.

## Cenário reproduzível

- Massa sintética inicial: 5 escolas, 1.000 alunos por escola e volume de turmas, matrículas, docentes e documentos registrado no gerador. Não usar dados reais.
- Aumentar a massa posteriormente para verificar crescimento de consultas e paginação; nenhuma quantidade representa capacidade comercial garantida.
- Exercitar separadamente 1, 10 e 25 sessões simultâneas, distribuídas entre escolas e com pausas entre ações. Registrar também requisições por segundo: sessões não equivalem a requisições simultâneas.
- Aumentar a carga gradualmente, medir aquecimento e executar pelo menos 10 minutos de observação por patamar após aquecimento, com amostras suficientes para os percentis.
- Mistura inicial proposta: 70% consultas, 20% buscas/paginação e 10% gravações. Login, upload e exportações têm cenários próprios.
- Executar uma rodada em que uma escola gera carga maior e verificar o efeito nas demais, preservando autorização e integridade.
- Registrar commit, imagem, hardware, limites Docker, banco, massa, concorrência, tempos, erros, CPU, memória e uso de disco. Repetir a comparação no mesmo ambiente.

Até a implementação do modelo de várias escolas, medir uma instalação única e identificar a limitação. O teste institucional completo depende das migrações e regras de isolamento.

## Direção de implementação

### Interface

- Preservar renderização HTML no servidor e avaliar o JavaScript necessário em cada tela.
- Compilar CSS na construção da imagem e servir arquivos estáticos versionados; retirar a compilação de Tailwind no navegador da entrega de produção.
- Carregar scripts por necessidade e medir o custo do shell React antes de decidir mantê-lo, reduzi-lo ou substituí-lo.
- Paginar listas no servidor; iniciar com 25 registros por página e limite máximo explícito. Não enviar todos os alunos para filtrar no navegador.
- Redimensionar imagens de perfil e carregar imagens fora da área visível sob demanda.
- Evitar efeitos e atualizações contínuas que consumam CPU sem ajudar a tarefa. Manter acessibilidade e feedback mesmo em uma interface leve.

### Aplicação e banco

- Medir número e duração de consultas dos fluxos críticos; corrigir consultas repetidas e carregamento desnecessário de relações conforme evidência.
- Projetar índices a partir das buscas reais e do escopo institucional, verificando planos de execução e custo de gravação.
- Buscar somente campos e registros necessários; aplicar paginação, limites de upload e limites de exportação.
- Ajustar workers, threads e pool do banco ao orçamento medido. O único worker atual evita inicialização concorrente do esquema legado; sua alteração depende de separar migrações da inicialização e validar conexões/memória.
- Usar cache apenas onde houver ganho medido, com chave que inclua escola e demais dimensões de acesso, além de invalidação definida. Não reutilizar conteúdo privado entre usuários.
- Avaliar processamento em segundo plano para relatórios pesados depois de medir o problema, incluindo o custo adicional do executor e a preservação do contexto da escola.

## Primeiras tarefas

| Ordem | Tarefa | Entrega |
| --- | --- | --- |
| 1 | Inventariar recursos e consultas de login, painel, alunos e turmas | Relatório inicial com tamanhos, tempos e consultas por tela |
| 2 | Criar massa sintética e executor com limites reproduzíveis | Comando de benchmark e resultados vinculados ao commit |
| 3 | Medir a versão atual antes de alterações | Linha de base documentada, com gargalos observados |
| 4 | Substituir Tailwind em runtime por CSS compilado | Comparação visual e de recursos com as telas existentes |
| 5 | Priorizar consultas, paginação e JavaScript conforme as medições | Antes/depois no mesmo ambiente e testes funcionais preservados |
| 6 | Adicionar verificações de tamanho e regressão de desempenho ao CI | Limites estáveis e relatórios; testes de carga em ambiente controlado |

Encontrado no código atual: templates usam `cdn.tailwindcss.com`, e o runtime compartilhado carrega React/ReactDOM via CDN. São candidatos a avaliação, não uma demonstração de que sejam o maior gargalo. O Tailwind informa que seu Play CDN é destinado a desenvolvimento, e orienta gerar CSS estático para produção.

## Relação com o CI e a liberação

Os testes funcionais já existentes não comprovam desempenho. Começar com relatórios de desempenho, estabelecer variabilidade e depois definir bloqueios de regressão. Não impor um percentual arbitrário de melhoria nem bloquear releases por ruído de runner compartilhado.

O CI pode verificar tamanho dos recursos e limites de consultas de forma determinística. Carga, p95 e memória precisam de ambiente com recursos e concorrência controlados. Toda otimização deve preservar isolamento entre escolas, permissões, integridade, acessibilidade e recuperação de erros.

## Referências

- [Tailwind: CSS estático e uso do Play CDN](https://v3.tailwindcss.com/docs/upgrade-guide)
- [MDN: definir orçamentos de desempenho a partir dos usuários](https://developer.mozilla.org/en-US/docs/Web/Performance/Guides/Performance_budgets)
- [Microsoft Edge: investigar desempenho e simular CPU mais lenta](https://learn.microsoft.com/microsoft-edge/devtools/performance/)
